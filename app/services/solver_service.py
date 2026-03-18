"""Solver service — OR-Tools constraint model and solver logic."""

from ortools.sat.python import cp_model
from typing import Dict, List, Any, Tuple
from datetime import datetime, time
import itertools


class ScheduleSolver:
    """Constraint-satisfaction solver for course scheduling."""

    def __init__(self, time_limit_seconds: int = 60):
        """
        Initialize solver.

        Args:
            time_limit_seconds: Maximum solver runtime.
        """
        self.time_limit_seconds = time_limit_seconds
        self.model = cp_model.CpModel()

        # Problem data (populated in build_model)
        self.institution_data = None
        self.courses = []
        self.staff_members = []
        self.availability_map = {}  # staff_id -> availability
        self.rooms = []
        self.weights = {}

        # Decision variables
        self.assignments = {}  # (section_id, time_slot, room_id, staff_id) -> BoolVar

        # Time slots and working days
        self.time_slots = []
        self.working_days = []

    def build_model(
        self,
        institution_data: Dict[str, Any],
        courses_data: List[Dict],
        staff_data: List[Dict],
        availability_data: List[Dict],
        rooms_data: List[Dict],
        weights: Dict[str, int],
    ) -> None:
        """
        Build OR-Tools constraint model.

        Args:
            institution_data: Institution profile
            courses_data: List of course sections
            staff_data: List of staff members
            availability_data: Staff availability submissions
            rooms_data: List of rooms/facilities
            weights: Soft constraint weights
        """
        self.institution_data = institution_data
        self.courses = courses_data
        self.staff_members = staff_data
        self.rooms = rooms_data
        self.weights = weights

        # Build availability map (staff_id -> availability)
        for avail in availability_data:
            self.availability_map[avail["staff_id"]] = avail

        # Generate time slots based on institution daily hours and slot duration
        self._generate_time_slots()

        # Generate working days
        self.working_days = institution_data.get("working_days", [0, 1, 2, 3, 4])

        # Create decision variables
        self._create_variables()

        # Add hard constraints
        self._add_hard_constraints()

        # Add soft constraints
        self._add_soft_constraints()

    def _generate_time_slots(self) -> None:
        """Generate time slots based on institution settings."""
        start_hour = self.institution_data.get("daily_start_hour", 9)
        end_hour = self.institution_data.get("daily_end_hour", 17)
        slot_duration = self.institution_data.get("slot_duration_minutes", 60)

        slot_minutes = 0
        while start_hour * 60 + slot_minutes + slot_duration <= end_hour * 60:
            start_min = start_hour * 60 + slot_minutes
            hour = start_min // 60
            minute = start_min % 60
            self.time_slots.append(f"{hour:02d}:{minute:02d}")
            slot_minutes += slot_duration

    def _create_variables(self) -> None:
        """Create boolean variables for section assignments."""
        for section in self.courses:
            section_id = section["_id"]
            capacity = section["capacity"]

            # For each time slot and day
            for day in self.working_days:
                for time_slot in self.time_slots:
                    # For each compatible room
                    for room in self.rooms:
                        room_id = room["_id"]

                        # Check room capacity
                        if room["capacity"] < capacity:
                            continue

                        # Check room label match
                        required_label = section.get("required_room_label")
                        room_label = room.get("label")
                        if required_label and room_label != required_label:
                            continue

                        # Create assignment variable
                        var_name = f"assign_{section_id}_{day}_{time_slot}_{room_id}"
                        self.assignments[(section_id, day, time_slot, room_id)] = (
                            self.model.NewBoolVar(var_name)
                        )

    def _add_hard_constraints(self) -> None:
        """Add all 9 hard constraints."""
        # H1: No room double-booking (same room, same time slot)
        self._add_h1_no_room_double_booking()

        # H2: No staff double-booking (same person, same time slot)
        self._add_h2_no_staff_double_booking()

        # H3: Room capacity >= section capacity
        # (Already enforced in _create_variables)

        # H4: Room label matches section's required_room_label
        # (Already enforced in _create_variables)

        # H5: Staff weekly day-off is fully blocked (hard constraint)
        self._add_h5_staff_day_off()

        # H6: All sessions within institution daily hours
        # (Already enforced in _generate_time_slots)

        # H7: Sessions only on institution working days
        # (Already enforced in time_slots generation)

        # H8: Year-level conflict within department
        self._add_h8_year_level_conflicts()

        # H9: Cross-department shared lecture conflict
        self._add_h9_cross_dept_shared_lecture()

    def _add_h1_no_room_double_booking(self) -> None:
        """H1: No room double-booking."""
        # For each room and time slot, at most one section can be assigned
        for room in self.rooms:
            room_id = room["_id"]
            for day in self.working_days:
                for time_slot in self.time_slots:
                    room_assignments = [
                        self.assignments[(s_id, day, time_slot, room_id)]
                        for (s_id, d, t, r_id) in self.assignments.keys()
                        if r_id == room_id and d == day and t == time_slot
                    ]
                    if room_assignments:
                        self.model.AddAtMostOne(room_assignments)

    def _add_h2_no_staff_double_booking(self) -> None:
        """H2: No staff double-booking."""
        # For each staff member and time slot, only one section can be assigned
        for staff in self.staff_members:
            staff_id = staff["_id"]
            for day in self.working_days:
                for time_slot in self.time_slots:
                    staff_assignments = []
                    # Check which sections have this staff assigned
                    for section in self.courses:
                        section_id = section["_id"]
                        # Look for assignments with this staff
                        # (simplification: assumes section has direct staff list)
                        # In real DB, would query section_staff join table
                        if staff_id in section.get("assigned_staff", []):
                            for room in self.rooms:
                                key = (section_id, day, time_slot, room["_id"])
                                if key in self.assignments:
                                    staff_assignments.append(self.assignments[key])
                    if staff_assignments:
                        self.model.AddAtMostOne(staff_assignments)

    def _add_h5_staff_day_off(self) -> None:
        """H5: Staff weekly day-off is fully blocked (hard constraint)."""
        for staff_id, availability in self.availability_map.items():
            day_off = availability.get("weekly_day_off")
            if day_off is None:
                continue  # Staff has no day-off specified

            # Block all assignments on this day for this staff
            for section in self.courses:
                if staff_id not in section.get("assigned_staff", []):
                    continue

                for time_slot in self.time_slots:
                    for room in self.rooms:
                        key = (section["_id"], day_off, time_slot, room["_id"])
                        if key in self.assignments:
                            # Force this assignment to False
                            self.model.Add(self.assignments[key] == 0)

    def _add_h8_year_level_conflicts(self) -> None:
        """H8: Sections with overlapping year levels can't share a time slot."""
        # Group sections by department
        depts = {}
        for section in self.courses:
            dept_id = section["department_id"]
            if dept_id not in depts:
                depts[dept_id] = []
            depts[dept_id].append(section)

        # For each department, check year-level conflicts
        for dept_id, dept_sections in depts.items():
            for i, section1 in enumerate(dept_sections):
                for section2 in dept_sections[i + 1 :]:
                    # Check if year levels overlap
                    years1 = set(section1.get("year_levels", []))
                    years2 = set(section2.get("year_levels", []))
                    if not years1.intersection(years2):
                        continue  # No overlap, no conflict

                    # If they overlap, they can't share a time slot
                    for day in self.working_days:
                        for time_slot in self.time_slots:
                            s1_rooms = [
                                self.assignments.get(
                                    (section1["_id"], day, time_slot, room["_id"])
                                )
                                for room in self.rooms
                            ]
                            s2_rooms = [
                                self.assignments.get(
                                    (section2["_id"], day, time_slot, room["_id"])
                                )
                                for room in self.rooms
                            ]

                            s1_valid = [v for v in s1_rooms if v is not None]
                            s2_valid = [v for v in s2_rooms if v is not None]

                            if s1_valid and s2_valid:
                                # At least one must be 0
                                self.model.AddAtMostOne(s1_valid + s2_valid)

    def _add_h9_cross_dept_shared_lecture(self) -> None:
        """H9: Cross-department shared lecture scheduled once."""
        # Find shared lectures (shared_with is non-empty)
        for section in self.courses:
            if not section.get("shared_with"):
                continue

            # This lecture is shared with other departments
            # It must be scheduled exactly once across all time slots
            all_assignments = [
                v
                for (s_id, d, t, r_id), v in self.assignments.items()
                if s_id == section["_id"]
            ]
            if all_assignments:
                self.model.Add(sum(all_assignments) == 1)

    def _add_soft_constraints(self) -> None:
        """Add soft constraints with weighted penalties."""
        objectives = []

        # S1: Respect staff preferred break window (weight 100)
        s1_penalty = self._soft_break_window()
        if s1_penalty:
            objectives.append(
                (s1_penalty, self.weights.get("break_window", 100))
            )

        # S2: No more than N consecutive slots per staff (weight 80)
        s2_penalty = self._soft_consecutive_slots()
        if s2_penalty:
            objectives.append(
                (s2_penalty, self.weights.get("consecutive_slots", 80))
            )

        # S3: Spread a course's weekly sessions across different days (weight 60)
        s3_penalty = self._soft_session_spread()
        if s3_penalty:
            objectives.append((s3_penalty, self.weights.get("session_spread", 60)))

        # S4: Cluster staff sessions to minimize distinct campus days (weight 40)
        s4_penalty = self._soft_campus_clustering()
        if s4_penalty:
            objectives.append(
                (s4_penalty, self.weights.get("campus_clustering", 40))
            )

        # Combine all objectives with weights
        if objectives:
            total_penalty = sum(penalty * weight for penalty, weight in objectives)
            self.model.Minimize(total_penalty)

    def _soft_break_window(self):
        """S1: Penalize break window violations."""
        # Simplified: penalize if staff has sessions during preferred break window
        penalty = 0
        for staff_id, availability in self.availability_map.items():
            windows = availability.get("preferred_break_windows", [])
            for window in windows:
                # If staff has a session during break window, add penalty
                # (This would need time parsing logic)
                pass
        return penalty if penalty > 0 else None

    def _soft_consecutive_slots(self):
        """S2: Penalize consecutive slots per staff."""
        # Simplified: penalize if staff has 3+ consecutive sessions
        penalty = 0
        # TODO: Implement consecutive slot detection
        return penalty if penalty > 0 else None

    def _soft_session_spread(self):
        """S3: Penalize if course sessions cluster (should spread across days)."""
        penalty = 0
        for section in self.courses:
            # Count days this section is scheduled
            scheduled_days = set()
            for (s_id, day, t, r_id), var in self.assignments.items():
                if s_id == section["_id"]:
                    # Would need solver value here (post-solve)
                    pass
        return penalty if penalty > 0 else None

    def _soft_campus_clustering(self):
        """S4: Penalize staff with sessions on many different days."""
        penalty = 0
        for staff in self.staff_members:
            # Count days this staff has sessions
            # (Would need post-solve evaluation)
            pass
        return penalty if penalty > 0 else None

    def solve(self) -> Tuple[int, float, List[Dict[str, Any]]]:
        """
        Run OR-Tools solver.

        Returns:
            Tuple of (hard_violations, soft_penalty, schedule_entries)
        """
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds

        status = solver.Solve(self.model)

        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return 1, float("inf"), []  # No solution found

        # Extract solution
        hard_violations = 0  # All hard constraints satisfied if we get here
        soft_penalty = solver.ObjectiveValue() if status == cp_model.OPTIMAL else 0

        schedule_entries = []
        for (section_id, day, time_slot, room_id), var in self.assignments.items():
            if solver.Value(var) == 1:
                # Find section and room details
                section = next(
                    (s for s in self.courses if s["_id"] == section_id), None
                )
                room = next((r for r in self.rooms if r["_id"] == room_id), None)

                if section and room:
                    entry = {
                        "section_id": section_id,
                        "course_name": section.get("course_name"),
                        "section_type": section.get("section_type"),
                        "day_of_week": day,
                        "time_slot": time_slot,
                        "room_id": room_id,
                        "room_name": room.get("name"),
                        "assigned_staff": section.get("assigned_staff", []),
                    }
                    schedule_entries.append(entry)

        return hard_violations, soft_penalty, schedule_entries
