"""End-to-end interaction tests driven through Streamlit's AppTest harness.

``test_app_pages.py`` only renders each page in its initial state. These tests click
"Generate Timetable" and then exercise View / Compare / Validate / Dashboard with a live
session timetable, plus the View page's filter widgets. Scheduler output goes to the temp
directory configured in ``conftest.py``.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_SCRIPT = Path(__file__).resolve().parents[1] / "run_app.py"


def _go(at: AppTest, page: str) -> AppTest:
    """Navigate to ``page`` with fresh widget state.

    Streamlit keeps widget values while a page stays mounted, so re-selecting the current page
    would inherit the previous test's filters. Bouncing through another page resets them.
    """
    if at.sidebar.radio[0].value == page:
        at.sidebar.radio[0].set_value("Methodology").run()
    return at.sidebar.radio[0].set_value(page).run()


def _widget(collection, label):
    return next(w for w in collection if w.label == label)


def _showing_text(at: AppTest) -> str:
    return next(m.value for m in at.markdown if "Showing" in m.value)


def _assert_clean(at: AppTest, page: str):
    assert not at.exception, f"{page} raised: {[e.value for e in at.exception]}"
    assert not at.error, f"{page} showed st.error: {[e.value for e in at.error]}"


@pytest.fixture(scope="module")
def generated_app():
    """An app session in which an ML timetable has been generated through the UI."""
    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=300)
    at.run()
    _go(at, "Generate timetable")
    at.button[0].click().run()
    _assert_clean(at, "Generate timetable")
    assert at.success, "generation did not report success"
    return at


def test_generate_reports_real_metrics(generated_app):
    at = generated_app
    metrics = at.session_state["active_metrics"]
    shown = {m.label: m.value for m in at.metric}
    assert shown["Scheduled"] == f"{metrics['scheduled_classes']} / {metrics['total_classes']}"
    assert shown["Room Overlaps"] == "0" and shown["Instructor Overlaps"] == "0"
    assert metrics["scheduled_classes"] > 850
    assert Path(at.session_state["active_path"]).exists()


def test_view_defaults_to_the_generated_schedule(generated_app):
    at = _go(generated_app, "View timetable")
    _assert_clean(at, "View timetable")
    assert at.selectbox[0].value == "Currently Generated Schedule"
    total = at.session_state["active_metrics"]["scheduled_classes"]
    assert f"{total:,} of {total:,}" in _showing_text(at)


@pytest.mark.parametrize("query", ["(", "[", "*", "\\", "1+", "no-such-class"])
def test_view_search_box_survives_special_characters(generated_app, query):
    at = _go(generated_app, "View timetable")
    _widget(at.text_input, "Search class ID").set_value(query).run()
    _assert_clean(at, f"View timetable search {query!r}")
    assert "Showing 0 of" in _showing_text(at)


def test_view_filters_narrow_the_result(generated_app):
    at = _go(generated_app, "View timetable")
    total = at.session_state["active_metrics"]["scheduled_classes"]

    rooms = _widget(at.multiselect, "Filter by room")
    rooms.set_value([rooms.options[0]]).run()
    _assert_clean(at, "room filter")
    assert 0 < int(_showing_text(at).split("Showing ")[1].split(" ")[0].replace(",", "")) < total

    _widget(at.text_input, "Search class ID").set_value("").run()
    depts = _widget(at.multiselect, "Filter by department")
    depts.set_value([depts.options[0]]).run()
    _assert_clean(at, "department filter")


def test_view_data_table_mode_renders(generated_app):
    at = _go(generated_app, "View timetable")
    at.get("segmented_control")[0].set_value("Data table").run()
    _assert_clean(at, "data table mode")
    assert at.dataframe, "data table mode should show a dataframe"


def test_view_every_saved_timetable_renders(generated_app):
    at = _go(generated_app, "View timetable")
    for source in at.selectbox[0].options:
        at.selectbox[0].set_value(source).run()
        _assert_clean(at, f"View timetable / {source}")


def test_compare_includes_the_session_run(generated_app):
    at = _go(generated_app, "Compare results")
    _assert_clean(at, "Compare results")
    table = at.dataframe[0].value
    assert any("this session" in str(s) for s in table["scheduler"]), "session run missing from comparison"
    assert {"baseline", "ml"} <= set(table["scheduler"]), "saved benchmark runs missing"
    session = table[table["scheduler"].str.contains("this session")].iloc[0]
    metrics = generated_app.session_state["active_metrics"]
    assert session["classes_scheduled"] == metrics["scheduled_classes"]
    assert session["shared_student_overlap_pairs_proxy"] == metrics["shared_student_overlap_pairs_proxy"]


def test_validate_agrees_with_the_generated_schedule(generated_app):
    at = _go(generated_app, "Validate timetable")
    _assert_clean(at, "Validate timetable")
    shown = {m.label: m.value for m in at.metric}
    metrics = generated_app.session_state["active_metrics"]
    assert shown["Room Overlaps (Hard)"] == str(metrics["room_overlap_pairs"])
    assert shown["Instructor Overlaps (Hard)"] == str(metrics["instructor_overlap_pairs"])
    assert shown["Unassigned Classes"] == str(metrics["unassigned_classes"])
    audit = at.dataframe[0].value
    not_modeled = audit[audit["Constraint"].isin(
        ["Date pattern exceptions", "Group constraints", "Multi-room and sharing rules"]
    )]
    assert len(not_modeled) == 3 and (not_modeled["Audit result"] == "Not evaluated").all()


def test_dashboard_shows_session_results_and_room_chart(generated_app):
    at = _go(generated_app, "Dashboard")
    _assert_clean(at, "Dashboard")
    labels = [m.label for m in at.metric]
    assert "Scheduled" in labels and "Room overlaps" in labels
    # Element type is "vega_lite_chart" on current Streamlit, "arrow_vega_lite_chart" on older releases.
    charts = at.get("vega_lite_chart") + at.get("arrow_vega_lite_chart")
    assert charts, "room utilisation chart missing"
