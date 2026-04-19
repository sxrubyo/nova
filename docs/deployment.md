# Deployment

## Development

1. Create `.env` from `.env.example` if you need persistent settings.
2. Install dependencies.
3. Run `python3 nova.py serve`.

## Production

1. Use PostgreSQL only when you explicitly want it.
2. Set `SECRET_KEY` and admin or auth tokens before exposure.
3. Provide only the provider keys you actually need.
4. Run behind a reverse proxy with TLS if exposed beyond localhost.
