# Testing Guide

Three levels of testing for Schedula FastAPI solver:

## 1. Unit Tests (Fast, No Dependencies)

**Tests solver logic in isolation, ~0.1s**

```bash
pytest tests/test_solver.py -v
```

**Coverage:**
- Solver initialization
- Time grid calculation
- Single section scheduling
- Multi-slot sessions (`slots_per_week`)
- H1 (room no-overlap)
- H5 (staff day-off)
- H8 (year-level conflicts)
- Section skipping (no compatible room)
- Section-type duration configuration

**Result:** 10 test cases, all passing

---

## 2. Integration Tests (API + MongoDB)

**Tests full `/schedule/generate` endpoint with real database**

### Setup

1. **Start MongoDB:**
   ```bash
   docker-compose up -d
   ```

   Verify it's running:
   ```bash
   docker ps | grep schedula-mongo
   ```

2. **Copy `.env` for local dev:**
   ```bash
   cp .env.example .env
   ```

   Already configured for `localhost:27017` with `user:password`

3. **Install dev dependencies:**
   ```bash
   pip install -e .
   ```

### Run Integration Tests

**Start FastAPI server in one terminal:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Run tests in another terminal:**
```bash
pytest tests/test_integration.py -v -s
```

**Coverage:**
- Health check
- Schedule generation success
- H5 constraint (staff day-off respected)
- H1 constraint (room no double-booking)
- slots_per_week enforcement
- Error handling (missing institution)
- Weight override (request → DB → config)

**Test data:**
- 1 institution, 2 rooms, 2 professors, 3 sections
- CS dept: Intro to CS lecture (2 slots/week) + lab (1 slot/week)
- Math dept: Calculus I (2 slots/week)
- Prof-001: day-off Friday, lunch break Wed 12-13
- Custom soft constraint weights in DB

### Check MongoDB Data

```bash
# Connect to MongoDB
docker exec -it schedula-mongo mongosh -u user -p password

# In mongosh:
use schedula
db.institutions.findOne()
db.courses.find()
db.users.find()
db.availability.find()
db.rooms.find()
db.constraints.findOne()
```

### Cleanup

```bash
docker-compose down
```

---

## 3. Local Manual Testing

**Use curl or Postman to test the API directly**

### Start Services

```bash
# Terminal 1: MongoDB
docker-compose up

# Terminal 2: FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Generate Schedule

```bash
curl -X POST http://localhost:8000/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{
    "institution_id": "test-inst-001",
    "term_label": "fall-2024",
    "weights": null
  }' | jq .
```

Response includes:
- `snapshot_id`: unique schedule ID
- `entries`: list of scheduled sessions with times/rooms
- `hard_violations`: 0 if all constraints satisfied
- `soft_penalty`: weighted penalty from soft constraints
- `warnings`: list of issues/info
- `summary`: statistics (total sections, scheduled sections, staff count, etc.)

### View Full Response

```bash
curl -s -X POST http://localhost:8000/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{
    "institution_id": "test-inst-001",
    "term_label": "fall-2024"
  }' | jq .
```

### Test With Custom Weights

```bash
curl -X POST http://localhost:8000/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{
    "institution_id": "test-inst-001",
    "term_label": "fall-2024",
    "weights": {
      "break_window": 200,
      "consecutive_slots": 150,
      "session_spread": 120,
      "campus_clustering": 80
    }
  }' | jq '.summary.weights'
```

---

## Performance Testing (Load Testing)

**Test solver on larger datasets (optional)**

Create a Python script to seed 100+ sections and measure solver time:

```python
# load_test.py
import asyncio
import time
from pymongo import AsyncMongoClient
from app.services.solver_service import ScheduleSolver

async def load_test():
    client = AsyncMongoClient("mongodb://user:password@localhost:27017")
    db = client["schedula"]

    # Fetch data
    inst = await db["institutions"].find_one({"_id": "test-inst-001"})
    courses = await db["courses"].find({"institution_id": "test-inst-001"}).to_list(None)
    staff = await db["users"].find({"institution_id": "test-inst-001"}).to_list(None)
    availability = await db["availability"].find({"institution_id": "test-inst-001"}).to_list(None)
    rooms = await db["rooms"].find({"institution_id": "test-inst-001"}).to_list(None)
    constraints = await db["constraints"].find_one({"institution_id": "test-inst-001"})

    # Time the solver
    solver = ScheduleSolver(time_limit_seconds=55, num_workers=8)

    start = time.time()
    solver.build_model(inst, courses, staff, availability, rooms, constraints or {})
    violations, penalty, entries = solver.solve()
    elapsed = time.time() - start

    print(f"Sections: {len(courses)}")
    print(f"Scheduled: {len(entries)}")
    print(f"Violations: {violations}")
    print(f"Penalty: {penalty:.0f}")
    print(f"Time: {elapsed:.1f}s")

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(load_test())
```

Run with:
```bash
python load_test.py
```

Expected performance:
- **50 sections**: <1s
- **200 sections**: 2-5s
- **1000 sections**: 10-30s
- **5000 sections** (very large campus): 40-55s

---

## CI/CD Integration

Ready to integrate with GitHub Actions or similar:

```yaml
# .github/workflows/test.yml (example)
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7.0-alpine
        options: >-
          --health-cmd mongosh
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        env:
          MONGO_INITDB_ROOT_USERNAME: user
          MONGO_INITDB_ROOT_PASSWORD: password

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - run: pip install -e .
      - run: pytest tests/test_solver.py -v
      - run: pytest tests/test_integration.py -v
```

---

## Troubleshooting

### MongoDB Connection Fails

```bash
# Check if container is running
docker ps | grep mongo

# Check logs
docker logs schedula-mongo

# Restart
docker-compose down && docker-compose up -d
```

### Solver Timeout in Tests

Increase `SOLVER_TIME_LIMIT_SECONDS` in `.env` or pass `time_limit_seconds` to test fixtures.

### Tests Skip Due to MongoDB Unreachable

```bash
# Verify MongoDB is listening
telnet localhost 27017
```

### Port Already in Use

```bash
# Kill existing process on 27017
lsof -i :27017 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

---

## Summary

| Level | Command | Time | Dependencies |
|-------|---------|------|--------------|
| Unit | `pytest tests/test_solver.py` | ~0.1s | None |
| Integration | `pytest tests/test_integration.py` | ~5s | MongoDB + FastAPI |
| Manual | `curl` or Postman | N/A | MongoDB + FastAPI |
| Load | Custom script | 1-55s | MongoDB |
