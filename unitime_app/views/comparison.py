"""Compare Results: side-by-side evaluation of baseline vs ML-guided scheduling."""
import streamlit as st
import pandas as pd

from unitime_app.data_loader import load_historical_evaluations


def render():
    st.title("⚖️ Compare Results")
    st.markdown(
        "Compare scheduling performance between the **Baseline** and **ML-Guided** methods. "
        "Saved benchmark runs are shown alongside your most recent run from this session, "
        "all on the Purdue Fall 2007 LLR benchmark."
    )

    eval_data = load_historical_evaluations()
    comp_df = eval_data.get("scheduler_comparison", pd.DataFrame()).copy()

    # Append current session run if available
    if "active_metrics" in st.session_state:
        am = st.session_state["active_metrics"]
        session_row = pd.DataFrame([{
            "scheduler": (
                f"{am['mode']}{' + repair' if am.get('repaired') else ''} "
                f"(this session · seed {am['seed']})"
            ),
            "classes_scheduled": am["scheduled_classes"],
            "total_classes": am["total_classes"],
            "unassigned_classes": am["unassigned_classes"],
            "room_overlap_pairs": am["room_overlap_pairs"],
            "instructor_overlap_pairs": am["instructor_overlap_pairs"],
            "shared_student_overlap_pairs_proxy": am["shared_student_overlap_pairs_proxy"],
            "preference_cost_sum": am["preference_cost_sum"],
            "runtime_seconds": am["runtime_seconds"],
        }])
        comp_df = pd.concat([comp_df, session_row], ignore_index=True)

    if comp_df.empty:
        st.info("No comparison data available yet. Generate at least one timetable first.")
        return

    # ── Comparison Table ────────────────────────────────────────────────
    st.subheader("Performance Comparison")
    st.dataframe(
        comp_df,
        column_config={
            "scheduler": st.column_config.TextColumn("Scheduler"),
            "classes_scheduled": st.column_config.NumberColumn("Scheduled", format="%d"),
            "total_classes": st.column_config.NumberColumn("Total", format="%d"),
            "unassigned_classes": st.column_config.NumberColumn("Unassigned", format="%d"),
            "room_overlap_pairs": st.column_config.NumberColumn("Room Overlaps", format="%d"),
            "instructor_overlap_pairs": st.column_config.NumberColumn("Instr. Overlaps", format="%d"),
            "shared_student_overlap_pairs_proxy": st.column_config.NumberColumn(
                "Student Overlap (proxy)", format="%d"
            ),
            "preference_cost_sum": st.column_config.NumberColumn("Pref Cost", format="%.1f"),
            "runtime_seconds": st.column_config.NumberColumn("Runtime (s)", format="%.2f"),
        },
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "**Student Overlap** is a *proxy* metric: it counts time-overlapping class pairs "
        "whose offerings share enrolled students. It is not a precise per-student conflict count."
    )

    st.markdown("---")

    # ── Charts ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Scheduled vs Unassigned")
        chart = comp_df.set_index("scheduler")[["classes_scheduled", "unassigned_classes"]]
        st.bar_chart(chart)
    with col2:
        if "runtime_seconds" in comp_df.columns:
            st.subheader("Runtime (seconds)")
            st.bar_chart(comp_df.set_index("scheduler")["runtime_seconds"])

    # ── Multi-seed repair summary ───────────────────────────────────────
    repair_summary = eval_data.get("repair_summary", {})
    if "runs" in repair_summary:
        st.subheader("Multi-Seed Repair Evaluation")
        st.markdown("Repair heuristic tested across multiple seeds to assess stability:")
        runs_df = pd.DataFrame(repair_summary["runs"])
        show_cols = [c for c in [
            "mode", "seed", "scheduled_classes", "unassigned_classes",
            "newly_repaired_classes", "preference_cost_sum",
            "room_overlap_pairs", "instructor_overlap_pairs",
        ] if c in runs_df.columns]
        st.dataframe(runs_df[show_cols], width="stretch", hide_index=True)

    # ── Honest interpretation ───────────────────────────────────────────
    st.info(
        "**Interpretation notes:**\n"
        "- Both schedulers enforce identical hard constraints (room & instructor overlap).\n"
        "- The ML model ranks candidates that resemble the reference timetable. "
        "It does *not* guarantee a globally optimal or universally better schedule.\n"
        "- Results may vary across seeds."
    )
