# Schedula Solver API — Setup & Integration Guide

**For:** Next.js Frontend Development Team
**Audience:** Frontend developers integrating with the solver API
**Last Updated:** 2026-03-23

---

## 📋 Prerequisites

- **Node.js 18+** (for Next.js frontend)
- **Python 3.12+** (backend — likely managed by backend team)
- **MongoDB Atlas account** (backend team manages this)
- **Git** (to clone both repositories)

---

## 🚀 Quick Start (5 minutes)

### 1. Clone Repositories

```bash
# Frontend (Next.js)
git clone https://github.com/your-org/schedula-nextjs.git
cd schedula-nextjs

# Backend (in another terminal)
git clone https://github.com/your-org/schedula-fastapi.git
cd schedula-fastapi
```

### 2. Start Backend (Python team usually does this)

```bash
cd schedula-fastapi

# Create virtual environment (if not done)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
python -m uvicorn app.main:app --reload
# API running at http://localhost:8000
```

### 3. Configure Frontend

```bash
cd schedula-nextjs

# Create .env.local
cat > .env.local << EOF
NEXT_PUBLIC_SOLVER_API_URL=http://localhost:8000
EOF

# Install dependencies
npm install

# Start Next.js
npm run dev
# Frontend running at http://localhost:3000
```

### 4. Verify Connection

```bash
# Test health check
curl http://localhost:8000/health/ready

# Output should be:
# {"status":"ready","database":"connected"}
```

---

## 📚 Documentation Files

| File | Purpose | Read Time |
|------|---------|-----------|
| **API_DOCUMENTATION.md** | Complete API reference (all endpoints, constraints, models) | 20 min |
| **FRONTEND_INTEGRATION_GUIDE.md** | Integration patterns, code examples, TypeScript types | 15 min |
| **postman_collection.json** | Postman API collection (import and test endpoints) | 5 min |
| **This file** | Setup and quick reference | 5 min |

---

## 🔧 Integration Steps

### Step 1: Create API Client

```typescript
// lib/scheduler-api.ts
import axios from 'axios';

const schedulerAPI = axios.create({
  baseURL: process.env.NEXT_PUBLIC_SOLVER_API_URL || 'http://localhost:8000',
  timeout: 65000,
});

export default schedulerAPI;
```

### Step 2: Create Custom Hook

```typescript
// hooks/useScheduleGeneration.ts
import { useState } from 'react';
import schedulerAPI from '@/lib/scheduler-api';

export function useScheduleGeneration() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateSchedule = async (institutionId: string, term: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await schedulerAPI.post('/schedule/generate', {
        institution_id: institutionId,
        term_label: term,
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

### Step 3: Use in Component

```typescript
// components/ScheduleGenerator.tsx
'use client';

import { useScheduleGeneration } from '@/hooks/useScheduleGeneration';
import { useState } from 'react';

