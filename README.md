# Nova OS

Nova OS is a unified runtime for governed AI agents and automations. It bundles a Python API, a local web dashboard, and a CLI into one installable system that can run on Linux, macOS, Termux, or Ubuntu inside Termux.

The supported execution path in this repository is `nova.py` + `nova/`. Legacy directories remain for compatibility while the public surface is being cleaned up.

## What ships today

- A FastAPI backend for evaluation, workspaces, ledger, discovery, and agent operations.
- A React dashboard served by the same local runtime when `frontend/dist` is available.
- A `nova` CLI for bootstrap, validation, status, auth, and operational workflows.
- A portable storage path with SQLite fallback and PostgreSQL support when explicitly configured.
- Optional Docker Compose and n8n integration for local or self-hosted environments.

## Install

### Recommended: one-line installer

```bash
curl -fsSL https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.sh | sh
```

The installer:

- detects the host platform
- profiles local toolchains and active developer context
- stages the canonical repo in `~/.nova/repo`
- creates an isolated Python runtime in `~/.nova/runtime`
- installs the canonical `nova` wrapper in `~/.nova/bin`
- starts Nova on `http://localhost:8000`

### Global CLI via npm

Nova is packaged for npm-style global installation, but the public registry release is not the primary distribution channel yet. The reliable path today is the GitHub tarball:

```bash
npm install -g https://codeload.github.com/sxrubyo/nova-os/tar.gz/refs/heads/main
nova commands
```

This still installs a global `nova` command. On first run it bootstraps the isolated Python runtime and then executes the real CLI.

### Windows / PowerShell

```powershell
irm https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.ps1 | iex
```

The PowerShell installer downloads the repository archive, bootstraps the same isolated runtime used on Unix hosts, creates `nova.cmd`, and adds the Nova bin directory to the user PATH.

### Docker Compose

```bash
cp .env.example .env
docker-compose up -d --build
```

Use this path when you want PostgreSQL and a containerized local stack. The compose setup runs the same modular runtime, not a separate product fork.

## Run locally from source

### Backend + dashboard

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 nova.py serve --host 0.0.0.0 --port 8000
```

If `frontend/dist` exists, the same process serves:

- dashboard: `http://localhost:8000/`
- API: `http://localhost:8000/api/*`

### Frontend development

```bash
cd frontend
npm install
npm run dev
```

### CLI

```bash
python3 nova.py --help
```

## Agent skill bridge

Nova can install its own governance skill bridge into local agent surfaces.

### Install for Codex

```bash
nova skill install --agent codex
```

This writes a native skill bundle to `~/.agents/skills/nova-governance/`.

### Install for Gemini CLI

```bash
nova skill install --agent gemini
```

This writes `~/.gemini/skills/nova-governance.md` and adds a bridge block to `~/.gemini/GEMINI.md`.

### Install for OpenCode

```bash
nova skill install --agent opencode
```

This writes `~/.config/opencode/skills/nova-governance.md` and adds a bridge block to `~/.config/opencode/AGENTS.md`.

### Core governance flow

```bash
nova discover --json
nova connect codex-cli --cannot-do "rm -rf"
nova validate --agent codex-cli --action terminal.command --payload '{"command":"rm -rf /tmp/demo"}'
```

### OpenCode first use

```bash
opencode providers login
opencode .
```

## Termux / Android

Nova OS supports Termux without root.

### Prerequisites

```sh
pkg install python git openssl
```

### Install

```sh
curl -fsSL https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.sh | sh
```

On Termux, Nova:

- uses SQLite at `~/.nova/nova.db`
- creates an isolated runtime at `~/.nova/runtime`
- skips Docker, nginx, and PostgreSQL
- runs in the background with `nohup`
- stores logs and PID files in `~/.nova/`

### Optional Termux:API integration

```sh
pkg install termux-api
```

This enables local notifications, vibration, battery inspection, and wake-lock helpers.

### Stop Nova

```sh
kill "$(cat ~/.nova/nova.pid)"
```

### Logs

```sh
tail -f ~/.nova/nova.log
```

## Architecture

Nova OS is organized as one runtime, not separate products:

```text
nova.py                 CLI entrypoint and local server launcher
nova/                   core package: API, kernel, storage, ledger, discovery
frontend/               React dashboard
backend/                compatibility layer and older deployment assets
n8n-nodes-nova/         n8n node integration
docs/                   deployment, architecture, API, contribution docs
tests/                  platform, API, discovery, and runtime tests
```

Core design points:

- `nova/platform.py` detects the host and degrades features cleanly.
- `nova/bootstrap.py` installs an isolated runtime instead of polluting system Python.
- `nova/db.py` provides a SQLite fallback for hosts without PostgreSQL.
- `nova/api/server.py` serves both API and dashboard from the same process when the frontend bundle exists.

## Configuration

Copy `.env.example` only when you need persistent local configuration:

```bash
cp .env.example .env
```

At minimum, production-like environments should define:

- `SECRET_KEY`
- `WORKSPACE_ADMIN_TOKEN`
- database settings if you want PostgreSQL
- only the provider keys you actually use

Never commit real `.env` files, tokens, local databases, or operational backups.

## Common commands

```bash
nova
nova commands
nova help
nova init
nova discover --json
nova connect codex_cli-<id> --cannot-do "rm -rf"
nova validate --action "Send email to customer@example.com"
nova status
nova watch
nova serve --host 0.0.0.0 --port 8000
```

## Discovery and governance

- `nova discover --json` returns both discovered agents and a host inventory summary with repositories, active terminals, installed toolchains, and local Codex context.
- Nova computes `recommended_installs` from what it actually sees on the host instead of trying to install every possible developer dependency up front.
- `nova connect <agent_key> --cannot-do "rm -rf"` attaches governance rules directly when onboarding a discovered agent.
- Discovery task execution is routed through Nova's evaluation pipeline before the connector runs, so a matching `cannot_do` rule blocks the task before the agent executes it.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Deployment notes](docs/deployment.md)
- [API reference](docs/api-reference.md)

## Project status

Nova OS is active and installable today. The remaining cleanup is repository hygiene:

- reducing legacy duplication
- tightening public documentation
- keeping the supported runtime path explicit

The goal is straightforward: one repo, one runtime, one local URL, and one public installation story.

## License

Released under the terms in [LICENSE](LICENSE).
