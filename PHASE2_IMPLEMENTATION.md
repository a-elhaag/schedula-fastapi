# Phase 2 Implementation: Enrollment Data Integration

## Overview

Phase 2 replaces hardcoded/randomly generated fill rates with real enrollment data stored in MongoDB. All changes maintain backward compatibility - the system gracefully handles missing enrollment records by showing 0% fill rate.

---

## What Was Implemented

### 1. Backend Database (Next.js/Node.js)

#### New Functions in `coordinatorService.js`

**`getEnrollment(institutionId, courseId, termLabel)`**
- Fetches enrollment for a specific course
- Returns: `{ enrolledStudents, capacity, fillRate, updatedAt }`
- Returns `null` if not found

**`getEnrollmentsByCourseIds(institutionId, termLabel, courseIds)`**
- Batch fetch enrollments for multiple courses
- Returns map: `{ courseId: { enrolledStudents, capacity, fillRate } }`
- Efficient for loading many courses at once

**`upsertEnrollment(institutionId, courseId, termLabel, enrolledStudents, capacity)`**
- Creates or updates enrollment record
- Validates input (enrolledStudents >= 0, capacity > 0)
- Automatically sets `updated_at` timestamp
- Returns `{ created, enrolledStudents, capacity, fillRate }`

**`deleteEnrollment(institutionId, courseId, termLabel)`**
- Soft deletes enrollment (sets `deleted_at`)
- Returns boolean indicating success

#### Updated Function: `getCoordinatorCourses()`

```javascript
// Now accepts termLabel option
const result = await getCoordinatorCourses(institutionId, { 
  departmentId,   // optional, filters by department
  termLabel,      // NEW: optional, triggers enrollment fetch
  limit,          // pagination
  skip            // pagination
});

// Returned courses now include:
{
  id: string,
  code: string,
  name: string,
  credits: number,
  sectionCount: number,
  enrolledStudents: number,  // NEW: from enrollments collection
  capacity: number,          // NEW: from enrollments collection
  fillRate: number,          // NEW: calculated (enrolled/capacity * 100)
  createdAt: string,
}
```

**Behavior**:
- If `termLabel` provided: queries enrollments, returns real data
- If `termLabel` omitted: skips enrollment query, returns 0 for all enrollment fields
- Gracefully handles missing enrollment records (shows 0%)

---

### 2. Frontend API Endpoints

#### New Route: `/api/coordinator/enrollments`

**GET** - Fetch enrollment for a course
```bash
GET /api/coordinator/enrollments?courseId=<id>&termLabel=<label>

Response (200):
{
  "enrollment": {
    "id": "ObjectId",
    "courseId": "ObjectId",
    "enrolledStudents": 45,
    "capacity": 50,
    "fillRate": 90,
    "updatedAt": "2024-01-15T10:30:00.000Z"
  }
}

Response (404):
{ "message": "No enrollment found", "enrollment": null }
```

**POST** - Create/update enrollment
```bash
POST /api/coordinator/enrollments
Content-Type: application/json

{
  "courseId": "ObjectId",
  "termLabel": "Fall 2024",
  "enrolledStudents": 45,
  "capacity": 50
}

Response (201/200):
{
  "ok": true,
  "message": "Enrollment created|updated",
  "enrollment": {
    "courseId": "ObjectId",
    "termLabel": "Fall 2024",
    "enrolledStudents": 45,
    "capacity": 50,
    "fillRate": 90
  }
}
```

**DELETE** - Remove enrollment
```bash
DELETE /api/coordinator/enrollments?courseId=<id>&termLabel=<label>

Response (200):
{ "ok": true, "message": "Enrollment deleted" }

Response (404):
{ "message": "Enrollment not found" }
```

---

### 3. Bulk Import Enhancement

Extended `/api/coordinator/import` POST endpoint to support enrollments CSV.

**CSV Format** (either course_code or course_id):
```csv
course_code,term_label,enrolled_students,capacity
CS101,Fall 2024,48,50
CS102,Fall 2024,52,50
CS103,Fall 2024,35,40
```

Or with course IDs:
```csv
course_id,term_label,enrolled_students,capacity
507f1f77bcf86cd799439011,Fall 2024,48,50
507f1f77bcf86cd799439012,Fall 2024,52,50
```

**Upload**:
```javascript
const formData = new FormData();
formData.append("file", csvFile);
formData.append("type", "enrollments");  // NEW type

const res = await fetch("/api/coordinator/import", {
  method: "POST",
  body: formData,
});

const { imported, type } = await res.json();
// imported = number of records created/updated
```

**Behavior**:
- Resolves course_code → course_id lookup if needed
- Creates if doesn't exist, updates if exists
- Skips invalid rows (missing termLabel, capacity <= 0, invalid courseId)
- Upserts via unique constraint (institution_id, term_label, course_id)

---

### 4. Frontend UI Updates

#### Updated `/api/coordinator/courses` Response

The endpoint now includes enrollment data when queried:

