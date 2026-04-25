<div align="center">

```
 ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗      ██████╗ ███████╗
 ████╗  ██║██╔═══██╗██║   ██║██╔══██╗    ██╔═══██╗██╔════╝
 ██╔██╗ ██║██║   ██║██║   ██║███████║    ██║   ██║███████╗
 ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║    ██║   ██║╚════██║
 ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║    ╚██████╔╝███████║
 ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝     ╚═════╝ ╚══════╝
```

**The missing layer in your AI stack.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows%20%7C%20Termux-lightgrey)](https://github.com/sxrubyo/nova-os)
[![npm](https://img.shields.io/badge/npm-nova--os-red)](https://www.npmjs.com/package/nova-os)
[![Version](https://img.shields.io/badge/version-4.0.8%20Supernova-gold)](https://github.com/sxrubyo/nova-os)
[![Status](https://img.shields.io/badge/status-active-brightgreen)](https://github.com/sxrubyo/nova-os)

</div>

---

## What is Nova OS?

Nova sits between your AI agents and the real world.

Every action an agent wants to execute passes through Nova first. Nova evaluates it in under 5ms, logs it to an immutable ledger, and either approves, blocks, or escalates — before anything reaches production.

```
agent wants to act  →  Nova evaluates (<5ms)  →  APPROVED / BLOCKED / ESCALATED  →  world
```

Not another agent. Not another chatbot. **Infrastructure.**

---

## The problem

AI agents execute actions without control. They hallucinate endpoints, send duplicate emails, write to wrong databases, run destructive commands — and nothing stops them.

When something goes wrong: no trace. No brake. No rollback.

Nova fixes that.

---

## Install

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

---

## Quickstart — 2 commands

```bash
# one command. every agent on your machine gets governed.
nova guard

# add a rule instantly in plain language
nova rule "never delete files from /prod"
```

That's it. Nova auto-discovers your agents, injects governance rules, and starts watching.

---

## How it works

```
Score ≥ 70   →  ✓  APPROVED   — executes immediately
Score 40-70  →  ⚠  ESCALATED  — pauses, waits for your decision
Score < 40   →  ✗  BLOCKED    — stopped, logged, explained
```

Every decision is written to the Intent Ledger. Cryptographic. Auditable. Permanent.

---

## Core commands

| Command | What it does |
|---|---|
| `nova init` | 13-step guided setup — agents, rules, policy, model |
| `nova guard` | Auto-discover and protect all agents in one command |
| `nova boot` | Start Nova Core + connect all agents |
| `nova run "<cmd>"` | Wrap any CLI command with risk classification |
| `nova shield` | HTTP proxy — intercept and validate every request |
| `nova protect` | Attach to a live HTTP agent (fire-and-forget) |
| `nova rule "<text>"` | Add a governance rule in plain language — active instantly |
| `nova validate` | Manually validate any action through the pipeline |
| `nova validate batch` | Validate up to 20 actions in parallel |
| `nova simulate` | Test policy without creating tokens or ledger entries |
| `nova watch` | Live-stream every decision as it happens |
| `nova ledger` | Browse the full immutable action history |
| `nova verify` | Check cryptographic chain integrity |
| `nova audit` | Generate a full audit report |
| `nova stats` | Analytics dashboard — risk profiles, anomalies, heatmaps |
| `nova memory` | Store and search agent context semantically |
| `nova scout` | Security scan — detect misconfigurations |
| `nova anomalies` | View detected behavioral anomalies |
| `nova benchmark` | Measure validation latency and throughput |
| `nova mcp export` | Export config as MCP-compatible manifest |
| `nova commands` | Full command reference |

---

## nova init — 13-step guided setup

```
Step 1   Welcome and orientation
Step 2   How Nova works — score system explained
Step 3   Auto-discovery — finds your agents automatically
Step 4   Pre-flight warnings — what Nova can and cannot do
Step 5   First rule — plain language, active immediately
Step 6   Identity — name and organization
Step 7   API key — generate, import, or use saved
Step 8   Server — local or custom URL
Step 9   Connection — cryptographic handshake
Step 10  Intelligence — choose your AI model
Step 11  Governance policy — strict / balanced / permissive / custom
Step 12  Escalation channel — CLI / email / webhook
Step 13  Skills — connect Gmail, Slack, GitHub and more
```

Supported models: **Claude · GPT-4 · Gemini · Groq · Mistral · DeepSeek · Cohere · OpenRouter · Ollama (local)**

---

## nova guard — one command, all agents

```bash
nova guard
```

Nova scans your environment, detects every AI agent running, and puts all of them under governance. No config files. No manual setup per agent.

```bash
nova guard --path .env      # protect a specific path from ALL agents
nova guard --path /prod     # nothing in /prod can be touched
```

---

## nova run — wrap any command

```bash
nova run "pm2 restart melissa"
nova run "rm -rf /tmp/old-logs"
nova run "git push origin main --force"
```

Nova classifies the risk, shows you the verdict, and either executes or blocks. Every run is logged.

---

## nova shield — HTTP proxy

```bash
nova shield
```

Starts a proxy on `127.0.0.1:7755`. Every HTTP request from your agents passes through it. Nova validates the action before forwarding. Nothing reaches your services unexamined.

---

## Agent auto-discovery

Nova detects agents running on your machine automatically:

```
OpenClaw          100% confidence  ● live
Melissa           100% confidence
n8n               100% confidence  ● live
Claude Code       100% confidence
OpenAI Codex CLI  100% confidence
Gemini CLI         50% confidence
GitHub Copilot     45% confidence
Custom OpenAI      35% confidence  ● live
```

---

## Governance flow

```
1. DISCOVER    →  auto-detect agents on your machine
2. CONNECT     →  attach rules: cannot_do, must_confirm, rate_limits
3. INTERCEPT   →  every action passes through Nova before execution
4. EVALUATE    →  deterministic rules + optional LLM validation in <5ms
5. DECIDE      →  APPROVED / BLOCKED / ESCALATED / DUPLICATE
6. LEDGER      →  cryptographic, immutable, permanent record
```

---

## Architecture

```
nova.py              CLI entrypoint + local server launcher
nova/                core: API, kernel, ledger, discovery, storage
frontend/            React dashboard at localhost:9800
n8n-nodes-nova/      n8n native integration
legacy/              compatibility layer — being cleaned up
docs/                deployment, API reference, architecture
tests/               platform, API, discovery, runtime tests
```

**Core design decisions:**

- **Fail-open** — Nova never blocks your work if it goes down
- **LLM-optional** — 90% of validations run without any AI call
- **Hot-reload rules** — update governance policies without restart
- **Immutable ledger** — cryptographic chain, nothing can be deleted
- **Transparent proxy** — wraps agents from outside, zero modification to agent code
- **Offline mode** — actions queue locally and sync when server returns
- **Bilingual** — ES/EN native, no config required

---

## Platform support

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
