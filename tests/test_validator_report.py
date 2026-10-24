"""Regression tests for the *shape* of the validator report and the honesty of the constraint audit.

These guard against two kinds of failure:
  * ``validate_timetable`` returning ``None`` (or an incomplete dict) instead of a full report.
  * the audit table claiming that unimplemented UniTime constraints were evaluated.
"""
import pandas as pd
import pytest

from unitime_app.config import HISTORICAL_TIMETABLES
from unitime_app.validator import constraint_audit_rows, validate_timetable

EXPECTED_KEYS = {
    "scheduled_classes",
    "total_classes",
    "unassigned_classes_count",
    "unassigned_class_ids",
    "room_overlap_pairs_count",
    "room_overlap_pairs",
    "instructor_overlap_pairs_count",
    "instructor_overlap_pairs",
    "room_capacity_issues_count",
    "room_capacity_issues",
    "student_overlap_proxy_count",
    "student_overlap_conflicts",
    "constraint_enforcement_status",
}


@pytest.fixture(scope="module")
def ml_report():
    path = HISTORICAL_TIMETABLES["ML-Guided (Greedy)"]
    return validate_timetable(pd.read_csv(path))


def test_validate_timetable_returns_complete_report(ml_report):
    assert isinstance(ml_report, dict), "validate_timetable must return a dict, not None"
    assert EXPECTED_KEYS <= set(ml_report)


def test_report_counts_are_internally_consistent(ml_report):
    assert ml_report["scheduled_classes"] + ml_report["unassigned_classes_count"] == ml_report["total_classes"]
    assert ml_report["unassigned_classes_count"] == len(ml_report["unassigned_class_ids"])
    assert ml_report["room_overlap_pairs_count"] == len(ml_report["room_overlap_pairs"])
    assert ml_report["instructor_overlap_pairs_count"] == len(ml_report["instructor_overlap_pairs"])
    assert ml_report["room_capacity_issues_count"] == len(ml_report["room_capacity_issues"])
    assert ml_report["student_overlap_proxy_count"] == len(ml_report["student_overlap_conflicts"])


def test_empty_timetable_reports_every_class_as_unassigned():
    empty = pd.DataFrame(
        columns=["class_id", "room_id", "days_mask", "start_slot", "length_slots"]
    )
    report = validate_timetable(empty)
    assert report["scheduled_classes"] == 0
    assert report["unassigned_classes_count"] == report["total_classes"] > 0
    assert report["room_overlap_pairs_count"] == 0
    assert report["instructor_overlap_pairs_count"] == 0


def test_report_marks_unimplemented_constraints_as_unenforced(ml_report):
    status = ml_report["constraint_enforcement_status"]
    for key in ("date_pattern_exceptions", "group_constraints", "multi_room_semantics", "room_sharing_rules"):
        assert "Pending" in status[key] or "Unenforced" in status[key], f"{key} must not be reported as enforced"


def test_audit_rows_never_claim_unimplemented_constraints_were_evaluated(ml_report):
    for report in (None, ml_report):
        rows = {r["Constraint"]: r for r in constraint_audit_rows(report)}
        for name in ("Date pattern exceptions", "Group constraints", "Multi-room and sharing rules"):
            assert rows[name]["Audit result"] == "Not evaluated"
            assert "Pending" in rows[name]["Enforcement"]


def test_audit_rows_without_a_report_do_not_invent_counts():
    rows = {r["Constraint"]: r for r in constraint_audit_rows(None)}
    assert rows["Weekly room overlap"]["Audit result"] == "See scheduler metrics"
    assert rows["Instructor overlap"]["Audit result"] == "See scheduler metrics"


def test_audit_rows_use_counts_from_the_given_report(ml_report):
    rows = {r["Constraint"]: r for r in constraint_audit_rows(ml_report)}
    assert rows["Weekly room overlap"]["Audit result"] == f"{ml_report['room_overlap_pairs_count']:,} violations"
    assert rows["Shared student conflicts"]["Enforcement"] == "Soft proxy only"
