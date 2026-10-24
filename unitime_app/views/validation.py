import json
from pathlib import Path
import streamlit as st
import pandas as pd

from unitime_app.config import GENERATED_DIR, HISTORICAL_TIMETABLES, VAL_DIR
from unitime_app.validator import constraint_audit_rows, validate_timetable
from unitime_app.views.viewer import load_selected_timetable


def render():
    st.title("🛡️ Timetable Validation & Constraint Audit")
    st.markdown(
        "Independently audit timetables against room collisions, instructor conflicts, "
        "capacity shortages, and shared-student conflicts. "
        "This validator calculates metrics dynamically from raw placement coordinates."
    )

    # Source selection
    sources = []
    if "active_timetable" in st.session_state:
        sources.append("Currently Generated Schedule")
    sources.extend(list(HISTORICAL_TIMETABLES.keys()))

    source_choice = st.selectbox(
        "Select Schedule to Validate",
        sources,
        index=0,
        help="Run independent verification against any generated or historical timetable."
    )

    uploaded_file = st.file_uploader(
        "Or Upload Custom CSV Timetable (Optional)",
        type=["csv"],
        help="Upload any external timetable CSV containing class_id, room_id, days_mask, start_slot, length_slots"
    )

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.info(f"Loaded {len(df)} records from uploaded file: `{uploaded_file.name}`")
        except Exception as e:
            st.error(f"Error reading uploaded CSV: {e}")
            return
    else:
        df = load_selected_timetable(source_choice)

    if df.empty:
        st.warning("No schedule available to audit.")
        return

    # Run validation
    with st.spinner("Recomputing pairwise room, instructor, and student overlaps..."):
        report = validate_timetable(df)

    # Primary performance rates
    total_classes = report["scheduled_classes"] + report["unassigned_classes_count"]
    acc_rate = round((report["scheduled_classes"] / max(1, total_classes)) * 100, 1)
    hard_violations = report["room_overlap_pairs_count"] + report["instructor_overlap_pairs_count"]
    prec_rate = round((max(0, report["scheduled_classes"] - hard_violations) / max(1, report["scheduled_classes"])) * 100, 1)

    m1, m2 = st.columns(2)
    with m1:
        st.metric(
            "🎯 Accuracy Rate (Schedule Placement)",
            f"{acc_rate}%",
            delta=f"{report['scheduled_classes']} / {total_classes} Classes Scheduled",
            help="Proportion of all requested course offerings successfully scheduled."
        )
    with m2:
        st.metric(
            "🛡️ Precision Rate (Constraint Compliance)",
            f"{prec_rate}%",
            delta="100% Conflict-Free" if hard_violations == 0 else f"{hard_violations} Collisions Detected",
            delta_color="normal" if hard_violations == 0 else "inverse",
            help="Proportion of scheduled placements meeting strict hard constraints without room or instructor collisions."
        )

    # Top metrics (4 headline metrics)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Room Overlaps (Hard)",
            report["room_overlap_pairs_count"],
            delta="0 (Pass)" if report["room_overlap_pairs_count"] == 0 else f"{report['room_overlap_pairs_count']} Violations",
            delta_color="normal" if report["room_overlap_pairs_count"] == 0 else "inverse"
        )
    with c2:
        st.metric(
            "Instructor Overlaps (Hard)",
            report["instructor_overlap_pairs_count"],
            delta="0 (Pass)" if report["instructor_overlap_pairs_count"] == 0 else f"{report['instructor_overlap_pairs_count']} Violations",
            delta_color="normal" if report["instructor_overlap_pairs_count"] == 0 else "inverse"
        )
    with c3:
        st.metric(
            "Room Capacity Deficits",
            report["room_capacity_issues_count"],
            delta=f"{report['room_capacity_issues_count']} Warnings" if report["room_capacity_issues_count"] > 0 else "0",
            delta_color="off"
        )
    with c4:
        st.metric(
            "Unassigned Classes",
            report["unassigned_classes_count"],
            delta=f"{report['unassigned_classes_count']} Unplaced" if report["unassigned_classes_count"] > 0 else "0",
            delta_color="off"
        )

    st.markdown("---")

    # Constraint status table: rows come from the validator module (single source of truth)
    st.subheader("Implementation & Verification Status")
    hard_clean = (
        report["room_overlap_pairs_count"] == 0
        and report["instructor_overlap_pairs_count"] == 0
    )
    if hard_clean:
        st.warning(
            "**Audit notice:** this schedule shows zero room and zero instructor overlaps, "
            "but it must **not** be described as fully valid. Several official UniTime constraints "
            "(calendar date exceptions, multi-class group constraints, room sharing) are not modeled "
            "in this prototype."
        )
    else:
        st.error(
            "**Hard-constraint violations found.** See the conflict tables below. In addition, "
            "date exceptions, group constraints and room sharing are not modeled in this prototype."
        )

    st.dataframe(pd.DataFrame(constraint_audit_rows(report)), width="stretch", hide_index=True)

    # Detailed Conflict Breakdowns
    if report["room_overlap_pairs_count"] > 0:
        st.subheader("🚨 Room Overlap Conflicts")
        st.dataframe(pd.DataFrame(report["room_overlap_pairs"]), width="stretch")

    if report["instructor_overlap_pairs_count"] > 0:
        st.subheader("🚨 Instructor Overlap Conflicts")
        st.dataframe(pd.DataFrame(report["instructor_overlap_pairs"]), width="stretch")

    if report.get("student_overlap_proxy_count", 0) > 0:
        with st.expander(f"View {report['student_overlap_proxy_count']} Shared-Student Overlap Pairs (Soft Proxy)"):
            st.dataframe(pd.DataFrame(report["student_overlap_conflicts"]), width="stretch")

    if report["room_capacity_issues_count"] > 0:
        with st.expander(f"View {report['room_capacity_issues_count']} Room Capacity Warnings"):
            st.dataframe(pd.DataFrame(report["room_capacity_issues"]), width="stretch")

    if report["unassigned_classes_count"] > 0:
        with st.expander(f"View {report['unassigned_classes_count']} Unassigned Class IDs"):
            st.write(report["unassigned_class_ids"])

    # Download report button
    report_json = json.dumps(report, indent=2, default=str)
    st.download_button(
        "📥 Download Full Validation Audit Report (JSON)",
        data=report_json,
        file_name="validation_report.json",
        mime="application/json"
    )
