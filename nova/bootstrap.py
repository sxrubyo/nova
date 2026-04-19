"""Portable bootstrap helpers for isolated Nova runtimes and wrappers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence


CommandRunner = Callable[[list[str]], None]
_BANNER_EMITTED = False

CORE_PACKAGES = [
    "fastapi",
    "uvicorn[standard]",
    "httpx",
    "aiosqlite",
    "asyncpg",
    "pydantic",
    "python-dotenv",
    "click",
    "rich",
    "cryptography",
]


def render_bootstrap_banner() -> str:
    """Return the installer banner shown while Nova bootstraps."""

    return "\n".join(
        [
            "****************************************",
            "*               NOVA OS                *",
            "*  discovery, policy, runtime online   *",
            "****************************************",
        ]
    )


def _supports_color() -> bool:
    return bool(getattr(sys.stderr, "isatty", lambda: False)())


def _styled(text: str, *, color_code: str) -> str:
    if not _supports_color():
        return text
    return f"\033[{color_code}m{text}\033[0m"


def _emit_banner() -> None:
    global _BANNER_EMITTED
    if _BANNER_EMITTED:
        return
    _BANNER_EMITTED = True
    print(_styled(render_bootstrap_banner(), color_code="94"), file=sys.stderr)


def _status(message: str) -> None:
    print(_styled(f"[nova] {message}", color_code="96"), file=sys.stderr)


def select_bin_dir(
    *,
    home_dir: str | Path | None = None,
    env: dict[str, str] | None = None,
    path_value: str | None = None,
    writable_check: Callable[[Path], bool] | None = None,
) -> Path:
    """Pick a wrapper directory that is either already on PATH or native to the host."""

    home = Path(home_dir) if home_dir is not None else Path.home()
    environment = dict(os.environ if env is None else env)
    path_entries = [Path(entry) for entry in (path_value or environment.get("PATH", "")).split(os.pathsep) if entry]
    can_write = writable_check or (lambda candidate: os.access(candidate, os.W_OK))

    prefix = environment.get("PREFIX", "").strip()
    if environment.get("TERMUX_VERSION") or "com.termux" in prefix:
        termux_bin = Path(prefix) / "bin" if prefix else home / "../usr/bin"
        if can_write(termux_bin):
            return termux_bin

    for candidate in path_entries:
        if can_write(candidate):
            return candidate

    fallback = home / ".local" / "bin"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


def ensure_shell_path(bin_dir: str | Path, *, home_dir: str | Path | None = None, path_value: str | None = None) -> None:
    """Persist the wrapper directory into the user's shell startup files when needed."""

    target = Path(bin_dir)
    current_path = path_value or os.environ.get("PATH", "")
    if str(target) in current_path.split(os.pathsep):
        return

    home = Path(home_dir) if home_dir is not None else Path.home()
    candidates = [home / ".bashrc", home / ".zshrc", home / ".profile"]
    profile = next((candidate for candidate in candidates if candidate.exists()), candidates[-1])
    line = f'export PATH="{target}:$PATH"'
    existing = profile.read_text(encoding="utf-8") if profile.exists() else ""
    if line in existing:
        return
    prefix = "" if existing.endswith("\n") or not existing else "\n"
    profile.write_text(f"{existing}{prefix}{line}\n", encoding="utf-8")


def runtime_root(home_dir: str | Path | None = None) -> Path:
    """Return the isolated runtime root used by Nova installers."""

    home = Path(home_dir) if home_dir is not None else Path.home()
    return home / ".nova" / "runtime"


def runtime_state_path(root: str | Path) -> Path:
    """Return the bootstrap state file stored alongside the isolated runtime."""

    return Path(root) / ".bootstrap-state.json"


def runtime_python_path(root: str | Path) -> Path:
    """Return the Python executable inside the isolated runtime."""

    root_path = Path(root)
    if os.name == "nt":
        return root_path / "Scripts" / "python.exe"
    return root_path / "bin" / "python"


def build_wrapper_script(
    runtime_python: str | Path,
    repo_dir: str | Path,
    *,
    windows: bool | None = None,
) -> str:
    """Generate the shell wrapper content for the `nova` command."""

    python_path = Path(runtime_python)
    repo_path = Path(repo_dir)
    return build_wrapper_script_for_platform(python_path, repo_path, windows=windows)


def build_wrapper_script_for_platform(
    runtime_python: str | Path,
    repo_dir: str | Path,
    *,
    windows: bool | None = None,
) -> str:
    """Generate the host wrapper content for the `nova` command."""

    python_path = Path(runtime_python)
    repo_path = Path(repo_dir)
    is_windows = os.name == "nt" if windows is None else windows
    if is_windows:
        return (
            "@echo off\r\n"
            f'"{python_path}" "{repo_path / "nova.py"}" %*\r\n'
        )
    return (
        "#!/usr/bin/env sh\n"
        f'exec "{python_path}" "{repo_path / "nova.py"}" "$@"\n'
    )


def detect_python() -> str:
    """Find a usable host Python for bootstrap operations."""

    for candidate in ("python3", "python"):
        binary = shutil.which(candidate)
        if binary:
            return binary
    raise RuntimeError("Python no está disponible en el host")


def _run_command(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=str(cwd) if cwd else None, check=True, text=True)


