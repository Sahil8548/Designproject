"""Tests for dashboard data helpers using real evaluation files."""
import pandas as pd
from unitime_app.config import HISTORICAL_TIMETABLES
from unitime_app.data_loader import load_dataset_statistics, load_rooms
from unitime_app.views.dashboard import historical_run_summary, room_utilisation_frame


def test_dashboard_uses_real_dataset_counts():
    stats = load_dataset_statistics()
    assert stats["classes_count"] == 896
    assert stats["rooms_count"] == 63
    assert stats["students_count"] == 30846
    assert stats["candidate_placements_count"] == 220904


def test_historical_run_summary_matches_saved_scheduler_files():
    hist = historical_run_summary()
    assert not hist.empty
    assert "classes_scheduled" in hist.columns
    assert "shared_student_overlap_pairs_proxy" in hist.columns
    scheduled = set(hist["classes_scheduled"].astype(int))
    assert 868 in scheduled
    assert 882 in scheduled
    assert (hist["room_overlap_pairs"] == 0).all()
    assert (hist["instructor_overlap_pairs"] == 0).all()


def test_room_utilisation_counts_actual_assignments():
    rooms = load_rooms()
    timetable = pd.read_csv(HISTORICAL_TIMETABLES["ML-Guided (Greedy)"])
    frame = room_utilisation_frame(timetable, rooms)
    assert "Capacity" in frame.columns
    assert "Assigned classes" in frame.columns
    assert int(frame["Assigned classes"].sum()) == len(timetable.dropna(subset=["room_id"]))
    assert frame["Capacity"].sum() == rooms["capacity"].sum()
