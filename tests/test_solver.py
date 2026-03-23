"""Tests for solver service."""

from app.services.solver_service import ScheduleSolver


def _base_institution(**overrides):
    return {
        "daily_start_hour": 9,
        "daily_end_hour": 17,
        "slot_duration_minutes": 60,
        "working_days": [0, 1, 2, 3, 4],
        **overrides,
    }


def _make_section(
    sid,
    dept="d1",
    cap=30,
    slots=1,
    years=None,
    staff=None,
    section_type="lecture",
    slot_duration_minutes=None,
):
    return {
        "_id": sid,
        "institution_id": "inst1",
        "department_id": dept,
        "course_name": f"Course {sid}",
        "section_type": section_type,
        "capacity": cap,
        "slots_per_week": slots,
        "slot_duration_minutes": slot_duration_minutes,
        "year_levels": years or [1],
        "assigned_staff": staff or [],
        "shared_with": [],
    }


def _make_room(rid, cap=40, label=None):
    return {"_id": rid, "institution_id": "inst1", "name": rid, "capacity": cap, "label": label}


def _duration_minutes(entry):
    sh, sm = map(int, entry["start_time"].split(":"))
    eh, em = map(int, entry["end_time"].split(":"))
    return (eh * 60 + em) - (sh * 60 + sm)


def test_solver_initializes():
    solver = ScheduleSolver(time_limit_seconds=30, num_workers=4)
    assert solver.time_limit_seconds == 30
    assert solver.num_workers == 4


def test_num_slots_per_day():
    """9–17 h at 60 min/slot = 8 slots."""
    solver = ScheduleSolver()
    solver.build_model(
        institution_data=_base_institution(),
        courses_data=[_make_section("s1")],
        staff_data=[],
        availability_data=[],
        rooms_data=[_make_room("r1")],
        weights={},
    )
    assert solver.num_slots_per_day == 8


def test_single_section_schedules():
    """One section, one room → solver returns exactly one entry."""
    solver = ScheduleSolver(time_limit_seconds=10)
    solver.build_model(
        institution_data=_base_institution(),
        courses_data=[_make_section("s1", slots=1)],
        staff_data=[],
        availability_data=[],
        rooms_data=[_make_room("r1")],
        weights={},
    )
    violations, penalty, entries = solver.solve()
    assert violations == 0
    assert len(entries) == 1
    assert entries[0]["section_id"] == "s1"


def test_slots_per_week_respected():
    """Section with slots_per_week=3 must produce 3 entries."""
    solver = ScheduleSolver(time_limit_seconds=10)
    solver.build_model(
        institution_data=_base_institution(),
        courses_data=[_make_section("s1", slots=3)],
        staff_data=[],
        availability_data=[],
        rooms_data=[_make_room("r1")],
        weights={},
    )
    violations, _, entries = solver.solve()
    assert violations == 0
    assert len(entries) == 3


def test_no_room_double_booking():
    """Two sections, one room → must be scheduled at different times."""
    solver = ScheduleSolver(time_limit_seconds=10)
    solver.build_model(
        institution_data=_base_institution(),
        courses_data=[
            _make_section("s1", cap=20),
            _make_section("s2", cap=20),
        ],
        staff_data=[],
        availability_data=[],
        rooms_data=[_make_room("r1", cap=40)],
        weights={},
    )
    violations, _, entries = solver.solve()
    assert violations == 0
    assert len(entries) == 2
    # No two entries share the same room + day + start_time
    slots = [(e["room_id"], e["day_of_week"], e["start_time"]) for e in entries]
    assert len(slots) == len(set(slots))


def test_h5_staff_day_off_respected():
    """Staff with day_off=0 (Monday) must not be scheduled on Monday."""
    solver = ScheduleSolver(time_limit_seconds=10)
    solver.build_model(
        institution_data=_base_institution(),
        courses_data=[_make_section("s1", staff=["staff1"], slots=2)],
        staff_data=[{"_id": "staff1", "institution_id": "inst1"}],
        availability_data=[{"staff_id": "staff1", "weekly_day_off": 0}],
        rooms_data=[_make_room("r1")],
        weights={},
    )
    violations, _, entries = solver.solve()
    assert violations == 0
    for e in entries:
        assert e["day_of_week"] != 0, "Session scheduled on staff's day off"


def test_h8_year_level_no_overlap():
    """Two same-dept same-year sections must not overlap in time."""
    solver = ScheduleSolver(time_limit_seconds=10)
    solver.build_model(
        institution_data=_base_institution(),
        courses_data=[
            _make_section("s1", dept="d1", years=[1]),
            _make_section("s2", dept="d1", years=[1]),
        ],
        staff_data=[],
        availability_data=[],
        rooms_data=[_make_room("r1"), _make_room("r2")],
        weights={},
    )
    violations, _, entries = solver.solve()
    assert violations == 0
    assert len(entries) == 2
    # They may be in different rooms but must not be at the same (day, start_time)
    times = [(e["day_of_week"], e["start_time"]) for e in entries]
    assert times[0] != times[1], "Year-level conflict: two sessions scheduled at same time"


def test_skipped_sections_tracked():
    """Section with no compatible room is skipped and tracked."""
    solver = ScheduleSolver(time_limit_seconds=10)
    solver.build_model(
        institution_data=_base_institution(),
        courses_data=[_make_section("s1", cap=100)],  # needs 100-seat room
        staff_data=[],
        availability_data=[],
        rooms_data=[_make_room("r1", cap=30)],        # only 30 seats
        weights={},
    )
    assert "s1" in solver._skipped


def test_section_type_duration_applies_when_section_duration_missing():
    """Lecture/tutorial durations can be configured globally by section type."""
    solver = ScheduleSolver(time_limit_seconds=10)
    solver.build_model(
        institution_data=_base_institution(slot_duration_minutes=30),
        courses_data=[
            _make_section("lec1", section_type="lecture", slots=1, slot_duration_minutes=None),
            _make_section("tut1", section_type="tutorial", slots=1, slot_duration_minutes=None),
        ],
        staff_data=[],
        availability_data=[],
        rooms_data=[_make_room("r1"), _make_room("r2")],
        weights={},
        section_type_durations={"lecture": 120, "tutorial": 60},
    )
    violations, _, entries = solver.solve()
    assert violations == 0

    by_section = {e["section_id"]: e for e in entries}
    assert _duration_minutes(by_section["lec1"]) == 120
    assert _duration_minutes(by_section["tut1"]) == 60


def test_section_duration_overrides_section_type_duration():
    """Explicit section duration takes priority over section-type duration."""
    solver = ScheduleSolver(time_limit_seconds=10)
    solver.build_model(
        institution_data=_base_institution(slot_duration_minutes=30),
        courses_data=[
            _make_section("lec1", section_type="lecture", slots=1, slot_duration_minutes=90),
        ],
        staff_data=[],
        availability_data=[],
        rooms_data=[_make_room("r1")],
        weights={},
        section_type_durations={"lecture": 120},
    )
    violations, _, entries = solver.solve()
    assert violations == 0
    assert len(entries) == 1
    assert _duration_minutes(entries[0]) == 90
