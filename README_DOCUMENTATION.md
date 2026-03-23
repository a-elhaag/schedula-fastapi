# 📚 Schedula Solver API — Complete Documentation Index

**Project:** Schedula Schedule Solver
**Version:** 0.1.0
**Status:** ✅ Production Ready (All 19 tests passing)
**Last Updated:** 2026-03-23

---

## 📖 Documentation Overview

This project includes **comprehensive documentation** for all stakeholders. Choose your role below:

### 👨‍💻 **Frontend Developers (Next.js Team)**

Start here if you're integrating the schedule solver into the UI.

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[SETUP_GUIDE.md](SETUP_GUIDE.md)** | 5-minute quick start + integration steps | 5 min |
| **[FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md)** | Code examples, patterns, TypeScript types | 15 min |
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** | Complete API reference (when you need details) | 20 min |
| **[postman_collection.json](postman_collection.json)** | Import into Postman for testing | 5 min |

**Quick Start:** Read SETUP_GUIDE.md first, then use FRONTEND_INTEGRATION_GUIDE.md for code.

---

### 🔧 **Backend/DevOps Team (Python + Azure)**

Start here if you're deploying, scaling, or maintaining the API.

| Document | Purpose | Read Time |
|----------|---------|-----------|
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Docker → Azure Container Apps (production) | 30 min |
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** | Complete API reference + constraints | 20 min |
| **[TESTING.md](TESTING.md)** | Unit, integration, and load testing | 15 min |

**Quick Start:** Review DEPLOYMENT.md for production setup, then check TESTING.md for validation.

---

### 📊 **Product/Project Managers**

Start here to understand what the system does and its capabilities.

