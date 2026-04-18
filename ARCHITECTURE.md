# Nova OS Architecture

Nova OS tiene dos capas activas en este repo:

1. `nova.py` como CLI y entrypoint del runtime.
2. `nova/` como paquete modular con API, kernel, discovery, ledger, memoria y seguridad.

El objetivo actual no es “enterprise-only”. El objetivo es correr el mismo núcleo en Linux normal, macOS y Termux, degradando dependencias externas cuando el host no las tenga.

## Runtime actual

- **CLI**: `nova.py`
- **API**: FastAPI + Uvicorn
- **Kernel**: `nova/kernel.py`
- **Storage principal**: SQLAlchemy async con SQLite por defecto y PostgreSQL cuando el host lo soporte
- **DB portable extra**: `nova/db.py` para bootstrap sin depender del ORM completo
- **Descubrimiento**: `nova/discovery/`
- **Ledger**: `nova/ledger/`
- **Memoria**: `nova/memory/`

## Decisiones de plataforma

- **Detección de host**: `nova/platform.py`
- **Termux**: sin Docker, sin systemd, sin PostgreSQL obligatorio
- **Linux con systemd**: puede correr como servicio
- **PM2/screen/nohup**: fallback cuando no hay systemd
- **Node**: opcional para frontend y discovery ampliado; no es requisito del core

## Base de datos

- Si hay PostgreSQL real y el runtime lo puede usar, Nova puede apuntar a `postgresql+asyncpg`.
- Si no, cae a SQLite en `~/.nova/nova.db`.
- La meta es mantener la misma interfaz del runtime y bajar dependencias externas, no reescribir el dominio.

## Flujo de validación

1. El agente envía una acción vía API, bridge o CLI.
2. El kernel aplica análisis de intención, reglas, sensibilidad, riesgo y cuota.
3. El pipeline decide `ALLOW`, `BLOCK`, `ESCALATE` o equivalentes operativos.
4. El ledger encadena la evidencia con firma SHA-256/HMAC.
5. Memoria y observabilidad guardan contexto operativo.

## Restricciones prácticas

- El repo todavía contiene código legacy en `backend/` y `legacy/`.
- El camino crítico productivo hoy es `nova.py` + `nova/`.
- Los scripts auxiliares deben degradar con gracia cuando no existe Docker, systemd o PostgreSQL.
