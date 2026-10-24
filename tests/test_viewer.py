"""Tests for timetable viewer helpers."""
import pandas as pd
from unitime_app.config import HISTORICAL_TIMETABLES
from unitime_app.views.viewer import (
    _enrich,
    _expand_to_days,
    calendar_grid_html,
    filter_timetable,
    weekly_grid_records,
)


def test_expand_to_days_keeps_day_column_when_empty():
    filtered = pd.DataFrame(
        columns=["class_id", "room_id", "days_mask", "start_slot", "length_slots"]
    )
    day_df = _expand_to_days(filtered)
    assert "_day" in day_df.columns
    assert day_df.empty
    assert weekly_grid_records(day_df) == []
    assert calendar_grid_html([], ["Mon", "Tue"]) == ""


def test_expand_to_days_splits_weekly_mask():
    df = pd.DataFrame(
        [
            {
                "class_id": 1,
                "room_id": 10,
                "days_mask": "1010100",
                "start_slot": 96,
                "length_slots": 12,
            }
        ]
    )
    day_df = _expand_to_days(df)
    assert list(day_df["_day"]) == ["Mon", "Wed", "Fri"]
    assert (day_df["class_id"] == 1).all()


def test_filter_timetable_and_empty_result_do_not_crash():
    df = pd.DataFrame(
        [
            {
                "class_id": 11,
                "room_id": 5,
                "department": "18",
                "days_human": "Mon, Wed",
                "days_mask": "1010000",
                "start_slot": 96,
                "length_slots": 12,
            }
        ]
    )
    none = filter_timetable(df, rooms=[999])
    assert none.empty
    day_df = _expand_to_days(none)
    assert "_day" in day_df.columns
    assert weekly_grid_records(day_df) == []

    found = filter_timetable(df, class_query="11")
    assert len(found) == 1


def test_weekly_grid_shows_class_room_and_times_from_historical():
    raw = pd.read_csv(HISTORICAL_TIMETABLES["ML-Guided (Greedy)"]).head(5)
    df = _enrich(raw.copy())
    day_df = _expand_to_days(df)
    records = weekly_grid_records(day_df)
    assert records
    sample = records[0]
    assert sample["class_id"] in set(df["class_id"].astype(int))
    assert "room_id" in sample
    assert sample["start_time"]
    assert sample["end_time"]
    html = calendar_grid_html(records, ["Mon", "Tue", "Wed", "Thu", "Fri"])
    assert "Class " in html
    assert "Room " in html
    assert "<th>Mon</th>" in html
    assert "Time" in html


def test_class_id_search_is_a_literal_substring_match():
    """Regression: regex metacharacters typed in the search box crashed the page."""
    df = pd.DataFrame(
        [
            {"class_id": 11, "room_id": 5, "department": "18", "days_human": "Mon", "days_mask": "1000000"},
            {"class_id": 112, "room_id": 6, "department": "18", "days_human": "Tue", "days_mask": "0100000"},
            {"class_id": 305, "room_id": 7, "department": "20", "days_human": "Wed", "days_mask": "0010000"},
        ]
    )
    for query in ["(", "[", "*", "\\", "1+", "."]:
        assert filter_timetable(df, class_query=query).empty, f"{query!r} must be matched literally"
    assert list(filter_timetable(df, class_query="11")["class_id"]) == [11, 112]
    assert list(filter_timetable(df, class_query=" 305 ")["class_id"]) == [305]


def test_available_days_includes_weekend_only_when_scheduled():
    from unitime_app.views.viewer import available_days

    weekday_only = pd.DataFrame({"days_mask": ["1010100", "0101000"]})
    assert available_days(weekday_only) == ["Mon", "Tue", "Wed", "Thu", "Fri"]

    with_sunday = pd.DataFrame({"days_mask": [1010100, 1]})  # ints lose leading zeros in CSVs
    assert available_days(with_sunday) == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sun"]


def test_calendar_grid_places_every_class_once_in_the_right_cell():
    records = [
        {"day": "Mon", "block": 540, "class_id": 1, "room_id": 5, "start_time": "09:00", "end_time": "10:00"},
        {"day": "Mon", "block": 540, "class_id": 2, "room_id": None, "start_time": "09:10", "end_time": "10:00"},
        {"day": "Wed", "block": 600, "class_id": 3, "room_id": 7, "start_time": "10:00", "end_time": "11:00"},
    ]
    html = calendar_grid_html(records, ["Mon", "Tue", "Wed"])
    for cid in (1, 2, 3):
        assert html.count(f"Class {cid}<") == 1
    assert "Room —" in html  # class without a room is still shown
    assert html.count("<tr>") == 3  # one header row + two occupied time blocks (09:00, 10:00)
