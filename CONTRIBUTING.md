# Contributing to Nova OS

Thanks for contributing.

Nova OS is being cleaned up into a sharper open-source surface. Contributions are most useful when they improve portability, runtime coherence, security, or developer clarity without adding unnecessary product branches.

## Ground rules

- Keep the supported runtime path centered on `nova.py` + `nova/`.
- Do not commit secrets, `.env` files, local databases, or operational backups.
- Avoid hardcoded machine-specific paths.
- Prefer changes that reduce external dependencies instead of increasing them.
- Update documentation when behavior changes.

## Development workflow

1. Fork the repository.
2. Create a feature branch.
3. Make focused changes.
4. Run the relevant verification commands.
5. Open a pull request with a clear technical description.

## Minimum verification

```bash
python3 -m pytest
cd frontend && npm run build
```

If your change touches installation or bootstrap behavior, also run:

```bash
bash -n install.sh
npm pack --dry-run
```

## Scope guidance

Good contributions:

- installation fixes
- portability improvements
- API correctness
- frontend and CLI coherence
- security and runtime hardening
- documentation that matches real behavior

Changes that usually need extra care:

- new deployment paths
- dependency-heavy integrations
- changes to signing, ledger, or auth flows
- anything that introduces another “official” runtime path

## Pull request quality bar

A good PR should explain:

- what changed
- why it changed
- how it was verified
- whether it affects the supported runtime path

## Issues

Bug reports are most useful when they include:

- operating system
- Python and Node versions
- exact commands used
- expected behavior
- actual behavior

For security-sensitive issues, follow [SECURITY.md](SECURITY.md).
