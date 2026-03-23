# Schedula Solver API Documentation

**Version:** 0.1.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-03-23

---

## 🚀 Quick Links

=== "Frontend Developer"
    **Get started in 30 minutes**

    1. Read [Setup Guide](#setup)
    2. Copy code from [Integration Guide](#integration)
    3. Test with [Postman Collection](#postman)

    [→ Go to Frontend Setup](#setup)

=== "Backend/DevOps"
    **Deploy to production**

    1. Review [Deployment Guide](#deployment)
    2. Check [Testing Guide](#testing)
    3. Monitor with [Azure Guide](#azure)

    [→ Go to Deployment](#deployment)

=== "API Consumer"
    **Just need the API reference**

    [→ Go to API Reference](#api-reference)

---

## Setup Guide {#setup}

### Prerequisites
- Node.js 18+
- Python 3.12+ (backend team manages)
- MongoDB Atlas account

### 5-Minute Quick Start

**Step 1: Clone Repositories**
```bash
# Frontend
git clone https://github.com/your-org/schedula-nextjs.git
cd schedula-nextjs

# Backend (in another terminal)
git clone https://github.com/your-org/schedula-fastapi.git
cd schedula-fastapi
```

**Step 2: Start Backend**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# API running at http://localhost:8000
```

**Step 3: Configure Frontend**
```bash
cd schedula-nextjs
cat > .env.local << EOF
NEXT_PUBLIC_SOLVER_API_URL=http://localhost:8000
EOF
npm install
npm run dev
# Frontend running at http://localhost:3000
```

**Step 4: Verify Connection**
```bash
curl http://localhost:8000/health/ready
# {"status":"ready","database":"connected"}
```

✅ **Done!** API and frontend running.

---

## Integration Guide {#integration}

### API Client Setup

=== "JavaScript/TypeScript"
    ```typescript
    // lib/scheduler-api.ts
    import axios from 'axios';

    const schedulerAPI = axios.create({
      baseURL: process.env.NEXT_PUBLIC_SOLVER_API_URL || 'http://localhost:8000',
      timeout: 65000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    export default schedulerAPI;
    ```

=== "Python"
    ```python
    import httpx

    client = httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=65.0
    )

    response = await client.post(
        "/schedule/generate",
        json={
            "institution_id": "test-inst-001",
            "term_label": "fall-2024"
        }
    )
    ```

=== "cURL"
    ```bash
    curl -X POST http://localhost:8000/schedule/generate \
      -H "Content-Type: application/json" \
      -d '{
        "institution_id": "test-inst-001",
        "term_label": "fall-2024"
      }'
    ```

### Custom React Hook

```typescript
// hooks/useScheduleGeneration.ts
import { useState } from 'react';
import schedulerAPI from '@/lib/scheduler-api';

export function useScheduleGeneration() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateSchedule = async (institutionId: string, termLabel: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await schedulerAPI.post('/schedule/generate', {
        institution_id: institutionId,
        term_label: termLabel,
      });
      return response.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message;
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  return { generateSchedule, loading, error };
}
```

### Use in Component

```typescript
// components/ScheduleGenerator.tsx
'use client';

import { useScheduleGeneration } from '@/hooks/useScheduleGeneration';
import { useState } from 'react';

export function ScheduleGenerator() {
  const { generateSchedule, loading, error } = useScheduleGeneration();
  const [schedule, setSchedule] = useState(null);

  const handleGenerate = async () => {
    try {
      const result = await generateSchedule('test-inst-001', 'fall-2024');
      setSchedule(result);
    } catch (err) {
      console.error('Generation failed:', err);
    }
  };

  return (
    <div>
      <button onClick={handleGenerate} disabled={loading}>
        {loading ? 'Generating...' : 'Generate Schedule'}
      </button>
      {error && <div className="error">{error}</div>}
      {schedule && (
        <div>
          <p>✓ Generated {schedule.summary.scheduled_sections} sections</p>
          <p>Hard Violations: {schedule.hard_violations}</p>
        </div>
      )}
    </div>
  );
}
```

---

## API Reference {#api-reference}

### Health & Status

=== "Health Check"
    ```http
    GET /health
    ```

    **Response:** 200 OK
    ```json
    {
      "status": "healthy",
      "timestamp": "2026-03-23T10:30:45.123Z"
    }
    ```

=== "Readiness Check"
    ```http
    GET /health/ready
    ```

    **Response:** 200 OK
    ```json
    {
      "status": "ready",
      "database": "connected"
    }
    ```

### Generate Schedule

```http
POST /schedule/generate
Content-Type: application/json
```

**Request Body:**
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
    "lecture": 60,
    "lab": 90,
    "tutorial": 45
  }
}
```

**Response:** 200 OK
```json
{
  "snapshot_id": "a1b2c3d4-e5f6-4789-0abc-def123456789",
  "institution_id": "test-inst-001",
  "term_label": "fall-2024",
  "generated_at": "2026-03-23T10:30:45.123Z",
  "entries": [
    {
      "section_id": "sec-cs101-lec",
      "day_of_week": 0,
      "start_time": "09:00",
      "end_time": "10:00",
      "room_id": "room-101",
      "assigned_staff": ["prof-001"],
      "year_levels": [1],
      "capacity": 45
    }
  ],
  "hard_violations": 0,
  "soft_penalty": 240.5,
  "warnings": [],
  "summary": {
    "total_sections": 3,
    "scheduled_sections": 3,
    "total_staff": 2,
    "total_rooms": 2,
    "weights": { ... }
  }
}
```

**Error Responses:**

| Status | Message | Solution |
|--------|---------|----------|
| 400 | No courses found | Add courses to institution |
| 404 | Institution not found | Verify institution_id |
| 500 | Solver error | Check logs |

---

## Constraints {#constraints}

### Hard Constraints (9 - Must Satisfy)

| ID | Name | Description |
|----|------|-------------|
| H1 | Room No-Overlap | No two sessions in same room + time |
| H2 | Staff No-Overlap | No instructor teaches simultaneously |
| H3 | Room Capacity | Students ≤ room capacity |
| H4 | Room Features | Required features available |
| H5 | Staff Day-Off | Respect time-off days |
| H6 | Session Slots | All required slots scheduled |
| H7 | Year-Level Conflicts | No conflicts in building |
| H8 | Staff Availability | Only during availability |
| H9 | Shared Sections | Same time + room |

### Soft Constraints (4 - Optimize)

| ID | Name | Default Weight | Description |
|----|------|-----------------|-------------|
| S1 | Break Windows | 100 | Staff lunch/breaks |
| S2 | Consecutive Slots | 80 | Teaching blocks |
| S3 | Session Spread | 60 | Throughout week |
| S4 | Campus Clustering | 40 | By building |

### Adjust Priorities

=== "Lab-Heavy Schedule"
    Optimize for lab clustering
    ```json
    {
      "break_window": 50,
      "consecutive_slots": 150,
      "session_spread": 40,
      "campus_clustering": 250
    }
    ```

=== "Staff Wellness"
    Optimize for breaks & spread
    ```json
    {
      "break_window": 300,
      "consecutive_slots": 50,
      "session_spread": 150,
      "campus_clustering": 30
    }
    ```

=== "Balanced (Default)"
    Default optimization
    ```json
    {
      "break_window": 100,
      "consecutive_slots": 80,
      "session_spread": 60,
      "campus_clustering": 40
    }
    ```

---

## Deployment {#deployment}

### Local Docker

```bash
docker build -t schedula-api:latest .
docker run -p 8000:8000 --env-file .env schedula-api:latest
```

### Azure Container Apps

=== "Step 1: Push to Registry"
    ```bash
    docker tag schedula-api:latest schedularegistry.azurecr.io/schedula-api:latest
    docker push schedularegistry.azurecr.io/schedula-api:latest
    ```

=== "Step 2: Deploy"
    ```bash
    az containerapp update \
      --name schedula-api \
      --resource-group schedula-rg \
      --image schedularegistry.azurecr.io/schedula-api:latest
    ```

=== "Step 3: Verify"
    ```bash
    curl https://<app-url>/health/ready
    ```

### Environment Variables

```bash
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net
MONGODB_DB_NAME=schedula
DEBUG=False
SOLVER_TIME_LIMIT_SECONDS=60
SOLVER_NUM_WORKERS=8
SOFT_WEIGHT_BREAK_WINDOW=100
SOFT_WEIGHT_CONSECUTIVE_SLOTS=80
SOFT_WEIGHT_SESSION_SPREAD=60
SOFT_WEIGHT_CAMPUS_CLUSTERING=40
```

---

## Testing {#testing}

### Run All Tests

```bash
pytest tests/ -v
```

### Test Coverage

| Type | Count | Time | Purpose |
|------|-------|------|---------|
| Unit Tests | 10 | 0.2s | Solver logic |
| Route Tests | 2 | 0.1s | Endpoints |
| Integration Tests | 7 | 0.3s | Full API |
| **Total** | **19** | **0.6s** | ✅ All passing |

### Test with Postman

1. Import `postman_collection.json`
2. Set variable: `baseUrl = http://localhost:8000`
3. Run requests

---

## Common Issues {#issues}

### "Cannot connect to http://localhost:8000"
**Cause:** Backend not running
**Solution:**
```bash
cd schedula-fastapi
python -m uvicorn app.main:app --reload
```

### "404 Institution not found"
**Cause:** Institution ID doesn't exist
**Solution:** Verify institution_id matches MongoDB data

### "Request timeout (60s)"
**Cause:** Schedule too complex
**Solution:** Add more rooms or relax availability constraints

### CORS errors
**Cause:** Frontend origin not whitelisted
**Solution:** Backend team must update CORS settings

### "High soft penalty" warning
**Cause:** Many soft constraints violated
**Solution:** Adjust weight priorities or add resources

---

## Performance {#performance}

| Metric | Value | Notes |
|--------|-------|-------|
| Health Check | < 10ms | Synchronous |
| Schedule Generation | 0.5–5s | Depends on size |
| Solver Timeout | 60s | Configurable |
| Max Sections | 500+ | Tested |
| Max Rooms | 100+ | Tested |
| Parallel Workers | 8 | Portfolio approach |

---

## Resources {#resources}

- **GitHub:** [schedula-fastapi](https://github.com/your-org/schedula-fastapi)
- **Swagger UI:** `http://localhost:8000/docs` (interactive)
- **MongoDB Atlas:** [Dashboard](https://www.mongodb.com/cloud/atlas)
- **OR-Tools:** [Documentation](https://developers.google.com/optimization)

---

## Support {#support}

**Questions?**

- **API not responding?** → Check [Common Issues](#issues)
- **Integration help?** → See [Integration Guide](#integration)
- **Deployment stuck?** → See [Deployment](#deployment)
- **Tests failing?** → Run `pytest tests/ -v`

---

**API Version:** 0.1.0
**Status:** ✅ Production Ready
**Tests:** 19/19 Passing
**Last Updated:** 2026-03-23
