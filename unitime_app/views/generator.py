"""Generate Timetable: run baseline or ML-guided scheduling with real-time progress."""
import streamlit as st

from unitime_app.scheduler import run_scheduler
from unitime_app.config import GENERATED_DIR


def render():
    st.title("⚙️ Generate Timetable")
    st.markdown(
        "Run the scheduling engine on the Purdue Fall 2007 dataset. "
        "Results are computed live — never hardcoded."
    )

    # ── Configuration ───────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        mode_label = st.radio(
            "Scheduling Method",
            ["ML-Guided (Trained Model)", "Baseline (Preference Cost)"],
            help=(
                "ML-Guided ranks candidates using the Logistic Regression model; "
                "Baseline uses room/time preference penalties."
            ),
        )
        mode = "ml" if "ML-Guided" in mode_label else "baseline"

        seed = st.number_input(
            "Random Seed (tie-breaking)",
            min_value=1, max_value=999999, value=42, step=1,
        )

    with col2:
        apply_repair = st.checkbox(
            "Enable Repair Heuristic",
            value=False,
            help="Post-scheduling repair: direct insertion + 1-level ejection.",
        )
        st.caption(
            f"📁 Outputs are saved to `{GENERATED_DIR.name}/`. "
            "Original benchmarks remain untouched."
        )

    st.markdown("---")

    # ── Run button ──────────────────────────────────────────────────────
    if st.button("🚀 Generate Timetable", type="primary", width="stretch"):
        bar = st.progress(0.0)
        status = st.empty()

        def on_progress(pct, msg):
            bar.progress(pct)
            status.markdown(f"**{msg}**")

        try:
            result = run_scheduler(
                mode=mode,
                seed=int(seed),
                apply_repair=apply_repair,
                progress_callback=on_progress,
                save_run=True,
            )
            st.session_state["active_timetable"] = result["timetable_df"]
            st.session_state["active_metrics"] = result["metrics"]
            st.session_state["active_unassigned"] = result["unassigned_class_ids"]
            st.session_state["active_mode"] = mode
            st.session_state["active_seed"] = seed
            st.session_state["active_path"] = str(result["output_path"])

            bar.progress(1.0)
            status.empty()
            st.success("✅ Timetable generated successfully!")

        except Exception as e:
            st.error(f"Generation failed: {e}")
            return

    # ── Show last-run results ───────────────────────────────────────────
    if "active_metrics" in st.session_state:
        m = st.session_state["active_metrics"]
        st.subheader("Results")

        # Primary Performance Rates
        acc_pct = m.get("accuracy_rate", round((m["scheduled_classes"] / max(1, m["total_classes"])) * 100, 1))
        prec_str = m.get("precision_rate", "100.0%")
        hard_cols = m["room_overlap_pairs"] + m["instructor_overlap_pairs"]

        r_top1, r_top2 = st.columns(2)
        with r_top1:
            st.metric(
                "🎯 Accuracy Rate (Schedule Placement)",
                f"{acc_pct}%",
                delta=f"{m['scheduled_classes']} / {m['total_classes']} Classes",
                help="Proportion of all requested classes placed successfully in the generated timetable."
            )
        with r_top2:
            st.metric(
                "🛡️ Precision Rate (Constraint Compliance)",
                prec_str if isinstance(prec_str, str) and "%" in prec_str else f"{prec_str}%",
                delta="Zero Collisions" if hard_cols == 0 else f"{hard_cols} Collisions",
                delta_color="normal" if hard_cols == 0 else "inverse",
                help="Proportion of scheduled placements verified conflict-free without room or instructor overlaps."
            )

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Scheduled", f"{m['scheduled_classes']} / {m['total_classes']}")
        r2.metric("Unassigned", f"{m['unassigned_classes']}")
        r3.metric("Room Overlaps", f"{m['room_overlap_pairs']}")
        r4.metric("Instructor Overlaps", f"{m['instructor_overlap_pairs']}")

        r5, r6, r7, r8 = st.columns(4)
        r5.metric("Student Conflict Proxy", f"{m['shared_student_overlap_pairs_proxy']:,}")
        r6.metric("Preference Cost", f"{m['preference_cost_sum']:,.1f}")
        r7.metric("Runtime", f"{m['runtime_seconds']}s")
        if m.get("repaired"):
            r8.metric(
                "Placed by repair",
                f"{m.get('newly_repaired_classes', 0)}",
                help="Classes the greedy pass left unassigned that the repair heuristic then placed.",
            )

        if m["unassigned_classes"] > 0:
            st.warning(
                f"{m['unassigned_classes']} classes could not be placed without "
                "violating hard room or instructor constraints."
            )
            with st.expander("View Unassigned Class IDs"):
                st.write(st.session_state.get("active_unassigned", []))

        st.info("👉 Go to **View Timetable** to explore the schedule, or **Compare Results** to evaluate.")