```javascript
// Courses page can optionally pass termLabel
const res = await fetch("/api/coordinator/courses?termLabel=Fall%202024");
const { items } = await res.json();

// Each course now has fillRate (real, not random!)
items[0] = {
  id: "...",
  code: "CS101",
  name: "Intro to CS",
  credits: 3,
  sectionCount: 2,
  enrolledStudents: 48,    // NEW: real data
  capacity: 50,           // NEW: real data  
  fillRate: 96,           // NEW: real data (replaced hardcoded Math.random())
}
```

#### CourseCard Display

CourseCard component already displays fillRate with color coding:
- Green: < 70% (low pressure)
- Yellow: 70-90% (moderate pressure)
- Red: >= 90% (high pressure, overcapacity)

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  COORDINATOR DASHBOARD                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ GET /api/coordinator/courses
                            │ (with optional ?termLabel=)
                            ▼
            ┌───────────────────────────────────┐
            │   Next.js API Route                │
            │   /api/coordinator/courses         │
            │                                   │
            │  1. Fetch courses from MongoDB   │
            │  2. If termLabel: fetch            │
            │     enrollments for all courses    │
            │  3. Merge data + calculate         │
            │     fillRate                       │
            └───────────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────────┐
            │      MongoDB Collections          │
            │                                   │
            │  - courses (existing)             │
            │  - enrollments (Phase 1)          │
            └───────────────────────────────────┘
                            │
                            ├─ Course data
                            └─ Enrollment data
                                 (or default 0%)
                            │
                            ▼
            ┌───────────────────────────────────┐
            │   JSON Response to Frontend       │
            │   (fillRate: real, not random)    │
            └───────────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────────┐
            │   CourseCard Component            │
            │   Displays fillRate with color    │
            └───────────────────────────────────┘
```

---

## How to Use

### 1. Add Enrollment Data

**Option A: Via API Endpoint**
```javascript
// Create/update enrollment for a course
const response = await fetch("/api/coordinator/enrollments", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    courseId: "507f1f77bcf86cd799439011",
    termLabel: "Fall 2024",
    enrolledStudents: 48,
    capacity: 50,
  }),
});
```

**Option B: Bulk Import via CSV**
1. Go to Coordinator Dashboard → Import
2. Upload CSV with `type=enrollments`
3. System automatically creates/updates records

### 2. View Real Fill Rates

Courses page automatically shows real fill rates (from enrollments collection):
- No random numbers
- Updates reflect actual enrollment data
- Can filter by term if termLabel is provided

### 3. Query Enrollments

**Get single enrollment**:
```javascript
const res = await fetch("/api/coordinator/enrollments?courseId=...&termLabel=...");
const { enrollment } = await res.json();
console.log(enrollment.fillRate);  // e.g., 96
```

**Get all course enrollments with data**:
```javascript
const res = await fetch("/api/coordinator/courses?termLabel=Fall%202024");
const { items } = await res.json();

items.forEach(course => {
  console.log(`${course.code}: ${course.fillRate}% full`);
});
```

---

## Database Changes

### Collections Modified
- `enrollments` (used, created in Phase 1)

### Indexes Used
- `institution_id + term_label + course_id` (unique)
- `institution_id + term_label` (for bulk queries)
- `updated_at` (for sorting)

---

## Backward Compatibility

✅ **Fully backward compatible**:
- If `termLabel` not provided: returns enrolledStudents=0, capacity=0, fillRate=0
- If enrollment doesn't exist: returns enrolledStudents=0, capacity=0, fillRate=0
- Existing code doesn't break - just shows 0% fill until enrollments added

✅ **Graceful degradation**:
- Missing enrollment records don't cause errors
- Frontend displays 0% fill (shows potential, not actual pressure)
- Coordinator can add enrollments anytime without affecting existing data

---

## Testing Checklist

- [ ] Create enrollment via API POST
- [ ] Fetch enrollment via API GET
- [ ] Update enrollment (upsert behavior)
- [ ] Delete enrollment (soft delete)
- [ ] Bulk import CSV with enrollments
- [ ] Verify fillRate calculated correctly
- [ ] Verify CourseCard displays fillRate
- [ ] Test with missing enrollments (shows 0%)
- [ ] Test with termLabel provided and omitted
- [ ] Verify backward compatibility (old code still works)

---

## Files Modified

1. **schedula proj/lib/server/coordinatorService.js**
   - Added 4 new enrollment functions
   - Updated getCoordinatorCourses() to fetch enrollments

2. **schedula proj/app/api/coordinator/courses/route.js**
   - Removed hardcoded fill rates
   - Added termLabel parameter
   - Now uses real enrollment data

3. **schedula proj/app/api/coordinator/enrollments/route.js** (NEW)
   - GET: fetch single enrollment
   - POST: create/update enrollment
   - DELETE: soft delete enrollment

4. **schedula proj/app/api/coordinator/import/route.js**
   - Added `type === "enrollments"` handling
   - Bulk upsert for enrollment CSV

---

## Next Steps (Phase 3)

Phase 3 will implement hard constraint enforcement in the solver:
- Use enrollment data to validate capacity constraints
- Implement missing hard constraints (H3, H4, H6, H7)
- Add conflict detection and resolution tracking

Phase 4 will:
- Update staff schedule page to use real API instead of hardcoded data
- Test end-to-end with real enrollment data
