# Testing

Test suite is based on `pytest` with async support.

## Test Configuration

`pytest.ini`:

- `asyncio_mode = auto`

## Test Files

- `tests/test_routes.py`: route-level health/root checks
- `tests/test_solver.py`: solver unit coverage
- `tests/test_integration.py`: API integration against MongoDB and live server

## Run Commands

All tests:

```bash
pytest -q
```

Verbose:

```bash
pytest tests/ -v
```

Single file:

```bash
pytest tests/test_solver.py -v
```

Filter by keyword:

```bash
pytest -k "constraint" -v
```

## What Is Covered

### Route tests

- `GET /health` returns healthy payload
- `GET /` returns basic service metadata

### Solver tests

- slot/day time-grid calculations
- slots-per-week enforcement
- room no-overlap
- staff day-off rule
- year-level conflict prevention
- skipped sections when no compatible rooms
- section duration precedence and overrides

### Integration tests

- seeded MongoDB collections are read correctly
- `/schedule/generate` happy path and error path
- weight override behavior in summary payload
- hard-constraint invariants in generated entries

## Integration Test Prerequisites

Integration tests expect:

- API reachable at `http://localhost:8000`
- MongoDB configured and accessible via env settings

Typical flow:

```bash
uvicorn app.main:app --reload
pytest tests/test_integration.py -v
```

## CI

`ci.yml` executes:

1. dependency install (`pip install -r requirements.txt`)
2. `pytest tests/ -v`
3. `ruff check .`
