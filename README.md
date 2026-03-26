# Nova OS v4.0.0

```text
╔══════════════════════════════════════════════╗
║                                              ║
║     ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗     ║
║     ████╗  ██║██╔═══██╗██║   ██║██╔══██╗    ║
║     ██╔██╗ ██║██║   ██║██║   ██║███████║    ║
║     ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║    ║
║     ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║    ║
║     ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝    ║
║                                              ║
║           Nova OS v4.0.0 (Enterprise)        ║
║         AI Governance Control Plane          ║
║                                              ║
╚══════════════════════════════════════════════╝
```

Nova OS es un control plane para agentes autónomos. Intercepta acciones, evalúa riesgo, decide `ALLOW/BLOCK/ESCALATE`, registra cada decisión en un ledger con hash chain y ejecuta acciones aprobadas por medio de providers o integraciones seguras.

## Quick Start

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python nova.py start
```

Servicios por defecto:

- API: `http://0.0.0.0:9800`
- Docs: `http://0.0.0.0:9800/api/docs`
- Bridge: `ws://0.0.0.0:9700`

## Arquitectura

- `nova/kernel.py`: orquestador principal.
- `nova/core/`: pipeline, análisis de intención, motor de riesgo, decisión y ejecución.
- `nova/ledger/`: audit trail con hash chain.
- `nova/gateway/`: router multi-provider con failover.
- `nova/security/`: reglas, sensibilidad, loops, bursts y anomalías.
- `nova/memory/`: core, episodic y working memory.
- `nova/workspace/`: workspaces, agentes, permisos y cuotas.
- `nova/api/`: FastAPI con rutas tipadas.
- `nova/bridge/`: WebSocket bridge para agentes en tiempo real.
- `nova/storage/`: SQLAlchemy async, modelos y repositorios.

## CLI

```bash
python nova.py start
python nova.py status
python nova.py evaluate --agent agent-alpha --action generate_response --payload '{"messages":[{"role":"user","content":"hello"}]}'
python nova.py agents list
python nova.py ledger verify
python nova.py gateway status
python nova.py seed
```

## Testing

```bash
make test
```

## Docs

- `docs/architecture.md`
- `docs/api-reference.md`
- `docs/deployment.md`
- `docs/contributing.md`
