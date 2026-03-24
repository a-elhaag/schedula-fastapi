# Schedula FastAPI Documentation

Schedula FastAPI is a stateless scheduling backend that builds course timetables using OR-Tools CP-SAT and data from MongoDB.

This documentation is the source of truth for:

- service architecture and request flow
- API endpoints and payloads
- model and collection contracts
- runtime configuration and environment variables
- tests, CI, and deployment workflows

## What This Service Does

- reads institution, courses, staff, availability, rooms, and weight configuration
- builds a constraint model for hard and soft scheduling rules
- solves and returns a schedule snapshot to the client
- does **not** persist generated snapshots (persistence is handled externally)

## Documentation Map

- `Quickstart`: local setup and development loop
- `Architecture`: internals, modules, and solver flow
- `API Reference`: route contracts with examples
- `Data Models`: Pydantic and MongoDB data shape reference
- `Configuration`: all settings from `.env`
- `Testing`: unit/integration test strategy and commands
- `Deployment`: production deployment and Pages/Azure notes
- `CI/CD Workflows`: GitHub Actions inventory and behavior

## Key Runtime Endpoints

- `GET /` service entry metadata
- `GET /health` liveness
- `GET /health/ready` readiness with MongoDB ping
- `POST /schedule/generate` schedule generation
