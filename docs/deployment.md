# Deployment

Desarrollo:

1. Crear `.env` desde `.env.example`.
2. Instalar dependencias.
3. Ejecutar `python nova.py start`.

Producción:

1. Usar PostgreSQL vía `NOVA_DB_URL`.
2. Configurar `NOVA_JWT_SECRET`.
3. Proveer API keys de providers necesarios.
4. Ejecutar detrás de un reverse proxy con TLS.
