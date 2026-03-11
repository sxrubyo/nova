# ✦ Nova OS — Enterprise Governance for AI Agents
**Maintained by @sxrubyo**

<p align="center">
  <img src="https://img.shields.io/badge/version-3.1.5-black?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/python-3.8+-blue?style=for-the-badge" alt="Python">
  <img src="https://img.shields.io/badge/license-AGPL--3.0-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/dependencies-zero-red?style=for-the-badge" alt="Zero Dependencies">
</p>

<p align="center">
  <strong>The firewall between your AI agents and the real world.</strong>
</p>

---

## 🎯 Why Nova OS?

AI agents are powerful—but without oversight, they're a **liability**. Nova OS is an enterprise governance layer that enforces policy, validates intent, and produces **immutable cryptographic proof** of every decision.

### **Core Capabilities**

| Feature | Description |
|---------|-------------|
| 🔐 **Intent Validation** | Every action is scored against your rules before execution (APPROVED/BLOCKED/ESCALATED/DUPLICATE) |
| 📜 **Immutable Ledger** | Cryptographic audit trail—tamper-proof and permanent |
| 🧠 **Memory Engine** | Agents remember context across executions |
| 🛡️ **Duplicate Guard** | Prevents repeated/similar actions automatically |
| 🤖 **Response Generation** | Approved responses generated inline (optional LLM) |
| ⚡ **Offline Queue** | Actions sync automatically when server reconnects |
| 📊 **Enterprise Dashboard** | Real-time metrics and health monitoring |
| 🔌 **12+ Integrations** | Gmail, Slack, Stripe, GitHub, PostgreSQL, and more |

---

## ⚡ Installation

### **One-Command Install**

```bash
# Linux / macOS
curl -sSL https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.ps1 | iex

# Docker (Recommended for production)
docker-compose -f https://raw.githubusercontent.com/sxrubyo/nova-os/main/docker-compose.yml up -d
```

### **Manual Installation**

```bash
# Clone repository
git clone https://github.com/sxrubyo/nova-os.git
cd nova-os

# Install CLI
pip install --user .

# Or run directly (zero dependencies)
python nova.py --help
```

---

## 🚀 Quick Start

### **1. Initialize Nova**
```bash
nova init
```
Follow the interactive wizard (7 steps, ~2 minutes). You will configure:
1. How Nova works (validation, ledger, scoring)
2. Risks & terms (safety guardrails)
3. Identity (name and org)
4. API key setup + documentation link
5. Server selection (local or custom)
6. Connection test
7. Skills setup (optional)

### **2. Create Your First Agent**
```bash
nova agent create
```
Choose from 8 pre-built templates or define custom rules.

### **3. Validate an Action**
```bash
nova validate --action "Send email to customer@example.com"
```
Output:
```
  ✓ APPROVED   [██████░░] 92/100   45ms
  Reason: Aligned with authorized communication rules
  Agent: Email Agent
  Ledger: #1847
```

### **4. Monitor in Real-Time**
```bash
nova watch
```
Live stream of all ledger entries as they happen.

---

## 📊 Dashboard & Metrics

```bash
nova status
```

```
  ✦ Nova OS v3.1.5
  ════════════════════════════════════════════════

  Server: https://api.nova-os.com
  Status: Connected
  Version: 3.1.5-shadow

  Activity
  ────────────────────────────────
  Total actions:      1,247
  Approved:         1,189 (95.3%)
  Blocked:             47 (3.8%)
  Escalated:           11 (0.9%)
  Duplicates:           8 (0.6%)

  Resources
  ────────────────────────────────
  Active agents:        3
  Memories stored:    127
  Avg score:           87
  Pending alerts:       2
```

---

## 🔌 Connected Skills

Extends Nova's governance to external systems:

| Category | Skills |
|----------|--------|
| **Communication** | ✉️ Gmail, ◈ Slack, ◉ WhatsApp, ◎ Telegram |
| **Data** | ⊞ Google Sheets, ◈ Airtable, ◻ Notion |
| **Development** | ◯ GitHub, ◈ Supabase, ◉ PostgreSQL |
| **Business** | ◈ Stripe, ◉ HubSpot |
| **Productivity** | ✉️ Email, 📅 Calendar (coming soon) |

**Install a skill:**
```bash
nova skill add slack
```
Follow the interactive setup wizard.

---

## 🔐 API Key Management

