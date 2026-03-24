# Architecture

## High-Level Flow

1. Client calls `POST /schedule/generate`
2. API reads required data from MongoDB collections
3. `ScheduleSolver` builds a CP-SAT model
4. Solver computes a feasible/optimal schedule
5. API returns snapshot payload (stateless response)

## Module Layout

- `app/main.py`: FastAPI app, lifespan hooks, CORS, router mounting
- `app/config.py`: environment-backed settings
- `app/database/client.py`: async MongoDB init/close and dependency provider
- `app/database/queries.py`: typed query helpers for each collection
- `app/routes/health.py`: liveness/readiness routes
- `app/routes/solver.py`: schedule generation endpoint and orchestration
- `app/services/solver_service.py`: OR-Tools model + constraints + solve
- `app/models/*.py`: request/response and domain data models

## Lifespan and DB Lifecycle

Startup:

- `init_db()` creates `AsyncMongoClient`
- ping check validates connectivity

Shutdown:

- `close_db()` closes client

`get_db()` is injected into routes using FastAPI dependency injection.

## Solver Pipeline

Inside `ScheduleSolver.build_model(...)`:

1. Build time-grid metadata from institution settings
2. Pre-compute compatible rooms per section (capacity + label)
3. Pre-compute staff-to-sections index
4. Create session variables and interval variables
5. Add hard constraints
6. Add soft penalties and objective minimization

Inside `solve()`:

1. Configure CP-SAT runtime (`max_time_in_seconds`, workers)
2. Solve model
3. Convert variable values into schedule entries
4. Return `(hard_violations, soft_penalty, entries)`

## Constraint Model Summary

Hard constraints:

- H1 room no-overlap via `AddNoOverlap` on room optional intervals
- H2 staff no-overlap via `AddNoOverlap` on staff intervals
- H3 room capacity room filtering
- H4 room label compatibility filtering
- H5 weekly day-off blocking
- H8 year-level conflict separation

Soft constraints:

- S1 break-window overlap penalty
- S2 adjacent-session penalty
- S3 same-day repeated-section penalty
- S4 staff campus-day penalty

## Time Representation

For each session occurrence:

- `day`: 0..N-1 over institution working days
- `slot`: start slot within day
- `abs_s`: absolute start in week timeline
- `abs_e`: absolute end in week timeline

This flattened timeline enables efficient overlap constraints.

## Stateless Contract

The backend returns generated snapshots but does not persist them.
Persistence and approval workflows are intentionally external to this API service.