def _requirements_signature(repo_path: Path) -> str:
    """Return a stable fingerprint for the dependency set Nova should install."""

    requirements_file = repo_path / "requirements.txt"
    fallback_file = repo_path / "nova_core_requirements.txt"

    if requirements_file.exists():
        payload = requirements_file.read_bytes()
    elif fallback_file.exists():
        payload = fallback_file.read_bytes()
    else:
        payload = "\n".join(CORE_PACKAGES).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def _load_runtime_state(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def ensure_runtime(
    repo_dir: str | Path,
    *,
    home_dir: str | Path | None = None,
    python_bin: str | None = None,
    command_runner: CommandRunner | None = None,
) -> Path:
    """Create/update the isolated runtime and install Nova dependencies."""

    repo_path = Path(repo_dir).resolve()
    root = runtime_root(home_dir)
    root.parent.mkdir(parents=True, exist_ok=True)
    runtime_python = runtime_python_path(root)
    state_path = runtime_state_path(root)
    runner = command_runner or (lambda command: _run_command(command, cwd=repo_path))
    host_python = python_bin or detect_python()
    current_state = {
        "repo_dir": str(repo_path),
        "python_bin": host_python,
        "requirements_signature": _requirements_signature(repo_path),
    }

    if runtime_python.exists() and _load_runtime_state(state_path) == current_state:
        _status("Nova bootstrap: using existing isolated runtime")
        return runtime_python

    if not runtime_python.exists():
        _status("Nova bootstrap: creating isolated runtime")
        runner([host_python, "-m", "venv", str(root)])

    _status("Nova bootstrap: installing Python dependencies")
    runner([str(runtime_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    requirements_file = repo_path / "requirements.txt"
    fallback_file = repo_path / "nova_core_requirements.txt"
    try:
        if requirements_file.exists():
            runner([str(runtime_python), "-m", "pip", "install", "-r", str(requirements_file)])
        elif fallback_file.exists():
            runner([str(runtime_python), "-m", "pip", "install", "-r", str(fallback_file)])
        else:
            runner([str(runtime_python), "-m", "pip", "install", *CORE_PACKAGES])
    except subprocess.CalledProcessError:
        runner([str(runtime_python), "-m", "pip", "install", *CORE_PACKAGES])

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(current_state, sort_keys=True), encoding="utf-8")

    return runtime_python


def install_cli_wrapper(
    repo_dir: str | Path,
    *,
    bin_dir: str | Path | None = None,
    home_dir: str | Path | None = None,
    python_bin: str | None = None,
) -> Path:
    """Create the host-side `nova` shell wrapper."""

    runtime_python = ensure_runtime(repo_dir, home_dir=home_dir, python_bin=python_bin)
    target_dir = Path(bin_dir) if bin_dir is not None else select_bin_dir(home_dir=home_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    wrapper_name = "nova.cmd" if os.name == "nt" else "nova"
    wrapper_path = target_dir / wrapper_name
    wrapper_path.write_text(
        build_wrapper_script_for_platform(runtime_python, Path(repo_dir).resolve()),
        encoding="utf-8",
    )
    wrapper_path.chmod(0o755)
    ensure_shell_path(target_dir, home_dir=home_dir)
    return wrapper_path


def init_runtime_database(repo_dir: str | Path, *, home_dir: str | Path | None = None, python_bin: str | None = None) -> None:
    """Initialize the fallback database inside the isolated runtime."""

    runtime_python = ensure_runtime(repo_dir, home_dir=home_dir, python_bin=python_bin)
    _run_command(
        [
            str(runtime_python),
            "-c",
            "import asyncio; from nova.db import init_db; asyncio.run(init_db())",
        ],
        cwd=Path(repo_dir).resolve(),
    )


def exec_nova(repo_dir: str | Path, argv: Sequence[str], *, home_dir: str | Path | None = None, python_bin: str | None = None) -> int:
    """Execute Nova through the isolated runtime."""

    runtime_python = ensure_runtime(repo_dir, home_dir=home_dir, python_bin=python_bin)
    command = [str(runtime_python), str(Path(repo_dir).resolve() / "nova.py"), *argv]
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nova bootstrap utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Create isolated runtime and CLI wrapper")
    install_parser.add_argument("--repo", required=True)
    install_parser.add_argument("--bin-dir")
    install_parser.add_argument("--home-dir")
    install_parser.add_argument("--python-bin")
    install_parser.add_argument("--skip-db-init", action="store_true")

    exec_parser = subparsers.add_parser("exec", help="Run nova.py through the isolated runtime")
    exec_parser.add_argument("--repo", required=True)
    exec_parser.add_argument("--home-dir")
    exec_parser.add_argument("--python-bin")
    exec_parser.add_argument("args", nargs=argparse.REMAINDER)

    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    if args.command == "install":
        _emit_banner()
        install_cli_wrapper(
            args.repo,
            bin_dir=args.bin_dir,
            home_dir=args.home_dir,
            python_bin=args.python_bin,
        )
        if not args.skip_db_init:
            init_runtime_database(
                args.repo,
                home_dir=args.home_dir,
                python_bin=args.python_bin,
            )
        return 0

    if args.command == "exec":
        runtime_args = list(args.args)
        if runtime_args[:1] == ["--"]:
            runtime_args = runtime_args[1:]
        return exec_nova(
            args.repo,
            runtime_args,
            home_dir=args.home_dir,
            python_bin=args.python_bin,
        )

    raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
