# Nova OS

Nova OS es una capa de gobernanza para agentes y automatizaciones. El repo combina backend FastAPI, frontend React, CLI y conectores para validar acciones, registrar evidencia y operar agentes desde una sola superficie.

Este árbol está en transición desde un entorno de producto interno a un repo público más limpio. La regla de este README es simple: no prometer nada que el código o la documentación local no puedan respaldar.

## Qué incluye hoy

- Backend FastAPI para workspaces, evaluación, discovery, ledger y conectores.
- Frontend React/Vite para dashboard, discovery y administración.
- CLI `nova` para inicialización, validación, monitoreo y utilidades operativas.
- Integración n8n (`n8n-nodes-nova/`) para validación y registro desde workflows.
- Docker Compose para levantar el stack local.

## Estructura

```text
backend/               API legacy y compatibilidad operativa
frontend/              aplicación React
nova/                  paquete modular principal
n8n-nodes-nova/        nodo e integración para n8n
docs/                  arquitectura, API y despliegue
tests/                 suite de backend y discovery
```

## Requisitos

- Python 3.10+
- Node.js 20+ para compilar el frontend
- Docker y Docker Compose solo si quieres el stack local completo

## Arranque local

### Opción 1: stack completo con Docker

```bash
cp .env.example .env
docker-compose up -d --build
```

Ese stack ahora usa el runtime modular real (`python3 nova.py serve`) detrás de PostgreSQL y construye el frontend desde `frontend/`, en vez de depender del backend legacy.

### Opción 2: desarrollo por separado

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 nova.py serve --host 0.0.0.0 --port 8000
```

Si existe `frontend/dist`, ese mismo proceso sirve el dashboard en `http://localhost:8000` y mantiene la API en `/api/*`.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

CLI:

```bash
python nova.py --help
```

## CLI profesional (`npm` + runtime aislado)

Si quieres exponer `nova` como comando global sin depender de `pip` del sistema:

```bash
npm install -g nova-os
nova --help
```

Ese binario no instala dependencias Python en el sistema. En el primer uso crea un runtime aislado en `~/.nova/runtime`, instala ahí los requisitos de Nova y luego ejecuta [nova.py](/home/ubuntu/nova-os/nova.py).

Si el paquete todavía no está publicado en el registry, instala el tarball directo por HTTPS para evitar el camino `git+ssh` que rompe fácil en Termux:

```bash
npm install -g https://codeload.github.com/sxrubyo/nova-os/tar.gz/refs/heads/main
nova --help
```

También funciona sin instalación global:

```bash
npx nova-os --help
```

Una vez instalado, el entrypoint local queda en:

```text
http://localhost:8000
```

## 📱 Termux / Android Installation

Nova OS corre nativamente en Android vía Termux sin root.

### Prerrequisitos

```sh
pkg install python git openssl
```

### Instalación

```sh
TMPDIR="$(mktemp -d)" && \
curl -L https://github.com/sxrubyo/nova-os/archive/refs/heads/main.tar.gz | tar -xz -C "$TMPDIR" && \
sh "$TMPDIR/nova-os-main/install.sh"
```

En Termux, Nova:

- usa SQLite en `~/.nova/nova.db`
- crea un runtime Python aislado en `~/.nova/runtime`
- evita Docker, nginx y PostgreSQL
- arranca en segundo plano con `nohup`
- guarda logs y PID en `~/.nova/`
- puede aprovechar `Termux:API` si está disponible

### Funciones opcionales con Termux:API

```sh
pkg install termux-api
```

Habilita notificaciones locales, vibración, batería y wake lock.

### Detener Nova

```sh
kill "$(cat ~/.nova/nova.pid)"
```

### Ver logs

```sh
tail -f ~/.nova/nova.log
```

## Configuración

Antes de correr Nova fuera de un entorno efímero:

```bash
cp .env.example .env
```

Rellena al menos:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `WORKSPACE_ADMIN_TOKEN`
- las llaves LLM que realmente vayas a usar
- credenciales OAuth solo si habilitas login externo

El repo no debe contener `.env` reales, tokens, bases locales ni scripts con secretos embebidos.

## Comandos útiles

```bash
nova init
nova validate --action "Send email to customer@example.com"
nova status
nova watch
```

## Documentación local

- [Arquitectura](ARCHITECTURE.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Docs / deployment](docs/deployment.md)
- [Docs / API](docs/api-reference.md)

## Estado actual

Nova OS ya tiene piezas serias de producto, pero el repo aún está en limpieza:

- se están retirando defaults de marketing y dominios ficticios
- se están separando secretos y scripts locales de Windows del árbol publicable
- se está alineando el frontend y los prompts para que la UI diga solo lo que el sistema realmente sabe

## Contribución

Si vas a contribuir:

```bash
pytest
cd frontend && npm run build
```

No abras PRs con:

- `.env`
- tokens
- bases `.db` / `.sqlite`
- dumps o backups operativos

## Licencia

Consulta [LICENSE](LICENSE).
