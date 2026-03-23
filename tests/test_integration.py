"""Integration tests for solver API with real MongoDB."""

import pytest
import httpx
from pymongo.asynchronous.mongo_client import AsyncMongoClient

from app.config import settings


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
async def mongo_db():
    """Connect to MongoDB and get database instance."""
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    # Cleanup before test
    await db.drop_collection("institutions")
    await db.drop_collection("courses")
    await db.drop_collection("users")
    await db.drop_collection("availability")
    await db.drop_collection("rooms")
    await db.drop_collection("constraints")

    yield db

    # Cleanup after test
    await client.aclose()


@pytest.fixture
async def seed_data(mongo_db):
    """Seed test data into MongoDB."""
    inst_id = "test-inst-001"

    # Institution
    await mongo_db["institutions"].insert_one({
        "_id": inst_id,
        "name": "Test University",
        "slug": "test-u",
        "working_days": [0, 1, 2, 3, 4],
        "daily_start_hour": 9,
        "daily_end_hour": 17,
        "slot_duration_minutes": 60,
        "deleted_at": None,
    })

    # Rooms (2 classrooms)
    rooms = [
        {
            "_id": "room-101",
            "institution_id": inst_id,
            "name": "Classroom 101",
            "capacity": 50,
            "label": None,
            "features": [],
            "deleted_at": None,
        },
        {
            "_id": "room-102",
            "institution_id": inst_id,
            "name": "Classroom 102",
            "capacity": 40,
            "label": "lab",
            "features": ["lab_equipment"],
            "deleted_at": None,
        },
    ]
    await mongo_db["rooms"].insert_many(rooms)

    # Staff (2 professors)
    staff = [
        {
            "_id": "prof-001",
            "institution_id": inst_id,
            "name": "Dr. Alice Smith",
            "email": "alice@test-u.edu",
            "role": "professor",
            "department_id": "cs",
            "deleted_at": None,
        },
        {
            "_id": "prof-002",
            "institution_id": inst_id,
            "name": "Dr. Bob Jones",
            "email": "bob@test-u.edu",
            "role": "professor",
            "department_id": "math",
            "deleted_at": None,
        },
    ]
    await mongo_db["users"].insert_many(staff)

    # Availability
    availability = [
        {
            "_id": "avail-001",
            "institution_id": inst_id,
            "staff_id": "prof-001",
            "term_label": "fall-2024",
            "weekly_day_off": 4,  # Friday
            "preferred_break_windows": [
                {
                    "day_of_week": 2,
                    "start_time": "12:00",
                    "end_time": "13:00",
                }
            ],
            "deleted_at": None,
        },
        {
            "_id": "avail-002",
            "institution_id": inst_id,
            "staff_id": "prof-002",
            "term_label": "fall-2024",
            "weekly_day_off": None,
            "preferred_break_windows": [],
            "deleted_at": None,
        },
    ]
    await mongo_db["availability"].insert_many(availability)

    # Courses (3 sections)
    courses = [
        {
            "_id": "sec-cs101-lec",
            "institution_id": inst_id,
            "department_id": "cs",
            "course_name": "Intro to CS",
            "section_type": "lecture",
            "capacity": 45,
            "slots_per_week": 2,
            "slot_duration_minutes": None,
            "year_levels": [1],
            "required_room_label": None,
            "assigned_staff": ["prof-001"],
            "shared_with": [],
            "deleted_at": None,
        },
        {
            "_id": "sec-cs101-lab",
            "institution_id": inst_id,
            "department_id": "cs",
            "course_name": "Intro to CS Lab",
            "section_type": "lab",
            "capacity": 25,
            "slots_per_week": 1,
            "slot_duration_minutes": None,
            "year_levels": [1],
            "required_room_label": "lab",
            "assigned_staff": [],
            "shared_with": [],
            "deleted_at": None,
        },
        {
            "_id": "sec-math101-lec",
            "institution_id": inst_id,
            "department_id": "math",
            "course_name": "Calculus I",
            "section_type": "lecture",
            "capacity": 35,
            "slots_per_week": 2,
            "slot_duration_minutes": None,
            "year_levels": [1],
            "required_room_label": None,
            "assigned_staff": ["prof-002"],
            "shared_with": [],
            "deleted_at": None,
        },
    ]
    await mongo_db["courses"].insert_many(courses)

    # Soft constraint weights
    await mongo_db["constraints"].insert_one({
        "_id": f"constr-{inst_id}",
        "institution_id": inst_id,
        "break_window": 100,
        "consecutive_slots": 80,
        "session_spread": 60,
        "campus_clustering": 40,
        "deleted_at": None,
    })

    yield inst_id

    # Cleanup
    await mongo_db["institutions"].delete_many({"_id": inst_id})
    await mongo_db["courses"].delete_many({"institution_id": inst_id})
    await mongo_db["users"].delete_many({"institution_id": inst_id})
    await mongo_db["availability"].delete_many({"institution_id": inst_id})
    await mongo_db["rooms"].delete_many({"institution_id": inst_id})
    await mongo_db["constraints"].delete_many({"institution_id": inst_id})


