# Data Models

This page summarizes model contracts used by the API and solver.

## API Models (`app/models/solver.py`)

### `GenerateScheduleRequest`

- `institution_id: str`
- `term_label: str`
- `weights: SolverWeights | null`
- `section_type_durations: SectionTypeDurations | null`

### `SolverWeights`

- `break_window: int >= 0` (default `100`)
- `consecutive_slots: int >= 0` (default `80`)
- `session_spread: int >= 0` (default `60`)
- `campus_clustering: int >= 0` (default `40`)

### `SectionTypeDurations`

Optional per-type duration overrides in minutes:

- `lecture`
- `lab`
- `tutorial`

### `GenerateScheduleResponse`

- `snapshot_id: str`
- `institution_id: str`
- `term_label: str`
- `generated_at: str`
- `entries: ScheduleEntryResponse[]`
- `hard_violations: int`
- `soft_penalty: float`
- `warnings: str[]`
- `summary: SummaryResponse`

## Domain Models (`app/models/*.py`)

### `Institution`

- `_id`, `name`, `slug`
- `working_days: int[]`
- `daily_start_hour`, `daily_end_hour`
- `slot_duration_minutes`

### `CourseSection`

- `_id`, `institution_id`, `department_id`
- `course_name`, `section_type`
- `year_levels[]`
- `slots_per_week`, `slot_duration_minutes`
- `capacity`, `required_room_label`
- `assigned_staff[]`, `shared_with[]`

Validation highlights:

- `year_levels` must be non-empty positive ints
- `shared_with` allowed only for `lecture`

### `Staff`

- `_id`, `institution_id`, `department_id`
- `name`, `email`, `role`
- `faculty_id`

### `Availability`

- `_id`, `institution_id`, `staff_id`, `term_label`
- `weekly_day_off`
- `preferred_break_windows[]`

### `Room`

- `_id`, `institution_id`, `faculty_id`
- `name`, `label`, `capacity`
- `features[]`

## MongoDB Collection Inputs

Primary collections read by solver route:

- `institutions`
- `courses`
- `users` (filtered to `role in [professor, ta]`)
- `availability`
- `rooms`
- `constraints`

Soft-delete convention:

- queries filter `deleted_at: null`

## Example Request/Response

### Request

```json
{
  "institution_id": "test-inst-001",
  "term_label": "fall-2024",
  "weights": {
    "break_window": 100,
    "consecutive_slots": 80,
    "session_spread": 60,
    "campus_clustering": 40
  }
}
```

### Response (trimmed)

```json
{
  "snapshot_id": "uuid",
  "institution_id": "test-inst-001",
  "entries": [
    {
      "section_id": "sec-cs101-lec",
      "day_of_week": 1,
      "start_time": "09:00",
      "end_time": "10:00",
      "room_id": "room-101"
    }
  ],
  "hard_violations": 0,
  "soft_penalty": 320.0
}
```
