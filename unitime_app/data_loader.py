"""Data loading and caching module for UniTime benchmark dataset."""
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Dict, Tuple
import pandas as pd

from unitime_app.config import (
    DATA_DIR, VAL_DIR, MODEL_DIR, FEATURE_FILE,
    MODEL_EVAL_FILE, SCHEDULER_COMP_FILE, SCHEDULER_EVAL_FILE, REPAIR_SUMMARY_FILE
)

try:
    import streamlit as st
    cache_data = st.cache_data
except Exception:
    def cache_data(func):
        return lru_cache(maxsize=16)(func)


@cache_data
def load_classes() -> pd.DataFrame:
    """Load normalized classes table.

    The ``dates`` column is a long binary mask; reading it as an integer
    overflows the 64‑bit limit when Streamlit converts the DataFrame to an
    Arrow table. We therefore force ``dates`` to be read as ``object`` (string).
    Other numeric columns may be interpreted as strings by pandas due to the
    explicit ``dtype`` mapping, so we coerce them back to the appropriate numeric
    type after loading.
    """
    # Force ``dates`` to stay a string; other columns will be inferred.
    df = pd.read_csv(
        DATA_DIR / "classes.csv",
        dtype={"dates": "object"},
        keep_default_na=False,
    )
    # Columns that should be numeric – convert them safely.
    for col in ["offering", "config", "roomToLimitRatio", "nrRooms", "parent"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@cache_data
def load_rooms() -> pd.DataFrame:
    """Load normalized rooms table."""
    return pd.read_csv(DATA_DIR / "rooms.csv")


@cache_data
def load_room_options() -> pd.DataFrame:
    """Load candidate room options per class."""
    return pd.read_csv(DATA_DIR / "candidate_room_options.csv")


@cache_data
def load_time_options() -> pd.DataFrame:
    """Load candidate time options per class."""
    return pd.read_csv(DATA_DIR / "candidate_time_options.csv")


@cache_data
def load_instructors() -> pd.DataFrame:
    """Load class-instructor relationships."""
    return pd.read_csv(DATA_DIR / "class_instructors.csv")


@cache_data
def load_students() -> pd.DataFrame:
    """Load student entity table."""
    return pd.read_csv(DATA_DIR / "students.csv")


@cache_data
def load_student_offerings() -> pd.DataFrame:
    """Load student offering enrollment links."""
    return pd.read_csv(DATA_DIR / "student_offerings.csv")


@cache_data
def load_group_constraints() -> pd.DataFrame:
    """Load group constraint entities."""
    return pd.read_csv(DATA_DIR / "group_constraints.csv")


@cache_data
def load_group_constraint_classes() -> pd.DataFrame:
    """Load group constraint to class link table."""
    return pd.read_csv(DATA_DIR / "group_constraint_classes.csv")


@cache_data
def load_data_quality_checks() -> pd.DataFrame:
    """Load data quality audit checks."""
    return pd.read_csv(DATA_DIR / "data_quality_checks.csv")


@cache_data
def load_committed_solution() -> pd.DataFrame:
    """Load benchmark reference committed solution assignments."""
    return pd.read_csv(DATA_DIR / "committed_solution_assignments.csv")


@cache_data
def load_candidate_features() -> pd.DataFrame:
    """Load pre-engineered candidate placement features."""
    return pd.read_csv(FEATURE_FILE)


@cache_data
def load_dataset_statistics() -> Dict[str, Any]:
    """Return dictionary of dataset summary counts."""
    classes = load_classes()
    rooms = load_rooms()
    time_opts = load_time_options()
    room_opts = load_room_options()
    instructors = load_instructors()
    students = load_students()
    offerings = load_student_offerings()
    group_cons = load_group_constraints()
    features = load_candidate_features()

    return {
        "classes_count": len(classes),
        "rooms_count": len(rooms),
        "total_room_capacity": int(rooms["capacity"].sum()),
        "time_options_count": len(time_opts),
        "room_options_count": len(room_opts),
        "candidate_placements_count": len(features),
        "instructors_count": instructors["instructor_id"].nunique(),
        "students_count": len(students),
        "student_offerings_count": len(offerings),
        "group_constraints_count": len(group_cons),
        "departments_count": classes["department"].nunique() if "department" in classes else 0,
    }


@cache_data
def load_historical_evaluations() -> Dict[str, Any]:
    """Load saved model and scheduler evaluation JSON and CSV summaries."""
    model_eval = {}
    if MODEL_EVAL_FILE.exists():
        with open(MODEL_EVAL_FILE, "r") as f:
            model_eval = json.load(f)

    scheduler_comp = pd.DataFrame()
    if SCHEDULER_COMP_FILE.exists():
        scheduler_comp = pd.read_csv(SCHEDULER_COMP_FILE)

    repair_summary = {}
    if REPAIR_SUMMARY_FILE.exists():
        with open(REPAIR_SUMMARY_FILE, "r") as f:
            repair_summary = json.load(f)

    return {
        "model_evaluation": model_eval,
        "scheduler_comparison": scheduler_comp,
        "repair_summary": repair_summary,
    }
