"""Dashboard view: dataset statistics, room utilisation, and recent results."""
import altair as alt
import pandas as pd
import streamlit as st

from unitime_app.config import HISTORICAL_TIMETABLES
from unitime_app.data_loader import (
    load_data_quality_checks,
    load_dataset_statistics,
    load_historical_evaluations,
    load_rooms,
)


def historical_run_summary() -> pd.DataFrame:
    """Return verified scheduler comparison rows from saved evaluation files."""
    eval_data = load_historical_evaluations()
    comp = eval_data.get("scheduler_comparison", pd.DataFrame())
    if comp is None or comp.empty:
        return pd.DataFrame()
    return comp.copy()


def room_utilisation_frame(timetable_df: pd.DataFrame, rooms_df: pd.DataFrame) -> pd.DataFrame:
    """Build capacity vs assigned-class counts keyed by room id."""
    room_cap = rooms_df.set_index("id")["capacity"]
    if timetable_df is None or timetable_df.empty or "room_id" not in timetable_df.columns:
        return pd.DataFrame({"Capacity": room_cap, "Assigned classes": 0})
    usage = (
        timetable_df["room_id"]
        .value_counts()
        .reindex(room_cap.index, fill_value=0)
    )
    return pd.DataFrame({"Capacity": room_cap, "Assigned classes": usage})


def room_utilisation_chart(chart_df: pd.DataFrame) -> alt.Chart:
    """Bar chart of classes assigned per room, coloured by room capacity.

    Capacity (up to ~470 seats) and class counts (up to ~30) differ by an order of
    magnitude, so they are not plotted on one axis; capacity is shown as colour and tooltip.
    """
    data = chart_df.reset_index().rename(columns={chart_df.index.name or "index": "Room"})
    data["Room"] = data["Room"].astype(str)
    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X("Room:N", sort=alt.EncodingSortField("Assigned classes", order="descending"),
                    title="Room (sorted by classes assigned)", axis=alt.Axis(labelAngle=-90)),
            y=alt.Y("Assigned classes:Q", title="Classes assigned"),
            color=alt.Color("Capacity:Q", title="Seats", scale=alt.Scale(scheme="blues")),
            tooltip=["Room:N", "Assigned classes:Q", "Capacity:Q"],
        )
        .properties(height=320)
    )


def _session_or_historical_timetable() -> tuple[pd.DataFrame, str]:
    if "active_timetable" in st.session_state:
        return st.session_state["active_timetable"], "this session"
    path = HISTORICAL_TIMETABLES.get("ML-Guided (Greedy)")
    if path is not None and path.exists():
        return pd.read_csv(path), "ML-guided historical run"
    return pd.DataFrame(), ""


def render():
    st.title("Dashboard")
    st.markdown(
        "Intelligent University Timetable Management System — automated academic "
        "scheduling on the Purdue Fall 2007 UniTime benchmark. Figures below come "
        "from the cleaned dataset and saved scheduler runs."
    )

    stats = load_dataset_statistics()

    st.subheader("Dataset")
    with st.container(horizontal=True):
        st.metric("Total classes", f"{stats['classes_count']:,}", border=True)
        st.metric("Available rooms", f"{stats['rooms_count']:,}", border=True)
        st.metric("Enrolled students", f"{stats['students_count']:,}", border=True)
        st.metric("Candidate placements", f"{stats['candidate_placements_count']:,}", border=True)

    with st.container(horizontal=True):
        st.metric("Unique instructors", f"{stats['instructors_count']:,}", border=True)
        st.metric("Student offerings", f"{stats['student_offerings_count']:,}", border=True)
        st.metric("Group constraints", f"{stats['group_constraints_count']:,}", border=True)
        st.metric("Academic departments", f"{stats['departments_count']:,}", border=True)

    st.subheader("Scheduling results")
    if "active_metrics" in st.session_state:
        m = st.session_state["active_metrics"]
        st.caption(f"This session · {m.get('mode', 'unknown')} · seed {m.get('seed', '—')}")
        with st.container(horizontal=True):
            st.metric("Scheduled", f"{m['scheduled_classes']} / {m['total_classes']}", border=True)
            st.metric("Unassigned", f"{m['unassigned_classes']}", border=True)
            st.metric("Room overlaps", f"{m['room_overlap_pairs']}", border=True)
            st.metric("Instructor overlaps", f"{m['instructor_overlap_pairs']}", border=True)

    hist = historical_run_summary()
    if not hist.empty:
        st.caption(
            "Verified historical greedy runs on the Purdue Fall 2007 LLR benchmark. "
            "Student overlap is a proxy, not a per-student conflict count."
        )
        display = hist.rename(columns={
            "scheduler": "Scheduler",
            "classes_scheduled": "Scheduled",
            "total_classes": "Total",
            "unassigned_classes": "Unassigned",
            "room_overlap_pairs": "Room overlaps",
            "instructor_overlap_pairs": "Instructor overlaps",
            "shared_student_overlap_pairs_proxy": "Student overlap (proxy)",
            "preference_cost_sum": "Preference cost",
            "runtime_seconds": "Runtime (s)",
        })
        st.dataframe(
            display,
            hide_index=True,
            alt="Historical baseline and ML-guided scheduler comparison metrics",
        )
    else:
        st.info("Historical scheduler comparison files were not found.")

    st.subheader("Room utilisation")
    rooms_df = load_rooms()
    timetable_df, source_label = _session_or_historical_timetable()
    if timetable_df.empty:
        st.info("Generate a timetable to see room utilisation statistics.")
    else:
        st.caption(f"Assigned class counts by room from the {source_label}.")
        chart_df = room_utilisation_frame(timetable_df, rooms_df)
        st.altair_chart(
            room_utilisation_chart(chart_df),
            width="stretch",
            alt="Classes assigned to each room, coloured by room capacity",
        )
        busiest = chart_df["Assigned classes"].idxmax()
        idle = int((chart_df["Assigned classes"] == 0).sum())
        st.caption(
            f"Busiest room: {busiest} ({int(chart_df['Assigned classes'].max())} classes, "
            f"{int(chart_df.loc[busiest, 'Capacity'])} seats) · rooms with no classes: {idle}."
        )

    with st.expander("Dataset and ML approach"):
        st.markdown(
            "- **Source:** `pu-fal07-llr.xml` — Purdue University Fall 2007 Large Lecture Rooms (UniTime v2.4 benchmark).\n"
            "- **ML model:** A logistic regression pipeline trained to rank candidate placements that match the reference timetable. "
            "It is *not* a validated conflict-prediction model or a global optimiser.\n"
            "- **Scheduler limitation:** Hard constraints (room and instructor overlap) are enforced. "
            "Group constraints, date-pattern exceptions, and room-sharing rules are not yet handled."
        )

    with st.expander("Data quality checks"):
        dq_df = load_data_quality_checks()
        st.dataframe(
            dq_df,
            hide_index=True,
            alt="Dataset quality audit checks and pass/fail status",
        )
