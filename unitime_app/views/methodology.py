"""Methodology view: detailed technical walkthrough of data, ML model, and limitations."""
import streamlit as st
import pandas as pd
import json

from unitime_app.data_loader import load_historical_evaluations
from unitime_app.model_loader import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def render():
    st.title("📖 Methodology & Model Architecture")
    st.markdown(
        "This section details the end-to-end data pipeline, machine learning modeling, "
        "and algorithmic limitations of the Intelligent University Timetable Management System."
    )

    eval_data = load_historical_evaluations()
    model_eval = eval_data.get("model_evaluation", {})

    # Tabbed Walkthrough
    tab1, tab2, tab3, tab4 = st.tabs([
        "1. Data Pipeline & Normalization",
        "2. ML Model & Evaluation",
        "3. Scheduling Engine",
        "4. Limitations & Truth in Advertising"
    ])

    with tab1:
        st.subheader("Data Cleaning & Table Normalization")
        st.markdown(
            """
            * **Benchmark Source:** Official Purdue University Fall 2007 Large Lecture Room (`pu-fal07-llr.xml`) benchmark dataset.
            * **Preservation of Raw Values:** The raw XML tree was parsed and flattened into 12 CSV tables (11 normalized data tables plus a `data_quality_checks.csv` audit table) without modifying the original XML.
            * **Candidate Placements:** Room options (14,823) and time options (8,601) per class were combined to produce 220,904 candidate placement rows.
            * **Target Leakage Prevention:** Features derived directly from the reference solution (such as reference shared student overlaps) were strictly excluded from model features.
            """
        )

    with tab2:
        st.subheader("Machine Learning Formulation & Holdout Metrics")
        st.markdown(
            """
            * **Supervised Learning Target:** Whether an exact `(class_id, room_id, days_mask, start_slot, length_slots)` tuple was selected in the official committed reference solution.
            * **Crucial Interpretation:** The model target is a **reference placement preference proxy**, *not* a conflict prediction model. A candidate that was not selected in the reference timetable is not necessarily invalid or poor.
            * **Grouped Data Split:** Split by `class_id` using `GroupShuffleSplit` (~65% train, 15% validation, 20% test). Candidate rows for any given class never cross train/validation/test partitions.
            * **Pipeline Architecture:**
              * Categorical: `SimpleImputer(most_frequent)` → `OneHotEncoder(handle_unknown='ignore')`
              * Numerical: `SimpleImputer(median)` → `StandardScaler()`
              * Classifier: `LogisticRegression(class_weight='balanced', solver='liblinear')`
            """
        )

        st.subheader("Holdout Test Metrics")
        if not model_eval:
            st.warning(
                "`model_evaluation.json` was not found, so holdout metrics are unavailable. "
                "No placeholder values are shown."
            )

        def _metric(key: str, as_percent: bool = False) -> str:
            """Format a saved holdout metric, or 'N/A' if it is not in the evaluation file."""
            value = model_eval.get(key)
            if value is None:
                return "N/A"
            return f"{value * 100:.1f}%" if as_percent else f"{value:.4f}"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Test ROC-AUC", _metric("test_roc_auc"), help="Measures relative ranking quality between reference and non-reference placements")
        c2.metric("Average Precision (PR-AUC)", _metric("test_average_precision"), help="Reflects the highly sparse positive base rate (~0.4%)")
        c3.metric("Test Recall @ 0.5", _metric("test_recall_at_0_5", as_percent=True))
        c4.metric("Test Precision @ 0.5", _metric("test_precision_at_0_5", as_percent=True))

        with st.expander("Feature Schema Details"):
            st.markdown(f"**Categorical Features ({len(CATEGORICAL_FEATURES)}):** `{', '.join(CATEGORICAL_FEATURES)}`")
            st.markdown(f"**Numeric Features ({len(NUMERIC_FEATURES)}):** `{', '.join(NUMERIC_FEATURES)}`")

    with tab3:
        st.subheader("Greedy Scheduling Engine")
        st.markdown(
            """
            * **Class Ordering:** Classes are ordered dynamically by constraint difficulty: classes with fewest candidate options, most assigned instructors, and largest student limits are scheduled first.
            * **Hard Pruning:** For each candidate option, the scheduler checks weekly room double-booking and instructor double-booking. Any option creating an overlap is immediately pruned.
            * **Scoring Heuristic:**
              $$\\text{Cost} = \\text{Base Preference Cost} + 0.05 \\times \\text{Shared Student Penalty} - 0.25 \\times \\text{ML Score}$$
            * **Repair Heuristic:** Incorporates direct candidate insertion and one-level ejection (temporarily displacing up to two conflicting classes) to resolve unassigned classes.
            """
        )

    with tab4:
        st.subheader("Limitations & Transparent Constraints Status")
        st.warning(
            """
            **Honest Limitations & Unsupported UniTime Semantics:**
            1. **Not a Full UniTime Clone:** UniTime uses a comprehensive constraint-satisfaction solver. This project is an exploratory benchmark prototype.
            2. **Unenforced Group Constraints:** 282 inter-class constraints (Back-to-Back, Spread, Same Room, Same Time) are cataloged in data but not fully enforced during placement.
            3. **Calendar Date Exceptions:** Weekly day patterns are checked without date-specific bitsets; some apparent overlaps in audits may not meet on identical calendar dates.
            4. **Generalization Boundary:** Trained on a single university term (Purdue Fall 2007). No claims of universal generalization to other institutions are made.
            """
        )
