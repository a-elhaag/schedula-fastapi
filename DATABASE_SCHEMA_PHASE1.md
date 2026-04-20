# Database Schema: New Collections (Phase 1)

This document describes the three new MongoDB collections added in Phase 1 to complete the Schedula database schema.

## Collections Overview

| Collection | Purpose | Indexes |
|-----------|---------|---------|
| `enrollments` | Track student enrollments per course section | institution_id + term_label, course_id |
| `schedule_revisions` | Version history of published schedules | institution_id + term_label + revision_number |
| `conflict_resolutions` | Track resolved schedule conflicts | schedule_revision_id, conflict_type |

---

## 1. Enrollments Collection

Stores enrollment data for each course section, including actual student counts and fill rates.

### Document Structure

```json
{
  "_id": "ObjectId",
  "institution_id": "string",
  "term_label": "string (e.g., 'Fall 2024')",
  "course_id": "string (reference to course section)",
  "enrolled_students": "integer (>= 0)",
  "capacity": "integer (>= 1)",
  "created_at": "datetime",
  "updated_at": "datetime",
  "deleted_at": "datetime or null"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | Yes | MongoDB primary key |
| `institution_id` | String | Yes | Institution identifier |
| `term_label` | String | Yes | Academic term (e.g., "Fall 2024", "Spring 2025") |
| `course_id` | String | Yes | Reference to course section ID |
| `enrolled_students` | Integer | Yes | Current enrollment count |
| `capacity` | Integer | Yes | Section capacity/max enrollment |
| `created_at` | DateTime | Yes | Record creation timestamp |
| `updated_at` | DateTime | Yes | Last modification timestamp |
| `deleted_at` | DateTime | No | Soft delete timestamp (null if active) |

### Computed Property

- **Fill Rate**: `(enrolled_students / capacity) * 100`
  - Calculated on-read, not stored
  - Used for coordinator course overview and solver weighting

### Indexes

```javascript
// Unique constraint: one enrollment per course per term
db.enrollments.createIndex(
  { institution_id: 1, term_label: 1, course_id: 1 },
  { name: "idx_institution_term_course", unique: true }
)

// Query by institution + term
db.enrollments.createIndex(
  { institution_id: 1, term_label: 1 },
  { name: "idx_institution_term" }
)

