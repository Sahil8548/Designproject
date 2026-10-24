"""Test suite for independent constraint validation."""
import pytest
import pandas as pd
from unitime_app.config import HISTORICAL_TIMETABLES
from unitime_app.validator import validate_timetable


def test_historical_schedules_zero_hard_overlaps():
    """Verify saved historical baseline and ML timetables have 0 room and instructor overlaps."""
    for name, path in HISTORICAL_TIMETABLES.items():
        if path.exists():
            df = pd.read_csv(path)
            report = validate_timetable(df)
            assert report["room_overlap_pairs_count"] == 0, f"{name} had room overlaps"
            assert report["instructor_overlap_pairs_count"] == 0, f"{name} had instructor overlaps"
            assert report["unassigned_classes_count"] >= 0


def test_validator_detects_injected_room_collision():
    """Validator must detect an intentionally injected room collision."""
    base_path = HISTORICAL_TIMETABLES["Baseline (Greedy)"]
    df = pd.read_csv(base_path).copy()

    # Intentionally duplicate class 0's placement into class 1 to create an artificial overlap
    df.loc[1, "room_id"] = df.loc[0, "room_id"]
    df.loc[1, "days_mask"] = df.loc[0, "days_mask"]
    df.loc[1, "start_slot"] = df.loc[0, "start_slot"]
    df.loc[1, "length_slots"] = df.loc[0, "length_slots"]

    report = validate_timetable(df)
    assert report["room_overlap_pairs_count"] >= 1, "Validator failed to catch injected room collision!"
    c1, c2 = report["room_overlap_pairs"][0]["class_1"], report["room_overlap_pairs"][0]["class_2"]
    assert {c1, c2} == {int(df.loc[0, "class_id"]), int(df.loc[1, "class_id"])}


def test_validator_detects_injected_instructor_collision():
    """Validator must detect an intentionally injected instructor collision."""
    base_path = HISTORICAL_TIMETABLES["Baseline (Greedy)"]
    df = pd.read_csv(base_path).copy()

    # Find two classes sharing an instructor from class_instructors.csv
    from unitime_app.data_loader import load_instructors
    inst_df = load_instructors()
    grouped = inst_df.groupby("instructor_id")["class_id"].apply(list)
    multi_classes = [c for c in grouped if len(c) > 1]
    assert len(multi_classes) > 0

    c_a, c_b = multi_classes[0][0], multi_classes[0][1]

    idx_a = df.index[df["class_id"] == c_a].tolist()
    idx_b = df.index[df["class_id"] == c_b].tolist()

    if idx_a and idx_b:
        # Align times and days
        df.loc[idx_b[0], "days_mask"] = df.loc[idx_a[0], "days_mask"]
        df.loc[idx_b[0], "start_slot"] = df.loc[idx_a[0], "start_slot"]
        df.loc[idx_b[0], "length_slots"] = df.loc[idx_a[0], "length_slots"]

        report = validate_timetable(df)
        assert report["instructor_overlap_pairs_count"] >= 1, "Validator failed to catch injected instructor collision!"
