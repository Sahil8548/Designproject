"""Headless smoke test: render every page of the Streamlit app and fail on any uncaught exception.

Uses Streamlit's official ``AppTest`` harness, which runs the real ``run_app.py`` script
without starting a server or opening a browser. It does not click "Generate Timetable"
(that is covered by ``test_scheduler.py`` and would write new files to ``generated_outputs/``).
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_SCRIPT = Path(__file__).resolve().parents[1] / "run_app.py"

PAGES = [
    "Dashboard",
    "Generate timetable",
    "View timetable",
    "Compare results",
    "Validate timetable",
    "Methodology",
]


def _render(page: str) -> AppTest:
    at = AppTest.from_file(str(APP_SCRIPT), default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value(page).run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exceptions(page):
    at = _render(page)
    assert not at.exception, f"{page} raised: {[e.value for e in at.exception]}"
    assert not at.error, f"{page} showed st.error: {[e.value for e in at.error]}"


def test_validation_page_reports_hard_constraint_metrics():
    """The page that previously crashed must show its four headline metrics."""
    at = _render("Validate timetable")
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert labels == [
        "Room Overlaps (Hard)",
        "Instructor Overlaps (Hard)",
        "Room Capacity Deficits",
        "Unassigned Classes",
    ]
