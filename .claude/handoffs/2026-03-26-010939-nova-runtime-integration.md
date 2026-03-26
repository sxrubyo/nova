# Handoff: Nova Runtime Integration

## Session Metadata
- Created: 2026-03-26 01:09:39
- Project: /home/ubuntu/nova-os
- Branch: main
- Session duration: ~3h

### Recent Commits (for context)
  - c1efd51 chore: remove demo and internal-only assets
  - bd3a454 feat: ship frontend refresh and github auth groundwork
  - 9532740 chore: start public installs with empty state
  - bb099a7 feat: add governance runtime modules and harden secret handling
  - 7ee24fc feat: dashboard + logo + glass buttons

## Handoff Chain

- **Continues from**: None (fresh start)
- **Supersedes**: None

> This is the first handoff for this task.

## Current State Summary

This session connected the live dashboard backend on `:8000` to the modular `nova/` runtime without touching the legacy login/session flow. The frontend path `frontend -> backend/main.py -> /assistant/chat|/assistant/execute -> modular Nova runtime` is now working end-to-end in production traffic. Both assistant chat and command execution create runtime records in Postgres (`nova_runtime_*` tables) and are mirrored back into the legacy `ledger` table for the existing UI. The remaining state is operational, not blocked.

## Codebase Understanding

## Architecture Overview

The live frontend does not talk to `nova.py` directly. It proxies `/api` to the legacy backend on port `8000`, and the assistant UI specifically hits `/assistant/chat`, `/assistant/execute`, and `/assistant/models` from `backend/main.py`. Login and workspace auth must stay in that legacy backend because `/auth/me`, session cookies, and `get_workspace` live there. The modular runtime is embedded from the legacy backend through `nova.integrations.legacy_backend`, which initializes `NovaKernel`, syncs the legacy workspace/agent into runtime storage, evaluates the action, then mirrors the decision/result back into legacy ledger surfaces.

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `backend/main.py` | Live backend used by the frontend and PM2/docker stack | Contains `/assistant/chat`, `/assistant/execute`, auth/session flow, runtime bridge loading, and legacy ledger mirroring |
| `nova/integrations/legacy_backend.py` | Embeds the modular runtime from the legacy backend | Chooses runtime DB URL, syncs workspaces/agents, and routes evaluations into `NovaKernel` |
| `nova/storage/models.py` | SQLAlchemy models for runtime persistence | Was changed to use `nova_runtime_*` table names to avoid collisions with legacy Postgres tables |
| `nova/core/pipeline.py` | Runtime evaluation pipeline | Persists runtime evaluations and drives ledger/memory/metrics writes after decisions |
| `frontend/vite.config.js` | Frontend API proxy | Confirms the frontend reaches the legacy backend on `127.0.0.1:8000`, not `nova.py` directly |
| `/home/ubuntu/.codex/skills/video-to-website/SKILL.md` | Custom skill organized this session | Moved from loose `SKILL.md` into a proper skill folder and normalized skill reference name |

## Key Patterns Discovered

- The live backend runs inside a separate mount namespace with `/app` as the effective project root; `backend/main.py` is mirrored there as the active app entrypoint.
- The modular runtime should be treated as an embedded control plane, not a replacement for the legacy auth/backend surface.
- Legacy and modular persistence must stay separated in Postgres. Sharing legacy table names such as `workspaces` caused schema collisions; the runtime now uses `nova_runtime_*` tables.
- When debugging live traffic here, database evidence is more reliable than assuming which code path ran. We verified runtime usage through `nova_runtime_ledger_records` and legacy UI sync through `ledger`.

## Work Completed

## Tasks Finished

- [x] Organized the loose skill file into `/home/ubuntu/.codex/skills/video-to-website/SKILL.md`
- [x] Traced the real live path used by the frontend and confirmed it terminates in `backend/main.py` on port `8000`
- [x] Added legacy-backend-to-runtime bridge logic so `/assistant/chat` and `/assistant/execute` call the modular runtime
- [x] Fixed runtime loading in the live backend container by resolving the correct repo root and syncing the `nova/` package into `/app`
- [x] Fixed runtime persistence collision by moving runtime tables to `nova_runtime_*` names in Postgres
- [x] Verified live end-to-end writes for assistant chat and assistant execute in both runtime Postgres tables and legacy `ledger`
- [x] Hardened legacy mirror code so partial request context does not crash `_mirror_runtime_evaluation_to_legacy`

## Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| `backend/main.py` | Added runtime repo-root detection, bridge warmup, token sync helpers, runtime mirroring, assistant chat/execute delegation, metadata normalization, and safe ctx access | Connect the existing frontend/backend flow to modular Nova without breaking login |
| `nova/integrations/legacy_backend.py` | Added `DATABASE_URL` fallback and asyncpg conversion logic | Let the embedded runtime use the live backend Postgres DB instead of falling back to container-local SQLite |
| `nova/storage/models.py` | Renamed runtime tables to `nova_runtime_workspaces`, `nova_runtime_agents`, `nova_runtime_evaluations`, `nova_runtime_ledger_records`, `nova_runtime_memories` | Prevent schema collisions with existing legacy Postgres tables |
| `nova/workspace/permissions.py` | Made JWT import tolerant when JWT libraries are absent | Avoid hard import failure when auth helpers are unused in embedded runtime flows |
| `/home/ubuntu/.codex/skills/video-to-website/SKILL.md` | Moved loose skill into proper folder and fixed `frontend-skill` reference | Clean up skill discovery and make it usable in future turns |

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Keep login/session flow in `backend/main.py` | Move auth to modular Nova, proxy everything through `nova.py`, keep auth legacy | Preserving working login was a hard requirement and the frontend already depends on the legacy backend surface |
| Embed modular Nova from the legacy backend | Replace backend with modular API, add separate sidecar service, embed kernel | Embedding minimized frontend changes and let the assistant routes adopt runtime evaluation immediately |
| Use `nova_runtime_*` Postgres tables | Reuse legacy tables, coerce runtime model types to match legacy `workspaces`, stay on SQLite | Dedicated runtime tables avoid schema drift/collision and keep ownership boundaries clean |
| Sync `nova/` into `/app` | Rebuild the whole container image, keep trying from host only, patch around missing imports | The live backend process could not import `nova`; syncing the package solved the actual runtime path in-place |

