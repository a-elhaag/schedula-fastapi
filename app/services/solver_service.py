"""Solver service — OR-Tools CP-SAT constraint model."""

from __future__ import annotations

from ortools.sat.python import cp_model
from typing import Any


class ScheduleSolver:
    def __init__(self, time_limit_seconds: int = 55, num_workers: int = 8):
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers
        self._has_objective = False

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
    ) -> None:
        self.model = cp_model.CpModel()
        self.courses = courses_data
        self.staff_members = staff_data
        self.rooms = rooms_data
        self.weights = weights
        self.availability_map: dict[str, dict] = {
            a["staff_id"]: a for a in availability_data
        }

        # Time grid (all durations measured in "slot units")
        start_h: int = institution_data.get("daily_start_hour", 9)
        end_h: int = institution_data.get("daily_end_hour", 17)
        inst_min: int = institution_data.get("slot_duration_minutes", 60)
        self.num_slots_per_day: int = (end_h - start_h) * 60 // inst_min
        self.working_days: list[int] = institution_data.get("working_days", [0, 1, 2, 3, 4])
        self.num_days: int = len(self.working_days)
        self.inst_min: int = inst_min
        self.start_hour: int = start_h
        self.section_type_durations: dict[str, int] = section_type_durations or {}

        # Pre-compute indexes (H3, H4 pre-filtering done here)
        self._build_room_index()
        self._build_staff_index()
        self._skipped: set[str] = set()

        # Create session variables
        self._create_sessions()

        # Hard constraints
        self._add_h1_h2_no_overlap()
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
        total = self.num_days * self.num_slots_per_day

        for section in self.courses:
            sid = section["_id"]
            room_ids = self.section_rooms.get(sid, [])
            if not room_ids:
                self._skipped.add(sid)
                continue

            k = section.get("slots_per_week", 1)
            sec_min = section.get("slot_duration_minutes")
            if sec_min is None:
                sec_min = self.section_type_durations.get(section.get("section_type", ""), self.inst_min)
            dur = max(1, (sec_min + self.inst_min - 1) // self.inst_min)   # duration in slot units

            for occ in range(k):
                tag = f"{sid}_{occ}"

                day_v = self.model.NewIntVar(0, self.num_days - 1, f"d_{tag}")
                slot_v = self.model.NewIntVar(0, self.num_slots_per_day - dur, f"sl_{tag}")

                abs_s = self.model.NewIntVar(0, total - dur, f"as_{tag}")
                abs_e = self.model.NewIntVar(dur, total, f"ae_{tag}")
                self.model.Add(abs_s == day_v * self.num_slots_per_day + slot_v)
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

    def _add_h5_staff_day_off(self) -> None:
        """H5: staff weekly day-off is fully blocked."""
        for staff_id, avail in self.availability_map.items():
            day_off = avail.get("weekly_day_off")
            if day_off is None or day_off not in self.working_days:
                continue
            day_off_idx = self.working_days.index(day_off)
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
        """
        # Build dept_id → sections (including shared_with registration for H9)
        dept_map: dict[str, list[dict]] = {}
        for s in self.courses:
            dept_map.setdefault(s["department_id"], []).append(s)
            for d in s.get("shared_with", []):
                dept_map.setdefault(d, []).append(s)

        for sections in dept_map.values():
            n = len(sections)
            for i in range(n):
                for j in range(i + 1, n):
                    s1, s2 = sections[i], sections[j]
                    if not set(s1.get("year_levels", [])) & set(s2.get("year_levels", [])):
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
                if dow not in self.working_days:
                    continue
                day_idx = self.working_days.index(dow)
                bk_s = self._time_to_slot(win.get("start_time") if isinstance(win, dict) else win.start_time)
                bk_e = self._time_to_slot(win.get("end_time") if isinstance(win, dict) else win.end_time)
                if bk_s >= bk_e or bk_s < 0 or bk_e > self.num_slots_per_day:
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
            staff_sess: list[dict] = []
            for sec_id in sec_ids:
                sec = self._section(sec_id)
                if not sec:
                    continue
                for occ in range(sec.get("slots_per_week", 1)):
                    s = self.sessions.get((sec_id, occ))
                    if s:
                        staff_sess.append(s)

            for i, sa in enumerate(staff_sess):
                for sb in staff_sess[i + 1:]:
                    tag = f"{staff_id}_{i}"
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
        terms: list = []

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
            for day_idx in range(self.num_days):
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

    def solve(self) -> tuple[int, float, list[dict[str, Any]]]:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.num_search_workers = self.num_workers
        solver.parameters.log_search_progress = False

        status = solver.Solve(self.model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return 1, float("inf"), []

        entries: list[dict] = []
        for (sid, _occ), sess in self.sessions.items():
            day_idx = solver.Value(sess["day"])
            slot_idx = solver.Value(sess["slot"])
            r_idx = solver.Value(sess["room_v"])
            room_id = sess["room_ids"][r_idx]

            day_of_week = self.working_days[day_idx]
            start_min = self.start_hour * 60 + slot_idx * self.inst_min
            end_min = start_min + sess["dur"] * self.inst_min

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
        return 0, soft_penalty, entries

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _section(self, section_id: str) -> dict | None:
        return next((s for s in self.courses if s["_id"] == section_id), None)

    def _collect_intervals(self, sec_ids: list[str]) -> list:
        """Collect all session IntervalVars for the given section IDs."""
        ivs = []
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
        return (h * 60 + m - self.start_hour * 60) // self.inst_min
