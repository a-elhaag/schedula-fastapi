# Phase 3 Implementation: Hard Constraints Enforcement

## Overview

Phase 3 implements comprehensive hard constraint enforcement in the schedule solver. Instead of just pre-filtering rooms, hard constraints are now properly validated before solving and enforced within the CP-SAT model itself.

---

## What Was Implemented

### 1. Constraint Validator Module

**File**: `backend/app/services/constraint_validator.py`

A new `ConstraintValidator` class provides pre-solve validation for all hard constraints.

#### **H3: Room Capacity Constraint**

```python
ConstraintValidator.validate_h3_room_capacity(
    courses: list[dict],
    rooms: list[dict],
    enrollments: dict[str, dict] | None = None
) -> tuple[bool, list[str]]
```

**What it does**:
- Checks each section has at least one room with sufficient capacity
- Uses actual enrollment data if available (from Phase 2)
- Falls back to section.capacity field if no enrollment data
- Returns detailed error messages indicating capacity gaps

**Example**:
```python
courses = [{"_id": "CS101", "capacity": 100}]
rooms = [{"_id": "room1", "capacity": 80}]

is_valid, errors = ConstraintValidator.validate_h3_room_capacity(courses, rooms)
# is_valid = False
# errors = ["H3 VIOLATION: CS101 requires capacity 100, but max available is 80..."]
```

#### **H4: Required Room Labels Constraint**

```python
ConstraintValidator.validate_h4_required_room_labels(
    courses: list[dict],
    rooms: list[dict]
) -> tuple[bool, list[str]]
```

**What it does**:
- Checks each section's `required_room_label` matches at least one room's `label`
- Reports which labels are missing/unavailable
- Sections without requirements always pass

**Example**:
```python
courses = [{"_id": "CS101Lab", "required_room_label": "Lab"}]
rooms = [{"_id": "room1", "label": "Lecture"}]

is_valid, errors = ConstraintValidator.validate_h4_required_room_labels(courses, rooms)
# is_valid = False
# errors = ["H4 VIOLATION: CS101Lab requires label 'Lab', but no such room exists..."]
```

#### **H6: Room Features Constraint**

```python
ConstraintValidator.validate_h6_room_features(
    courses: list[dict],
    rooms: list[dict],
    room_feature_requirements: dict[str, list[str]] | None = None
) -> tuple[bool, list[str]]
```

**What it does**:
- Checks rooms have all features required by their section type
- Feature requirements passed as dict: `{"lab": ["computers", "projector"]}`
- Skips validation if no requirements defined
- Helps ensure lab sections get computers, lectures get projectors, etc.

**Example**:
```python
courses = [{"_id": "PHY101Lab", "section_type": "lab"}]
rooms = [{"_id": "lab1", "features": ["projector"]}]  # Missing "computers"
requirements = {"lab": ["computers", "projector"]}

is_valid, errors = ConstraintValidator.validate_h6_room_features(
    courses, rooms, requirements
)
# is_valid = False
# errors = ["H6 VIOLATION: lab sections require features ['computers', 'projector']..."]
```

#### **H7: Session Overlap Prevention**

```python
ConstraintValidator.validate_h7_session_overlap_prevention(
    courses: list[dict],
    staff_data: list[dict]
) -> tuple[bool, list[str]]
```

