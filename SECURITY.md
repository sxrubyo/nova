# Security Policy

Security is a core concern for Nova OS because the project sits between autonomous systems and real side effects.

## Security principles

- Least privilege for agent execution paths
- Verifiable audit trails for critical decisions
- Clear error boundaries and traceable failures
- No bundled secrets in public distributions

## Reporting a vulnerability

Do not post security-sensitive issues publicly.

Preferred reporting path:

1. Use GitHub private vulnerability reporting if it is enabled for this repository.
2. If that is not available, contact the repository maintainers privately before disclosure.

Please include:

- affected version or commit
- reproduction steps
- impact assessment
- proposed mitigation if you have one

## Secrets and local state

- Treat `~/.nova/` as sensitive local state.
- Do not commit `.env` files, tokens, or local databases.
- Public installs should start empty: no seeded admin token, no seeded workspace, no preloaded ledger.

## Production basics

- Replace all development credentials before exposing Nova to untrusted networks.
- Prefer TLS termination in front of any public deployment.
- Restrict who can access operator endpoints and dashboard routes.
- Review provider keys and workspace tokens regularly.
