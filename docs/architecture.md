# Architecture

Nova OS is organized around an async kernel that coordinates:

- intent evaluation
- risk scoring
- allow/block/escalate decisions
- immutable ledger entries
- contextual memory
- provider routing
- WebSocket bridge logic
- HTTP API handling

The central execution flow lives under `nova/` and is consumed by both the API surface and the operational runtime.