**What it does**:
- Checks for logically problematic staff assignments
- Warns if an instructor is assigned > 20 slots/week (heuristic)
- Currently returns warnings only (doesn't fail validation)
- Actual no-overlap enforcement handled by solver (H1/H2)

#### **Bonus: Enrollment-Capacity Alignment**

```python
ConstraintValidator.validate_enrollment_capacity_alignment(
    courses: list[dict],
    rooms: list[dict],
    enrollments: dict[str, dict]
) -> tuple[bool, list[str]]
```

**What it does**:
- Checks course capacity doesn't exceed max available room
- Suggests solutions (reduce course capacity or add larger rooms)

#### **Combined Validation**

```python
is_feasible, critical_errors, warnings = ConstraintValidator.run_all_validations(
    courses=courses_data,
    staff_data=staff_data,
    rooms=rooms_data,
    enrollments=enrollments_data,  # From Phase 2
    room_feature_requirements=requirements_dict  # Optional
)

# Returns:
# is_feasible: bool - True if all hard constraints pass
# critical_errors: list[str] - H3, H4 violations (make schedule infeasible)
# warnings: dict[str, list[str]] - Non-critical issues (H6, H7)
```

---

### 2. Updated Solver Service

**File**: `backend/app/services/solver_service.py`

#### **New `build_model()` Parameters**

```python
solver.build_model(
    institution_data=...,
    courses_data=...,
    staff_data=...,
    availability_data=...,
    rooms_data=...,
    weights=...,
    section_type_durations=...,
    enrollments_data=enrollments_dict,        # NEW: enrollment data
    room_feature_requirements=requirements_dict,  # NEW: feature requirements
)
```

Returns:
```python
is_feasible, critical_errors, warnings = solver.build_model(...)
```

**What changed**:
1. Calls `ConstraintValidator.run_all_validations()` before building model
2. Returns tuple instead of None
3. Stores validation results in `solver.validation_errors` and `solver.validation_warnings`
4. Returns immediately if validation fails (no point building model)

#### **New Hard Constraint Methods**

**`_add_h3_room_capacity()`**
- Adds CP-SAT constraint enforcing room capacity
- For each section, restricts room_v to valid indices where room capacity >= required
- Uses enrollment data if available

**`_add_h4_required_room_labels()`**
- Adds CP-SAT constraint enforcing room labels
- For each section with required_room_label, restricts room_v to matching rooms
- Uses `AddAllowedAssignments()` to enforce discrete choices

#### **New `solve()` Return Values**

```python
error_code, soft_penalty, entries, validation_errors = solver.solve()

# error_code: 0 = success, 1 = validation failed, 2 = solver timeout/infeasible
# soft_penalty: objective value (inf if error)
# entries: schedule entries ([] if error)
# validation_errors: list of error messages if any
```

---

### 3. Updated Solver Route

**File**: `backend/app/routes/solver.py`

#### **New Behavior**

1. **Fetches enrollment data** (added get_enrollments import)
2. **Converts enrollments list to dict** for O(1) lookup by course_id
3. **Validates before solving**:
   - If validation fails → returns 400 response with error details
   - Includes both critical_errors and validation_warnings
4. **Handles new return signatures**:
   - build_model returns (is_feasible, errors, warnings)
   - solve returns (error_code, soft_penalty, entries, errors)
5. **Includes validation results in response** for frontend debugging

#### **Response Structure**

Success response includes validation_warnings (if any):
```json
{
  "snapshot_id": "...",
  "institution_id": "...",
  "term_label": "...",
  "generated_at": "2026-04-20T...",
  "entries": [...schedule entries...],
  "hard_violations": 0,
  "soft_penalty": 123.5,
  "warnings": [
    "H7 WARNING: Prof A assigned to 25 slots/week (max recommended: 20)..."
  ],
  "summary": {
    "total_sections": 50,
    "scheduled_sections": 48,
    "total_staff": 20,
    "total_rooms": 15,
    "weights": {...},
    "validation_warnings": {
      "h7_overlap": ["Prof A warning..."]
    }
  }
}
```

Failure response (hard constraint violation):
```json
{
  "snapshot_id": "...",
  "institution_id": "...",
  "term_label": "...",
  "generated_at": "2026-04-20T...",
  "entries": [],
  "hard_violations": 2,
  "soft_penalty": Infinity,
  "warnings": [
    "H3 VIOLATION: CS101 requires capacity 100, but max available is 80...",
    "H4 VIOLATION: PHY101Lab requires label 'Lab', but no such room exists..."
  ],
  "summary": {
    "total_sections": 50,
    "scheduled_sections": 0,
    "total_staff": 20,
    "total_rooms": 15,
    "weights": {...},
    "validation_errors": [
      "H3 VIOLATION: ...",
      "H4 VIOLATION: ..."
    ],
    "validation_warnings": {...}
  }
}
```

---

## How Hard Constraints Work

### Pre-Solve Validation (before solver runs)

1. **ConstraintValidator** checks all hard constraints
2. **Returns detailed error messages** if any violations found
3. **Prevents solver from running** on infeasible problems
4. **Saves CPU time** (no timeout on impossible schedules)

### Hard Constraint Enforcement (in solver)

1. **H3 (Room Capacity)**:
   - Creates constraint: `room_v ∈ {valid_room_indices}`
   - Valid = rooms where capacity >= required
   - Fails if empty set (caught by validation)

2. **H4 (Required Labels)**:
   - Creates constraint: `room_v ∈ {labeled_room_indices}`
   - Labeled = rooms where label matches requirement
   - Fails if empty set (caught by validation)

3. **H1/H2 (No Overlap)**: Already implemented
   - AddNoOverlap ensures no room/staff double-booking

4. **H5/H8**: Already implemented
   - Staff day-offs and year-level conflicts

### Soft Constraints

Unaffected by Phase 3. Still penalized (not enforced):
- S1: Break windows (w=100)
- S2: Consecutive slots (w=80)
- S3: Session spread (w=60)
- S4: Campus clustering (w=40)

---

## Error Messages & Debugging

### Hard Constraint Violations

**H3 Capacity**:
```
H3 VIOLATION: Section CSC101 requires capacity 95, but max available is 80. 
Add larger rooms or reduce enrollment.
```

**H4 Labels**:
```
H4 VIOLATION: Section CSC202Lab requires room label 'Lab', 
but no such room exists. Available labels: ['Lecture', 'Studio']
```

**H6 Features**:
```
H6 VIOLATION: lab sections (e.g., PHY101Lab) require features ['computers', 'projector'], 
but no room has all of them. Available features: ['projector', 'whiteboard']
```

### Solver Infeasibility

If validation passes but solver returns INFEASIBLE:
```
{
  "hard_violations": 2,
  "warnings": [
    "Solver could not find a feasible solution. Check that all hard constraints can be satisfied."
  ]
}
```

This might happen if:
- Staff assignments create unavoidable conflicts
- Time grid too small for number of sessions
- Complex cross-constraints make satisfaction impossible

---

## Testing

**File**: `backend/tests/test_constraint_validator.py`

Includes 15+ test cases covering:

✅ H3 Room Capacity
- Valid capacity scenarios
- Insufficient rooms
- With/without enrollment data

✅ H4 Required Labels
- Valid labels
- Missing labels
- Sections without requirements

✅ H6 Room Features
- Valid features
- Missing features
- No requirements defined

✅ H7 Session Overlap
- Reasonable workloads
- Excessive slots warnings

✅ Combined Validations
- All pass
- Multiple violations
- Edge cases

**Run tests**:
```bash
cd backend
pytest tests/test_constraint_validator.py -v
```

---

## Integration with Phase 2

Phase 3 uses Phase 2 enrollment data:

```
Coordinator uploads enrollment CSV (Phase 2)
    ↓
enrollments collection populated
    ↓
GET /schedule/generate called
    ↓
Solver fetches enrollments
    ↓
H3 validation uses actual enrolled_students (not capacity field)
    ↓
Room capacity checked against real enrollment
    ↓
Schedule respects actual demand
```

**Example**:
- Course capacity: 100
- Enrollment: 95 students
- Min room size needed: 95 (from enrollment)
- Room with capacity 100 is assigned ✓
- Room with capacity 90 is rejected ✓

---

## Next Steps (Phase 4)

Phase 4 will remove hardcoded demo data from staff schedule page:
- Update `/app/staff/schedule/page.js` to call API
- Test with real schedule data from solver
- Verify end-to-end integration

---

## Files Modified/Created

1. ✅ `backend/app/services/constraint_validator.py` (NEW - 250+ lines)
2. ✅ `backend/app/services/solver_service.py` (updated):
   - Added imports
   - Updated `__init__`
   - Updated `build_model` signature and implementation
   - Added `_add_h3_room_capacity()`
   - Added `_add_h4_required_room_labels()`
   - Updated `solve()` signature and error handling
3. ✅ `backend/app/routes/solver.py` (updated):
   - Added get_enrollments import
   - Updated POST /schedule/generate handler
   - Added validation check before solve
   - Added enrollment data conversion
4. ✅ `backend/tests/test_constraint_validator.py` (NEW - 300+ lines)

---

## Configuration

No new environment variables needed. Optional:

**Feature Requirements** (if using H6):
```python
# Set in route handler or config
room_feature_requirements = {
    "lab": ["computers", "projector"],
    "lecture": ["projector"],
    "tutorial": []
}

solver.build_model(
    ...,
    room_feature_requirements=room_feature_requirements
)
```

---

## Summary

Phase 3 transforms hard constraints from "suggestions" to actual restrictions:

| Constraint | Before | After |
|-----------|--------|-------|
| **H3** | Pre-filter only | Validated + Enforced in solver |
| **H4** | Pre-filter only | Validated + Enforced in solver |
| **H6** | Not implemented | Validated (warnings) |
| **H7** | Partial (H1/H2) | Warnings for excessive workload |

Result: **Solver only generates feasible schedules** that actually satisfy hard constraints.

