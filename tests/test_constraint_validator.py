"""Tests for constraint validator."""

import pytest
from app.services.constraint_validator import ConstraintValidator


class TestConstraintValidatorH3:
    """Test H3: Room Capacity Constraint"""
    
    def test_h3_valid_room_capacity(self):
        """Sections should pass if rooms with sufficient capacity exist."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "capacity": 50}
        ]
        rooms = [
            {"_id": "room1", "capacity": 60, "label": "A"},
            {"_id": "room2", "capacity": 40, "label": "B"}
        ]
        
        is_valid, errors = ConstraintValidator.validate_h3_room_capacity(courses, rooms)
        assert is_valid
        assert len(errors) == 0
    
    def test_h3_insufficient_room_capacity(self):
        """Sections should fail if no room has sufficient capacity."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "capacity": 100}
        ]
        rooms = [
            {"_id": "room1", "capacity": 50},
            {"_id": "room2", "capacity": 80}
        ]
        
        is_valid, errors = ConstraintValidator.validate_h3_room_capacity(courses, rooms)
        assert not is_valid
        assert len(errors) > 0
        assert "H3 VIOLATION" in errors[0]
    
    def test_h3_with_enrollment_data(self):
        """Should use enrollment data if provided."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "capacity": 100}
        ]
        rooms = [
            {"_id": "room1", "capacity": 60},
            {"_id": "room2", "capacity": 50}
        ]
        enrollments = {
            "sec1": {"enrolled_students": 55}
        }
        
        is_valid, errors = ConstraintValidator.validate_h3_room_capacity(
            courses, rooms, enrollments
        )
        # room2 has capacity 50 which is < 55 enrolled, but room1 has 60
        assert is_valid
        assert len(errors) == 0


class TestConstraintValidatorH4:
    """Test H4: Required Room Labels Constraint"""
    
    def test_h4_valid_label(self):
        """Sections with label requirements should pass if matching room exists."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "required_room_label": "Lab"}
        ]
        rooms = [
            {"_id": "room1", "label": "Lab", "capacity": 50},
            {"_id": "room2", "label": "Lecture", "capacity": 100}
        ]
        
        is_valid, errors = ConstraintValidator.validate_h4_required_room_labels(courses, rooms)
        assert is_valid
        assert len(errors) == 0
    
    def test_h4_missing_label(self):
        """Sections should fail if required label doesn't exist."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "required_room_label": "Lab"}
        ]
        rooms = [
            {"_id": "room1", "label": "Lecture", "capacity": 100}
        ]
        
        is_valid, errors = ConstraintValidator.validate_h4_required_room_labels(courses, rooms)
        assert not is_valid
        assert len(errors) > 0
        assert "H4 VIOLATION" in errors[0]
    
    def test_h4_no_label_requirement(self):
        """Sections without label requirements should always pass."""
        courses = [
            {"_id": "sec1", "course_name": "CS101"}
        ]
        rooms = [
            {"_id": "room1", "label": "Lab"}
        ]
        
        is_valid, errors = ConstraintValidator.validate_h4_required_room_labels(courses, rooms)
        assert is_valid
        assert len(errors) == 0


class TestConstraintValidatorH6:
    """Test H6: Room Features Constraint"""
    
    def test_h6_valid_features(self):
        """Sections should pass if rooms with required features exist."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "section_type": "lab"}
        ]
        rooms = [
            {"_id": "room1", "features": ["computers", "projector"]},
            {"_id": "room2", "features": ["projector"]}
        ]
        requirements = {"lab": ["computers", "projector"]}
        
        is_valid, errors = ConstraintValidator.validate_h6_room_features(
            courses, rooms, requirements
        )
        assert is_valid
        assert len(errors) == 0
    
    def test_h6_missing_features(self):
        """Sections should fail if no room has all required features."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "section_type": "lab"}
        ]
        rooms = [
            {"_id": "room1", "features": ["computers"]},
            {"_id": "room2", "features": ["projector"]}
        ]
        requirements = {"lab": ["computers", "projector"]}
        
        is_valid, errors = ConstraintValidator.validate_h6_room_features(
            courses, rooms, requirements
        )
        assert not is_valid
        assert len(errors) > 0
        assert "H6 VIOLATION" in errors[0]
    
    def test_h6_no_requirements(self):
        """Should pass if no feature requirements defined."""
        courses = [{"_id": "sec1", "course_name": "CS101", "section_type": "lecture"}]
        rooms = [{"_id": "room1", "features": []}]
        
        is_valid, errors = ConstraintValidator.validate_h6_room_features(courses, rooms)
        assert is_valid
        assert len(errors) == 0


class TestConstraintValidatorH7:
    """Test H7: Session Overlap Prevention"""
    
    def test_h7_no_violations(self):
        """Should pass when instructors don't have excessive slots."""
        courses = [
            {"_id": "sec1", "assigned_staff": ["staff1"], "slots_per_week": 3},
            {"_id": "sec2", "assigned_staff": ["staff1"], "slots_per_week": 2},
        ]
        staff = [{"_id": "staff1", "name": "Prof A"}]
        
        is_valid, errors = ConstraintValidator.validate_h7_session_overlap_prevention(
            courses, staff
        )
        # H7 returns warnings, not errors, so always "valid"
        assert is_valid
    
    def test_h7_warning_for_excessive_slots(self):
        """Should warn when instructor has > 20 slots/week."""
        courses = [
            {"_id": "sec1", "assigned_staff": ["staff1"], "slots_per_week": 10},
            {"_id": "sec2", "assigned_staff": ["staff1"], "slots_per_week": 12},
        ]
        staff = [{"_id": "staff1", "name": "Prof A"}]
        
        # H7 doesn't return errors (only warnings logged)
        is_valid, errors = ConstraintValidator.validate_h7_session_overlap_prevention(
            courses, staff
        )
        assert is_valid
        assert len(errors) == 0  # Currently warnings only


class TestRunAllValidations:
    """Test the combined validation function."""
    
    def test_all_validations_pass(self):
        """All validations should pass with good data."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "capacity": 50, "required_room_label": "Lecture"}
        ]
        staff = [{"_id": "staff1", "name": "Prof A"}]
        rooms = [
            {"_id": "room1", "label": "Lecture", "capacity": 60}
        ]
        
        is_feasible, critical_errors, warnings = ConstraintValidator.run_all_validations(
            courses, staff, rooms
        )
        assert is_feasible
        assert len(critical_errors) == 0
    
    def test_all_validations_fail_on_capacity(self):
        """Should fail if any hard constraint is violated."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "capacity": 100}
        ]
        staff = []
        rooms = [
            {"_id": "room1", "capacity": 50}
        ]
        
        is_feasible, critical_errors, warnings = ConstraintValidator.run_all_validations(
            courses, staff, rooms
        )
        assert not is_feasible
        assert len(critical_errors) > 0
        assert any("H3" in err for err in critical_errors)
    
    def test_all_validations_with_multiple_violations(self):
        """Should report all violations found."""
        courses = [
            {"_id": "sec1", "course_name": "CS101", "capacity": 100, "required_room_label": "Lab"},
            {"_id": "sec2", "course_name": "CS102", "capacity": 80}
        ]
        staff = []
        rooms = [
            {"_id": "room1", "label": "Lecture", "capacity": 50}
        ]
        
        is_feasible, critical_errors, warnings = ConstraintValidator.run_all_validations(
            courses, staff, rooms
        )
        assert not is_feasible
        assert len(critical_errors) >= 2  # H3 + H4 violations
