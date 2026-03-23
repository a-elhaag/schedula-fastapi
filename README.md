# Schedula FastAPI Backend

Campus-wide course scheduling solver for higher education institutions.

## Features

- ✓ Constraint-based schedule generation (OR-Tools)
- ✓ 9 hard constraints (no conflicts, capacity, day-offs)
- ✓ 4 soft constraints (break windows, clustering, spread)
- ✓ Async MongoDB integration (PyMongo Async)
- ✓ FastAPI stateless backend
- ✓ Azure Container Apps deployment

## Quick Start

### Prerequisites

- Python 3.10+
- MongoDB Atlas cluster
- Docker (optional)

### Local Development

1. **Clone and install**:

   ```bash
   cd /Users/anas/Projects/schedula-fastapi
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB URI
   ```

3. **Run server**:

   ```bash
   python -m uvicorn app.main:app --reload
   ```

4. **API docs**:
   - Swagger UI: http://localhost:8000/docs
   - Health: http://localhost:8000/health

### Docker

```bash
docker build -t schedula-fastapi .
docker run -p 8000:8000 \
  -e MONGODB_URI="mongodb+srv://..." \
  schedula-fastapi
```

## Project Structure

```
app/
├── main.py              # FastAPI initialization
├── config.py            # Settings from environment
├── models/              # Pydantic request/response schemas
│   ├── institution.py
│   ├── course.py
│   ├── staff.py
│   ├── availability.py
│   ├── room.py
│   ├── schedule.py
│   └── solver.py
├── database/            # MongoDB async operations
│   ├── client.py        # PyMongo async connection
│   └── queries.py       # Reusable query functions
├── routes/              # API endpoints
│   ├── health.py
│   └── solver.py
├── services/            # Business logic
│   ├── solver_service.py # OR-Tools model builder
│   └── validation.py
└── utils/               # Helpers
```

## API Endpoints

### Health

- `GET /health` — Basic health check
- `GET /health/ready` — Readiness check (with DB)

### Schedule Generation (Phase 3)

- `POST /schedule/generate` — Generate schedule snapshot
  ```json
  {
    "institution_id": "inst_123",
    "term_label": "Spring 2024",
    "weights": {
      "break_window": 100,
      "consecutive_slots": 80,
      "session_spread": 60,
      "campus_clustering": 40
    }
  }
  ```

## Constraints

### Hard (must all pass)

- H1: No room double-booking
- H2: No staff double-booking
- H3: Room capacity ≥ section capacity
- H4: Room label matches section requirement
- H5: Weekly day-off fully blocked
- H6: All sessions within daily hours
- H7: Sessions only on working days
- H8: Year-level conflicts within department
- H9: Cross-department shared lecture enforcement

### Soft (weighted penalties)

- S1 (100): Staff break window violations
- S2 (80): Consecutive slots per staff
- S3 (60): Session spread across days
- S4 (40): Campus day clustering

## Database Models

See [Database Schema — MongoDB](https://www.notion.so/Database-Schema-MongoDB-322934a70f9581478055c3df3ce84ba3?pvs=21)

## Testing

```bash
pytest tests/
pytest tests/test_solver.py -v
pytest -k "constraint" -v
```

## Deployment

### Azure Container Apps

```bash
az containerapp create \
  --name schedula-solver \
  --resource-group my-rg \
  --environment my-env \
  --registry-server acr.azurecr.io \
  --image schedula-fastapi:latest \
  --ingress external \
  --target-port 8000 \
  --env-vars MONGODB_URI=... DEBUG=false
```

## Development Standards

- **Async everything**: Use `async def` for all handlers and DB queries
- **Type hints**: Always annotate function signatures
- **Docstrings**: Include parameters, returns, exceptions
- **Institution filter**: Every MongoDB query must filter by `institution_id`
- **No writes on FastAPI**: Only snapshots returned; Next.js owns DB writes

See [.instructions.md](.instructions.md) for full development guidelines.

## Related Repositories

- **Frontend**: Next.js 14+ with Auth.js
- **Infrastructure**: Bicep/Terraform for Azure
- **Database**: MongoDB Atlas connection string

## License

Reserved. Schedula SaaS Platform.
