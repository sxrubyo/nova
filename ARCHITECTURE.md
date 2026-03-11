# 🏛️ Nova OS Architecture

Nova OS is designed as a high-performance, zero-latency governance layer for autonomous systems. The architecture follows a "Security-by-Design" principle, ensuring that no action is executed without cryptographic verification.

## 🏗️ System Overview
The system is composed of three primary layers:

1. **The Core CLI (nova.py)**: A zero-dependency Python engine that acts as the primary interface. It handles local state, animations, and the arrow-key navigation system.
2. **The Validation API**: A FastAPI-based backend that processes intents, calculates scores, and interfaces with the Memory Engine.
3. **The Intent Ledger**: A PostgreSQL-backed immutable log where every action is hashed and chained to ensure auditability.

## 🔄 The Validation Flow
Every intent follows this lifecycle:
- **Ingestion**: The agent sends an action request via Webhook or CLI.
- **Scoring**: Nova evaluates the intent against active Rule Templates (e.g., Email Safety, Database Guard).
- **Consensus**: A verdict is reached (APPROVED, BLOCKED, ESCALATED).
- **Hashing**: The action, timestamp, and verdict are hashed to create a unique fingerprint.
- **Ledger Entry**: The signed record is written to the immutable ledger.

## 🛠️ Tech Stack
- **Language**: Python 3.8+ (Zero external dependencies for the CLI).
- **Backend**: FastAPI / Uvicorn.
- **Database**: PostgreSQL (Relational integrity for the Ledger).
- **Environment**: Docker & Docker Compose for enterprise-grade deployment.

---
*Architecture defined by Nova OS Engineering.*
