"""Independent constraint validation engine for university timetables."""
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

from unitime_app.data_loader import (
    load_classes, load_rooms, load_room_options, load_time_options,
    load_instructors, load_student_offerings, load_group_constraints
)
from unitime_app.scheduler import day_indices, times_overlap


def validate_timetable(timetable_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Independently validate a timetable against hard and soft constraints.
    Returns comprehensive metrics and detailed conflict records.
    """
    classes = load_classes()
    rooms = load_rooms()
    instructors = load_instructors()
    room_opts = load_room_options()
    time_opts = load_time_options()
    so = load_student_offerings()

    total_classes = len(classes)
    cls_limit_map = classes.set_index("id")["classLimit"].fillna(0).to_dict()
    room_cap_map = rooms.set_index("id")["capacity"].to_dict()
    instr_map = instructors.groupby("class_id")["instructor_id"].apply(lambda s: set(map(str, s))).to_dict()

    # Pre-index student offerings for shared-student overlap calculation
    offering_students = so.groupby("offering_id")["student_id"].apply(lambda s: set(map(int, s))).to_dict()
    class_offering = {int(r.id): int(r.offering) if pd.notna(r.offering) else -1 for r in classes.itertuples()}
    offering_ids = sorted(set(v for v in class_offering.values() if v >= 0))
    offering_sets = {oid: offering_students.get(oid, set()) for oid in offering_ids}

    student_offers: Dict[int, List[int]] = {}
    for oid, studs in offering_sets.items():
        for stu in studs:
            student_offers.setdefault(stu, []).append(oid)

    pair_counts = Counter()
    for stu, oids in student_offers.items():
        unique = sorted(set(oids))
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair_counts[(unique[i], unique[j])] += 1

    shared_student_counts: Dict[Tuple[int, int], int] = {}
    for (o1, o2), n in pair_counts.items():
        shared_student_counts[(o1, o2)] = n
        shared_student_counts[(o2, o1)] = n

    def _safe_int(val, default=None):
        try:
            if pd.isna(val) or val is None or str(val).strip() == "":
                return default
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return default

    def _safe_mask(val):
        s = str(val).split(".")[0].strip()
        return s.zfill(7)[-7:] if s else "0000000"

    # Extract rows as dictionaries and filter valid placements
    assigned_records = []
    scheduled_class_ids = set()

    for r in timetable_df.to_dict("records"):
        cid = _safe_int(r.get("class_id"))
        if cid is None:
            continue
        # A valid scheduled class must have days_mask, start_slot, and length_slots
        s_slot = _safe_int(r.get("start_slot"))
        l_slot = _safe_int(r.get("length_slots"))
        if s_slot is not None and l_slot is not None and l_slot > 0:
            scheduled_class_ids.add(cid)
            assigned_records.append({
                "class_id": cid,
                "room_id": _safe_int(r.get("room_id")),
                "days_mask": _safe_mask(r.get("days_mask")),
                "start_slot": s_slot,
                "length_slots": l_slot,
            })

    all_class_ids = set(classes["id"].astype(int))
    unassigned_ids = sorted(list(all_class_ids - scheduled_class_ids))

    room_overlap_conflicts: List[Dict[str, Any]] = []
    instr_overlap_conflicts: List[Dict[str, Any]] = []
    student_overlap_conflicts: List[Dict[str, Any]] = []
    room_capacity_issues: List[Dict[str, Any]] = []

    # 1. Check capacity deficits
    for r in assigned_records:
        cid = r["class_id"]
        rid = r.get("room_id")
        limit = cls_limit_map.get(cid, 0)
        if rid is not None:
            cap = room_cap_map.get(rid, 0)
            if cap < limit:
                room_capacity_issues.append({
                    "class_id": cid,
                    "room_id": rid,
                    "class_limit": limit,
                    "room_capacity": cap,
                    "deficit": limit - cap
                })

    # 2. Check pairwise overlaps
    n = len(assigned_records)
    for i in range(n):
        r1 = assigned_records[i]
        c1 = r1["class_id"]
        d1 = r1["days_mask"]
        s1 = r1["start_slot"]
        l1 = r1["length_slots"]
        room1 = r1["room_id"]

        for j in range(i + 1, n):
            r2 = assigned_records[j]
            c2 = r2["class_id"]
            d2 = r2["days_mask"]
            s2 = r2["start_slot"]
            l2 = r2["length_slots"]
            room2 = r2["room_id"]

            if not times_overlap(d1, s1, l1, d2, s2, l2):
                continue

            # Room overlap check
            if room1 is not None and room2 is not None and room1 == room2:
                room_overlap_conflicts.append({
                    "class_1": c1,
                    "class_2": c2,
                    "room_id": room1,
                    "days_1": d1,
                    "days_2": d2,
                    "start_slot_1": s1,
                    "start_slot_2": s2,
                    "length_slots_1": l1,
                    "length_slots_2": l2
                })

            # Instructor overlap check
            shared_instr = instr_map.get(c1, set()) & instr_map.get(c2, set())
            if shared_instr:
                instr_overlap_conflicts.append({
                    "class_1": c1,
                    "class_2": c2,
                    "instructor_ids": sorted(list(shared_instr)),
                    "days_1": d1,
                    "days_2": d2,
                    "start_slot_1": s1,
                    "start_slot_2": s2
                })

            # Student overlap proxy
            o1 = class_offering.get(c1, -1)
            o2 = class_offering.get(c2, -1)
            if o1 >= 0 and o2 >= 0:
                shared_count = 1 if o1 == o2 else shared_student_counts.get((o1, o2), 0)
                if shared_count > 0:
                    student_overlap_conflicts.append({
                        "class_1": c1,
                        "class_2": c2,
                        "offering_1": o1,
                        "offering_2": o2,
                        "estimated_students": shared_count
                    })

    # Summary metrics
    return {
        "scheduled_classes": len(scheduled_class_ids),
        "total_classes": total_classes,
        "unassigned_classes_count": len(unassigned_ids),
        "unassigned_class_ids": unassigned_ids,
        "room_overlap_pairs_count": len(room_overlap_conflicts),
        "room_overlap_pairs": room_overlap_conflicts,
        "instructor_overlap_pairs_count": len(instr_overlap_conflicts),
        "instructor_overlap_pairs": instr_overlap_conflicts,
        "room_capacity_issues_count": len(room_capacity_issues),
        "room_capacity_issues": room_capacity_issues,
        "student_overlap_proxy_count": len(student_overlap_conflicts),
        "student_overlap_conflicts": student_overlap_conflicts,
        "constraint_enforcement_status": {
            "weekly_room_overlap": "Enforced (Hard)",
            "instructor_overlap": "Enforced (Hard)",
            "room_and_time_preferences": "Enforced (Soft Objective)",
            "shared_student_conflicts": "Approximated (Soft Penalty Proxy)",
            "date_pattern_exceptions": "Pending / Unenforced",
            "group_constraints": "Pending / Unenforced (BTB, SPREAD, SAME_ROOM, etc.)",
            "multi_room_semantics": "Pending / Unenforced",
            "room_sharing_rules": "Pending / Unenforced"
        }
    }


def constraint_audit_rows(report: dict | None = None) -> list[dict]:
    """Describe enforced vs proxy vs unevaluated UniTime checks.

    Counts are taken from an independent validation report when provided.
    Missing evaluations are labeled explicitly; this never invents accuracy.
    """
    report = report or {}
    room_n = report.get("room_overlap_pairs_count")
    instr_n = report.get("instructor_overlap_pairs_count")
    student_n = report.get("student_overlap_proxy_count")
    cap_n = report.get("room_capacity_issues_count")
    unassigned_n = report.get("unassigned_classes_count")

    def count_label(value, suffix="violations"):
        if value is None:
            return "See scheduler metrics"
        return f"{value:,} {suffix}"

    return [
        {
            "Constraint": "Weekly room overlap",
            "Enforcement": "Hard constraint",
            "Audit result": count_label(room_n),
            "Notes": "Independent pairwise check of shared rooms on overlapping weekly slots.",
        },
        {
            "Constraint": "Instructor overlap",
            "Enforcement": "Hard constraint",
            "Audit result": count_label(instr_n),
            "Notes": "Independent pairwise check of shared instructors on overlapping weekly slots.",
        },
        {
            "Constraint": "Shared student conflicts",
            "Enforcement": "Soft proxy only",
            "Audit result": count_label(student_n, "overlapping pairs (proxy)"),
            "Notes": "Counts time-overlapping class pairs whose offerings share students. Not a per-student conflict count.",
        },
        {
            "Constraint": "Room capacity fit",
            "Enforcement": "Diagnostic check",
            "Audit result": count_label(cap_n, "classes under capacity"),
            "Notes": "Flags rooms smaller than the class limit; not used as a hard prune in the greedy scheduler.",
        },
        {
            "Constraint": "Unassigned classes",
            "Enforcement": "Reported",
            "Audit result": count_label(unassigned_n, "unplaced"),
            "Notes": "Classes with no feasible room/time under hard room and instructor checks.",
        },
        {
            "Constraint": "Date pattern exceptions",
            "Enforcement": "Pending / not evaluated",
            "Audit result": "Not evaluated",
            "Notes": "Semester date bitsets and mid-term exceptions are not applied.",
        },
        {
            "Constraint": "Group constraints",
            "Enforcement": "Pending / not evaluated",
            "Audit result": "Not evaluated",
            "Notes": "BTB, SPREAD, SAME_ROOM, SAME_TIME, and related group constraints are cataloged but unenforced.",
        },
        {
            "Constraint": "Multi-room and sharing rules",
            "Enforcement": "Pending / not evaluated",
            "Audit result": "Not evaluated",
            "Notes": "UniTime multi-room classes and room-sharing rules are not modeled.",
        },
    ]