## Pending Work

## Immediate Next Steps

1. Verify the actual frontend "Talk with your agent" UI path in a browser and confirm it reflects the new runtime-backed ledger entries without manual curls.
2. Decide whether to keep or remove the container-local `nova.db`; it is no longer the desired runtime store for live traffic, but historical debug writes remain there.
3. Clean up the container/runtime deployment path so `/app/nova` is sourced from the repo or image build formally instead of ad hoc syncing.

## Blockers/Open Questions

- [ ] Deployment hygiene: the current live fix depends on the `nova/` package being present in `/app` inside the running backend namespace. It works now, but should be made part of the image/build process.
- [ ] PM2 path mismatch: a separate `nova.py shield --listen 0.0.0.0:9002` process still exists and is not the path the frontend uses. Decide whether to keep, rewire, or remove it.

## Deferred Items

- Formalize runtime packaging into the backend container/image. Deferred because the urgent goal was restoring live assistant connectivity first.
- Audit whether all runtime subsystems that currently use Postgres should get explicit migrations. Deferred because runtime CRUD now works with `create_all`.

## Context for Resuming Agent

## Important Context

The most important fact is that the live UI was never broken at the frontend layer; it was wired to the wrong backend/runtime path. The dashboard frontend proxies to the legacy backend on `:8000`, so the correct integration point was `backend/main.py`, not `nova.py` or the standalone `nova-api` process. The backend initially fell back because the live `/app` runtime could not import `nova`, then because the embedded runtime defaulted to SQLite, and then because runtime models collided with legacy Postgres tables. All of those are now fixed. Current live evidence:

- `GET /assistant/models` shows `openrouter` available.
- `POST /assistant/chat` creates legacy ledger rows like `id=38` and runtime rows such as `eval_39054f8d9175413d`.
- `POST /assistant/execute` creates legacy ledger rows like `id=39` and runtime rows such as `eval_8068e090484f0a08`.
- Postgres now contains `nova_runtime_agents=1`, `nova_runtime_evaluations=6`, `nova_runtime_ledger_records=5` as of the end of this session.

If something regresses later, the first checks should be:
1. Is the live backend worker still running from `/app`?
2. Does `/app/nova` still exist in that namespace?
3. Do new assistant actions create rows in `nova_runtime_ledger_records` and `ledger`?

## Assumptions Made

- The frontend continues to rely on `backend/main.py` for auth/session and assistant routes.
- The Postgres instance at `db:5432` inside the backend namespace and `127.0.0.1:5432` from the host are the same logical database.
- OpenRouter remains the active available provider in the live backend environment.

## Potential Gotchas

- `uvicorn --reload` respawns child workers; always confirm the current worker PID before inspecting `/proc/<pid>/environ`.
- `/app` only exists inside the backend process mount namespace. From the host you must use `/proc/<uvicorn-pid>/root/app` or `nsenter`.
- Legacy `workspaces` and runtime `workspace` concepts are intentionally separate now. Do not rename runtime tables back to generic names or Postgres collisions will return.
- `backend/main.py` is mirrored as the live `/app` backend entrypoint inside the container namespace, but the `nova/` package was not automatically present there until it was synced.

## Environment State

## Tools/Services Used

- Live backend: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Postgres: legacy backend DB plus runtime `nova_runtime_*` tables in the same logical database
- Runtime provider: OpenRouter
- Shell debugging: `nsenter`, `/proc/<pid>/root/app`, direct `curl`, direct `asyncpg` queries

## Active Processes

- `uvicorn` parent process PID `4081952` on port `8000`
- Current worker PID changed during reloads; verify with `ps -ef | rg "uvicorn main:app|multiprocessing.spawn"`
- Separate `nova.py shield --listen 0.0.0.0:9002` process still exists but is not on the critical path for the frontend assistant

## Environment Variables

- `DATABASE_URL`
- `OPENROUTER_API_KEY`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `SECRET_KEY`
- `WORKSPACE_ADMIN_TOKEN`
- `FRONTEND_URL`
- `SESSION_COOKIE_NAME`

## Related Resources

- `backend/main.py`
- `nova/integrations/legacy_backend.py`
- `nova/storage/models.py`
- `nova/core/pipeline.py`
- `frontend/vite.config.js`
- `/home/ubuntu/.codex/skills/systematic-debugging/SKILL.md`
- `/home/ubuntu/.codex/skills/session-handoff/SKILL.md`

---

**Security Reminder**: Before finalizing, run `validate_handoff.py` to check for accidental secret exposure.
