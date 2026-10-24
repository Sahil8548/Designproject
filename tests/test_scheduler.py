"""Test suite for scheduling execution and safe persistence."""
from pathlib import Path
import pytest
from unitime_app.config import GENERATED_DIR, HISTORICAL_TIMETABLES
from unitime_app.scheduler import run_scheduler


def test_scheduler_ml_generation_and_safe_output():
    """Verify that scheduling runs without errors and writes only to GENERATED_DIR."""
    # Capture historical file modification times before run
    hist_mtimes = {
        name: p.stat().st_mtime for name, p in HISTORICAL_TIMETABLES.items() if p.exists()
    }

    result = run_scheduler(mode="ml", seed=42, apply_repair=False, save_run=True)

    assert "timetable_df" in result
    df = result["timetable_df"]
    assert len(df) > 850
    assert result["metrics"]["room_overlap_pairs"] == 0
    assert result["metrics"]["instructor_overlap_pairs"] == 0
    assert result["output_path"] is not None
    assert Path(result["output_path"]).parent == GENERATED_DIR

    # Verify that historical files were NOT touched or overwritten
    for name, old_mtime in hist_mtimes.items():
        assert HISTORICAL_TIMETABLES[name].stat().st_mtime == old_mtime, f"{name} was modified!"
