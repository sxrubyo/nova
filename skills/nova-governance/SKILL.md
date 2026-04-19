---
name: nova-governance
description: Use when an agent needs to discover local repositories, terminals, toolchains, or active agent runtimes and apply Nova governance rules before acting.
---

# Nova Governance

## Overview

Use Nova as the local control plane before executing risky agent work. Start with host discovery, identify the target runtime, attach explicit `can_do` or `cannot_do` rules, then validate the next action through Nova instead of trusting the agent blindly.

## When To Use

- You need to inspect the current host before coding or operating.
- You want to govern `codex`, `gemini`, `opencode`, `n8n`, HTTP agents, or local processes.
- You need to add a deny rule such as `rm -rf`, secret exfiltration, or direct production writes.
- You want evidence from `nova discover --json` before making a tooling or install decision.

## Core Workflow

1. Discover the host and running agents.

```bash
nova discover --json
```

Look at:
- `agents` for detected runtimes
- `inventory.repositories` and `inventory.terminals`
- `inventory.tooling`
- `inventory.recommended_installs`

2. Attach governance to the selected runtime.

```bash
nova connect codex-cli --cannot-do "rm -rf" --cannot-do "exfiltrate secrets"
```

3. Validate a risky action before execution.

```bash
nova validate --agent codex-cli --action terminal.command --payload '{"command":"rm -rf /tmp/demo"}'
```

4. If the action is allowed, continue through Nova-aware execution paths. If it is blocked, change the plan instead of bypassing policy.

## Quick Patterns

- Inspect the machine before choosing dependencies:

```bash
nova discover --json
```

- Put a CLI under deny rules fast:

```bash
nova connect codex-cli --cannot-do "rm -rf" --cannot-do "git push --force"
```

- Gate a terminal command:

```bash
nova validate --agent codex-cli --action terminal.command --payload '{"command":"git push --force"}'
```

- Govern an HTTP agent:

```bash
nova connect local-http-agent --url http://127.0.0.1:8080 --cannot-do "delete production data"
```

## Operator Notes

- Prefer `nova discover --json` over guessing host state.
- Add the narrowest deny rule that prevents the unsafe behavior.
- Keep rules explicit and test them with `nova validate`.
- Do not bypass Nova for destructive terminal actions once governance is attached.
