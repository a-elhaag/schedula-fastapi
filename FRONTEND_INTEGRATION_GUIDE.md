# Frontend Integration Guide — Schedula Solver API

**For:** Next.js Frontend Team
**Purpose:** Quick reference for integrating with the schedule solver
**Last Updated:** 2026-03-23

---

## Quick Start (Copy-Paste Ready)

### 1. Install Dependencies

```bash
npm install axios  # or fetch, your choice
```

### 2. API Client Setup

```typescript
// lib/scheduler-api.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_SOLVER_API_URL || 'http://localhost:8000';

const schedulerAPI = axios.create({
  baseURL: API_BASE_URL,
  timeout: 65000,  // Solver timeout is 60s
  headers: {
    'Content-Type': 'application/json',
  },
});

export default schedulerAPI;
```

### 3. Health Check

```typescript
// Verify API is ready before allowing schedule generation
export async function checkSolverHealth() {
  try {
    const response = await schedulerAPI.get('/health/ready');
    return response.data.status === 'ready';
  } catch (error) {
    console.error('Solver not ready:', error);
    return false;
  }
}
```

### 4. Generate Schedule (Basic)

```typescript
// hooks/useScheduleGeneration.ts
import { useState } from 'react';
import schedulerAPI from '@/lib/scheduler-api';

export function useScheduleGeneration() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [schedule, setSchedule] = useState<any>(null);

  const generateSchedule = async (institutionId: string, termLabel: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await schedulerAPI.post('/schedule/generate', {
        institution_id: institutionId,
        term_label: termLabel,
      });

      setSchedule(response.data);
      return response.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message;
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  return { generateSchedule, loading, error, schedule };
}
```

### 5. Use in a Component

```typescript
// components/ScheduleGenerator.tsx
'use client';

import { useScheduleGeneration } from '@/hooks/useScheduleGeneration';
import { useState, useEffect } from 'react';

export function ScheduleGenerator({ institutionId }: { institutionId: string }) {
  const { generateSchedule, loading, error, schedule } = useScheduleGeneration();
  const [term, setTerm] = useState('fall-2024');

  const handleGenerate = async () => {
    try {
      const result = await generateSchedule(institutionId, term);
      console.log('Schedule generated:', result);
      // Display schedule in your UI
    } catch (err) {
      console.error('Generation failed:', err);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        placeholder="e.g., fall-2024"
      />
      <button onClick={handleGenerate} disabled={loading}>
        {loading ? 'Generating...' : 'Generate Schedule'}
      </button>

      {error && <div className="error">{error}</div>}

      {schedule && (
        <div>
          <p>✓ Generated {schedule.summary.scheduled_sections} of {schedule.summary.total_sections} sections</p>
          <p>Hard Violations: {schedule.hard_violations}</p>
          {schedule.warnings.length > 0 && (
            <ul>
              {schedule.warnings.map((w: string, i: number) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## API Endpoints Reference

### Health Checks
```typescript
// Quick check
GET /health
Response: { status: "healthy", timestamp: "2026-03-23T..." }

// Full check (includes MongoDB)
GET /health/ready
Response: { status: "ready", database: "connected" }
```

### Schedule Generation
```typescript
POST /schedule/generate
Content-Type: application/json

Request:
{
  institution_id: string         // Required
  term_label: string             // Required (e.g., "fall-2024")
  weights?: {                    // Optional - override solver priorities
    break_window?: number        // Default: 100
    consecutive_slots?: number   // Default: 80
    session_spread?: number      // Default: 60
    campus_clustering?: number   // Default: 40
  }
  section_type_durations?: {     // Optional - override session lengths
    lecture?: number             // In minutes
    lab?: number
    tutorial?: number
  }
}