```bash
# List keys
nova keys

# Create new key
nova keys create

# Switch active key
nova keys use
```

**Features:**
- Local keychain encryption
- Secure generation with `secrets.token_hex()`
- Automatic clipboard copy
- Key masking in CLI (`nova_xxxx••••xxxx`)

---

## 📦 Enterprise Features

### **Signed Audit Reports**
```bash
nova audit --output report.json
```
Generates SHA-256 signed JSON with full chain verification.

### **Offline Queue**
Actions are queued locally if server is unreachable:
```bash
nova sync  # Process queue when back online
```

### **Multi-Profile Support**
Switch between dev/staging/prod environments:
```bash
nova config → Profiles
```

### **Shell Autocompletion**
```bash
# Bash
eval "$(nova completion bash)"

# Zsh
eval "$(nova completion zsh)"

# Fish
nova completion fish > ~/.config/fish/completions/nova.fish
```

---

## 🎨 Premium UI Features

- **Arrow-Key Navigation**: Full keyboard control (↑↓ Enter)
- **Ghost Writing**: Text appears letter-by-letter
- **Agent Wake-up**: Cinematic startup sequence
- **Progress Bars**: Real-time feedback for long operations
- **Sparklines**: Inline visualizations (`▁▂▃▄▅▆▇█`)
- **Relative Timestamps**: "2h ago", "3d ago"

---

## 🛠️ Configuration

All configuration is stored in `~/.nova/`:

```
~/.nova/
├── config.json       # Main config
├── keys.json         # API keychain
├── profiles.json     # Multi-env profiles
├── history.json      # Command history
├── offline_queue.json # Sync queue
├── sessions/         # Session artifacts (future-proofed)
├── skills/           # Skill configs
└── logs/             # CLI logs (when enabled)
```

**Environment Variables:**
```bash
export NOVA_DEBUG=1          # Enable debug logs
export NOVA_VERBOSE=1        # Enable verbose output
export NO_COLOR=1            # Disable colors
export NOVA_SERVER=https://api.your-domain.com
```

**Security Defaults (Local Only):** The `docker-compose.yml` file ships with development defaults for `POSTGRES_PASSWORD` and `SECRET_KEY`. Override them via environment variables (or a `.env` file) before any production deployment. The frontend dashboard uses a demo API key by default; set `localStorage.setItem('nova_api_key', '...')` in the browser or front the `/api` path with an auth-protecting reverse proxy.

---

## 🚀 Deployment Options

### **Local Development**
```bash
docker-compose up -d
```

### **Cloud Deployment**
- **AWS ECS**: [docs.nova-os.com/aws](https://docs.nova-os.com/aws)
- **Google Cloud Run**: [docs.nova-os.com/gcp](https://docs.nova-os.com/gcp)
- **DigitalOcean**: 1-click deploy available

### **Managed Cloud**
Contact us for Nova Cloud: `sxrubyo@gmail.com`

---

## 📚 Documentation

- **Full Docs**: [docs.nova-os.com](https://docs.nova-os.com)
- **API Reference**: [api.nova-os.com/docs](https://api.nova-os.com/docs)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Security**: [SECURITY.md](SECURITY.md)

---

## 🤝 Contributing

We love contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/sxrubyo/nova-os.git
cd nova-os
pip install -r requirements-dev.txt
pytest tests/
```

---

## 📈 Roadmap

- **Q1 2025**: Multilingual agents, advanced analytics dashboard
- **Q2 2025**: Team workspaces, RBAC, SSO integration
- **Q3 2025**: Custom scoring models, plugin marketplace
- **Q4 2025**: Distributed ledger, blockchain integration

---

## 💼 Enterprise Support

| Plan | Features | Price |
|------|----------|-------|
| **Community** | Full CLI, self-hosted server | Free (AGPL-3.0) |
| **Team** | Cloud hosting, 5 agents, email support | $49/mo |
| **Enterprise** | On-premise, unlimited agents, 24/7 support | Contact us |

**Contact:** `sxrubyo@gmail.com` | **Discord:** [discord.gg/nova](https://discord.gg/nova)

---

## 📝 License

**Nova CLI**: AGPL-3.0 — Free for personal and commercial use, source code must remain open.

**Nova Server**: Commercial license required for enterprise deployments.

---

<p align="center">
  <strong>Intelligence with limits. Actions with proof.</strong><br>
  Built with ❤️ by the Nova OS team.
</p>
