# Architecture

Nova OS se organiza alrededor de un kernel asincrónico que coordina:

- evaluación de intenciones
- scoring de riesgo
- decisiones allow/block/escalate
- ledger inmutable
- memoria contextual
- routing de providers
- bridge WebSocket
- API HTTP

El pipeline central vive en `nova/core/pipeline.py` y es consumido tanto por la API como por el bridge.
