# Nova OS Architecture

Nova OS has one supported runtime path in this repository:

1. `nova.py` as the CLI and local server entrypoint
2. `nova/` as the core package for API, kernel, discovery, ledger, memory, and security

Legacy directories still exist, but the production path should be read as `nova.py` + `nova/`.

## Runtime model

- **CLI**: `nova.py`
- **API**: FastAPI + Uvicorn
- **Kernel**: `nova/kernel.py`
- **Primary storage**: async SQLAlchemy with SQLite by default and PostgreSQL when explicitly configured
- **Portable bootstrap DB layer**: `nova/db.py`
- **Discovery**: `nova/discovery/`
- **Ledger**: `nova/ledger/`
- **Memory**: `nova/memory/`

## Platform strategy

- **Host detection**: `nova/platform.py`
- **Termux**: no Docker, no systemd, no PostgreSQL requirement
- **Linux with systemd**: can run as a managed service
- **PM2 / screen / nohup**: fallback process managers
- **Node.js**: optional for frontend build and extended tooling; not required for the core runtime

## Storage model

- If PostgreSQL is explicitly configured and reachable, Nova uses it.
- Otherwise Nova falls back to SQLite at `~/.nova/nova.db`.
- The goal is portability without changing the public runtime interface.

## Validation flow

1. An agent action arrives through the API, bridge, or CLI.
2. The kernel evaluates intent, rules, sensitivity, risk, and quota.
3. The pipeline produces an operational verdict such as `ALLOW`, `BLOCK`, or `ESCALATE`.
4. The ledger records the event with SHA-256 or HMAC-based signing.
5. Memory and observability persist the operational context.

## Practical constraints

- `backend/` and `legacy/` still exist and should be treated as compatibility code.
- The local dashboard is served by the same runtime when `frontend/dist` exists.
- Installers and helper scripts must degrade gracefully when Docker, systemd, or PostgreSQL are missing.