Response:
{
  snapshot_id: string            // Unique ID for this schedule
  institution_id: string
  term_label: string
  generated_at: string           // ISO timestamp
  entries: [
    {
      section_id: string
      day_of_week: 0-4            // 0=Monday, 4=Friday
      start_time: string          // "09:00"
      end_time: string            // "10:00"
      room_id: string
      assigned_staff: string[]
      year_levels: number[]
      capacity: number
    }
  ]
  hard_violations: number        // 0 = no violations
  soft_penalty: number           // Lower is better
  warnings: string[]
  summary: {
    total_sections: number
    scheduled_sections: number
    total_staff: number
    total_rooms: number
    weights: object              // Final weights used
  }
}
```

---

## Common Patterns

### Pattern 1: Display Schedule as Table

```typescript
interface ScheduleEntry {
  section_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  room_id: string;
  assigned_staff: string[];
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

export function ScheduleTable({ entries }: { entries: ScheduleEntry[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Section</th>
          <th>Day</th>
          <th>Time</th>
          <th>Room</th>
          <th>Instructor</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr key={`${entry.section_id}-${entry.day_of_week}-${entry.start_time}`}>
            <td>{entry.section_id}</td>
            <td>{DAYS[entry.day_of_week]}</td>
            <td>{entry.start_time}-{entry.end_time}</td>
            <td>{entry.room_id}</td>
            <td>{entry.assigned_staff.join(', ')}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### Pattern 2: Visualize Schedule as Weekly Grid

```typescript
export function WeeklyScheduleGrid({ entries }: { entries: ScheduleEntry[] }) {
  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
  const HOURS = Array.from({ length: 8 }, (_, i) => `${9 + i}:00`);

  const getSessionsAt = (day: number, time: string) => {
    return entries.filter(
      (e) => e.day_of_week === day && e.start_time === time
    );
  };

  return (
    <div className="grid">
      <div className="corner" />
      {DAYS.map((day) => (
        <div key={day} className="day-header">{day}</div>
      ))}

      {HOURS.map((hour) => (
        <>
          <div key={`hour-${hour}`} className="hour-header">{hour}</div>
          {DAYS.map((day, dayIdx) => {
            const sessions = getSessionsAt(dayIdx, hour);
            return (
              <div key={`${day}-${hour}`} className="cell">
                {sessions.map((s) => (
                  <div key={s.section_id} className="session">
                    <strong>{s.section_id}</strong>
                    <br />
                    {s.room_id}
                  </div>
                ))}
              </div>
            );
          })}
        </>
      ))}
    </div>
  );
}
```

### Pattern 3: Handle Solver Errors

```typescript
async function generateWithErrorHandling(institutionId: string, term: string) {
  try {
    const schedule = await schedulerAPI.post('/schedule/generate', {
      institution_id: institutionId,
      term_label: term,
    });

    // Check warnings
    if (schedule.data.hard_violations > 0) {
      showAlert('⚠️ Schedule has hard constraint violations', 'warning');
    }

    if (schedule.data.warnings.length > 0) {
      console.warn('Schedule warnings:', schedule.data.warnings);
    }

    if (schedule.data.soft_penalty > 1000) {
      showAlert('High soft penalty - consider adjusting weights', 'info');
    }

    return schedule.data;

  } catch (error: any) {
    if (error.response?.status === 404) {
      showAlert('Institution not found', 'error');
    } else if (error.response?.status === 400) {
      showAlert('Invalid request or no courses found', 'error');
    } else if (error.response?.status === 500) {
      showAlert('Solver error - check logs', 'error');
    } else {
      showAlert(`Unexpected error: ${error.message}`, 'error');
    }
    throw error;
  }
}
```

### Pattern 4: Adjust Constraint Weights

```typescript
// Prioritize consecutive teaching blocks (no fragmentation)
const lectureHeavyWeights = {
  break_window: 50,
  consecutive_slots: 200,  // High priority
  session_spread: 30,
  campus_clustering: 100,
};

// Prioritize staff breaks (wellness first)
const staffWellnessWeights = {
  break_window: 200,       // High priority
  consecutive_slots: 50,
  session_spread: 100,
  campus_clustering: 30,
};

// Prioritize lab clustering (logistics)
const labClusteringWeights = {
  break_window: 60,
  consecutive_slots: 80,
  session_spread: 40,
  campus_clustering: 250,  // High priority
};

// Use in request
const response = await schedulerAPI.post('/schedule/generate', {
  institution_id: 'test-inst-001',
  term_label: 'fall-2024',
  weights: lectureHeavyWeights,  // or any of the above
});
```

### Pattern 5: Override Session Durations

```typescript
// Some universities have non-standard session lengths
const response = await schedulerAPI.post('/schedule/generate', {
  institution_id: 'test-inst-001',
  term_label: 'fall-2024',
  section_type_durations: {
    lecture: 75,    // 1h 15m (instead of default 60)
    lab: 150,       // 2.5 hours (instead of default 90)
    tutorial: 45,   // Standard
  },
});
```

### Pattern 6: Save Schedule to Database

```typescript
// After getting schedule from solver, persist to your backend
export async function saveScheduleSnapshot(schedule: any) {
  // Your backend should save this snapshot for audit trail
  const response = await fetch('/api/schedules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      snapshot_id: schedule.snapshot_id,
      institution_id: schedule.institution_id,
      term_label: schedule.term_label,
      entries: schedule.entries,
      metadata: {
        generated_at: schedule.generated_at,
        hard_violations: schedule.hard_violations,
        soft_penalty: schedule.soft_penalty,
        warnings: schedule.warnings,
      },
      approved_by: null,  // Coordinator approves later
      approved_at: null,
    }),
  });

  return response.json();
}
```

---

## Environment Setup

### Next.js `.env.local`

```bash
# Solver API endpoint
NEXT_PUBLIC_SOLVER_API_URL=http://localhost:8000

# Or for production
# NEXT_PUBLIC_SOLVER_API_URL=https://solver.schedula.dev
```

### TypeScript Types (Optional but Recommended)

```typescript
// types/schedule.ts

export interface GenerateScheduleRequest {
  institution_id: string;
  term_label: string;
  weights?: SolverWeights;
  section_type_durations?: SectionTypeDurations;
}

export interface SolverWeights {
  break_window?: number;
  consecutive_slots?: number;
  session_spread?: number;
  campus_clustering?: number;
}

export interface SectionTypeDurations {
  lecture?: number;
  lab?: number;
  tutorial?: number;
}

export interface ScheduleEntry {
  section_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  room_id: string;
  assigned_staff: string[];
  year_levels: number[];
  capacity: number;
}

export interface GenerateScheduleResponse {
  snapshot_id: string;
  institution_id: string;
  term_label: string;
  generated_at: string;
  entries: ScheduleEntry[];
  hard_violations: number;
  soft_penalty: number;
  warnings: string[];
  summary: {
    total_sections: number;
    scheduled_sections: number;
    total_staff: number;
    total_rooms: number;
    weights: SolverWeights;
  };
}
```

---

## Testing with cURL

### Test Health
```bash
curl http://localhost:8000/health/ready
# Output: {"status":"ready","database":"connected"}
```

### Test Schedule Generation
```bash
curl -X POST http://localhost:8000/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{
    "institution_id": "test-inst-001",
    "term_label": "fall-2024"
  }'
```

### Test with Custom Weights
```bash
curl -X POST http://localhost:8000/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{
    "institution_id": "test-inst-001",
    "term_label": "fall-2024",
    "weights": {
      "break_window": 200,
      "consecutive_slots": 50,
      "session_spread": 100,
      "campus_clustering": 30
    }
  }'
```

---

## Performance Tips

1. **Cache health checks** - Don't call `/health/ready` on every request. Cache for 30s.
2. **Show loading state** - Solver takes 0.5–5 seconds. Show spinner.
3. **Handle timeouts** - Set axios timeout to 65s (solver timeout is 60s + buffer).
4. **Validate inputs** - Check `institution_id` and `term_label` before sending.
5. **Monitor soft_penalty** - If > 1000, warn user and suggest adjusting weights.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `404 Not found` | Institution doesn't exist | Verify institution_id in MongoDB |
| `400 Bad Request` | No courses found | Ensure institution has courses |
| `500 Solver error` | Invalid constraint model | Check course data format |
| `Timeout` | Solver takes > 60s | Increase SOLVER_TIME_LIMIT_SECONDS or reduce problem size |
| `Cannot connect` | API not running | Start FastAPI: `python -m uvicorn app.main:app` |

---

## Need Help?

- **Swagger UI:** `http://localhost:8000/docs` (interactive API explorer)
- **FastAPI Logs:** Check console output for solver errors
- **MongoDB Issues:** Verify connection string in `.env`

---

**Next.js Version:** 15+
**Python Version:** 3.12+ (backend)
**API Version:** 0.1.0
