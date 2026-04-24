<div align="center">

```
 ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗      ██████╗ ███████╗
 ████╗  ██║██╔═══██╗██║   ██║██╔══██╗    ██╔═══██╗██╔════╝
 ██╔██╗ ██║██║   ██║██║   ██║███████║    ██║   ██║███████╗
 ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║    ██║   ██║╚════██║
 ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║    ╚██████╔╝███████║
 ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝     ╚═════╝ ╚══════╝
```

**Governance runtime for AI agents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows%20%7C%20Termux-lightgrey)](https://github.com/sxrubyo/nova-os)
[![npm](https://img.shields.io/badge/npm-nova--os-red)](https://www.npmjs.com/package/nova-os)
[![Status](https://img.shields.io/badge/status-active-brightgreen)](https://github.com/sxrubyo/nova-os)

</div>

---

## What is Nova OS?

Nova OS sits between your AI agents and the real world.

Every action an agent wants to execute — send an email, write to a database, call an API, run a command — passes through Nova first. Nova evaluates it, logs it, and either approves or blocks it before anything reaches production.

```
agent wants to act  →  Nova evaluates  →  APPROVED / BLOCKED / ESCALATED  →  world
```

Not another agent. Not another chatbot. **Infrastructure.**

---

## The problem

AI agents execute actions without control. They hallucinate endpoints, send duplicate emails, write to wrong databases, run destructive commands — and nothing stops them.

When something goes wrong: no trace. No brake. No rollback.

Nova fixes that.

---

## What Nova does

```
✔  Validates   every agent action against your rules before execution
✔  Blocks      duplicates, risky operations, and policy violations
✔  Logs        every decision to an immutable ledger
✔  Escalates   ambiguous actions for human review
✔  Wraps       any agent as a transparent proxy — zero agent modification
```

---

## Quick Install

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.ps1 | iex
```

**npm:**
```bash
npm install -g nova-os
nova
```

**Termux (Android, no root):**
```bash
pkg install python git openssl
curl -fsSL https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.sh | bash
```

**Docker:**
```bash
cp .env.example .env
docker-compose up -d --build
```

Then open: `http://localhost:8000`

---

## Quickstart

```bash
# discover agents running on your machine
nova discover --json

# attach governance rules to an agent
nova connect codex-cli --cannot-do "rm -rf"

# validate an action before it executes
nova validate --agent codex-cli \
  --action terminal.command \
  --payload '{"command":"rm -rf /tmp/demo"}'

# watch the ledger live
nova watch
```

---

## Core Commands

| Command | What it does |
|---|---|
| `nova` | Interactive launcher |
| `nova serve` | Start API + dashboard on `localhost:8000` |
| `nova discover` | Detect agents and host context |
| `nova connect <agent>` | Attach governance rules to an agent |
| `nova validate` | Evaluate an action through the pipeline |
| `nova status` | Runtime health check |
| `nova watch` | Live ledger stream |
| `nova commands` | Full command reference |

---

## Agent Skill Bridge

Nova injects its governance layer directly into your coding agents:

```bash
nova skill install --agent codex
nova skill install --agent gemini
nova skill install --agent opencode
```

Supported: **Codex · Gemini CLI · OpenCode · Claude Code**

---

## Governance Flow

```
1. DISCOVER    →  detect agents and host inventory
2. CONNECT     →  attach rules: cannot_do, must_confirm, rate_limits
3. INTERCEPT   →  every action passes through Nova before execution
4. EVALUATE    →  deterministic rules + optional LLM validation
5. DECIDE      →  APPROVED / BLOCKED / ESCALATED / DUPLICATE
6. LEDGER      →  immutable record of every decision
```

---

## Architecture

```
nova.py                 CLI entrypoint + local server launcher
nova/                   core: API, kernel, ledger, discovery, storage
frontend/               React dashboard (served by the same process)
n8n-nodes-nova/         n8n integration
docs/                   deployment, API reference, architecture
tests/                  platform, API, discovery, runtime tests
```

**Core design decisions:**

- **Fail-open** — Nova never blocks your work if it goes down
- **LLM-optional** — core validation runs without any AI dependency
- **Hot-reload rules** — update governance policies without restart
- **Immutable ledger** — every decision is permanent and traceable
- **Transparent proxy** — wraps agents from outside, zero agent modification required

---

## Platform Support

| Platform | Status |
|---|---|
| Linux | ✅ Full support |
| macOS | ✅ Full support |
| Windows | ✅ PowerShell installer |
| Termux (Android) | ✅ No root required |
| Docker | ✅ Compose stack included |

---

## Configuration

```bash
cp .env.example .env
```

Minimum for production:
```env
SECRET_KEY=your-secret-key
WORKSPACE_ADMIN_TOKEN=your-token
```

PostgreSQL optional. SQLite by default. Never commit `.env` files.

---

## Contributing

Nova OS is early and open. Issues, PRs and feedback welcome.

If you are building something on top of it — reach out.

---

<div align="center">

Built by [sxrubyo](https://github.com/sxrubyo) · Black & Boss · MIT License

</div>
