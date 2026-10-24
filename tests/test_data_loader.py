"""Test suite for data loading module."""
import pytest
import pandas as pd
from unitime_app.data_loader import (
    load_classes, load_rooms, load_room_options, load_time_options,
    load_instructors, load_students, load_student_offerings,
    load_group_constraints, load_data_quality_checks, load_dataset_statistics,
    load_candidate_features
)


def test_classes_table():
    df = load_classes()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 896
    assert "id" in df.columns
    assert "department" in df.columns
    assert "classLimit" in df.columns


def test_rooms_table():
    df = load_rooms()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 63
    assert "id" in df.columns
    assert "capacity" in df.columns
    assert df["capacity"].sum() == 7919


def test_candidate_features_table():
    df = load_candidate_features()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 220904
    assert "class_id" in df.columns
    assert "room_id" in df.columns
    assert "days_mask" in df.columns


def test_dataset_statistics():
    stats = load_dataset_statistics()
    assert stats["classes_count"] == 896
    assert stats["rooms_count"] == 63
    assert stats["students_count"] == 30846
    assert stats["candidate_placements_count"] == 220904
    assert stats["group_constraints_count"] == 282


def test_data_quality_checks():
    df = load_data_quality_checks()
    assert not df.empty
    assert "check" in df.columns
    assert "status" in df.columns
    assert (df["status"] == "PASS").all()
