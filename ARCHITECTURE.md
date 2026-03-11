# 🏛️ Nova OS Architecture
**Maintained by @sxrubyo**

Nova OS v3.0.0 is a high-performance, zero-latency governance layer for autonomous systems. The architecture follows a Security-by-Design principle: no action is executed without cryptographic verification, and every decision is traceable.

## 🏗️ System Overview
The system is composed of three primary layers:

1. **The Core CLI (nova.py)**: A zero-dependency Python engine that acts as the primary interface. It handles local state, animations, and the arrow-key navigation system.
2. **The Validation API**: A FastAPI backend that processes intents, calculates scores (heuristic or LLM), enforces duplicate detection, and triggers alerts.
3. **The Intent Ledger**: A PostgreSQL-backed immutable log where every action is hashed and chained to ensure auditability.

Supporting services in v3.0.0:
- **Memory Engine**: relevance-based context retrieval and auto-save.
- **Duplicate Guard**: similarity-based suppression with time windows.
- **Alert System**: escalations and violations routed into alerts.
- **Analytics Engine**: usage metrics, score trends, and operational stats.

## 🔄 The Validation Flow
Every intent follows this lifecycle:
- **Ingestion**: The agent sends an action request via Webhook or CLI.
- **Scoring**: Nova evaluates the intent against active rules (heuristic or LLM).
- **Duplicate Check**: A similarity window prevents repeated actions.
- **Consensus**: A verdict is reached (APPROVED, BLOCKED, ESCALATED, DUPLICATE).
- **Hashing**: The action, timestamp, and verdict are hashed to create a unique fingerprint.
- **Ledger Entry**: The signed record is written to the immutable ledger.
- **Alerts + Memory**: Violations create alerts; key context is stored for future decisions.

## 🛠️ Tech Stack
- **Language**: Python 3.8+ (Zero external dependencies for the CLI).
- **Backend**: FastAPI / Uvicorn.
- **Database**: PostgreSQL (Relational integrity for the Ledger).
- **Environment**: Docker & Docker Compose for enterprise-grade deployment.

---
*Architecture defined by Nova OS Engineering.*
