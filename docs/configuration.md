# Configuration

Runtime settings are defined in `app/config.py` using `pydantic-settings` and loaded from `.env`.

## Environment Variables

## FastAPI

- `APP_NAME` (default: `Schedula Schedule Solver`)
- `DEBUG` (default: `false`)
- `CORS_ORIGINS` (default: `[*]`)
- `LOG_LEVEL` (default: `INFO`)

## MongoDB

- `MONGODB_URI` (required in production)
- `MONGODB_DB_NAME` (default: `schedula`)

## Solver Runtime

- `SOLVER_TIME_LIMIT_SECONDS` (default: `55`)
- `SOLVER_NUM_WORKERS` (default: `8`)

## Default Soft Weights

Used when neither request-level nor DB-level weight overrides are supplied.

- `SOFT_WEIGHT_BREAK_WINDOW` (default: `100`)
- `SOFT_WEIGHT_CONSECUTIVE_SLOTS` (default: `80`)
- `SOFT_WEIGHT_SESSION_SPREAD` (default: `60`)
- `SOFT_WEIGHT_CAMPUS_CLUSTERING` (default: `40`)

## Example `.env`

```dotenv
APP_NAME=Schedula Schedule Solver
DEBUG=true
CORS_ORIGINS=["*"]
LOG_LEVEL=INFO

MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>/<db>?retryWrites=true&w=majority
MONGODB_DB_NAME=schedula

SOLVER_TIME_LIMIT_SECONDS=55
SOLVER_NUM_WORKERS=8

SOFT_WEIGHT_BREAK_WINDOW=100
SOFT_WEIGHT_CONSECUTIVE_SLOTS=80
SOFT_WEIGHT_SESSION_SPREAD=60
SOFT_WEIGHT_CAMPUS_CLUSTERING=40
```

## Weight Resolution Order

For `/schedule/generate`, final weights are resolved in this order:

1. request body `weights`
2. MongoDB `constraints` collection
3. environment defaults (`SOFT_WEIGHT_*`)

## Notes

- Keep `MONGODB_URI` in secrets, never in source control.
- `SOLVER_NUM_WORKERS` should match runtime CPU availability for best throughput.
- Set restrictive `CORS_ORIGINS` in production.
