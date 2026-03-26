"""Nova kernel orchestration."""

from __future__ import annotations

import asyncio
import resource
import sys
import time
from datetime import datetime, timezone
from typing import Any

import uvicorn

from nova.config import NovaConfig
from nova.constants import NOVA_VERSION
from nova.core.action_executor import ActionExecutor
from nova.core.decision_engine import DecisionEngine
from nova.core.intent_analyzer import IntentAnalyzer
from nova.core.pipeline import EvaluationPipeline
from nova.core.risk_engine import RiskEngine
from nova.ledger.intent_ledger import IntentLedger
from nova.memory.memory_engine import MemoryEngine
from nova.observability.alerts import AlertManager
from nova.observability.logger import configure_logging, get_logger
from nova.observability.metrics import MetricsCollector
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
        self.alerts = AlertManager()
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
        self._startup_time = time.time()
        self._initialized = True

    async def start(self) -> None:
        await self.initialize()
        from nova.api.server import create_app
        from nova.bridge.bridge_server import NovaBridge
        from nova.utils.formatting import banner

        self._bridge = NovaBridge(self, self.config)
        await self._bridge.start()
        app = create_app(self)
        self.logger.info("kernel_started", version=self.config.version, api_port=self.config.api_port, bridge_port=self.config.bridge_port)
        print(banner())
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
        await self.gateway.stop()
        await self.anomaly_detector.stop()
        await dispose_engine()
        self.logger.info("kernel_shutdown_complete")

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        return await self.pipeline.evaluate(request)

    async def get_status(self) -> SystemStatus:
        await self.initialize()
        uptime = time.time() - (self._startup_time or time.time())
        active_agents = 0
        default_workspace = await self.workspace_manager.ensure_default_workspace()
        active_agents = len(await self.agent_registry.list(default_workspace.id))
        usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_mb = usage_kb / 1024 if sys.platform != "darwin" else usage_kb / (1024 * 1024)
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
