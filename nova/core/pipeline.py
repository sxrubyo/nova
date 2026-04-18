"""Core evaluation pipeline."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from nova.core.decision_engine import DecisionEngine
from nova.core.intent_analyzer import IntentAnalyzer
from nova.core.risk_engine import RiskEngine
from nova.ledger.intent_ledger import IntentLedger
from nova.memory.importance_scorer import ImportanceScorer
from nova.memory.memory_engine import MemoryEngine
from nova.observability.logger import get_logger
from nova.observability.metrics import MetricsCollector
from nova.security.anomaly_detector import AnomalyDetector, AnomalyEvent
from nova.security.burst_detector import BurstDetector
from nova.security.loop_detector import LoopDetector
from nova.security.rule_validator import RuleValidator
from nova.security.sensitivity_scanner import SensitivityScanner
from nova.storage.database import session_scope
from nova.storage.models import EvaluationModel
from nova.storage.repositories.evaluation_repo import EvaluationRepository
from nova.types import Decision, DecisionAction, EvaluationContext, EvaluationRequest, EvaluationResult, IntentAnalysis, RiskFactor, RiskLevel, RiskScore, RuleValidationResult, SensitivityResult, WorkspaceRules, WorkspaceThresholds
from nova.utils.crypto import generate_id


class EvaluationPipeline:
    """Sequential evaluation flow with early exits for hard violations."""

    def __init__(
        self,
        *,
        agent_registry: object,
        quota_manager: object,
        intent_analyzer: IntentAnalyzer,
        rule_validator: RuleValidator,
        sensitivity_scanner: SensitivityScanner,
        loop_detector: LoopDetector,
        burst_detector: BurstDetector,
        risk_engine: RiskEngine,
        decision_engine: DecisionEngine,
        action_executor: object,
        memory: MemoryEngine,
        ledger: IntentLedger,
        gateway: object,
        metrics: MetricsCollector,
        anomaly_detector: AnomalyDetector,
    ) -> None:
        self.agent_registry = agent_registry
        self.quota_manager = quota_manager
        self.intent_analyzer = intent_analyzer
        self.rule_validator = rule_validator
        self.sensitivity_scanner = sensitivity_scanner
        self.loop_detector = loop_detector
        self.burst_detector = burst_detector
        self.risk_engine = risk_engine
        self.decision_engine = decision_engine
        self.action_executor = action_executor
        self.memory = memory
        self.ledger = ledger
        self.gateway = gateway
        self.metrics = metrics
        self.anomaly_detector = anomaly_detector
        self.importance = ImportanceScorer()
        self.logger = get_logger("nova.pipeline")

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        eval_id = generate_id("eval")
        start_time = time.monotonic()
        context = EvaluationContext(eval_id=eval_id, request=request)

        try:
            agent = await self.agent_registry.get(request.agent_id)
            if not agent or agent.status.value != "active":
                return self._blocked_result(
                    context=context,
                    code="AGENT_INVALID",
                    reason="Agent not found or inactive",
                    risk_value=90,
                    started_at=start_time,
                )

            if not await self.quota_manager.check(agent.workspace_id):
                return self._blocked_result(
                    context=context,
                    code="QUOTA_EXCEEDED",
                    reason="Monthly evaluation quota exceeded",
                    risk_value=85,
                    started_at=start_time,
                )

            if not await self._check_agent_quota(agent.id, agent.metadata):
                return self._blocked_result(
                    context=context,
                    code="AGENT_DAILY_QUOTA_EXCEEDED",
                    reason="Agent-specific daily quota exceeded",
                    risk_value=82,
                    started_at=start_time,
                )

            intent = await self.intent_analyzer.analyze(
                action=request.action,
                payload=request.payload,
                agent_context=agent,
            )
            context.intent = intent

            workspace_rules = self._resolve_rules(agent)
            rule_result = await self.rule_validator.validate(intent=intent, agent=agent, workspace_rules=workspace_rules)
            if rule_result.violated:
                context.violations.append(rule_result)
                if rule_result.severity == "critical":
                    return self._blocked_result(
                        context=context,
                        code="RULE_VIOLATION",
                        reason=f"Critical rule violated: {rule_result.rule_name}",
                        risk_value=95,
                        started_at=start_time,
                    )

            sensitivity = await self.sensitivity_scanner.scan(
                payload=request.payload,
                patterns=["api_key", "password", "ssn", "credit_card", "email_pii", "phone", "address", "jwt_token"],
            )
            context.sensitivity = sensitivity

            loop_detected = await self.loop_detector.check(
                agent_id=request.agent_id,
                current_action=request.action,
                similarity_threshold=0.85,
            )
            if loop_detected.is_loop:
                context.anomalies.append("loop_detected")

            burst_detected = await self.burst_detector.check(
                agent_id=request.agent_id,
                window_seconds=60,
                threshold=50,
            )
            if burst_detected.is_burst:
                context.anomalies.append("burst_detected")

            agent_history = await self.memory.get_recent(agent.id)
            workspace_risk_profile = agent.workspace.risk_profile if agent.workspace else type("Profile", (), {"business_hours_start": 8, "business_hours_end": 18, "timezone": "UTC", "sensitivity_bias": 0})()
            risk_score = await self.risk_engine.calculate(
                intent=intent,
                rule_result=rule_result,
                sensitivity=sensitivity,
                loop_detected=loop_detected,
                burst_detected=burst_detected,
                agent_history=agent_history,
                workspace_risk_profile=workspace_risk_profile,
                agent_evaluation_count=agent.evaluation_count,
            )
            context.risk_score = risk_score

            decision = await self.decision_engine.decide(
                risk_score=risk_score,
                context=context,
                thresholds=self._resolve_thresholds(agent),
            )
            context.decision = decision

            ledger_entry = await self.ledger.record(
                eval_id=eval_id,
                agent_id=request.agent_id,
                workspace_id=agent.workspace_id,
                intent=intent,
                risk_score=risk_score,
                decision=decision,
                sensitivity_flags=sensitivity.flags,
                anomalies=context.anomalies,
                timestamp=datetime.now(timezone.utc),
                payload=request.payload,
            )

            execution_result = None
            if decision.action == DecisionAction.ALLOW:
                execution_result = await self.action_executor.execute(
                    intent=intent,
                    provider=self.gateway.get_optimal_provider(intent),
                    payload=request.payload,
                )
                await self.ledger.record_completion(eval_id=eval_id, result=execution_result)

            importance = self.importance.score(risk_score, decision)
            await self.memory.store(
                agent_id=request.agent_id,
                workspace_id=agent.workspace_id,
                event_type="evaluation",
                data={
                    "eval_id": eval_id,
                    "action": request.action,
                    "risk_score": risk_score.value,
                    "decision": decision.action.value,
                },
                importance=importance,
            )

            await self.quota_manager.increment(agent.workspace_id)
            duration_ms = (time.monotonic() - start_time) * 1000
            await self.metrics.record_evaluation(
                duration_ms=duration_ms,
                risk_score=risk_score.value,
                decision=decision.action.value,
                provider=intent.target_provider or getattr(execution_result, "provider", None),
            )
            await self.anomaly_detector.submit(
                AnomalyEvent(
                    agent_id=agent.id,
                    workspace_id=agent.workspace_id,
                    action=request.action,
                    decision=decision.action.value,
                    risk_score=risk_score.value,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            await self._persist_evaluation(
                eval_id=eval_id,
                agent_id=agent.id,
                workspace_id=agent.workspace_id,
                action=request.action,
                payload=request.payload,
                decision=decision.action.value,
                risk_score=risk_score.value,
                status="completed",
                duration_ms=duration_ms,
                provider=intent.target_provider or getattr(execution_result, "provider", None),
            )

            return EvaluationResult(
                eval_id=eval_id,
                status="completed",
                decision=decision,
                risk_score=risk_score,
                intent_analysis=intent,
                sensitivity=sensitivity,
                anomalies=context.anomalies,
                ledger_hash=ledger_entry.hash,
                execution_result=execution_result,
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as exc:  # noqa: BLE001
            await self.ledger.record_error(eval_id, str(exc))
            self.logger.error("evaluation_failed", eval_id=eval_id, error=str(exc))
            raise

    async def _check_agent_quota(self, agent_id: str, metadata: dict[str, object]) -> bool:
        quota = dict(metadata or {}).get("quota") or {}
        max_per_day = int(quota.get("max_evaluations_per_day") or 0)
        if max_per_day <= 0:
            return True
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        async with session_scope() as session:
            repo = EvaluationRepository(session)
            count = await repo.count_since(agent_id, since)
        return count < max_per_day

    def _resolve_rules(self, agent: object) -> WorkspaceRules:
        workspace_rules = agent.workspace.rules if agent.workspace else WorkspaceRules()
        metadata = dict(getattr(agent, "metadata", {}) or {})
        agent_rules = dict(metadata.get("permissions") or {})
        can_do = list(dict.fromkeys([*workspace_rules.can_do, *list(getattr(agent, "permissions", []) or []), *agent_rules.get("can_do", [])]))
        cannot_do = list(dict.fromkeys([*workspace_rules.cannot_do, *agent_rules.get("cannot_do", [])]))
        return WorkspaceRules(can_do=can_do, cannot_do=cannot_do)

    def _resolve_thresholds(self, agent: object) -> WorkspaceThresholds:
        workspace_thresholds = agent.workspace.thresholds if agent.workspace else WorkspaceThresholds()
        metadata = dict(getattr(agent, "metadata", {}) or {})
        overrides = dict(metadata.get("risk_thresholds") or {})
        return WorkspaceThresholds(
            auto_allow=int(overrides.get("auto_allow", workspace_thresholds.auto_allow)),
            escalate=int(overrides.get("escalate", workspace_thresholds.escalate)),
            auto_block=int(overrides.get("auto_block", workspace_thresholds.auto_block)),
        )

    async def _persist_evaluation(
        self,
        *,
        eval_id: str,
        agent_id: str,
        workspace_id: str,
        action: str,
        payload: dict[str, object],
        decision: str,
        risk_score: int,
        status: str,
        duration_ms: float,
        provider: str | None,
    ) -> None:
        async with session_scope() as session:
            repo = EvaluationRepository(session)
            await repo.create(
                EvaluationModel(
                    id=eval_id,
                    agent_id=agent_id,
                    workspace_id=workspace_id,
                    action=action,
                    payload=payload,
                    status=status,
                    decision=decision,
                    risk_score=risk_score,
                    duration_ms=duration_ms,
                    provider=provider,
                )
            )

    def _blocked_result(
        self,
        *,
        context: EvaluationContext,
        code: str,
        reason: str,
        risk_value: int,
        started_at: float,
    ) -> EvaluationResult:
        intent = context.intent or IntentAnalysis(
            action_type=context.request.action,
            target=context.request.action,
            target_provider=None,
            parameters=context.request.payload,
            inferred_purpose=reason,
            confidence=1.0,
            raw_action=context.request.action,
        )
        sensitivity = context.sensitivity or SensitivityResult()
        level = RiskLevel.CRITICAL if risk_value >= 80 else RiskLevel.HIGH
        risk_score = context.risk_score or RiskScore(
            value=risk_value,
            level=level,
            factors=[RiskFactor(name=code.lower(), impact=risk_value, detail=reason)],
            breakdown={"rule_layer": risk_value, "sensitivity_layer": 0, "behavior_layer": 0},
            recommendations=["Review agent status or workspace quota before retrying."],
        )
        decision = Decision(action=DecisionAction.BLOCK, reason=reason)
        return EvaluationResult(
            eval_id=context.eval_id,
            status="blocked",
            decision=decision,
            risk_score=risk_score,
            intent_analysis=intent,
            sensitivity=sensitivity,
            anomalies=list(context.anomalies),
            ledger_hash=None,
            execution_result=None,
            duration_ms=(time.monotonic() - started_at) * 1000,
            timestamp=datetime.now(timezone.utc),
            metadata={"code": code},
        )
