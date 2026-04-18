"""System scanner that discovers agents across configs, processes, ports, and containers."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from nova.discovery.agent_manifest import DiscoveredAgent
from nova.discovery.fingerprints import AGENT_FINGERPRINTS
from nova.utils.crypto import generate_id, sha256_hex

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency on some hosts
    psutil = None


class SystemScanner:
    """See what is installed, running, and reachable on the current machine."""

    def __init__(self) -> None:
        self._http_timeout = 3.0

    async def full_scan(self) -> list[DiscoveredAgent]:
        discovered: list[DiscoveredAgent] = []
        discovered.extend(await self._scan_config_files())
        discovered.extend(await self._scan_binaries())
        discovered.extend(await self._scan_pip_packages())
        discovered.extend(await self._scan_npm_packages())
        discovered.extend(await self._scan_processes())
        discovered.extend(await self._scan_ports())
        discovered.extend(await self._scan_docker())
        discovered.extend(await self._scan_systemd())

        consolidated = self._deduplicate(discovered)
        confirmed = self._filter_confirmed_agents(consolidated)
        now = datetime.now(timezone.utc)
        for agent in confirmed:
            agent.discovered_at = agent.discovered_at or now
            agent.last_seen_at = now
            agent.nova_id = agent.nova_id or generate_id("discovered")
            if agent.is_running and agent.is_healthy is True:
                agent.status = "online"
            elif agent.is_running:
                agent.status = "running"
            elif agent.detection_methods:
                agent.status = "idle"
        return sorted(confirmed, key=lambda item: (-item.confidence, item.name))

    async def _scan_config_files(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
            for config_path in fingerprint.get("detection", {}).get("config_paths", []):
                expanded = Path(config_path).expanduser()
                if not expanded.exists():
                    continue
                agent = self._build_agent(
                    fingerprint_key=agent_key,
                    method="config_file",
                    detail=str(expanded),
                    confidence=0.9,
                    config_path=str(expanded),
                    metadata={"source": "filesystem"},
                )
                if expanded.is_file():
                    try:
                        content = expanded.read_text(encoding="utf-8")
                        agent.raw_config = content
                        if expanded.suffix == ".json":
                            agent.parsed_config = json.loads(content)
                        elif expanded.suffix == ".toml":
                            agent.parsed_config = tomllib.loads(content)
                    except Exception:  # noqa: BLE001
                        pass
                found.append(agent)
        return found

    async def _scan_binaries(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
            for binary in fingerprint.get("detection", {}).get("binary_names", []):
                path = shutil.which(binary)
                if not path:
                    continue
                version = await self._command_output([binary, "--version"], timeout=5)
                found.append(
                    self._build_agent(
                        fingerprint_key=agent_key,
                        method="binary",
                        detail=path,
                        confidence=0.95,
                        version=version.strip() or None,
                        binary_path=path,
                    )
                )
        return found

    async def _scan_pip_packages(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        payload = await self._command_output([sys.executable, "-m", "pip", "list", "--format", "json"], timeout=15)
        if not payload:
            return found
        try:
            installed = {package["name"].lower(): package["version"] for package in json.loads(payload)}
        except json.JSONDecodeError:
            return found
        for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
            for package in fingerprint.get("detection", {}).get("pip_packages", []):
                version = installed.get(package.lower())
                if not version:
                    continue
                found.append(
                    self._build_agent(
                        fingerprint_key=agent_key,
                        method="pip_package",
                        detail=f"{package}=={version}",
                        confidence=0.7,
                        version=version,
                    )
                )
        return found

    async def _scan_npm_packages(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        payload = await self._command_output(["npm", "list", "-g", "--json", "--depth=0"], timeout=15)
        if not payload:
            return found
        try:
            dependencies = json.loads(payload).get("dependencies", {})
        except json.JSONDecodeError:
            return found
        for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
            for package in fingerprint.get("detection", {}).get("npm_packages", []):
                info = dependencies.get(package)
                if not info:
                    continue
                found.append(
                    self._build_agent(
                        fingerprint_key=agent_key,
                        method="npm_package",
                        detail=f"{package}@{info.get('version', '?')}",
                        confidence=0.7,
                        version=info.get("version"),
                    )
                )
        return found

    async def _scan_processes(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        if psutil is None:
            return found
        for process in psutil.process_iter(["pid", "name", "cmdline", "status", "create_time", "memory_info"]):
            try:
                cmdline = " ".join(process.info.get("cmdline") or [])
                process_name = process.info.get("name") or ""
                matched = False
                for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
                    if not fingerprint.get("discoverable", True):
                        continue
                    for pattern in fingerprint.get("detection", {}).get("process_patterns", []):
                        if re.search(pattern, process_name, re.IGNORECASE) or re.search(pattern, cmdline, re.IGNORECASE):
                            matched = True
                            found.append(
                                self._build_agent(
                                    fingerprint_key=agent_key,
                                    method="process",
                                    detail=f"PID {process.pid}: {cmdline or process_name}",
                                    confidence=0.85,
                                    pid=process.pid,
                                    is_running=True,
                                    process_info=self._process_info(process),
                                )
                            )
                            break
                    if matched:
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return found

    async def _scan_ports(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        listening_ports = await self._listening_ports()
        for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
            if not fingerprint.get("discoverable", True):
                continue
            health_paths = fingerprint.get("detection", {}).get("health_paths", [])
            for port in fingerprint.get("detection", {}).get("default_ports", []):
                if port not in listening_ports:
                    continue
                is_healthy, detail = await self._probe_http(port, health_paths=health_paths)
                if not is_healthy:
                    continue
                found.append(
                    self._build_agent(
                        fingerprint_key=agent_key,
                        method="port",
                        detail=detail or f"Port {port} responded",
                        confidence=0.75,
                        port=port,
                        is_running=True,
                        is_healthy=is_healthy,
                    )
                )
        return found

    async def _scan_docker(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        payload = await self._command_output(["docker", "ps", "--format", "{{json .}}"], timeout=10)
        if not payload:
            return found
        for line in payload.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                container = json.loads(line)
            except json.JSONDecodeError:
                continue
            image = container.get("Image", "")
            container_name = container.get("Names", "")
            ports_text = container.get("Ports", "")
            mapped_port = self._extract_port(ports_text)
            matched = False
            for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
                if not fingerprint.get("discoverable", True):
                    continue
                for docker_image in fingerprint.get("detection", {}).get("docker_images", []):
                    if docker_image.lower() in image.lower():
                        matched = True
                        found.append(
                            self._build_agent(
                                fingerprint_key=agent_key,
                                method="docker",
                                detail=f"{container_name} ({image})",
                                confidence=0.95,
                                container_id=container.get("ID"),
                                container_name=container_name,
                                port=mapped_port,
                                is_running=True,
                            )
                        )
                        break
                if matched:
                    break
        return found

    async def _scan_environment(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        current_env = dict(os.environ)
        for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
            matched_vars = [name for name in fingerprint.get("detection", {}).get("env_vars", []) if name in current_env]
            if not matched_vars:
                continue
            found.append(
                self._build_agent(
                    fingerprint_key=agent_key,
                    method="env_var",
                    detail=", ".join(f"{name} is set" for name in matched_vars),
                    confidence=0.5,
                    env_vars=matched_vars,
                )
            )
        return found

    async def _scan_systemd(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        output = await self._command_output(
            ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain"],
            timeout=10,
        )
        if not output:
            return found
        for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
            for pattern in fingerprint.get("detection", {}).get("process_patterns", []):
                if not re.search(pattern, output, re.IGNORECASE):
                    continue
                found.append(
                    self._build_agent(
                        fingerprint_key=agent_key,
                        method="systemd",
                        detail=f"systemd service matched {pattern}",
                        confidence=0.8,
                    )
                )
                break
        return found

    async def _scan_dotenv_files(self) -> list[DiscoveredAgent]:
        found: list[DiscoveredAgent] = []
        search_paths = [Path.home(), Path.home() / "projects", Path.home() / "ubuntu", Path("/opt")]
        for base_path in search_paths:
            if not base_path.exists():
                continue
            for env_file in self._iter_dotenv_files(base_path, max_depth=2):
                try:
                    content = env_file.read_text(encoding="utf-8")
                except Exception:  # noqa: BLE001
                    continue
                for agent_key, fingerprint in AGENT_FINGERPRINTS.items():
                    env_vars = [name for name in fingerprint.get("detection", {}).get("env_vars", []) if name in content]
                    if not env_vars:
                        continue
                    found.append(
                        self._build_agent(
                            fingerprint_key=agent_key,
                            method="dotenv_file",
                            detail=f"{env_file} contains {', '.join(env_vars)}",
                            confidence=0.6,
                            config_path=str(env_file),
                            env_vars=env_vars,
                        )
                    )
        return found

    def _iter_dotenv_files(self, base_path: Path, max_depth: int = 2) -> list[Path]:
        files: list[Path] = []
        base_depth = len(base_path.parts)
        for root, dirnames, filenames in os.walk(base_path):
            current = Path(root)
            if len(current.parts) - base_depth >= max_depth:
                dirnames[:] = []
            if ".env" in filenames:
                files.append(current / ".env")
        return files

    def _deduplicate(self, agents: list[DiscoveredAgent]) -> list[DiscoveredAgent]:
        grouped: dict[str, DiscoveredAgent] = {}
        for agent in agents:
            existing = grouped.get(agent.agent_key)
            if existing is None:
                grouped[agent.agent_key] = agent
                continue
            existing.merge(agent)
        return list(grouped.values())

    def _filter_confirmed_agents(self, agents: list[DiscoveredAgent]) -> list[DiscoveredAgent]:
        confirmed: list[DiscoveredAgent] = []
        for agent in agents:
            fingerprint = AGENT_FINGERPRINTS.get(agent.fingerprint_key, {})
            if not fingerprint.get("discoverable", True):
                continue
            detection = fingerprint.get("detection", {})
            required_matches = int(detection.get("required_matches", 1))
            matched_signals = len(agent.detection_methods)
            if matched_signals < required_matches:
                continue
            agent.metadata = {
                **dict(agent.metadata or {}),
                "logo_path": fingerprint.get("logo_path"),
                "matched_signals": matched_signals,
                "required_matches": required_matches,
                "supported_signals": self._supported_signal_count(fingerprint),
                "evidence": [
                    {"method": item.method, "detail": item.detail, "confidence": item.confidence}
                    for item in agent.evidence
                ],
            }
            confirmed.append(agent)
        return confirmed

    def _supported_signal_count(self, fingerprint: dict[str, Any]) -> int:
        detection = fingerprint.get("detection", {})
        signal_groups = [
            "config_paths",
            "binary_names",
            "pip_packages",
            "npm_packages",
            "process_patterns",
            "default_ports",
            "docker_images",
        ]
        return sum(1 for key in signal_groups if detection.get(key))

    def _build_agent(self, fingerprint_key: str, method: str, detail: str, confidence: float, **kwargs: Any) -> DiscoveredAgent:
        fingerprint = AGENT_FINGERPRINTS[fingerprint_key]
        identity = self._identity_for(fingerprint_key, kwargs)
        agent_key = f"{fingerprint_key}-{sha256_hex(identity)[:10]}"
        agent = DiscoveredAgent(
            agent_key=agent_key,
            fingerprint_key=fingerprint_key,
            name=fingerprint["name"],
            type=fingerprint["type"],
            icon=fingerprint.get("icon", "cpu"),
            color=fingerprint.get("color", "#6B7280"),
            confidence=confidence,
            detection_method=method,
            fingerprint=fingerprint,
            capabilities=dict(fingerprint.get("capabilities", {})),
            risk_profile=dict(fingerprint.get("risk_profile", {})),
            metadata=kwargs.pop("metadata", {}),
            **kwargs,
        )
        agent.add_evidence(method, detail, confidence)
        return agent

    def _identity_for(self, fingerprint_key: str, data: dict[str, Any]) -> str:
        if fingerprint_key == "generic_process_agent":
            return f"process:{data.get('pid') or data.get('detail') or 'unknown'}"
        if fingerprint_key == "generic_docker_agent":
            return f"docker:{data.get('container_name') or data.get('container_id') or 'unknown'}"
        return fingerprint_key

    def _extract_port(self, ports_text: str) -> int | None:
        match = re.search(r"(?P<host>\d+)->(?P<container>\d+)/tcp", ports_text)
        if match:
            return int(match.group("host"))
        match = re.search(r":(?P<host>\d+)->", ports_text)
        if match:
            return int(match.group("host"))
        return None

    async def _command_output(self, command: list[str], timeout: int = 10) -> str:
        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""
        if completed.returncode != 0 and not completed.stdout and not completed.stderr:
            return ""
        return (completed.stdout or completed.stderr or "").strip()

    async def _listening_ports(self) -> set[int]:
        ports: set[int] = set()
        if psutil is not None:
            for connection in psutil.net_connections(kind="tcp"):
                if connection.status == "LISTEN":
                    ports.add(connection.laddr.port)
            return ports
        output = await self._command_output(["ss", "-tln"], timeout=5)
        for line in output.splitlines():
            match = re.search(r":(\d+)\s", line)
            if match:
                ports.add(int(match.group(1)))
        return ports

    async def _probe_http(self, port: int, *, health_paths: list[str] | None = None) -> tuple[bool, str | None]:
        probe_paths = [path for path in (health_paths or []) if path]
        if not probe_paths:
            probe_paths = ["/health", "/healthz", "/"]
        urls = [f"http://127.0.0.1:{port}{path}" for path in probe_paths]
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            for url in urls:
                try:
                    response = await client.get(url)
                    if response.status_code < 400 or response.status_code in {401, 403}:
                        return True, url
                except Exception:  # noqa: BLE001
                    continue
        return False, None

    def _process_info(self, process: Any) -> dict[str, Any]:
        created_at = process.info.get("create_time")
        memory_info = process.info.get("memory_info")
        return {
            "pid": process.info.get("pid"),
            "status": process.info.get("status"),
            "started": datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat() if created_at else None,
            "memory_mb": round((memory_info.rss / 1024 / 1024), 2) if memory_info else 0,
        }
