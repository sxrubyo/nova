"""Portable bootstrap helpers for isolated Nova runtimes and wrappers."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence


CommandRunner = Callable[[list[str]], None]

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


def runtime_root(home_dir: str | Path | None = None) -> Path:
    """Return the isolated runtime root used by Nova installers."""

    home = Path(home_dir) if home_dir is not None else Path.home()
    return home / ".nova" / "runtime"


def runtime_python_path(root: str | Path) -> Path:
    """Return the Python executable inside the isolated runtime."""

    root_path = Path(root)
    if os.name == "nt":
        return root_path / "Scripts" / "python.exe"
    return root_path / "bin" / "python"


def build_wrapper_script(runtime_python: str | Path, repo_dir: str | Path) -> str:
    """Generate the shell wrapper content for the `nova` command."""

    python_path = Path(runtime_python)
    repo_path = Path(repo_dir)
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
    runner = command_runner or (lambda command: _run_command(command, cwd=repo_path))
    host_python = python_bin or detect_python()

    if not runtime_python.exists():
        runner([host_python, "-m", "venv", str(root)])

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
    target_dir = Path(bin_dir) if bin_dir is not None else Path.home() / ".local" / "bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    wrapper_path = target_dir / "nova"
    wrapper_path.write_text(build_wrapper_script(runtime_python, Path(repo_dir).resolve()), encoding="utf-8")
    wrapper_path.chmod(0o755)
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
