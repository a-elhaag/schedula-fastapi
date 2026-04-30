"""Hard constraint validators for schedule solver."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConstraintValidator:
    """
    Validates and enforces hard constraints on schedule data before solver runs.
    Provides early detection of infeasible problems.
    """

    @staticmethod
    def validate_h3_room_capacity(
        courses: list[dict[str, Any]],
        rooms: list[dict[str, Any]],
        enrollments: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[bool, list[str]]:
        """
        H3: Room Capacity Constraint
        Check: For each section, there exists at least one room with groups_capacity >= section.num_groups.

        Returns (is_valid, error_messages)
        """
        errors = []

        for course in courses:
            section_id = course["_id"]
            required_groups = course.get("num_groups", 1)

            # Find compatible rooms
            compatible_rooms = [
                r for r in rooms
                if r.get("groups_capacity", 0) >= required_groups
            ]

            if not compatible_rooms:
                room_caps = [r.get("groups_capacity", 0) for r in rooms]
                max_cap = max(room_caps) if room_caps else 0
                errors.append(
                    f"H3 VIOLATION: Section {course.get('course_name', section_id)} "
                    f"requires {required_groups} group(s), but max available is {max_cap}. "
                    f"Add rooms with higher groups_capacity or reduce num_groups."
                )

        return len(errors) == 0, errors

    @staticmethod
    def validate_h4_required_room_labels(
        courses: list[dict[str, Any]],
        rooms: list[dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        """
        H4: Required Room Labels Constraint
        Check: For each section with required_room_label, at least one room exists with that label.
        
        Returns (is_valid, error_messages)
        """
        errors = []
        available_labels = {r.get("label") for r in rooms if r.get("label")}
        
        for course in courses:
            req_label = course.get("required_room_label")
            if not req_label:
                continue
            
            if req_label not in available_labels:
                errors.append(
                    f"H4 VIOLATION: Section {course.get('course_name', course['_id'])} "
                    f"requires room label '{req_label}', but no such room exists. "
                    f"Available labels: {sorted(available_labels) if available_labels else 'none'}"
                )
        
        return len(errors) == 0, errors

    @staticmethod
    def validate_h6_room_features(
        courses: list[dict[str, Any]],
        rooms: list[dict[str, Any]],
        room_feature_requirements: dict[str, list[str]] | None = None,
    ) -> tuple[bool, list[str]]:
        """
        H6: Room Features/Availability Constraint
        Check: For each section, at least one room exists with all required features.
        
        room_feature_requirements: dict mapping section_type to list of required features
        Example: {"lab": ["computers", "projector"], "lecture": ["projector"]}
        
        Returns (is_valid, error_messages)
        """
        if not room_feature_requirements:
            # No feature requirements defined, skip validation
            return True, []
        
        errors = []
        
        for course in courses:
            section_type = course.get("section_type", "")
            required_features = room_feature_requirements.get(section_type, [])
            
            if not required_features:
                continue
            
            # Find rooms with all required features
            compatible_rooms = [
                r for r in rooms
                if all(f in r.get("features", []) for f in required_features)
            ]
            
            if not compatible_rooms:
                available_features = set()
                for r in rooms:
                    available_features.update(r.get("features", []))
                
                errors.append(
                    f"H6 VIOLATION: {section_type.title()} sections (e.g., {course.get('course_name', course['_id'])}) "
                    f"require features {required_features}, but no room has all of them. "
                    f"Available features: {sorted(available_features) if available_features else 'none'}"
                )
        
        return len(errors) == 0, errors

    @staticmethod
    def validate_h7_session_overlap_prevention(
        courses: list[dict[str, Any]],
        staff_data: list[dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        """
        H7: Session Overlap Prevention
        Check: No instructor is assigned to multiple sections without overlap capacity.
        
        Note: The solver itself (H1/H2) enforces no-overlap.
        This validator checks for logically problematic assignments pre-solve.
        
        For example: if a staff member is assigned to 3 sections all with
        slots_per_week > 1, they might conflict regardless of room availability.
        
        Returns (is_valid, error_messages)
        """
        errors = []
        
        # Build staff -> sections mapping
        staff_sections: dict[str, list[dict]] = {}
        for course in courses:
            for staff_id in course.get("assigned_staff", []):
                staff_sections.setdefault(staff_id, []).append(course)
        
        # Check each staff member
        for staff_id, assigned_courses in staff_sections.items():
            if len(assigned_courses) <= 1:
                continue
            
            # Simple heuristic: total slots per week should be reasonable
            # Assuming max 20 slots per week per instructor
            total_slots = sum(c.get("slots_per_week", 1) for c in assigned_courses)
            if total_slots > 20:
                course_names = ", ".join(c.get("course_name", c["_id"]) for c in assigned_courses[:3])
                if len(assigned_courses) > 3:
                    course_names += f", ... ({len(assigned_courses)} total)"
                
                # Find staff name if available
                staff_obj = next((s for s in staff_data if s["_id"] == staff_id), None)
                staff_name = staff_obj.get("name", staff_id) if staff_obj else staff_id
                
                logger.warning(
                    f"H7 WARNING: {staff_name} assigned to {len(assigned_courses)} courses "
                    f"with {total_slots} total slots/week (max recommended: 20). "
                    f"Courses: {course_names}. May cause conflicts."
                )
        
        # For now, don't fail validation (warnings only)
        # Could be made stricter by returning errors
        return True, []

    @staticmethod
    def run_all_validations(
        courses: list[dict[str, Any]],
        staff_data: list[dict[str, Any]],
        rooms: list[dict[str, Any]],
        enrollments: dict[str, dict[str, Any]] | None = None,
        room_feature_requirements: dict[str, list[str]] | None = None,
    ) -> tuple[bool, list[str], dict[str, list[str]]]:
        """
        Run all hard constraint validations.
        
        Returns:
            is_valid: bool - True if all critical constraints pass
            critical_errors: list[str] - H3, H4 errors that make schedule infeasible
            warnings: dict[str, list[str]] - Non-critical issues (H6, H7, etc.)
        """
        critical_errors = []
        warnings = {}
        
        # H3: Room capacity
        h3_valid, h3_errors = ConstraintValidator.validate_h3_room_capacity(
            courses, rooms, enrollments
        )
        if not h3_valid:
            critical_errors.extend(h3_errors)
        
        # H4: Required room labels
        h4_valid, h4_errors = ConstraintValidator.validate_h4_required_room_labels(
            courses, rooms
        )
        if not h4_valid:
            critical_errors.extend(h4_errors)
        
        # H6: Room features
        h6_valid, h6_errors = ConstraintValidator.validate_h6_room_features(
            courses, rooms, room_feature_requirements
        )
        if not h6_valid:
            warnings["h6_features"] = h6_errors
        
        # H7: Session overlap (warnings only for now)
        h7_valid, h7_errors = ConstraintValidator.validate_h7_session_overlap_prevention(
            courses, staff_data
        )
        if h7_errors:
            warnings["h7_overlap"] = h7_errors

        is_valid = h3_valid and h4_valid
        return is_valid, critical_errors, warnings
