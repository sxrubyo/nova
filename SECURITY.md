# 🛡️ Security Policy

At Nova OS, security is not a feature—it is our core identity. This document outlines our security protocols and how to report vulnerabilities.

## 🔑 Security Principles
- **Least Privilege**: Agents are granted only the minimum access required for their specific intent.
- **Auditability**: Every action is cryptographically signed and stored in an immutable ledger.
- **Zero Trust**: No internal or external action is considered safe until it is scored and validated.

## 🚨 Reporting a Vulnerability
We take security issues seriously. If you discover a vulnerability, please do not open a public issue. Instead, follow this process:
1. **Report**: Send an encrypted email to `enterprise@nova-os.com`.
2. **Verification**: Our team will acknowledge the receipt within 24 hours.
3. **Disclosure**: We will work with you to patch the issue before a public disclosure is made.

## 🔒 API Key Management
- Keys are generated locally using `secrets.token_hex(16)`.
- The CLI implements key masking (`nova_xxxx••••xxxx`) to prevent accidental exposure in logs or screenshots.
- Keys are stored in a local encrypted keychain at `~/.nova/keys.json`.

---
**Nova OS Security Team** *Building a safer future for autonomous agents.*