// Sort by recency
db.enrollments.createIndex(
  { updated_at: -1 },
  { name: "idx_updated_at" }
)
```

### Use Cases

1. **Fetch fill rates for coordinator dashboard**
   ```python
   db.enrollments.find({
     "institution_id": "<id>",
     "term_label": "<term>",
     "deleted_at": None
   })
   ```

2. **Update enrollment when student enrolls/drops**
   ```python
   db.enrollments.update_one(
     {"institution_id": "<id>", "term_label": "<term>", "course_id": "<id>"},
     {"$set": {"enrolled_students": <count>, "updated_at": <now>}}
   )
   ```

3. **Bulk import from CSV**
   - Accept CSV with course_id and enrolled_students
   - Upsert records via course_id lookup

---

## 2. Schedule Revisions Collection

Maintains a complete history of every published schedule for audit trails and comparison.

### Document Structure

```json
{
  "_id": "ObjectId",
  "institution_id": "string",
  "term_label": "string",
  "revision_number": "integer (>= 1)",
  "published_at": "datetime",
  "published_by": "string (user ID)",
  "entries": [
    {
      "section_id": "string",
      "day_of_week": "integer (0-6)",
      "start_time": "string (HH:MM)",
      "end_time": "string (HH:MM)",
      "room_id": "string",
      "assigned_staff": ["string"]
    }
  ],
  "hard_violations": "integer (>= 0)",
  "soft_penalty_total": "float (>= 0)",
  "warnings": ["string"],
  "notes": "string or null",
  "created_at": "datetime",
  "deleted_at": "datetime or null"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | Yes | MongoDB primary key |
| `institution_id` | String | Yes | Institution identifier |
| `term_label` | String | Yes | Academic term |
| `revision_number` | Integer | Yes | Sequential version (1, 2, 3, ...) |
| `published_at` | DateTime | Yes | When schedule was published |
| `published_by` | String | Yes | User ID of coordinator who published |
| `entries` | Array | Yes | List of schedule entries (class sessions) |
| `entries.section_id` | String | Yes | Course section being scheduled |
| `entries.day_of_week` | Integer | Yes | 0 = Monday, 6 = Sunday |
| `entries.start_time` | String | Yes | 24-hour format (e.g., "09:00") |
| `entries.end_time` | String | Yes | 24-hour format (e.g., "10:30") |
| `entries.room_id` | String | Yes | Assigned room |
| `entries.assigned_staff` | Array | Yes | Staff IDs teaching this session |
| `hard_violations` | Integer | Yes | Count of constraint violations |
| `soft_penalty_total` | Float | Yes | Objective function value |
| `warnings` | Array | Yes | Any warnings from solver |
| `notes` | String | No | Coordinator notes about this revision |
| `created_at` | DateTime | Yes | Record creation timestamp |
| `deleted_at` | DateTime | No | Soft delete timestamp |

### Computed Property

- **Is Feasible**: `hard_violations == 0`
  - Indicates if schedule satisfies all hard constraints

### Indexes

```javascript
// Get schedule by version
db.schedule_revisions.createIndex(
  { institution_id: 1, term_label: 1, revision_number: -1 },
  { name: "idx_institution_term_revision" }
)

// Get all revisions for term
db.schedule_revisions.createIndex(
  { institution_id: 1, term_label: 1 },
  { name: "idx_institution_term" }
)

// Get recent revisions
db.schedule_revisions.createIndex(
  { published_at: -1 },
  { name: "idx_published_at" }
)
```

### Use Cases

1. **Fetch latest published schedule**
   ```python
   db.schedule_revisions.find_one(
     {"institution_id": "<id>", "term_label": "<term>", "deleted_at": None},
     sort=[("revision_number", -1)]
   )
   ```

2. **Get schedule history/revisions**
   ```python
   db.schedule_revisions.find(
     {"institution_id": "<id>", "term_label": "<term>", "deleted_at": None},
     sort=[("revision_number", -1)]
   )
   ```

3. **Compare two schedule versions**
   ```python
   rev1 = db.schedule_revisions.find_one({revision_number: 1})
   rev2 = db.schedule_revisions.find_one({revision_number: 2})
   # Compare entries arrays
   ```

4. **Store new published schedule**
   ```python
   db.schedule_revisions.insert_one({
     "institution_id": "<id>",
     "term_label": "<term>",
     "revision_number": <next_number>,
     "published_at": <now>,
     "published_by": "<user_id>",
     "entries": <solver_output>,
     "hard_violations": <count>,
     "soft_penalty_total": <value>,
     "warnings": []
   })
   ```

---

## 3. Conflict Resolutions Collection

Audit trail of conflicts detected during scheduling and how they were resolved.

### Document Structure

```json
{
  "_id": "ObjectId",
  "institution_id": "string",
  "term_label": "string",
  "schedule_revision_id": "string (reference to schedule_revisions._id)",
  "conflict_type": "string (enum)",
  "affected_sections": ["string"],
  "description": "string",
  "resolution_action": "string",
  "resolved_by": "string (user ID)",
  "resolved_at": "datetime",
  "notes": "string or null",
  "created_at": "datetime",
  "deleted_at": "datetime or null"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | Yes | MongoDB primary key |
| `institution_id` | String | Yes | Institution identifier |
| `term_label` | String | Yes | Academic term |
| `schedule_revision_id` | String | Yes | Reference to schedule revision containing this conflict |
| `conflict_type` | Enum | Yes | Type of conflict (see below) |
| `affected_sections` | Array | Yes | Course section IDs involved in conflict |
| `description` | String | Yes | Human-readable description of the conflict |
| `resolution_action` | String | Yes | Action taken (e.g., "moved_to_different_room", "changed_time_slot") |
| `resolved_by` | String | Yes | User ID of coordinator who resolved |
| `resolved_at` | DateTime | Yes | When resolution occurred |
| `notes` | String | No | Additional notes from resolver |
| `created_at` | DateTime | Yes | Record creation timestamp |
| `deleted_at` | DateTime | No | Soft delete timestamp |

### Conflict Types

```
ENUM conflict_type {
  "room_overlap"              // Multiple classes assigned to same room + time
  "instructor_overlap"        // Instructor teaching multiple classes at same time
  "capacity_exceeded"         // More students enrolled than room capacity
  "room_feature_missing"      // Required room feature (e.g., projector) unavailable
  "time_slot_unavailable"     // Requested time slot conflicts with instructor availability
  "other"                     // Miscellaneous conflicts
}
```

### Indexes

```javascript
// Find all conflicts for a schedule
db.conflict_resolutions.createIndex(
  { schedule_revision_id: 1 },
  { name: "idx_schedule_revision_id" }
)

// Find conflicts by type
db.conflict_resolutions.createIndex(
  { conflict_type: 1 },
  { name: "idx_conflict_type" }
)

// Get all conflicts for term
db.conflict_resolutions.createIndex(
  { institution_id: 1, term_label: 1 },
  { name: "idx_institution_term" }
)

// Get recent resolutions
db.conflict_resolutions.createIndex(
  { resolved_at: -1 },
  { name: "idx_resolved_at" }
)
```

### Use Cases

1. **Get all conflicts for a schedule revision**
   ```python
   db.conflict_resolutions.find({
     "schedule_revision_id": "<id>",
     "deleted_at": None
   })
   ```

2. **Create conflict resolution record**
   ```python
   db.conflict_resolutions.insert_one({
     "institution_id": "<id>",
     "term_label": "<term>",
     "schedule_revision_id": "<id>",
     "conflict_type": "room_overlap",
     "affected_sections": ["sec1", "sec2"],
     "description": "CSE101L and CSE102L scheduled in Room A at same time",
     "resolution_action": "moved_to_different_room",
     "resolved_by": "<user_id>",
     "resolved_at": <now>
   })
   ```

3. **Analytics: count conflicts by type**
   ```python
   db.conflict_resolutions.aggregate([
     {"$match": {"institution_id": "<id>", "term_label": "<term>"}},
     {"$group": {"_id": "$conflict_type", "count": {"$sum": 1}}}
   ])
   ```

---

## Collection Initialization

When the backend starts, the `init_db()` function automatically:

1. Connects to MongoDB
2. Creates all indexes via `init_indexes()`
3. Logs index creation status

**File**: `backend/app/database/indexes.py`

```python
await init_indexes(db)  # Called in app/database/client.py
```

---

## Soft Delete Strategy

All three collections support soft deletes using the `deleted_at` field:

- **Active records**: `deleted_at = null`
- **Deleted records**: `deleted_at = <datetime>`

All queries automatically filter: `{"deleted_at": null}`

**Rationale**: Preserves historical data for audits while logically removing from API responses.

---

## Query Functions

All CRUD operations are available in `backend/app/database/queries.py`:

### Enrollments
- `get_enrollment()` - Fetch single enrollment
- `get_enrollments()` - Fetch all for term
- `create_enrollment()` - Insert new
- `update_enrollment()` - Update existing
- `delete_enrollment()` - Soft delete

### Schedule Revisions
- `get_schedule_revision()` - Fetch specific version
- `get_latest_schedule_revision()` - Fetch newest
- `get_schedule_revisions()` - Fetch all for term
- `create_schedule_revision()` - Insert new
- `delete_schedule_revision()` - Soft delete

### Conflict Resolutions
- `get_conflict_resolution()` - Fetch single
- `get_conflict_resolutions_for_schedule()` - For revision
- `get_conflict_resolutions_by_term()` - For term
- `create_conflict_resolution()` - Insert new
- `delete_conflict_resolution()` - Soft delete

---

## Next Steps

**Phase 2**: Use enrollments collection to replace hardcoded fill rates in API

**Phase 3**: Use schedule_revisions + conflict_resolutions for solver constraint validation

**Phase 4**: Use enrollments in staff schedule page
