"""Solver service — OR-Tools CP-SAT constraint model."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ortools.sat.python import cp_model

from app.services.constraint_validator import ConstraintValidator

logger = logging.getLogger(__name__)


@dataclass
class TimeGrid:
    """Time grid configuration for solver."""
    num_slots_per_day: int
    num_days: int
    working_days: list[int]
    start_hour: int
    inst_min: int  # slot duration in minutes


class ScheduleSolver:
    def __init__(self, time_limit_seconds: int = 55, num_workers: int = 8):
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers
        self._has_objective = False
        self._section_index: dict[str, dict] = {}
        self.validation_errors: list[str] = []
        self.validation_warnings: dict[str, list[str]] = {}

    # ──────────────────────────────────────────────────────────────────────
    # Entry point
    # ──────────────────────────────────────────────────────────────────────

    def build_model(
        self,
        institution_data: dict[str, Any],
        courses_data: list[dict],
        staff_data: list[dict],
        availability_data: list[dict],
        rooms_data: list[dict],
        weights: dict[str, int],
        section_type_durations: dict[str, int] | None = None,
        enrollments_data: dict[str, dict[str, Any]] | None = None,
        room_feature_requirements: dict[str, list[str]] | None = None,
    ) -> tuple[bool, list[str], dict[str, list[str]]]:
        """
        Build the constraint model and run validations.
        
        Returns:
            is_feasible: bool - Whether model is buildable
            critical_errors: list[str] - Hard constraint violations
            warnings: dict[str, list[str]] - Non-critical issues
        """
        # Run pre-solve validations
        is_feasible, critical_errors, warnings = ConstraintValidator.run_all_validations(
            courses=courses_data,
            staff_data=staff_data,
            rooms=rooms_data,
            enrollments=enrollments_data,
            room_feature_requirements=room_feature_requirements,
        )
        
        if critical_errors:
            logger.error(f"Hard constraint violations detected:\n" + "\n".join(critical_errors))
            self.validation_errors = critical_errors
            return False, critical_errors, warnings
        
        if warnings:
            for constraint, msgs in warnings.items():
                logger.warning(f"{constraint} warnings:\n" + "\n".join(msgs))
        
        self.validation_errors = []
        self.validation_warnings = warnings
        
        self.model = cp_model.CpModel()
        self.courses = courses_data
        self.staff_members = staff_data
        self.rooms = rooms_data
        self.weights = weights
        self.enrollments = enrollments_data or {}
        self.availability_map: dict[str, dict] = {
            a["staff_id"]: a for a in availability_data
        }

        # Build section index for O(1) lookup
        self._section_index = {s["_id"]: s for s in courses_data}

        # Time grid (all durations measured in "slot units")
        start_h: int = institution_data.get("daily_start_hour", 9)
        end_h: int = institution_data.get("daily_end_hour", 17)
        inst_min: int = institution_data.get("slot_duration_minutes", 60)
        num_slots_per_day: int = (end_h - start_h) * 60 // inst_min
        working_days: list[int] = institution_data.get("working_days", [0, 1, 2, 3, 4])

        self.time_grid = TimeGrid(
            num_slots_per_day=num_slots_per_day,
            num_days=len(working_days),
            working_days=working_days,
            start_hour=start_h,
            inst_min=inst_min,
        )
        self.section_type_durations: dict[str, int] = section_type_durations or {}

        # Pre-compute indexes (H3, H4 pre-filtering done here)
        self._build_room_index()
        self._build_staff_index()
        self._skipped: set[str] = set()

        # Pre-compute indexes and create session variables
        self._create_sessions()
        logger.debug(f"Built model with {len(self.sessions)} sessions, {len(self._skipped)} skipped")

        # Hard constraints
        self._add_h1_h2_no_overlap()
        self._add_h3_room_capacity()  # NEW: Hard constraint enforcement
        self._add_h4_required_room_labels()  # NEW: Hard constraint enforcement
        self._add_h5_staff_day_off()
        self._add_h8_year_level_conflicts()

        # Soft constraints → collect weighted penalty terms
        penalty: list = []
        penalty += self._soft_s1_break_window()
        penalty += self._soft_s2_consecutive_slots()
        penalty += self._soft_s3_session_spread()
        penalty += self._soft_s4_campus_clustering()

        if penalty:
            self.model.Minimize(sum(penalty))
            self._has_objective = True
        
        return True, [], warnings

    # ──────────────────────────────────────────────────────────────────────
    # Pre-computation
    # ──────────────────────────────────────────────────────────────────────

    def _build_room_index(self) -> None:
        """H3 + H4: pre-filter compatible rooms per section."""
        self.section_rooms: dict[str, list[str]] = {}
        for s in self.courses:
            cap = s["capacity"]
            req = s.get("required_room_label")
            self.section_rooms[s["_id"]] = [
                r["_id"] for r in self.rooms
                if r["capacity"] >= cap and (not req or r.get("label") == req)
            ]

    def _build_staff_index(self) -> None:
        """staff_id → [section_id, ...]"""
        self.staff_sections: dict[str, list[str]] = {}
        for s in self.courses:
            for sid in s.get("assigned_staff", []):
                self.staff_sections.setdefault(sid, []).append(s["_id"])

    # ──────────────────────────────────────────────────────────────────────
    # Variables
    # ──────────────────────────────────────────────────────────────────────

    def _create_sessions(self) -> None:
        """
        For each section with slots_per_week=k, create k session occurrences.

        Time encoding:
            abs_time = day_index * num_slots_per_day + slot_index

        Collapsing the week to a single integer timeline lets a single
        IntervalVar per session drive all NoOverlap constraints.

        For room NoOverlap (H1) we create one optional IntervalVar per
        (session, possible_room) pair, active only when that room is chosen.
        """
        self.sessions: dict[tuple[str, int], dict] = {}
        # room_id → list of optional intervals (for H1 AddNoOverlap)
        self.room_opt_ivs: dict[str, list] = {}
        total = self.time_grid.num_days * self.time_grid.num_slots_per_day

        for section in self.courses:
            sid = section["_id"]
            room_ids = self.section_rooms.get(sid, [])
            if not room_ids:
                self._skipped.add(sid)
                continue

            k = section.get("slots_per_week", 1)
            sec_min = section.get("slot_duration_minutes")
            if sec_min is None:
                sec_min = self.section_type_durations.get(section.get("section_type", ""), self.time_grid.inst_min)
            dur = max(1, (sec_min + self.time_grid.inst_min - 1) // self.time_grid.inst_min)   # duration in slot units

            for occ in range(k):
                tag = f"{sid}_{occ}"

                day_v = self.model.NewIntVar(0, self.time_grid.num_days - 1, f"d_{tag}")
                slot_v = self.model.NewIntVar(0, self.time_grid.num_slots_per_day - dur, f"sl_{tag}")

                abs_s = self.model.NewIntVar(0, total - dur, f"as_{tag}")
                abs_e = self.model.NewIntVar(dur, total, f"ae_{tag}")
                self.model.Add(abs_s == day_v * self.time_grid.num_slots_per_day + slot_v)
                self.model.Add(abs_e == abs_s + dur)

                iv = self.model.NewIntervalVar(abs_s, dur, abs_e, f"iv_{tag}")
                room_v = self.model.NewIntVar(0, len(room_ids) - 1, f"rv_{tag}")

                # Optional interval per compatible room for H1
                for r_idx, r_id in enumerate(room_ids):
                    is_here = self.model.NewBoolVar(f"rh_{tag}_{r_idx}")
                    self.model.Add(room_v == r_idx).OnlyEnforceIf(is_here)
                    self.model.Add(room_v != r_idx).OnlyEnforceIf(is_here.Not())
                    opt_iv = self.model.NewOptionalIntervalVar(
                        abs_s, dur, abs_e, is_here, f"oiv_{tag}_{r_idx}"
                    )
                    self.room_opt_ivs.setdefault(r_id, []).append(opt_iv)

                self.sessions[(sid, occ)] = {
                    "day": day_v,
                    "slot": slot_v,
                    "abs_s": abs_s,
                    "abs_e": abs_e,
                    "iv": iv,
                    "room_v": room_v,
                    "room_ids": room_ids,
                    "dur": dur,
                }

    # ──────────────────────────────────────────────────────────────────────
    # Hard constraints
    # ──────────────────────────────────────────────────────────────────────

    def _add_h1_h2_no_overlap(self) -> None:
        """
        H1: no room double-booking — AddNoOverlap per room over optional intervals.
        H2: no staff double-booking — AddNoOverlap per staff over their sessions.
        """
        for ivs in self.room_opt_ivs.values():
            if len(ivs) > 1:
                self.model.AddNoOverlap(ivs)

        for staff_id, sec_ids in self.staff_sections.items():
            ivs = self._collect_intervals(sec_ids)
            if len(ivs) > 1:
                self.model.AddNoOverlap(ivs)

    def _add_h3_room_capacity(self) -> None:
        """
        H3: Room Capacity Constraint (Hard)
        Enforce: assigned_room.capacity >= section.enrollment
        
        Uses enrollment data if available, else uses section.capacity field.
        This is a hard constraint — if infeasible, solver returns INFEASIBLE.
        """
        for section in self.courses:
            sid = section["_id"]
            room_ids = self.section_rooms.get(sid, [])
            
            if not room_ids:
                # Pre-filtering already skipped this section
                continue
            
            # Get required capacity: prefer actual enrollment, fall back to section capacity
            required_capacity = section["capacity"]
            if sid in self.enrollments:
                required_capacity = self.enrollments[sid].get("enrolled_students", section["capacity"])
            
            # For each possible room, check capacity
            room_capacities = {}
            for room_id in room_ids:
                room = next((r for r in self.rooms if r["_id"] == room_id), None)
                if room:
                    room_capacities[room_id] = room.get("capacity", 0)
            
            # Ensure all candidate rooms meet capacity requirement
            # If any room has capacity < required, remove it from candidates
            valid_rooms = [
                r_id for r_id in room_ids
                if room_capacities.get(r_id, 0) >= required_capacity
            ]
            
            if not valid_rooms:
                # Pre-filtering should have caught this, but log for auditing
                logger.warning(
                    f"H3 violation: Section {section.get('course_name', sid)} "
                    f"requires capacity {required_capacity}, but pre-filtering found no valid rooms. "
                    f"This should have been caught during validation."
                )
                continue
            
            # Add hard constraint: for each session of this section,
            # the assigned room must have sufficient capacity
            for k in range(section.get("slots_per_week", 1)):
                session = self.sessions.get((sid, k))
                if not session:
                    continue
                
                # room_v must index a room with sufficient capacity
                room_v = session["room_v"]
                valid_room_indices = [
                    i for i, r_id in enumerate(session["room_ids"])
                    if r_id in valid_rooms
                ]
                
                if valid_room_indices:
                    # Add constraint: room_v must be one of the valid indices
                    self.model.AddAllowedAssignments([room_v], [(i,) for i in valid_room_indices])

    def _add_h4_required_room_labels(self) -> None:
        """
        H4: Required Room Labels Constraint (Hard)
        Enforce: if section.required_room_label exists, assigned_room.label must match it.
        
        This is a hard constraint — if infeasible, solver returns INFEASIBLE.
        """
        for section in self.courses:
            sid = section["_id"]
            req_label = section.get("required_room_label")
            
            if not req_label:
                # No label requirement for this section
                continue
            
            room_ids = self.section_rooms.get(sid, [])
            if not room_ids:
                continue
            
            # Find rooms with matching label
            labeled_rooms = [
                r_id for r_id in room_ids
                if any(r["_id"] == r_id and r.get("label") == req_label for r in self.rooms)
            ]
            
            if not labeled_rooms:
                logger.warning(
                    f"H4 violation: Section {section.get('course_name', sid)} "
                    f"requires label '{req_label}', but pre-filtering found no matching rooms. "
                    f"This should have been caught during validation."
                )
                continue
            
            # Add hard constraint for each session
            for k in range(section.get("slots_per_week", 1)):
                session = self.sessions.get((sid, k))
                if not session:
                    continue
                
                room_v = session["room_v"]
                labeled_room_indices = [
                    i for i, r_id in enumerate(session["room_ids"])
                    if r_id in labeled_rooms
                ]
                
                if labeled_room_indices:
                    self.model.AddAllowedAssignments([room_v], [(i,) for i in labeled_room_indices])

    def _add_h5_staff_day_off(self) -> None:
        """H5: staff weekly day-off is fully blocked."""
        for staff_id, avail in self.availability_map.items():
            day_off = avail.get("weekly_day_off")
            if day_off is None or day_off not in self.time_grid.working_days:
                continue
            day_off_idx = self.time_grid.working_days.index(day_off)
            for sec_id in self.staff_sections.get(staff_id, []):
                sec = self._section(sec_id)
                if not sec:
                    continue
                for occ in range(sec.get("slots_per_week", 1)):
                    sess = self.sessions.get((sec_id, occ))
                    if sess:
                        self.model.Add(sess["day"] != day_off_idx)

    def _add_h8_year_level_conflicts(self) -> None:
        """
        H8: sections in same dept with overlapping year levels can't share a time slot.
        H9 propagation: shared lectures also conflict with year-level peers in shared_with depts.

        Optimization: pre-compute year_level sets once; skip pair if same section ID
        (can happen when a course is in shared_with of another in same dept).
        """
        # Build dept_id → sections (including shared_with registration for H9)
        dept_map: dict[str, list[dict]] = {}
        for s in self.courses:
            dept_map.setdefault(s["department_id"], []).append(s)
            for d in s.get("shared_with", []):
                dept_map.setdefault(d, []).append(s)

        for sections in dept_map.values():
            # Pre-compute year_level frozensets for O(1) intersection check
            year_sets = [frozenset(s.get("year_levels", [])) for s in sections]
            n = len(sections)
            for i in range(n):
                if not year_sets[i]:
                    continue
                for j in range(i + 1, n):
                    s1, s2 = sections[i], sections[j]
                    # Skip duplicate entries (same section in multiple depts via shared_with)
                    if s1["_id"] == s2["_id"]:
                        continue
                    if not year_sets[i] & year_sets[j]:
                        continue
                    ivs = self._collect_intervals([s1["_id"], s2["_id"]])
                    if len(ivs) > 1:
                        self.model.AddNoOverlap(ivs)

    # ──────────────────────────────────────────────────────────────────────
    # Soft constraints
    # ──────────────────────────────────────────────────────────────────────

    def _soft_s1_break_window(self) -> list:
        """S1 (w=100): penalize sessions during staff preferred break windows."""
        w = self.weights.get("break_window", 100)
        terms: list = []

        for staff_id, avail in self.availability_map.items():
            for win in avail.get("preferred_break_windows", []):
                dow = win.get("day_of_week") if isinstance(win, dict) else win.day_of_week
                if dow not in self.time_grid.working_days:
                    continue
                day_idx = self.time_grid.working_days.index(dow)
                bk_s = self._time_to_slot(win.get("start_time") if isinstance(win, dict) else win.start_time)
                bk_e = self._time_to_slot(win.get("end_time") if isinstance(win, dict) else win.end_time)
                if bk_s >= bk_e or bk_s < 0 or bk_e > self.time_grid.num_slots_per_day:
                    continue

                for sec_id in self.staff_sections.get(staff_id, []):
                    sec = self._section(sec_id)
                    if not sec:
                        continue
                    for occ in range(sec.get("slots_per_week", 1)):
                        sess = self.sessions.get((sec_id, occ))
                        if not sess:
                            continue
                        tag = f"{staff_id}_{sec_id}_{occ}"

                        on_day = self.model.NewBoolVar(f"s1_od_{tag}")
                        self.model.Add(sess["day"] == day_idx).OnlyEnforceIf(on_day)
                        self.model.Add(sess["day"] != day_idx).OnlyEnforceIf(on_day.Not())

                        before_end = self.model.NewBoolVar(f"s1_be_{tag}")
                        self.model.Add(sess["slot"] < bk_e).OnlyEnforceIf(before_end)
                        self.model.Add(sess["slot"] >= bk_e).OnlyEnforceIf(before_end.Not())

                        after_start = self.model.NewBoolVar(f"s1_as_{tag}")
                        self.model.Add(sess["slot"] + sess["dur"] > bk_s).OnlyEnforceIf(after_start)
                        self.model.Add(sess["slot"] + sess["dur"] <= bk_s).OnlyEnforceIf(after_start.Not())

                        overlap = self.model.NewBoolVar(f"s1_ov_{tag}")
                        self.model.AddBoolAnd([on_day, before_end, after_start]).OnlyEnforceIf(overlap)
                        self.model.AddBoolOr([on_day.Not(), before_end.Not(), after_start.Not()]).OnlyEnforceIf(overlap.Not())
                        terms.append(overlap * w)
        return terms

    def _soft_s2_consecutive_slots(self) -> list:
        """S2 (w=80): penalize each pair of back-to-back sessions for a staff member."""
        w = self.weights.get("consecutive_slots", 80)
        terms: list = []

        for staff_id, sec_ids in self.staff_sections.items():
            staff_sess: list[tuple[str, int, dict]] = []
            for sec_id in sec_ids:
                sec = self._section(sec_id)
                if not sec:
                    continue
                for occ in range(sec.get("slots_per_week", 1)):
                    s = self.sessions.get((sec_id, occ))
                    if s:
                        staff_sess.append((sec_id, occ, s))

            for i, (sec_a, occ_a, sa) in enumerate(staff_sess):
                for j, (sec_b, occ_b, sb) in enumerate(staff_sess[i + 1:], start=i + 1):
                    tag = f"{staff_id}_{sec_a}_{occ_a}_{sec_b}_{occ_b}"
                    # a immediately before b
                    ab = self.model.NewBoolVar(f"s2_ab_{tag}")
                    self.model.Add(sa["abs_e"] == sb["abs_s"]).OnlyEnforceIf(ab)
                    self.model.Add(sa["abs_e"] != sb["abs_s"]).OnlyEnforceIf(ab.Not())
                    # b immediately before a
                    ba = self.model.NewBoolVar(f"s2_ba_{tag}")
                    self.model.Add(sb["abs_e"] == sa["abs_s"]).OnlyEnforceIf(ba)
                    self.model.Add(sb["abs_e"] != sa["abs_s"]).OnlyEnforceIf(ba.Not())

                    adj = self.model.NewBoolVar(f"s2_adj_{tag}")
                    self.model.AddBoolOr([ab, ba]).OnlyEnforceIf(adj)
                    self.model.AddBoolAnd([ab.Not(), ba.Not()]).OnlyEnforceIf(adj.Not())
                    terms.append(adj * w)
        return terms

    def _soft_s3_session_spread(self) -> list:
        """S3 (w=60): penalize slots_per_week > 1 sections scheduled on the same day."""
        w = self.weights.get("session_spread", 60)
        terms: list[Any] = []

        for section in self.courses:
            sid = section["_id"]
            k = section.get("slots_per_week", 1)
            if k < 2:
                continue
            for i in range(k):
                for j in range(i + 1, k):
                    sa = self.sessions.get((sid, i))
                    sb = self.sessions.get((sid, j))
                    if not sa or not sb:
                        continue
                    same = self.model.NewBoolVar(f"s3_{sid}_{i}_{j}")
                    self.model.Add(sa["day"] == sb["day"]).OnlyEnforceIf(same)
                    self.model.Add(sa["day"] != sb["day"]).OnlyEnforceIf(same.Not())
                    terms.append(same * w)
        return terms

    def _soft_s4_campus_clustering(self) -> list:
        """S4 (w=40): penalize each day a staff member has any session (minimize campus days)."""
        w = self.weights.get("campus_clustering", 40)
        terms: list = []

        for staff_id, sec_ids in self.staff_sections.items():
            for day_idx in range(self.time_grid.num_days):
                day_flags: list = []
                for sec_id in sec_ids:
                    sec = self._section(sec_id)
                    if not sec:
                        continue
                    for occ in range(sec.get("slots_per_week", 1)):
                        sess = self.sessions.get((sec_id, occ))
                        if not sess:
                            continue
                        flag = self.model.NewBoolVar(f"s4_f_{staff_id}_{sec_id}_{occ}_{day_idx}")
                        self.model.Add(sess["day"] == day_idx).OnlyEnforceIf(flag)
                        self.model.Add(sess["day"] != day_idx).OnlyEnforceIf(flag.Not())
                        day_flags.append(flag)

                if not day_flags:
                    continue

                has_day = self.model.NewBoolVar(f"s4_hd_{staff_id}_{day_idx}")
                # has_day = 1 iff any flag = 1
                for f in day_flags:
                    self.model.AddImplication(f, has_day)      # flag=1 → has_day=1
                self.model.AddBoolOr(day_flags + [has_day.Not()])  # has_day=0 → all flags=0
                terms.append(has_day * w)
        return terms

    # ──────────────────────────────────────────────────────────────────────
    # Solve
    # ──────────────────────────────────────────────────────────────────────

    def solve(self) -> tuple[int, float, list[dict[str, Any]], list[str]]:
        """
        Solve the constraint model and return schedule.
        
        Returns:
            error_code: int (0=success, 1=hard constraint violation, 2=solver timeout/infeasible)
            soft_penalty: float
            entries: list[dict]
            validation_errors: list[str]
        """
        # If validation failed, return immediately
        if self.validation_errors:
            logger.error(f"Cannot solve due to validation errors")
            return 1, float("inf"), [], self.validation_errors
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.num_search_workers = self.num_workers
        solver.parameters.log_search_progress = False
        # Stop as soon as a good-enough solution is found (reduces wall-clock time)
        solver.parameters.stop_after_first_solution = not self._has_objective

        status = solver.Solve(self.model)

        if status == cp_model.INFEASIBLE:
            logger.warning("Solver found problem INFEASIBLE (hard constraints cannot be satisfied)")
            errors = ["Solver could not find a feasible solution. Check that all hard constraints can be satisfied."]
            return 2, float("inf"), [], errors
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.warning(f"Solver status: {status} (not OPTIMAL/FEASIBLE)")
            errors = [f"Solver returned status {status} (not OPTIMAL/FEASIBLE)"]
            return 2, float("inf"), [], errors

        entries: list[dict[str, Any]] = []
        for (sid, _occ), sess in self.sessions.items():
            day_idx = solver.Value(sess["day"])
            slot_idx = solver.Value(sess["slot"])
            r_idx = solver.Value(sess["room_v"])
            room_id = sess["room_ids"][r_idx]

            day_of_week = self.time_grid.working_days[day_idx]
            start_min = self.time_grid.start_hour * 60 + slot_idx * self.time_grid.inst_min
            end_min = start_min + sess["dur"] * self.time_grid.inst_min

            sec = self._section(sid)
            entries.append({
                "section_id": sid,
                "course_name": sec.get("course_name", "") if sec else "",
                "section_type": sec.get("section_type", "") if sec else "",
                "day_of_week": day_of_week,
                "start_time": f"{start_min // 60:02d}:{start_min % 60:02d}",
                "end_time": f"{end_min // 60:02d}:{end_min % 60:02d}",
                "room_id": room_id,
                "assigned_staff": sec.get("assigned_staff", []) if sec else [],
            })

        soft_penalty = solver.ObjectiveValue() if self._has_objective else 0.0
        return 0, soft_penalty, entries, []

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _section(self, section_id: str) -> dict | None:
        """Get section by ID using cached index."""
        return self._section_index.get(section_id)

    def _collect_intervals(self, sec_ids: list[str]) -> list:
        """Collect all session IntervalVars for the given section IDs."""
        ivs: list = []
        for sec_id in sec_ids:
            sec = self._section(sec_id)
            if not sec:
                continue
            for occ in range(sec.get("slots_per_week", 1)):
                sess = self.sessions.get((sec_id, occ))
                if sess:
                    ivs.append(sess["iv"])
        return ivs

    def _time_to_slot(self, t: Any) -> int:
        """Convert a time value (HH:MM string or time object) to a slot index."""
        if isinstance(t, str):
            h, m = map(int, t.split(":"))
        else:
            h, m = t.hour, t.minute
        return (h * 60 + m - self.time_grid.start_hour * 60) // self.time_grid.inst_min
