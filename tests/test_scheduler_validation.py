"""Cross-checks between the scheduler's self-reported metrics and the independent validator.

The scheduler counts overlaps while it builds a timetable; ``validate_timetable`` recomputes them
from the finished table. If the two ever disagree, one of them is wrong. These tests also cover
the repair heuristic, which previously had no test.
"""
import pandas as pd
import pytest

from unitime_app.config import HISTORICAL_TIMETABLES, SCHEDULER_COMP_FILE
from unitime_app.scheduler import run_scheduler
from unitime_app.validator import validate_timetable


@pytest.fixture(scope="module")
def ml_run():
    return run_scheduler(mode="ml", seed=42, apply_repair=False, save_run=False)


@pytest.fixture(scope="module")
def baseline_repaired_run():
    return run_scheduler(mode="baseline", seed=42, apply_repair=True, save_run=False)


def _assert_scheduler_matches_validator(run):
    metrics, df = run["metrics"], run["timetable_df"]
    report = validate_timetable(df)
    assert report["scheduled_classes"] == metrics["scheduled_classes"] == len(df)
    assert report["unassigned_classes_count"] == metrics["unassigned_classes"]
    assert sorted(report["unassigned_class_ids"]) == sorted(run["unassigned_class_ids"])
    assert report["room_overlap_pairs_count"] == metrics["room_overlap_pairs"]
    assert report["instructor_overlap_pairs_count"] == metrics["instructor_overlap_pairs"]
    assert report["student_overlap_proxy_count"] == metrics["shared_student_overlap_pairs_proxy"]
    assert metrics["scheduled_classes"] + metrics["unassigned_classes"] == metrics["total_classes"]
    assert not df["class_id"].duplicated().any(), "a class was scheduled twice"


def test_ml_run_metrics_match_independent_validator(ml_run):
    _assert_scheduler_matches_validator(ml_run)
    assert ml_run["metrics"]["room_overlap_pairs"] == 0
    assert ml_run["metrics"]["instructor_overlap_pairs"] == 0


def test_repair_run_is_valid_and_actually_repairs(baseline_repaired_run):
    _assert_scheduler_matches_validator(baseline_repaired_run)
    metrics = baseline_repaired_run["metrics"]
    assert metrics["repaired"] is True
    assert metrics["newly_repaired_classes"] > 0, "repair heuristic placed nothing on the baseline run"
    # Repair must never reintroduce hard-constraint violations.
    assert metrics["room_overlap_pairs"] == 0
    assert metrics["instructor_overlap_pairs"] == 0


def test_repair_improves_on_the_saved_greedy_baseline(baseline_repaired_run):
    saved = pd.read_csv(SCHEDULER_COMP_FILE).set_index("scheduler")
    greedy_unassigned = int(saved.loc["baseline", "unassigned_classes"])
    assert baseline_repaired_run["metrics"]["unassigned_classes"] < greedy_unassigned


def test_validator_reproduces_saved_benchmark_metrics():
    """Recompute the saved greedy results independently and compare with the saved summary file."""
    saved = pd.read_csv(SCHEDULER_COMP_FILE).set_index("scheduler")
    for scheduler_key, timetable_key in [("baseline", "Baseline (Greedy)"), ("ml", "ML-Guided (Greedy)")]:
        report = validate_timetable(pd.read_csv(HISTORICAL_TIMETABLES[timetable_key]))
        row = saved.loc[scheduler_key]
        assert report["scheduled_classes"] == row["classes_scheduled"], scheduler_key
        assert report["unassigned_classes_count"] == row["unassigned_classes"], scheduler_key
        assert report["room_overlap_pairs_count"] == row["room_overlap_pairs"], scheduler_key
        assert report["instructor_overlap_pairs_count"] == row["instructor_overlap_pairs"], scheduler_key
        assert report["student_overlap_proxy_count"] == row["shared_student_overlap_pairs_proxy"], scheduler_key


def test_saved_run_filenames_share_the_repaired_marker(tmp_path, monkeypatch):
    """Timetable CSV and metrics JSON for the same run must be identifiable as a pair."""
    import unitime_app.scheduler as sched

    monkeypatch.setattr(sched, "GENERATED_DIR", tmp_path)
    run_scheduler(mode="ml", seed=7, apply_repair=True, save_run=True)
    csvs = sorted(p.name for p in tmp_path.glob("timetable_*.csv"))
    jsons = sorted(p.name for p in tmp_path.glob("metrics_*.json"))
    assert len(csvs) == len(jsons) == 1
    assert "_repaired_" in csvs[0] and "_repaired_" in jsons[0]
    assert csvs[0].removeprefix("timetable_").removesuffix(".csv") == jsons[0].removeprefix("metrics_").removesuffix(".json")
