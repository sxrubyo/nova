"""Codex CLI connector."""

from __future__ import annotations

import time
import tomllib
from pathlib import Path

from nova.discovery.agent_manifest import AgentLogEntry, AgentTask, ConnectionResult, DiscoveredAgent, HealthStatus, TaskResult
from nova.discovery.connectors.base_connector import BaseAgentConnector

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency on some hosts
    psutil = None


class CodexConnector(BaseAgentConnector):
    """Wrap Codex CLI as a controllable subprocess-backed agent."""

    connector_name = "codex"

    async def connect(self, agent: DiscoveredAgent) -> ConnectionResult:
        if not agent.binary_path:
            return ConnectionResult(success=False, agent_key=agent.agent_key, error="Codex CLI not found")
        config = self._read_codex_config()
        return ConnectionResult(
            success=True,
            agent_key=agent.agent_key,
            connection_type="subprocess",
            connector=self.connector_name,
            capabilities={
                **dict(agent.capabilities or {}),
                "approval_mode": config.get("approval_policy") or config.get("approval_mode") or "suggest",
            },
            metadata={"binary_path": agent.binary_path, "config": config},
        )

    async def health_check(self, agent: DiscoveredAgent) -> HealthStatus:
        result = await self._run_subprocess([agent.binary_path or "codex", "--version"], timeout=5)
        return HealthStatus(ok=result.success, status="online" if result.success else "offline", detail=result.output or result.error or "")

    async def get_status(self, agent: DiscoveredAgent) -> dict[str, object]:
        processes: list[dict[str, object]] = []
        if psutil is not None:
            for process in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
                try:
                    haystack = f"{process.info.get('name') or ''} {' '.join(process.info.get('cmdline') or [])}"
                    if "codex" not in haystack.lower():
                        continue
                    processes.append(
                        {
                            "pid": process.info["pid"],
                            "command": " ".join(process.info.get("cmdline") or []),
                            "started": process.info.get("create_time"),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return {
            "connector": self.connector_name,
            "is_running": bool(processes) or bool(agent.is_running),
            "config": self._read_codex_config(),
            "processes": processes,
        }

    async def send_task(self, agent: DiscoveredAgent, task: AgentTask) -> TaskResult:
        command = [agent.binary_path or "codex"]
        if task.model:
            command.extend(["--model", task.model])
        if task.approval_mode == "full-auto":
            command.append("--full-auto")
        elif task.approval_mode == "auto-edit":
            command.append("--auto-edit")
        if task.working_directory:
            command.extend(["--cd", task.working_directory])
        extra_args = task.payload.get("extra_args", []) if isinstance(task.payload, dict) else []
        command.extend(str(item) for item in extra_args)
        command.append(task.prompt)
        return await self._run_subprocess(command, cwd=task.working_directory, timeout=task.timeout or 300)

    async def get_logs(self, _: str, limit: int = 100) -> list[AgentLogEntry]:
        log_paths = [Path.home() / ".codex" / "log" / "codex-tui.log", Path.home() / ".codex" / "history.jsonl"]
        for path in log_paths:
            if not path.exists():
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
            return [
                AgentLogEntry(timestamp=str(index), level="info", message=line[:500], metadata={"path": str(path)})
                for index, line in enumerate(lines, start=max(len(lines) - limit, 0))
            ]
        return await super().get_logs(_, limit=limit)

    def _read_codex_config(self) -> dict[str, object]:
        config_paths = [
            Path.home() / ".codex" / "config.toml",
            Path.home() / ".codex" / "config.json",
            Path.home() / ".config" / "codex" / "config.toml",
        ]
        for path in config_paths:
            if not path.exists():
                continue
            try:
                if path.suffix == ".toml":
                    return tomllib.loads(path.read_text(encoding="utf-8"))
                return self._json_from_file(path)
            except Exception:  # noqa: BLE001
                continue
        return {}

    def _json_from_file(self, path: Path) -> dict[str, object]:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
