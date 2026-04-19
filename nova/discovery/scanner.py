"""System scanner that discovers agents across configs, processes, ports, and containers."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from nova.discovery.agent_manifest import DiscoveredAgent
from nova.discovery.fingerprints import AGENT_FINGERPRINTS
from nova.platform import PLATFORM
from nova.utils.crypto import generate_id, sha256_hex

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

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
        discovered.extend(await self._scan_environment())
        discovered.extend(await self._scan_dotenv_files())
        discovered.extend(await self._scan_processes())
        discovered.extend(await self._scan_ports())
        if PLATFORM.has_docker:
            discovered.extend(await self._scan_docker())
        if PLATFORM.has_systemd:
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

    def host_inventory(self, *, roots: list[Path] | None = None) -> dict[str, Any]:
        """Summarize repositories, terminals, and local governance signals."""

        repositories = self._scan_repositories(roots=roots)
        terminals = self._scan_terminal_processes(repositories=repositories)
        self._annotate_repository_activity(repositories, terminals)
        host = self._host_profile()
        tooling = self._scan_tooling()
        applications = [item for item in tooling if item.get("installed") and item.get("category") in {"assistant", "editor", "automation"}]
        recommended_installs = self._build_install_recommendations(
            repositories=repositories,
            terminals=terminals,
            tooling=tooling,
            host=host,
        )
        codex_home = Path.home() / ".codex"
        active_repo_paths = sorted({terminal["repo_path"] for terminal in terminals if terminal.get("repo_path")})
        ecosystem_counts = self._ecosystem_counts(repositories)
        return {
            "summary": {
                "repositories": len(repositories),
                "terminals": len(terminals),
                "active_repositories": len(active_repo_paths),
                "toolchains": len([item for item in tooling if item.get("installed")]),
                "applications": len(applications),
                "recommended_installs": len(recommended_installs),
                "ecosystems": ecosystem_counts,
            },
            "repositories": repositories,
            "terminals": terminals,
            "tooling": tooling,
            "applications": applications,
            "recommended_installs": recommended_installs,
            "host": host,
            "signals": {
                "has_codex_home": codex_home.exists(),
                "codex_home": str(codex_home),
                "cwd": str(Path.cwd()),
                "platform": PLATFORM.type,
                "active_repo_paths": active_repo_paths,
            },
        }

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
        if not PLATFORM.has_docker:
            return found
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
        if not PLATFORM.has_systemd:
            return found
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

    def _scan_repositories(self, *, roots: list[Path] | None = None, max_depth: int = 3, max_results: int = 40) -> list[dict[str, Any]]:
        repositories: list[dict[str, Any]] = []
        seen: set[str] = set()
        markers = [".git", ".codex", "package.json", "pyproject.toml", "requirements.txt", "docker-compose.yml"]

        for root in self._repository_search_roots(roots):
            for candidate in self._iter_candidate_directories(root, max_depth=max_depth):
                if len(repositories) >= max_results:
                    return repositories
                marker_hits = [marker for marker in markers if (candidate / marker).exists()]
                if not marker_hits:
                    continue
                resolved = str(candidate.resolve())
                if resolved in seen:
                    continue
                if any(
                    repository.get("has_git")
                    and Path(repository["path"]) in Path(resolved).parents
                    and ".git" not in marker_hits
                    and ".codex" not in marker_hits
                    for repository in repositories
                ):
                    continue
                seen.add(resolved)
                repositories.append(
                    {
                        "name": candidate.name,
                        "path": resolved,
                        "markers": marker_hits,
                        "has_git": ".git" in marker_hits,
                        "has_codex": ".codex" in marker_hits,
                        "ecosystems": self._detect_ecosystems(candidate),
                    }
                )
        return repositories

    def _repository_search_roots(self, roots: list[Path] | None = None) -> list[Path]:
        if roots is not None:
            return [Path(root).expanduser() for root in roots if Path(root).expanduser().exists()]

        candidates = [
            Path.cwd(),
            Path(PLATFORM.home),
            Path(PLATFORM.home) / "projects",
            Path(PLATFORM.home) / "workspace",
            Path(PLATFORM.home) / "src",
        ]
        unique: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            expanded = candidate.expanduser()
            if not expanded.exists():
                continue
            resolved = str(expanded.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            unique.append(expanded)
        return unique

    def _iter_candidate_directories(self, root: Path, *, max_depth: int) -> list[Path]:
        candidates: list[Path] = []
        root = root.expanduser()
        if not root.exists():
            return candidates
        base_depth = len(root.parts)
        skip_dirs = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}
        for current_root, dirnames, _ in os.walk(root):
            current = Path(current_root)
            depth = len(current.parts) - base_depth
            if depth > max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = [item for item in dirnames if item not in skip_dirs and not item.startswith(".cache")]
            candidates.append(current)
        return candidates

    def _detect_ecosystems(self, directory: Path) -> list[str]:
        ecosystems: list[str] = []
        if (directory / "package.json").exists():
            ecosystems.append("node")
        if (directory / "pyproject.toml").exists() or (directory / "requirements.txt").exists():
            ecosystems.append("python")
        if (directory / "docker-compose.yml").exists():
            ecosystems.append("docker")
        return ecosystems

    def _annotate_repository_activity(self, repositories: list[dict[str, Any]], terminals: list[dict[str, Any]]) -> None:
        terminal_counts: dict[str, int] = {}
        for terminal in terminals:
            repo_path = terminal.get("repo_path")
            if not repo_path:
                continue
            terminal_counts[repo_path] = terminal_counts.get(repo_path, 0) + 1

        for repository in repositories:
            active_terminals = terminal_counts.get(repository["path"], 0)
            repository["active_terminals"] = active_terminals
            repository["is_active"] = active_terminals > 0

        repositories.sort(
            key=lambda item: (
                0 if item.get("is_active") else 1,
                0 if item.get("has_codex") else 1,
                item.get("name", ""),
            )
        )

    def _ecosystem_counts(self, repositories: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for repository in repositories:
            for ecosystem in repository.get("ecosystems", []):
                counts[ecosystem] = counts.get(ecosystem, 0) + 1
        return dict(sorted(counts.items()))

    def _host_profile(self) -> dict[str, Any]:
        package_manager = self._detect_package_manager()
        return {
            "platform": PLATFORM.type,
            "process_manager": PLATFORM.process_manager,
            "db_engine": PLATFORM.db_engine,
            "package_manager": package_manager,
            "cwd": str(Path.cwd()),
            "home": str(Path(PLATFORM.home)),
        }

    def _detect_package_manager(self) -> dict[str, Any]:
        candidates = [
            ("pkg", True),
            ("brew", True),
            ("apt-get", True),
            ("dnf", True),
            ("pacman", True),
            ("winget", True),
            ("choco", True),
            ("scoop", True),
        ]
        for command, auto_install in candidates:
            if shutil.which(command) is not None:
                return {"name": command, "auto_install_supported": auto_install}
        return {"name": None, "auto_install_supported": False}

    def _scan_tooling(self) -> list[dict[str, Any]]:
        tool_specs = [
            {"key": "git", "label": "Git", "commands": ["git"], "category": "vcs"},
            {"key": "python", "label": "Python", "commands": ["python3", "python", "py"], "category": "runtime"},
            {"key": "pip", "label": "pip", "commands": ["pip3", "pip"], "category": "runtime"},
            {"key": "uv", "label": "uv", "commands": ["uv"], "category": "runtime"},
            {"key": "node", "label": "Node.js", "commands": ["node"], "category": "runtime"},
            {"key": "npm", "label": "npm", "commands": ["npm"], "category": "runtime"},
            {"key": "pnpm", "label": "pnpm", "commands": ["pnpm"], "category": "runtime"},
            {"key": "bun", "label": "Bun", "commands": ["bun"], "category": "runtime"},
            {"key": "docker", "label": "Docker", "commands": ["docker"], "category": "automation"},
            {"key": "rg", "label": "ripgrep", "commands": ["rg"], "category": "automation"},
            {"key": "gh", "label": "GitHub CLI", "commands": ["gh"], "category": "automation"},
            {"key": "codex", "label": "Codex CLI", "commands": ["codex"], "category": "assistant"},
            {"key": "claude", "label": "Claude CLI", "commands": ["claude"], "category": "assistant"},
            {"key": "n8n", "label": "n8n", "commands": ["n8n"], "category": "automation"},
            {"key": "ollama", "label": "Ollama", "commands": ["ollama"], "category": "automation"},
            {"key": "code", "label": "VS Code", "commands": ["code"], "category": "editor"},
            {"key": "cursor", "label": "Cursor", "commands": ["cursor"], "category": "editor"},
            {"key": "zed", "label": "Zed", "commands": ["zed"], "category": "editor"},
            {"key": "tmux", "label": "tmux", "commands": ["tmux"], "category": "terminal"},
            {"key": "screen", "label": "screen", "commands": ["screen"], "category": "terminal"},
        ]

        tooling: list[dict[str, Any]] = []
        for spec in tool_specs:
            resolved = self._resolve_tool_binary(spec["commands"])
            tooling.append(
                {
                    "key": spec["key"],
                    "label": spec["label"],
                    "category": spec["category"],
                    "installed": resolved is not None,
                    "path": resolved,
                    "version": self._tool_version(spec["key"], resolved) if resolved else None,
                }
            )
        return tooling

    def _resolve_tool_binary(self, commands: list[str]) -> str | None:
        for command in commands:
            resolved = shutil.which(command)
            if resolved:
                return resolved
        return None

    def _tool_version(self, key: str, resolved: str) -> str | None:
        command = Path(resolved).name
        version_command = [command, "--version"]
        if key == "python" and command.lower() == "py":
            version_command = [command, "-3", "--version"]
        elif key == "tmux":
            version_command = [command, "-V"]
        elif key == "screen":
            version_command = [command, "-v"]
        output = self._sync_command_output(version_command)
        if not output:
            return None
        return output.splitlines()[0].strip()[:120]

    def _sync_command_output(self, command: list[str], timeout: int = 4) -> str:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return (completed.stdout or completed.stderr or "").strip()

    def _build_install_recommendations(
        self,
        *,
        repositories: list[dict[str, Any]],
        terminals: list[dict[str, Any]],
        tooling: list[dict[str, Any]],
        host: dict[str, Any],
    ) -> list[dict[str, Any]]:
        installed = {item["key"]: bool(item.get("installed")) for item in tooling}
        package_manager = str((host.get("package_manager") or {}).get("name") or "")
        ecosystem_counts = self._ecosystem_counts(repositories)
        active_repositories = [repository for repository in repositories if repository.get("is_active")]
        active_ecosystems = self._ecosystem_counts(active_repositories)
        has_codex = any(repository.get("has_codex") for repository in repositories) or (Path.home() / ".codex").exists()

        recommendations: list[dict[str, Any]] = []

        def add(tool_key: str, *, reason: str, packages: list[str], auto_installable: bool, severity: str = "recommended") -> None:
            install_command = self._build_install_command(package_manager, packages)
            recommendations.append(
                {
                    "tool": tool_key,
                    "severity": severity,
                    "reason": reason,
                    "packages": packages,
                    "auto_installable": auto_installable and bool(install_command),
                    "install_command": install_command,
                }
            )

        if repositories and not installed.get("git", False):
            add(
                "git",
                reason=f"{len(repositories)} repository roots detected and Git is missing",
                packages=self._package_names("git", package_manager),
                auto_installable=True,
                severity="essential",
            )

        if ecosystem_counts.get("python", 0) and not installed.get("python", False):
            repo_count = active_ecosystems.get("python", 0) or ecosystem_counts.get("python", 0)
            add(
                "python",
                reason=f"{repo_count} Python repository contexts detected and Python is missing",
                packages=self._package_names("python", package_manager),
                auto_installable=True,
                severity="essential",
            )

        if ecosystem_counts.get("node", 0) and (not installed.get("node", False) or not installed.get("npm", False)):
            repo_count = active_ecosystems.get("node", 0) or ecosystem_counts.get("node", 0)
            add(
                "node",
                reason=f"{repo_count} Node-based repositories detected and Node/npm are incomplete",
                packages=self._package_names("node", package_manager),
                auto_installable=True,
            )

        if ecosystem_counts.get("docker", 0) and not installed.get("docker", False):
            repo_count = active_ecosystems.get("docker", 0) or ecosystem_counts.get("docker", 0)
            add(
                "docker",
                reason=f"{repo_count} repositories define Docker workflows but Docker is missing",
                packages=self._package_names("docker", package_manager),
                auto_installable=False,
            )

        if has_codex and not installed.get("rg", False):
            add(
                "rg",
                reason="Codex context detected and ripgrep is missing; Nova and Codex both scan faster with rg",
                packages=self._package_names("rg", package_manager),
                auto_installable=True,
            )

        if terminals and PLATFORM.type in {"linux", "macos", "termux"} and not installed.get("tmux", False):
            add(
                "tmux",
                reason=f"{len(terminals)} terminal sessions detected; tmux improves resilient long-running agent sessions",
                packages=self._package_names("tmux", package_manager),
                auto_installable=True,
                severity="optional",
            )

        return [item for item in recommendations if item["packages"]]

    def _package_names(self, tool: str, package_manager: str) -> list[str]:
        packages = {
            "git": {
                "apt-get": ["git"],
                "dnf": ["git"],
                "pacman": ["git"],
                "brew": ["git"],
                "pkg": ["git"],
                "winget": ["Git.Git"],
                "choco": ["git"],
                "scoop": ["git"],
            },
            "python": {
                "apt-get": ["python3", "python3-pip", "python3-venv"],
                "dnf": ["python3", "python3-pip", "python3-virtualenv"],
                "pacman": ["python", "python-pip"],
                "brew": ["python"],
                "pkg": ["python"],
                "winget": ["Python.Python.3.11"],
                "choco": ["python"],
                "scoop": ["python"],
            },
            "node": {
                "apt-get": ["nodejs", "npm"],
                "dnf": ["nodejs", "npm"],
                "pacman": ["nodejs", "npm"],
                "brew": ["node"],
                "pkg": ["nodejs"],
                "winget": ["OpenJS.NodeJS.LTS"],
                "choco": ["nodejs-lts"],
                "scoop": ["nodejs-lts"],
            },
            "docker": {
                "apt-get": ["docker.io"],
                "dnf": ["docker"],
                "pacman": ["docker"],
                "brew": ["docker"],
                "winget": ["Docker.DockerDesktop"],
                "choco": ["docker-desktop"],
                "scoop": ["docker"],
            },
            "rg": {
                "apt-get": ["ripgrep"],
                "dnf": ["ripgrep"],
                "pacman": ["ripgrep"],
                "brew": ["ripgrep"],
                "pkg": ["ripgrep"],
                "winget": ["BurntSushi.ripgrep.MSVC"],
                "choco": ["ripgrep"],
                "scoop": ["ripgrep"],
            },
            "tmux": {
                "apt-get": ["tmux"],
                "dnf": ["tmux"],
                "pacman": ["tmux"],
                "brew": ["tmux"],
                "pkg": ["tmux"],
                "winget": ["Termius.Termius"],
                "choco": ["tmux"],
                "scoop": ["tmux"],
            },
        }
        return list(packages.get(tool, {}).get(package_manager, []))

    def _build_install_command(self, package_manager: str, packages: list[str]) -> str | None:
        if not package_manager or not packages:
            return None
        joined = " ".join(packages)
        commands = {
            "apt-get": f"sudo apt-get install -y {joined}",
            "dnf": f"sudo dnf install -y {joined}",
            "pacman": f"sudo pacman -S --noconfirm {joined}",
            "brew": f"brew install {joined}",
            "pkg": f"pkg install -y {joined}",
            "winget": " ; ".join(f"winget install --id {package} -e" for package in packages),
            "choco": f"choco install -y {joined}",
            "scoop": f"scoop install {joined}",
        }
        return commands.get(package_manager)

    def _scan_terminal_processes(self, *, repositories: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if psutil is None:
            return []

        terminals: list[dict[str, Any]] = []
        terminal_binaries = {
            "bash",
            "zsh",
            "fish",
            "sh",
            "tmux",
            "screen",
            "pwsh",
            "powershell",
            "cmd.exe",
            "cmd",
            "wt.exe",
            "windows terminal",
            "konsole",
            "gnome-terminal",
            "kitty",
            "wezterm",
            "alacritty",
        }

        for process in psutil.process_iter(["pid", "name", "cmdline", "create_time", "status"]):
            try:
                name = str(process.info.get("name") or "")
                command_parts = [str(item) for item in process.info.get("cmdline") or [] if item]
                cmdline = " ".join(command_parts)
                binary_names = {Path(part).name.lower() for part in command_parts}
                terminal_match = name.lower() in terminal_binaries or bool(binary_names & terminal_binaries)
                if not terminal_match:
                    continue
                haystack = f"{name} {cmdline}".lower()
                cwd = None
                with contextlib.suppress(Exception):
                    cwd = process.cwd()
                repo = self._match_repository_for_path(cwd, repositories or [])
                terminals.append(
                    {
                        "pid": process.info.get("pid"),
                        "name": name or "terminal",
                        "cwd": cwd,
                        "repo_path": repo.get("path") if repo else None,
                        "repo_name": repo.get("name") if repo else None,
                        "has_codex_context": bool((repo or {}).get("has_codex")) or ".codex" in haystack,
                        "command": cmdline,
                        "status": process.info.get("status"),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return terminals[:25]

    def _match_repository_for_path(self, cwd: str | None, repositories: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not cwd:
            return None
        try:
            current = Path(cwd).resolve()
        except Exception:  # noqa: BLE001
            return None

        matches = [
            repository
            for repository in repositories
            if current == Path(repository["path"]) or Path(repository["path"]) in current.parents
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: len(str(item["path"])))

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
            try:
                for connection in psutil.net_connections(kind="tcp"):
                    if connection.status == "LISTEN":
                        ports.add(connection.laddr.port)
                return ports
            except Exception:  # noqa: BLE001
                ports.clear()
        for command in (["ss", "-tln"], ["netstat", "-tln"], ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"]):
            output = await self._command_output(command, timeout=5)
            if not output:
                continue
            for line in output.splitlines():
                match = re.search(r":(\d+)\s", line)
                if match:
                    ports.add(int(match.group(1)))
            if ports:
                break
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
