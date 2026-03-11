# 🤝 Contributing to Nova OS
**Maintained by Nova Governance**

Thank you for your interest in strengthening Nova. We are building industry-grade infrastructure for AI agent governance, and we value contributions that advance security, performance, and clarity.

## ⚖️ Our Philosophy
- **Zero Dependencies**: Nova's core must remain lightweight. We strictly use standard Python 3.8+. Do not introduce external libraries without a critical justification.
- **Extreme Speed**: If a validation cycle exceeds 50ms, the code is not production-ready. Performance is a feature.
- **Cryptographic Integrity**: The Ledger is the heart of Nova. Any changes to signature or hashing logic must be discussed with maximum priority.
- **Version Compatibility**: Update CLI help strings, error payloads, and documentation when behavior changes.

## 🛠️ How to Get Started

1. **Fork the repository** and clone it to your local environment.
2. **Create a feature branch**: `git checkout -b feature/amazing-improvement`.
3. **Develop with Quality**: Write clean, self-documented code and utilize Python type hinting.
4. **Technical Verification**: Run `python nova.py status` (backend required) to ensure core paths remain intact.
5. **Pull Request**: Submit your changes with a clear description of the impact and technical reasoning.

## 📝 Code Standards
- **Full Compatibility**: Code must run flawlessly across Windows (PowerShell), macOS, and Linux.
- **User Experience (UX)**: If modifying the CLI, respect the existing visual language and arrow-key navigation system.
- **Documentation**: If you add a feature, update internal manuals, help strings, and any version references.

## 🐛 Bug Reporting
If you encounter a flaw, please open an **Issue** including:
- Operating system and Python version.
- Exact steps to replicate the issue.
- Expected behavior vs. actual outcome.

## 💡 Skill Suggestions
Do you have an idea for a new CRM integration or a payment gateway "Skill"? Suggestions for expanding the **Constellation** are always welcome.

---
**Executive Contact:** `Nova Governance`  
*Building the nervous system of AI together.*