# ──────────────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check():
    """Test /health endpoint."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_schedule_generate_success(seed_data):
    """Test successful schedule generation."""
    inst_id = seed_data
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post(
            "/schedule/generate",
            json={
                "institution_id": inst_id,
                "term_label": "fall-2024",
                "weights": None,
            },
        )

    assert resp.status_code == 200
    data = resp.json()

    # Verify response structure
    assert "snapshot_id" in data
    assert data["institution_id"] == inst_id
    assert data["term_label"] == "fall-2024"
    assert "entries" in data
    assert "hard_violations" in data
    assert "soft_penalty" in data
    assert "warnings" in data
    assert "summary" in data

    # Verify no hard violations
    assert data["hard_violations"] == 0

    # Verify all sections scheduled (3 sections)
    assert data["summary"]["total_sections"] == 3
    assert data["summary"]["scheduled_sections"] == 3

    # Verify entries have required fields
    for entry in data["entries"]:
        assert "section_id" in entry
        assert "day_of_week" in entry
        assert "start_time" in entry
        assert "end_time" in entry
        assert "room_id" in entry
        assert entry["day_of_week"] in [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_schedule_no_h5_violation(seed_data):
    """Verify H5 (day-off) constraint: prof-001 has Friday off."""
    inst_id = seed_data
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post(
            "/schedule/generate",
            json={
                "institution_id": inst_id,
                "term_label": "fall-2024",
            },
        )

    data = resp.json()
    entries = data["entries"]

    # Filter prof-001's sessions
    prof1_sessions = [e for e in entries if "prof-001" in e.get("assigned_staff", [])]

    # Verify none are on Friday (day 4)
    for session in prof1_sessions:
        assert session["day_of_week"] != 4, "Prof-001 scheduled on their day off (Friday)"


@pytest.mark.asyncio
async def test_schedule_h1_no_room_double_booking(seed_data):
    """Verify H1 (room no-overlap): no two sessions in same room + day + time."""
    inst_id = seed_data
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post(
            "/schedule/generate",
            json={
                "institution_id": inst_id,
                "term_label": "fall-2024",
            },
        )

    data = resp.json()
    entries = data["entries"]

    # Group by (room, day, start_time)
    slots = {}
    for entry in entries:
        key = (entry["room_id"], entry["day_of_week"], entry["start_time"])
        if key in slots:
            pytest.fail(f"Room double-booking: {key} used by {slots[key]} and {entry['section_id']}")
        slots[key] = entry["section_id"]


@pytest.mark.asyncio
async def test_schedule_slots_per_week(seed_data):
    """Verify slots_per_week enforcement: cs-101-lec scheduled 2x/week."""
    inst_id = seed_data
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post(
            "/schedule/generate",
            json={
                "institution_id": inst_id,
                "term_label": "fall-2024",
            },
        )

    data = resp.json()
    entries = data["entries"]

    # Count cs-101-lec
    cs_lec_count = len([e for e in entries if e["section_id"] == "sec-cs101-lec"])
    assert cs_lec_count == 2, f"CS lecture should be scheduled 2x/week, got {cs_lec_count}"

    # Count cs-101-lab
    cs_lab_count = len([e for e in entries if e["section_id"] == "sec-cs101-lab"])
    assert cs_lab_count == 1, f"CS lab should be scheduled 1x/week, got {cs_lab_count}"


@pytest.mark.asyncio
async def test_institution_not_found():
    """Test error handling for missing institution."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post(
            "/schedule/generate",
            json={
                "institution_id": "nonexistent",
                "term_label": "fall-2024",
            },
        )

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_weights_override(seed_data):
    """Test request weights override DB weights."""
    inst_id = seed_data
    custom_weights = {
        "break_window": 200,
        "consecutive_slots": 150,
        "session_spread": 120,
        "campus_clustering": 80,
    }

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post(
            "/schedule/generate",
            json={
                "institution_id": inst_id,
                "term_label": "fall-2024",
                "weights": custom_weights,
            },
        )

    data = resp.json()

    # Verify custom weights were used
    for key, val in custom_weights.items():
        assert data["summary"]["weights"][key] == val