export function ScheduleGenerator() {
  const { generateSchedule, loading, error } = useScheduleGeneration();
  const [schedule, setSchedule] = useState(null);

  const handleGenerate = async (institutionId: string, term: string) => {
    try {
      const result = await generateSchedule(institutionId, term);
      setSchedule(result);
    } catch (err) {
      console.error('Failed:', err);
    }
  };

  return (
    <div>
      <button onClick={() => handleGenerate('test-inst-001', 'fall-2024')} disabled={loading}>
        {loading ? 'Generating...' : 'Generate Schedule'}
      </button>

      {error && <div className="error">{error}</div>}

      {schedule && (
        <div>
          <h2>✓ Schedule Generated</h2>
          <p>Sections: {schedule.summary.scheduled_sections}/{schedule.summary.total_sections}</p>
          <p>Hard Violations: {schedule.hard_violations}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 📡 API Endpoints Quick Reference

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Check if API is alive |
| GET | `/health/ready` | Check if API + MongoDB are ready |
| POST | `/schedule/generate` | Generate schedule (main endpoint) |

### Generate Schedule Request

```json
{
  "institution_id": "string",        // Required: institution ID
  "term_label": "string",            // Required: e.g., "fall-2024"
  "weights": {                       // Optional: customize priorities
    "break_window": 100,             // Staff break preference
    "consecutive_slots": 80,         // Consecutive teaching blocks
    "session_spread": 60,            // Spread sessions per week
    "campus_clustering": 40          // Cluster by building
  },
  "section_type_durations": {        // Optional: custom session lengths
    "lecture": 60,                   // In minutes
    "lab": 90,
    "tutorial": 45
  }
}
```

### Generate Schedule Response

```json
{
  "snapshot_id": "uuid",
  "institution_id": "string",
  "term_label": "string",
  "generated_at": "2026-03-23T...",
  "entries": [                       // Scheduled sessions
    {
      "section_id": "string",
      "day_of_week": 0-4,            // 0=Mon, 4=Fri
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "room_id": "string",
      "assigned_staff": ["string"],
      "year_levels": [1, 2],
      "capacity": 45
    }
  ],
  "hard_violations": 0,              // Must be 0
  "soft_penalty": 240.5,             // Lower is better
  "warnings": [],
  "summary": {
    "total_sections": 3,
    "scheduled_sections": 3,
    "total_staff": 2,
    "total_rooms": 2,
    "weights": {...}
  }
}
```

---

## 🧪 Testing with Postman

### Import Collection
1. Open Postman
2. **File → Import**
3. Select `postman_collection.json` from this repository
4. Set variable: `baseUrl = http://localhost:8000`
5. Start testing endpoints

### Sample Requests (Postman)
- **Health Check:** `GET /health`
- **Basic Schedule:** `POST /schedule/generate` with `{"institution_id": "test-inst-001", "term_label": "fall-2024"}`
- **Custom Weights:** Include `weights` object in request body

---

## 🌍 Environment Configuration

### Local Development `.env.local`
```bash
NEXT_PUBLIC_SOLVER_API_URL=http://localhost:8000
```

### Staging `.env.staging`
```bash
NEXT_PUBLIC_SOLVER_API_URL=https://solver-staging.schedula.dev
```

### Production `.env.production`
```bash
NEXT_PUBLIC_SOLVER_API_URL=https://solver.schedula.dev
```

---

## 📊 Constraint Priority Examples

### Example 1: Lab-Heavy Schedule
Optimize for lab clustering and consecutive sessions
```json
{
  "break_window": 50,          // Low priority
  "consecutive_slots": 150,    // High priority
  "session_spread": 40,        // Low priority
  "campus_clustering": 250     // Very high priority
}
```

### Example 2: Staff Wellness-First
Optimize for breaks and session spread
```json
{
  "break_window": 300,         // Very high priority
  "consecutive_slots": 50,     // Low priority
  "session_spread": 150,       // High priority
  "campus_clustering": 30      // Low priority
}
```

### Example 3: Balanced (Default)
Balanced optimization
```json
{
  "break_window": 100,         // Medium
  "consecutive_slots": 80,     // Medium
  "session_spread": 60,        // Medium-low
  "campus_clustering": 40      // Medium-low
}
```

---

## ⚡ Performance Expectations

| Metric | Value |
|--------|-------|
| **Health Check** | < 10ms |
| **Schedule Generation** | 0.5–5 seconds (depends on size) |
| **Solver Timeout** | 60 seconds |
| **Max Sections** | 500+ |
| **Typical Sections** | 50–200 |

### Optimization Tips
1. Add a loading spinner (solver takes 1–5 seconds)
2. Set axios timeout to 65s (60s + buffer)
3. Monitor `soft_penalty` — if > 1000, warn user
4. Cache health checks for 30 seconds
5. Consider pagination if schedule has 100+ entries

---

## 🐛 Common Issues & Solutions

### Issue 1: `Cannot connect to http://localhost:8000`
**Cause:** Backend API not running
**Solution:**
```bash
cd schedula-fastapi
python -m uvicorn app.main:app --reload
```

### Issue 2: `404 Institution not found`
**Cause:** Institution ID doesn't exist
**Solution:** Verify institution_id matches MongoDB data

### Issue 3: `Request timeout (60s)`
**Cause:** Schedule too complex or solver taking too long
**Solution:**
- Increase `SOLVER_TIME_LIMIT_SECONDS` (backend config)
- Add more rooms to reduce conflicts
- Relax staff availability constraints

### Issue 4: CORS errors in browser
**Cause:** Frontend origin not whitelisted
**Solution:** Backend team must add your frontend origin to CORS settings

### Issue 5: `High soft penalty` warning
**Cause:** Many soft constraints violated
**Solution:**
- Review constraints in database
- Adjust weight priorities
- Add more resources (rooms, staff)

---

## 🔍 Debugging

### Check API Health
```bash
curl http://localhost:8000/health/ready
# Should return: {"status":"ready","database":"connected"}
```

### Check API Logs
```bash
# If running with --reload (development)
# Look at console output for errors

# Common errors:
# - "Institution not found" → verify institution_id
# - "No courses found" → add courses to institution
# - "Solver error" → check constraint model
```

### Test with cURL
```bash
# Basic request
curl -X POST http://localhost:8000/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{"institution_id": "test-inst-001", "term_label": "fall-2024"}'

# With custom weights
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

## 📖 Full Documentation

For complete details, see:
- **API_DOCUMENTATION.md** — All endpoints, models, constraints
- **FRONTEND_INTEGRATION_GUIDE.md** — Code examples, patterns, TypeScript types

---

## 🤝 Support & Contact

**Questions?**
- Check **API_DOCUMENTATION.md** (common issues section)
- Review **FRONTEND_INTEGRATION_GUIDE.md** (troubleshooting)
- Access Swagger UI: `http://localhost:8000/docs` (interactive)

**Report Issues:**
- GitHub: `https://github.com/your-org/schedula-fastapi/issues`

---

## ✅ Verification Checklist

- [ ] Backend running: `http://localhost:8000/health` returns 200
- [ ] MongoDB connected: `http://localhost:8000/health/ready` returns `"ready"`
- [ ] Frontend `.env.local` configured with `NEXT_PUBLIC_SOLVER_API_URL`
- [ ] API client created (`lib/scheduler-api.ts`)
- [ ] Custom hook created (`hooks/useScheduleGeneration.ts`)
- [ ] Component integrated with schedule generation
- [ ] Test request succeeds with cURL
- [ ] Postman collection imported and tested
- [ ] Load state displays while generating
- [ ] Error handling displays user-friendly messages

---

**Ready to integrate?** Start with the integration steps above, then refer to **FRONTEND_INTEGRATION_GUIDE.md** for code patterns.

Good luck! 🚀
