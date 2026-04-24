"""Nova kernel orchestration."""

from __future__ import annotations

import asyncio
import errno
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
from nova.nova_types import EvaluationRequest, EvaluationResult, SystemStatus
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
        self._discovery_task: asyncio.Task[Any] | None = None

    async def initialize(self) -> None:
        if self._initialized:
            return
        await init_database(self.config)
        await self.workspace_manager.ensure_default_workspace()
        await self.anomaly_detector.start()
        await self.gateway.start()
        self._startup_time = time.time()
        self._initialized = True

    def start_discovery_background(self) -> None:
        if not self.config.discovery_enabled or self._discovery_task is not None:
            return

        async def _runner() -> None:
            try:
                await self.discovery.start()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.logger.warning("discovery_start_failed", error=str(exc))

        self._discovery_task = asyncio.create_task(_runner(), name="nova-discovery-start")
        self._background_tasks.append(self._discovery_task)

    async def start(self, *, open_browser: bool = True) -> None:
        await self.initialize()
        from nova.api.server import create_app
        from nova.bridge.bridge_server import NovaBridge
        from nova.utils.browser import bind_api_url, bind_bridge_url, local_dashboard_url, local_docs_url, open_dashboard_when_ready, open_url
        from nova.utils.formatting import existing_runtime_banner, startup_banner

        existing_runtime = await self._probe_existing_runtime_status()
        if existing_runtime is not None:
            print(
                existing_runtime_banner(
                    api_url=bind_api_url(self.config),
                    dashboard_url=local_dashboard_url(self.config),
                    docs_url=local_docs_url(self.config),
                    bridge_url=bind_bridge_url(self.config),
                    version=str(existing_runtime.get("version") or self.config.version),
                    active_agents=existing_runtime.get("active_agents"),
                    uptime_seconds=existing_runtime.get("uptime_seconds"),
                )
            )
            if open_browser:
                open_url(local_dashboard_url(self.config))
            return

        self._bridge = NovaBridge(self, self.config)
        try:
            await self._bridge.start()
        except OSError as exc:
            if await self._handle_address_in_use(exc, open_browser=open_browser):
                return
            raise RuntimeError(self._port_conflict_message("bridge", self.config.bridge_port)) from exc
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
        self.start_discovery_background()
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
        except OSError as exc:
            if await self._handle_address_in_use(exc, open_browser=open_browser):
                return
            raise RuntimeError(self._port_conflict_message("api", self.config.api_port)) from exc
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

    async def _probe_existing_runtime_status(self) -> dict[str, Any] | None:
        import httpx

        status_url = f"http://127.0.0.1:{self.config.api_port}/api/status"
        try:
            async with httpx.AsyncClient(timeout=1.5, follow_redirects=True) as client:
                response = await client.get(status_url)
        except Exception:
            return None

        if response.status_code != 200:
            return None

        try:
            payload = response.json()
        except ValueError:
            return None

        if not isinstance(payload, dict):
            return None
        if not payload.get("version") and payload.get("status") not in {"operational", "degraded", "starting"}:
            return None
        return payload

    async def _handle_address_in_use(self, exc: OSError, *, open_browser: bool) -> bool:
        if not _is_address_in_use(exc):
            return False

        existing_runtime = await self._probe_existing_runtime_status()
        if existing_runtime is None:
            return False

        from nova.utils.browser import bind_api_url, bind_bridge_url, local_dashboard_url, local_docs_url, open_url
        from nova.utils.formatting import existing_runtime_banner

        print(
            existing_runtime_banner(
                api_url=bind_api_url(self.config),
                dashboard_url=local_dashboard_url(self.config),
                docs_url=local_docs_url(self.config),
                bridge_url=bind_bridge_url(self.config),
                version=str(existing_runtime.get("version") or self.config.version),
                active_agents=existing_runtime.get("active_agents"),
                uptime_seconds=existing_runtime.get("uptime_seconds"),
            )
        )
        if open_browser:
            open_url(local_dashboard_url(self.config))
        return True

    def _port_conflict_message(self, target: str, port: int) -> str:
        return (
            f"Nova could not start because the {target} port {port} is already in use. "
            f"If Nova is already running, open http://127.0.0.1:{self.config.api_port}/ . "
            "Otherwise free the port or start with explicit --port/--bridge-port values."
        )

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


def _is_address_in_use(exc: OSError) -> bool:
    return getattr(exc, "errno", None) in {errno.EADDRINUSE, 48, 10048}
