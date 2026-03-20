# 🛡️ Security Policy
**Maintained by Nova Governance**

At Nova OS, security is a first-class requirement. This document outlines our security principles and how to report vulnerabilities.

## 🔑 Security Principles
- **Least Privilege**: Agents are granted only the minimum access required for their specific intent.
- **Auditability**: Every action is cryptographically signed and stored in an immutable ledger.
- **Zero Trust**: No internal or external action is considered safe until it is scored and validated.
- **Deterministic Accountability**: Each API error includes a stable error code and optional request ID for traceability.

## 🚨 Reporting a Vulnerability
We take security issues seriously. If you discover a vulnerability, please do not open a public issue. Instead, follow this process:
1. **Report**: Send an encrypted email to `Nova Governance`.
2. **Verification**: Our team will acknowledge the receipt within 24 hours.
3. **Disclosure**: We will work with you to patch the issue before a public disclosure is made.

## 🔒 API Key Management
- Keys are generated locally using `secrets.token_hex(16)`.
- The CLI implements key masking (`nova_xxxx••••xxxx`) to prevent accidental exposure in logs or screenshots.
- Keys are stored in a local keychain at `~/.nova/keys.json` with restrictive file permissions on POSIX systems.
- Config, profiles, and offline queue files are stored locally; treat the `~/.nova/` directory as sensitive.

## 🔍 Error Traceability
Nova standardizes API error payloads with:
- `error`: human-readable message
- `code`: stable error code (e.g., `HTTP_401`, `RATE_LIMIT`)
- `request_id`: optional request identifier for support and audits

## 🧪 Development Defaults
The default `docker-compose.yml` ships with development credentials for local use. Replace `POSTGRES_PASSWORD` and `SECRET_KEY` before exposing the system to untrusted networks. Public installs are expected to start empty: no bundled workspace, no seeded API key, and no preloaded ledger data.

---
**Nova OS Security Team** *Building a safer future for autonomous agents.*
