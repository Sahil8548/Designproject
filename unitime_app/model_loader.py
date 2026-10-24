"""Model loading and inference scoring module."""
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple
import joblib
import numpy as np
import pandas as pd

from unitime_app.config import MODEL_FILE

try:
    import streamlit as st
    cache_resource = st.cache_resource
except Exception:
    def cache_resource(func):
        return lru_cache(maxsize=4)(func)

CATEGORICAL_FEATURES = ["department_id", "subpart_id", "days_mask"]
NUMERIC_FEATURES = [
    "start_minutes", "duration_minutes", "break_time", "class_limit", "room_capacity",
    "capacity_surplus", "capacity_ratio", "room_preference", "time_preference",
    "room_is_discouraged", "instructor_count", "group_constraint_count",
    "group_type_count_BTB", "group_type_count_BTB_TIME", "group_type_count_CAN_SHARE_ROOM",
    "group_type_count_DIFF_TIME", "group_type_count_MEET_WITH", "group_type_count_NHB(1.5)",
    "group_type_count_NHB_GTE(1)", "group_type_count_SAME_DAYS", "group_type_count_SAME_INSTR",
    "group_type_count_SAME_ROOM", "group_type_count_SAME_START", "group_type_count_SAME_STUDENTS",
    "group_type_count_SAME_TIME", "group_type_count_SPREAD"
]


@cache_resource
def load_trained_model():
    """Load the serialized scikit-learn pipeline."""
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"Model file not found at {MODEL_FILE}")
    return joblib.load(MODEL_FILE)


def score_candidate_features(features_df: pd.DataFrame) -> np.ndarray:
    """Predict reference placement probability score for each candidate row."""
    model = load_trained_model()
    feature_cols = CATEGORICAL_FEATURES + NUMERIC_FEATURES
    X = features_df[feature_cols]
    scores = model.predict_proba(X)[:, 1]
    return scores
