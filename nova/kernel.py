"""Nova kernel orchestration."""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timezone
from typing import Any

import uvicorn

try:
    import resource
except ModuleNotFoundError:  # pragma: no cover - Windows compatibility
    resource = None

from nova.config import NovaConfig
from nova.constants import NOVA_VERSION
from nova.core.action_executor import ActionExecutor
from nova.core.decision_engine import DecisionEngine
from nova.core.intent_analyzer import IntentAnalyzer
from nova.core.pipeline import EvaluationPipeline
from nova.discovery.discovery_engine import DiscoveryEngine
from nova.core.risk_engine import RiskEngine
from nova.ledger.intent_ledger import IntentLedger
from nova.memory.memory_engine import MemoryEngine
from nova.observability.alerts import AlertManager
from nova.observability.logger import configure_logging, get_logger
from nova.observability.metrics import MetricsCollector
from nova.realtime.event_bus import RuntimeEventBus
from nova.security.anomaly_detector import AnomalyDetector
from nova.security.burst_detector import BurstDetector
from nova.security.loop_detector import LoopDetector
from nova.security.rule_validator import RuleValidator
from nova.security.sensitivity_scanner import SensitivityScanner
from nova.storage.database import dispose_engine, init_database
from nova.types import EvaluationRequest, EvaluationResult, SystemStatus
from nova.workspace.agent_registry import AgentRegistry
from nova.workspace.quota_manager import QuotaManager
from nova.workspace.workspace_manager import WorkspaceManager


