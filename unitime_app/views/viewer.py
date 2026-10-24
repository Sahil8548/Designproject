"""View Timetable: weekly calendar grid, filters, search, and CSV export."""
import pandas as pd
import streamlit as st

from unitime_app.config import DAY_NAMES, HISTORICAL_TIMETABLES, decode_days_mask, slot_to_time_str
from unitime_app.data_loader import load_classes


def load_selected_timetable(source_key: str) -> pd.DataFrame:
    """Load timetable from session state or historical disk files."""
    if source_key == "Currently Generated Schedule" and "active_timetable" in st.session_state:
        return st.session_state["active_timetable"].copy()
    file_path = HISTORICAL_TIMETABLES.get(source_key)
    if file_path and file_path.exists():
        return pd.read_csv(file_path)
    return pd.DataFrame()


def _load_selected_timetable(source_key: str) -> pd.DataFrame:
    return load_selected_timetable(source_key)


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add human-readable columns if missing."""
    if "days_human" not in df.columns and "days_mask" in df.columns:
        df["days_human"] = df["days_mask"].apply(decode_days_mask)
    if "start_time_str" not in df.columns and "start_slot" in df.columns:
        df["start_time_str"] = df["start_slot"].apply(slot_to_time_str)
    if "end_time_str" not in df.columns and "start_slot" in df.columns and "length_slots" in df.columns:
        df["end_time_str"] = (df["start_slot"] + df["length_slots"]).apply(slot_to_time_str)
    classes_df = load_classes().set_index("id")
    if "department" not in df.columns:
        df["department"] = df["class_id"].map(classes_df["department"]).fillna("Unknown")
    if "class_limit" not in df.columns:
        df["class_limit"] = df["class_id"].map(classes_df["classLimit"]).fillna(0)
    return df


def _expand_to_days(df: pd.DataFrame) -> pd.DataFrame:
    """Expand each row into one row per active weekday for the calendar grid.

    The UniTime dataset uses a 7-character bitmask (Mon–Sun). Classes that
    meet on multiple days appear in each column. Some classes use a long
    semester date pattern rather than a simple weekly pattern; we extract only
    the weekly day component here and note the limitation.
    """
    rows = []
    for _, r in df.iterrows():
        mask = str(r.get("days_mask", "0000000")).split(".")[0].zfill(7)[-7:]
        for i, ch in enumerate(mask):
            if ch == "1":
                rows.append({**r.to_dict(), "_day": DAY_NAMES[i]})
    if not rows:
        empty = df.iloc[0:0].copy()
        empty["_day"] = pd.Series(dtype="object")
        return empty
    return pd.DataFrame(rows)


def filter_timetable(
    df: pd.DataFrame,
    rooms=None,
    departments=None,
    days=None,
    class_query: str = "",
) -> pd.DataFrame:
    """Apply optional room, department, day, and class-id filters."""
    filtered = df.copy()
    if rooms:
        filtered = filtered[filtered["room_id"].isin(rooms)]
    if departments:
        filtered = filtered[filtered["department"].astype(str).isin(departments)]
    if days:
        filtered = filtered[filtered["days_human"].apply(
            lambda x: any(d in str(x) for d in days) if pd.notna(x) else False
        )]
    query = (class_query or "").strip()
    if query:
        # regex=False: the box is a plain substring search, so "(" or "*" must not be parsed as a pattern.
        filtered = filtered[filtered["class_id"].astype(str).str.contains(query, regex=False)]
    return filtered


def available_days(df: pd.DataFrame) -> list[str]:
    """Weekdays that occur in the timetable (always Mon-Fri; Sat/Sun only if scheduled)."""
    present = set()
    if "days_mask" in df.columns:
        for mask in df["days_mask"].dropna().unique():
            m = str(mask).split(".")[0].zfill(7)[-7:]
            present.update(DAY_NAMES[i] for i, ch in enumerate(m) if ch == "1")
    return [d for d in DAY_NAMES if d in present or d in DAY_NAMES[:5]]


def weekly_grid_records(day_df: pd.DataFrame) -> list[dict]:
    """Return calendar cells with class id, room, and scheduled times."""
    if day_df is None or day_df.empty or "_day" not in day_df.columns:
        return []
    work = day_df.copy()
    work["_start_min"] = work["start_slot"].astype(int) * 5
    work["_block"] = (work["_start_min"] // 30) * 30
    records = []
    for _, c in work.iterrows():
        rid = c.get("room_id")
        records.append({
            "day": c["_day"],
            "block": int(c["_block"]),
            "class_id": int(c["class_id"]),
            "room_id": int(rid) if pd.notna(rid) else None,
            "start_time": c.get("start_time_str", ""),
            "end_time": c.get("end_time_str", ""),
        })
    return records


_GRID_CSS = """
<style>
.tt-grid {width:100%; border-collapse:collapse; font-size:0.78rem;}
.tt-grid th {
    background:#0d2b5e; color:#fff; padding:8px 4px;
    text-align:center; position:sticky; top:0; z-index:2;
}
.tt-grid td {
    border:1px solid #dee2e6; vertical-align:top; padding:2px;
    min-width:120px; height:60px; background:#ffffff; color:#1a2332;
}
.tt-cell {
    background:#e8f0fe; border-left:3px solid #1a56db;
    border-radius:4px; padding:3px 5px; margin:1px 0;
    font-size:0.72rem; line-height:1.25; color:#1a2332;
}
.tt-cell b {color:#0d2b5e;}
.tt-time-col {
    background:#f7f9fc !important; color:#1a2332; font-weight:600; text-align:right;
    padding-right:6px; white-space:nowrap; width:90px;
}
</style>
"""


def calendar_grid_html(records: list[dict], day_columns: list) -> str:
    """Render days as columns and time slots as rows."""
    if not records:
        return ""
    blocks = sorted({int(r["block"]) for r in records})
    cells: dict[tuple, list] = {}
    for rec in records:
        cells.setdefault((rec["day"], int(rec["block"])), []).append(rec)
    html_parts = [_GRID_CSS, '<div style="overflow-x:auto;"><table class="tt-grid"><thead><tr>']
    html_parts.append('<th style="width:90px;">Time</th>')
    for d in day_columns:
        html_parts.append(f"<th>{d}</th>")
    html_parts.append("</tr></thead><tbody>")

    for block in blocks:
        h, m = divmod(int(block), 60)
        label = f"{h:02d}:{m:02d}"
        html_parts.append(f'<tr><td class="tt-time-col">{label}</td>')
        for d in day_columns:
            html_parts.append("<td>")
            for rec in cells.get((d, block), []):
                rid = rec["room_id"] if rec["room_id"] is not None else "—"
                html_parts.append(
                    f'<div class="tt-cell"><b>Class {rec["class_id"]}</b><br>'
                    f'Room {rid} · {rec["start_time"]}–{rec["end_time"]}</div>'
                )
            html_parts.append("</td>")
        html_parts.append("</tr>")

    html_parts.append("</tbody></table></div>")
    return "".join(html_parts)


def _render_calendar_grid(day_df: pd.DataFrame, day_columns: list):
    """Render an HTML table that resembles a weekly timetable grid."""
    records = weekly_grid_records(day_df)
    if not records:
        st.info("No classes to display with the current filters.", icon=":material/info:")
        return
    html = calendar_grid_html(records, day_columns)
    st.html(html)


def render():
    st.title("View timetable")

    sources = []
    if "active_timetable" in st.session_state:
        sources.append("Currently Generated Schedule")
    sources.extend(list(HISTORICAL_TIMETABLES.keys()))

    source_choice = st.selectbox("Select timetable", sources, index=0)
    df = load_selected_timetable(source_choice)

    if df.empty:
        st.warning(
            "No timetable data found. Go to **Generate timetable** to create one, "
            "or select a historical schedule above."
        )
        return

    df = _enrich(df)

    with st.container():
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            all_rooms = sorted([int(r) for r in df["room_id"].dropna().unique()])
            sel_rooms = st.multiselect("Filter by room", all_rooms)
        with f2:
            all_depts = sorted([str(d) for d in df["department"].dropna().unique()])
            sel_depts = st.multiselect("Filter by department", all_depts)
        with f3:
            day_opts = available_days(df)
            sel_days = st.pills("Filter by day", day_opts, selection_mode="multi")
        with f4:
            search = st.text_input("Search class ID")

    filtered = filter_timetable(
        df,
        rooms=sel_rooms,
        departments=sel_depts,
        days=sel_days,
        class_query=search,
    )

    st.markdown(f"**Showing {len(filtered):,} of {len(df):,} scheduled assignments**")

    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"{source_choice.lower().replace(' ', '_')}_export.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )

    view_mode = st.segmented_control(
        "Display",
        ["Weekly calendar grid", "Data table"],
        default="Weekly calendar grid",
    ) or "Weekly calendar grid"

    if view_mode == "Weekly calendar grid":
        day_df = _expand_to_days(filtered)
        if day_df.empty or "_day" not in day_df.columns:
            st.info("No classes to display with the current filters.", icon=":material/info:")
            return
        active_days = sorted(day_df["_day"].unique(), key=lambda d: DAY_NAMES.index(d))
        if not active_days:
            active_days = ["Mon", "Tue", "Wed", "Thu", "Fri"]

        st.caption(
            "The calendar shows the weekly day component of each class. "
            "Some classes use semester date patterns with mid-term exceptions; "
            "those details are not reflected in this weekly view."
        )
        _render_calendar_grid(day_df, active_days)
    else:
        display_cols = [
            "class_id", "department", "room_id", "days_human", "start_time_str",
            "end_time_str", "duration_minutes", "class_limit", "room_capacity",
            "preference_cost", "ml_score",
        ]
        actual_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(
            filtered[actual_cols],
            column_config={
                "class_id": st.column_config.NumberColumn("Class ID", format="%d"),
                "department": st.column_config.TextColumn("Dept"),
                "room_id": st.column_config.NumberColumn("Room", format="%d"),
                "days_human": st.column_config.TextColumn("Days"),
                "start_time_str": st.column_config.TextColumn("Start"),
                "end_time_str": st.column_config.TextColumn("End"),
                "duration_minutes": st.column_config.NumberColumn("Dur (min)", format="%d"),
                "class_limit": st.column_config.NumberColumn("Limit", format="%d"),
                "room_capacity": st.column_config.NumberColumn("Room Cap", format="%d"),
                "preference_cost": st.column_config.NumberColumn("Pref Cost", format="%.1f"),
                "ml_score": st.column_config.NumberColumn("ML Score", format="%.4f"),
            },
            hide_index=True,
            alt="Filtered timetable assignments with class, room, and time columns",
        )
