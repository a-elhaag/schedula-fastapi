# API Reference

Base URL (local): `http://localhost:8000`

## GET `/`

Returns service metadata.

### Response

```json
{
  "message": "Schedula Schedule Solver API",
  "docs": "/docs",
  "health": "/health"
}
```

## GET `/health`

Liveness endpoint.

### Response

```json
{
  "status": "healthy",
  "timestamp": "2026-03-24T00:00:00.000000+00:00"
}
```

## GET `/health/ready`

Readiness endpoint with MongoDB connectivity check.

### Ready Response

```json
{
  "status": "ready",
  "database": "connected"
}
```

### Not Ready Response

Status: `503`

```json
{
  "status": "not_ready",
  "database": "disconnected",
  "error": "..."
}
```

## POST `/schedule/generate`

Generate a schedule snapshot from MongoDB input data.

### Request Body

```json
{
  "institution_id": "test-inst-001",
  "term_label": "fall-2024",
  "weights": {
    "break_window": 100,
    "consecutive_slots": 80,
    "session_spread": 60,
    "campus_clustering": 40
  },
  "section_type_durations": {
    "lecture": 120,
    "lab": 180,
    "tutorial": 60
  }
}
```

Notes:

- `weights` is optional
- `section_type_durations` is optional
- weight precedence is `request > constraints collection > app defaults`

### Success Response (`200`)

```json
{
  "snapshot_id": "f0f2b9fe-8cb0-4f0b-b149-2a204ac4aa8f",
  "institution_id": "test-inst-001",
  "term_label": "fall-2024",
  "generated_at": "2026-03-24T00:00:00.000000+00:00",
  "entries": [
    {
      "section_id": "sec-cs101-lec",
      "course_name": "Intro to CS",
      "section_type": "lecture",
      "day_of_week": 1,
      "start_time": "09:00",
      "end_time": "10:00",
      "room_id": "room-101",
      "assigned_staff": ["prof-001"]
    }
  ],
  "hard_violations": 0,
  "soft_penalty": 320.0,
  "warnings": [],
  "summary": {
    "total_sections": 3,
    "scheduled_sections": 3,
    "total_staff": 2,
    "total_rooms": 2,
    "weights": {
      "break_window": 100,
      "consecutive_slots": 80,
      "session_spread": 60,
      "campus_clustering": 40
    }
  }
}
```

### Error Responses

- `404`: institution not found
- `400`: no courses found for institution
- `500`: solver/runtime failure

### Constraint Behavior

Hard constraints include:

- H1: room no-overlap
- H2: staff no-overlap
- H3: room capacity filtering
- H4: room label compatibility filtering
- H5: weekly staff day off
- H8: year-level conflict prevention

Soft objective terms include:

- S1: preferred break-window overlap penalty
- S2: back-to-back session penalty
- S3: same-day multi-session penalty for a section
- S4: per-day campus attendance penalty per staff

## OpenAPI UI

Use FastAPI interactive docs for live schema inspection:

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`