| Document | Purpose |
|----------|---------|
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md#overview)** | System overview, features, architecture |
| **[CONSTRAINT_SYSTEM](#constraint-system-reference)** (below) | What the solver optimizes for |

---

## 🚀 Quick Navigation

### I want to...

**Generate a schedule via API**
→ See [API_DOCUMENTATION.md — Schedule Generation](API_DOCUMENTATION.md#generate-optimal-schedule)

**Integrate with Next.js**
→ See [FRONTEND_INTEGRATION_GUIDE.md — Quick Start](FRONTEND_INTEGRATION_GUIDE.md#quick-start-copy-paste-ready)

**Deploy to production**
→ See [DEPLOYMENT.md — Azure Container Apps](DEPLOYMENT.md#3-azure-container-apps-deployment)

**Test the API locally**
→ See [SETUP_GUIDE.md — Quick Start](SETUP_GUIDE.md#-quick-start-5-minutes)

**Understand constraints**
→ See [Constraint System Reference](#constraint-system-reference) (below)

**Adjust solver priorities**
→ See [FRONTEND_INTEGRATION_GUIDE.md — Pattern 4](FRONTEND_INTEGRATION_GUIDE.md#pattern-4-adjust-constraint-weights)

**Run tests**
→ See [TESTING.md](TESTING.md)

---

## 🎯 Constraint System Reference

### Hard Constraints (Must Satisfy)

The solver **cannot violate** these constraints. If infeasible, returns best approximation with `hard_violations > 0`.

| ID | Name | Description | Impact |
|----|------|-------------|--------|
| **H1** | Room No-Overlap | No two sessions in same room at same time | Critical |
| **H2** | Staff No-Overlap | No instructor teaches simultaneously | Critical |
| **H3** | Room Capacity | Student count ≤ room capacity | High |
| **H4** | Room Features | Required lab/equipment available | High |
| **H5** | Staff Day-Off | Instructors not on their assigned day-off | High |
| **H6** | Session Slots | All required slots scheduled | Critical |
| **H7** | Year-Level Conflicts | No simultaneous sessions in same building for same year | Medium |
| **H8** | Staff Availability | Sessions only during availability windows | High |
| **H9** | Shared Sections | Shared courses same time+room | Medium |

### Soft Constraints (Optimize)

These are **preferences** with configurable weights. Goal is to minimize penalties.

| ID | Name | Default Weight | Description | Examples |
|----|------|-----------------|-------------|----------|
| **S1** | Break Windows | 100 | Schedule staff lunch/breaks | 12:00–13:00 lunch preference |
| **S2** | Consecutive Slots | 80 | Prefer consecutive blocks | Minimize fragmentation |
| **S3** | Session Spread | 60 | Spread throughout week | Avoid 3+ sections on one day |
| **S4** | Campus Clustering | 40 | Cluster by building/campus | Keep labs together |

**How to adjust:** See [FRONTEND_INTEGRATION_GUIDE.md — Pattern 4](FRONTEND_INTEGRATION_GUIDE.md#pattern-4-adjust-constraint-weights)

---

## 📡 API Endpoints Quick Reference

### Health & Status

```http
GET /health
GET /health/ready
```

### Schedule Generation

```http
POST /schedule/generate
Content-Type: application/json

{
  "institution_id": "string",
  "term_label": "string",
  "weights": { ... },  // Optional
  "section_type_durations": { ... }  // Optional
}
```

**Full Details:** See [API_DOCUMENTATION.md — Endpoints](API_DOCUMENTATION.md#endpoints)

---

## 🛠️ Setup Checklist

### Local Development (5 minutes)

```bash
# 1. Backend
cd schedula-fastapi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# 2. Frontend (in another terminal)
cd schedula-nextjs
npm install
NEXT_PUBLIC_SOLVER_API_URL=http://localhost:8000 npm run dev

# 3. Verify
curl http://localhost:8000/health/ready
# {"status":"ready","database":"connected"}
```

**Full Setup:** See [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 📊 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Health Check** | < 10ms | Synchronous |
| **Schedule Generation** | 0.5–5s | Depends on size |
| **Max Timeout** | 60s | Configurable |
| **Max Sections** | 500+ | Tested |
| **Max Rooms** | 100+ | Tested |
| **Parallel Workers** | 8 | Portfolio approach |

---

## 🐳 Deployment Overview

### Local (Docker)
```bash
docker build -t schedula-api:latest .
docker run -p 8000:8000 --env-file .env schedula-api:latest
```

### Production (Azure Container Apps)
```bash
# Push to registry
docker push schedularegistry.azurecr.io/schedula-api:latest

# Deploy
az containerapp update --name schedula-api --resource-group schedula-rg \
  --image schedularegistry.azurecr.io/schedula-api:latest
```

**Full Guide:** See [DEPLOYMENT.md](DEPLOYMENT.md)

---

## ✅ Testing

All **19 tests passing**:
- 10 unit tests (solver logic)
- 2 route tests (endpoints)
- 7 integration tests (full API + MongoDB)

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_solver.py -v        # Unit tests
pytest tests/test_integration.py -v   # Integration tests
```

**Full Testing Guide:** See [TESTING.md](TESTING.md)

---

## 🔐 Environment Variables

### Required
```bash
MONGODB_URI=mongodb+srv://...  # Connection string
MONGODB_DB_NAME=schedula       # Database name
```

### Optional
```bash
DEBUG=False                           # Development mode
SOLVER_TIME_LIMIT_SECONDS=60         # Timeout
SOLVER_NUM_WORKERS=8                 # Parallel workers
SOFT_WEIGHT_BREAK_WINDOW=100         # Constraint weights
SOFT_WEIGHT_CONSECUTIVE_SLOTS=80
SOFT_WEIGHT_SESSION_SPREAD=60
SOFT_WEIGHT_CAMPUS_CLUSTERING=40
```

---

## 🤝 Support Matrix

| Question | Answer | Document |
|----------|--------|----------|
| How do I use the API? | POST /schedule/generate with institution_id & term_label | [API_DOCUMENTATION.md](API_DOCUMENTATION.md) |
| How do I integrate with Next.js? | Use useScheduleGeneration hook + fetch/axios | [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md) |
| How do I deploy? | Docker → Azure Container Apps | [DEPLOYMENT.md](DEPLOYMENT.md) |
| How do I test locally? | pytest or Postman | [TESTING.md](TESTING.md) + [postman_collection.json](postman_collection.json) |
| How do I adjust priorities? | Modify "weights" in request | [FRONTEND_INTEGRATION_GUIDE.md — Pattern 4](FRONTEND_INTEGRATION_GUIDE.md#pattern-4-adjust-constraint-weights) |
| What constraints are enforced? | 9 hard + 4 soft constraints | [Constraint System Reference](#constraint-system-reference) (above) |
| How do I scale to production? | Use auto-scaling in Azure | [DEPLOYMENT.md — Scaling](DEPLOYMENT.md#6-scaling-configuration) |
| What if schedule fails? | Check hard_violations in response | [API_DOCUMENTATION.md — Error Handling](API_DOCUMENTATION.md#error-handling) |

---

## 📁 Project Structure

```
schedula-fastapi/
├── app/
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Configuration from .env
│   ├── models/
│   │   └── solver.py           # Request/response models
│   ├── routes/
│   │   ├── health.py           # Health check endpoints
│   │   └── solver.py           # Schedule generation endpoint
│   ├── services/
│   │   └── solver_service.py   # OR-Tools CP-SAT solver
│   └── database/
│       ├── client.py           # MongoDB connection
│       └── queries.py          # Database queries
├── tests/
│   ├── test_solver.py          # Unit tests (10 tests)
│   ├── test_routes.py          # Route tests (2 tests)
│   ├── test_integration.py     # Integration tests (7 tests)
│   └── conftest.py             # Pytest configuration
├── Dockerfile                  # Container image
├── docker-compose.yml          # Local MongoDB (dev only)
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── .env                        # Environment variables
├── .env.example                # Example configuration
│
├── 📚 DOCUMENTATION (You are here)
├── API_DOCUMENTATION.md        # Complete API reference
├── FRONTEND_INTEGRATION_GUIDE.md # Frontend patterns & code
├── SETUP_GUIDE.md              # Quick start
├── DEPLOYMENT.md               # Production deployment
├── TESTING.md                  # Testing guide
├── postman_collection.json     # Postman endpoints
└── README_DOCUMENTATION.md     # This file
```

---

## 🎓 Learning Path

### For Frontend Developers
1. Read [SETUP_GUIDE.md](SETUP_GUIDE.md) (5 min)
2. Follow Quick Start section
3. Read [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md) (15 min)
4. Copy code patterns into your project
5. Test with [postman_collection.json](postman_collection.json)

### For Backend/DevOps
1. Read [DEPLOYMENT.md](DEPLOYMENT.md) (30 min)
2. Set up Docker locally
3. Create Azure Container Apps
4. Configure GitHub Actions CI/CD
5. Read [TESTING.md](TESTING.md) for validation

### For Product/Managers
1. Read [API_DOCUMENTATION.md — Overview](API_DOCUMENTATION.md#overview)
2. Review [Constraint System Reference](#constraint-system-reference) (above)
3. Check performance characteristics (this page)

---

## 🚨 Critical Files

These files are essential for different roles:

| Role | Critical Files |
|------|-----------------|
| **Frontend Dev** | SETUP_GUIDE.md, FRONTEND_INTEGRATION_GUIDE.md |
| **Backend Dev** | API_DOCUMENTATION.md, TESTING.md |
| **DevOps/Infra** | DEPLOYMENT.md, Dockerfile, docker-compose.yml |
| **QA/Tester** | TESTING.md, postman_collection.json |
| **PM/Manager** | API_DOCUMENTATION.md (Overview + Constraints) |

---

## 🔗 External References

- **MongoDB Atlas**: https://www.mongodb.com/cloud/atlas
- **Google OR-Tools**: https://developers.google.com/optimization
- **FastAPI**: https://fastapi.tiangolo.com/
- **Azure Container Apps**: https://learn.microsoft.com/en-us/azure/container-apps/
- **Next.js**: https://nextjs.org/docs

---

## 📞 Getting Help

1. **API not responding?** Check [SETUP_GUIDE.md — Common Issues](SETUP_GUIDE.md#-common-issues--solutions)
2. **Integration help?** See [FRONTEND_INTEGRATION_GUIDE.md — Examples](FRONTEND_INTEGRATION_GUIDE.md#examples)
3. **Deployment blocked?** Check [DEPLOYMENT.md — Troubleshooting](DEPLOYMENT.md#troubleshooting)
4. **Test failures?** See [TESTING.md](TESTING.md)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-03-23 | Initial release with 9 hard + 4 soft constraints, MongoDB integration, full test suite |

---

## ✨ Summary

**Schedula Solver API** is a production-ready, stateless microservice that generates optimal class schedules using constraint-based optimization.

- ✅ **9 hard constraints** (must satisfy)
- ✅ **4 soft constraints** (optimize)
- ✅ **19 passing tests** (unit + integration)
- ✅ **Complete documentation** (for all roles)
- ✅ **Ready to deploy** (Docker + Azure)

---

**Last Updated:** 2026-03-23
**API Version:** 0.1.0
**Status:** 🟢 Production Ready

**Questions?** Choose your role above and read the relevant documentation. 📚
