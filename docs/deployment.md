# Deployment

Notes for deploying Schedula FastAPI:

- Build and publish container via `Dockerfile` and `docker-compose.yml`.
- Ensure environment variables (e.g., database connection) are set securely.
- For production, run with an ASGI server behind a reverse proxy.

See `Dockerfile` and `docker-compose.yml` for an example container setup.