class NovaKernel:
    """The heart of Nova OS. Initializes and coordinates all subsystems."""

    def __init__(self, config: NovaConfig | None = None) -> None:
        self.config = config or NovaConfig()
        self.config.ensure_directories()
        self.logger = configure_logging(self.config)
        self.events = RuntimeEventBus(limit=300)
        self.alerts = AlertManager(event_bus=self.events)
        self.metrics = MetricsCollector()
        self.workspace_manager = WorkspaceManager(self.config)
        self.agent_registry = AgentRegistry()
        self.quota_manager = QuotaManager()
        self.intent_analyzer = IntentAnalyzer()
        self.risk_engine = RiskEngine()
        self.decision_engine = DecisionEngine()
        self.memory = MemoryEngine(self.config)
        self.ledger = IntentLedger()
        self.gateway = __import__("nova.gateway.router", fromlist=["GatewayRouter"]).GatewayRouter(self.config, self.alerts)
        self.loop_detector = LoopDetector()
        self.burst_detector = BurstDetector()
        self.rule_validator = RuleValidator()
        self.sensitivity_scanner = SensitivityScanner()
        self.anomaly_detector = AnomalyDetector(self.config, self.alerts)
        self.action_executor = ActionExecutor(self.config, self.gateway)
        self.discovery = DiscoveryEngine(
            kernel=self,
            event_bus=self.events,
            scan_ttl_seconds=self.config.discovery_scan_ttl_seconds,
            watch_interval_seconds=self.config.discovery_watch_interval_seconds,
        )
        self.pipeline = EvaluationPipeline(
            agent_registry=self.agent_registry,
            quota_manager=self.quota_manager,
            intent_analyzer=self.intent_analyzer,
            rule_validator=self.rule_validator,
            sensitivity_scanner=self.sensitivity_scanner,
            loop_detector=self.loop_detector,
            burst_detector=self.burst_detector,
            risk_engine=self.risk_engine,
            decision_engine=self.decision_engine,
            action_executor=self.action_executor,
            memory=self.memory,
            ledger=self.ledger,
            gateway=self.gateway,
            metrics=self.metrics,
            anomaly_detector=self.anomaly_detector,
        )
        self._startup_time: float | None = None
        self._initialized = False
        self._api_server: uvicorn.Server | None = None
        self._bridge: Any = None
        self._background_tasks: list[asyncio.Task[Any]] = []

    async def initialize(self) -> None:
        if self._initialized:
            return
        await init_database(self.config)
        await self.workspace_manager.ensure_default_workspace()
        await self.anomaly_detector.start()
        await self.gateway.start()
        if self.config.discovery_enabled:
            await self.discovery.start()
        self._startup_time = time.time()
        self._initialized = True

    async def start(self, *, open_browser: bool = True) -> None:
        await self.initialize()
        from nova.api.server import create_app
        from nova.bridge.bridge_server import NovaBridge
        from nova.utils.browser import bind_api_url, bind_bridge_url, local_dashboard_url, local_docs_url, open_dashboard_when_ready
        from nova.utils.formatting import startup_banner

        self._bridge = NovaBridge(self, self.config)
        await self._bridge.start()
        app = create_app(self, serve_frontend=True)
        self.logger.info("kernel_started", version=self.config.version, api_port=self.config.api_port, bridge_port=self.config.bridge_port)
        print(
            startup_banner(
                api_url=bind_api_url(self.config),
                dashboard_url=local_dashboard_url(self.config),
                docs_url=local_docs_url(self.config),
                bridge_url=bind_bridge_url(self.config),
                version=self.config.version,
            )
        )
        if open_browser:
            self._background_tasks.append(
                asyncio.create_task(
                    open_dashboard_when_ready(self.config),
                    name="nova-open-dashboard",
                )
            )
        self._api_server = uvicorn.Server(
            uvicorn.Config(
                app,
                host=self.config.host,
                port=self.config.api_port,
                log_level=self.config.log_level.lower(),
            )
        )
        try:
            await self._api_server.serve()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        if self._bridge is not None:
            await self._bridge.stop()
        for task in self._background_tasks:
            task.cancel()
        if self.config.discovery_enabled:
            await self.discovery.stop()
        await self.gateway.stop()
        await self.anomaly_detector.stop()
        await dispose_engine()
        self.logger.info("kernel_shutdown_complete")

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        result = await self.pipeline.evaluate(request)
        await self.events.publish(
            "evaluation_completed",
            {
                "eval_id": result.eval_id,
                "agent_id": request.agent_id,
                "risk_score": result.risk_score.value,
                "decision": result.decision.action.value,
                "duration_ms": round(result.duration_ms, 2),
                "status": result.status,
            },
        )
        return result

    async def get_status(self) -> SystemStatus:
        await self.initialize()
        uptime = time.time() - (self._startup_time or time.time())
        active_agents = 0
        default_workspace = await self.workspace_manager.ensure_default_workspace()
        active_agents = len(await self.agent_registry.list(default_workspace.id))
        memory_mb = _memory_usage_mb()
        return SystemStatus(
            status="operational",
            version=NOVA_VERSION,
            uptime_seconds=uptime,
            memory_usage_mb=round(memory_mb, 2),
            active_agents=active_agents,
            subsystems={
                "kernel": "ok",
                "gateway": "ok",
                "ledger": "ok",
                "memory": "ok",
                "security": "ok",
                "bridge": "ok" if self._bridge is not None else "idle",
                "api": "ok" if self._api_server is not None else "idle",
                "discovery": "ok" if self.discovery.last_scan_at else "idle",
            },
            providers=[provider.snapshot() for provider in self.gateway.providers.values()],
            timestamp=datetime.now(timezone.utc),
        )


_DEFAULT_KERNEL: NovaKernel | None = None


def get_kernel(config: NovaConfig | None = None) -> NovaKernel:
    """Return the default singleton kernel."""

    global _DEFAULT_KERNEL
    if _DEFAULT_KERNEL is None:
        _DEFAULT_KERNEL = NovaKernel(config)
    return _DEFAULT_KERNEL


def _memory_usage_mb() -> float:
    """Return resident memory usage across supported host platforms."""

    if resource is not None:
        usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return usage_kb / 1024 if sys.platform != "darwin" else usage_kb / (1024 * 1024)

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            process = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                process,
                ctypes.byref(counters),
                counters.cb,
            )
            if ok:
                return counters.WorkingSetSize / (1024 * 1024)
        except Exception:
            return 0.0

    return 0.0
