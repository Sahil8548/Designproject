#!/usr/bin/env python3
"""Repair and multi-seed evaluation stage for the UniTime timetable prototype."""
from pathlib import Path
import json, time, random
import pandas as pd
import numpy as np
import joblib

import os

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("UNITIME_ROOT", SCRIPT_DIR.parent))
DATA = ROOT / "unitime_cleaned"
VAL = ROOT / "unitime_validation_stage"
OUT = Path(os.environ.get("UNITIME_OUT", SCRIPT_DIR))
OUT.mkdir(exist_ok=True)

def days(mask):
    return [i for i,c in enumerate(str(mask).split(".")[0].zfill(7)[-7:]) if c=="1"]

def overlap(a,b):
    return bool(set(days(a["days_mask"])) & set(days(b["days_mask"]))) and \
        int(a["start_slot"]) < int(b["start_slot"])+int(b["length_slots"]) and \
        int(b["start_slot"]) < int(a["start_slot"])+int(a["length_slots"])

def main():
    t0=time.time()
    classes=pd.read_csv(DATA/"classes.csv").fillna({"classLimit":0})
    rooms=pd.read_csv(DATA/"rooms.csv")
    room_opts=pd.read_csv(DATA/"candidate_room_options.csv")
    time_opts=pd.read_csv(DATA/"candidate_time_options.csv")
    instructors=pd.read_csv(DATA/"class_instructors.csv")
    features=pd.read_csv(VAL/"candidate_placement_features.csv")
    model=joblib.load(OUT/"reference_placement_ranker.joblib")
    cats=["department_id","subpart_id","days_mask"]
    nums=[
        "start_minutes","duration_minutes","break_time","class_limit","room_capacity",
        "capacity_surplus","capacity_ratio","room_preference","time_preference",
        "room_is_discouraged","instructor_count","group_constraint_count",
        "group_type_count_BTB","group_type_count_BTB_TIME","group_type_count_CAN_SHARE_ROOM",
        "group_type_count_DIFF_TIME","group_type_count_MEET_WITH","group_type_count_NHB(1.5)",
        "group_type_count_NHB_GTE(1)","group_type_count_SAME_DAYS","group_type_count_SAME_INSTR",
        "group_type_count_SAME_ROOM","group_type_count_SAME_START","group_type_count_SAME_STUDENTS",
        "group_type_count_SAME_TIME","group_type_count_SPREAD"
    ]
    X=features[cats+nums]
    features["ml_score"]=model.predict_proba(X)[:,1]
    features["base_cost"]=features["room_preference"].fillna(0)+features["time_preference"].fillna(0)
    # Roomless classes get candidates from time options; classes with a room option
    # use joined room-time features.
    class_df=classes.set_index("id")
    instr_map=instructors.groupby("class_id")["instructor_id"].apply(lambda x:set(map(int,x))).to_dict()
    room_map={int(k):g for k,g in room_opts.groupby("class_id")}
    time_map={int(k):g for k,g in time_opts.groupby("class_id")}
    f_map={int(k):g for k,g in features.groupby("class_id",sort=False)}
    candidates={}
    for cid in class_df.index.astype(int):
        opts=[]
        rg=room_map.get(cid)
        tg=time_map.get(cid)
        if tg is None or tg.empty:
            candidates[cid]=[]; continue
        if rg is None or rg.empty:
            for r in tg.itertuples(index=False):
                opts.append({"class_id":cid,"room_id":None,"days_mask":str(r.days).zfill(7),
                    "start_slot":int(r.start_slot),"length_slots":int(r.length_slots),
                    "room_preference":0.0,"time_preference":float(r.preference or 0),
                    "base_cost":float(r.preference or 0),"ml_score":0.0})
        else:
            for r in f_map.get(cid,pd.DataFrame()).itertuples(index=False):
                opts.append({"class_id":cid,"room_id":int(r.room_id),"days_mask":str(r.days_mask).zfill(7),
                    "start_slot":int(r.start_slot),"length_slots":int(r.length_slots),
                    "room_preference":float(r.room_preference or 0),"time_preference":float(r.time_preference or 0),
                    "base_cost":float(r.base_cost),"ml_score":float(r.ml_score)})
        candidates[cid]=opts

    def blockers(cid,opt,assigned):
        bad=[]
        for other, a in assigned.items():
            if not overlap(opt,a): continue
            same_room=opt["room_id"] is not None and a["room_id"] is not None and int(opt["room_id"])==int(a["room_id"])
            same_instr=bool(instr_map.get(cid,set()) & instr_map.get(other,set()))
            if same_room or same_instr: bad.append(other)
        return bad

    def score(opt, mode):
        # Keep preference costs primary; model is a mild ranking bonus in ML mode.
        return float(opt["base_cost"]) - (0.25*float(opt["ml_score"]) if mode=="ml" else 0.0)

    def build(seed,mode):
        rng=random.Random(seed)
        # Use previous ML/baseline schedule as seed for its mode, then attempt repair.
        file=OUT/f"timetable_{mode}.csv"
        initial=pd.read_csv(file)
        assigned={}
        for r in initial.to_dict("records"):
            cid=int(r["class_id"])
            if pd.isna(r["room_id"]): room=None
            else: room=int(r["room_id"])
            assigned[cid]={"class_id":cid,"room_id":room,"days_mask":str(r["days_mask"]).zfill(7),
                           "start_slot":int(r["start_slot"]),"length_slots":int(r["length_slots"]),
                           "room_preference":float(r.get("room_preference",0) or 0),
                           "time_preference":float(r.get("time_preference",0) or 0),
                           "base_cost":float(r.get("preference_cost",0) or 0),
                           "ml_score":float(r.get("ml_score",0) or 0)}
        missing=[int(c) for c in class_df.index if int(c) not in assigned]
        # Prioritize the most constrained missing classes, then randomized tie break.
        missing.sort(key=lambda c:(len(candidates.get(c,[])),rng.random()))
        repair_success=[]
        for cid in missing:
            opts=sorted(candidates.get(cid,[]),key=lambda o:(score(o,mode),rng.random()))
            placed=False
            # First try direct insertion.
            for opt in opts:
                if not blockers(cid,opt,assigned):
                    assigned[cid]=opt; repair_success.append(cid); placed=True; break
            if placed: continue
            # One-level ejection repair: displace at most two conflicts, then re-place them.
            for opt in opts[:120]:
                bad=blockers(cid,opt,assigned)
                if not bad or len(bad)>2: continue
                saved={b:assigned.pop(b) for b in bad}
                if blockers(cid,opt,assigned):
                    assigned.update(saved); continue
                assigned[cid]=opt
                okay=True
                for b in sorted(bad,key=lambda x:len(candidates.get(x,[]))):
                    alt=sorted(candidates.get(b,[]),key=lambda o:(score(o,mode),rng.random()))
                    found=None
                    for a in alt[:160]:
                        if not blockers(b,a,assigned):
                            found=a; break
                    if found is None:
                        okay=False; break
                    assigned[b]=found
                if okay:
                    repair_success.append(cid); placed=True; break
                assigned.pop(cid,None)
                for b in bad: assigned.pop(b,None)
                assigned.update(saved)
            # if not placed, leave class unassigned
        # Validate independently with pairwise check
        room_conf=instr_conf=0
        ids=list(assigned)
        for i,c1 in enumerate(ids):
            for c2 in ids[i+1:]:
                a,b=assigned[c1],assigned[c2]
                if overlap(a,b):
                    if a["room_id"] is not None and b["room_id"] is not None and int(a["room_id"])==int(b["room_id"]):
                        room_conf+=1
                    if instr_map.get(c1,set()) & instr_map.get(c2,set()):
                        instr_conf+=1
        out=pd.DataFrame([{"class_id":cid,"room_id":a["room_id"],"days_mask":a["days_mask"],
            "start_slot":a["start_slot"],"length_slots":a["length_slots"],
            "start_minutes":a["start_slot"]*5,"duration_minutes":a["length_slots"]*5,
            "room_preference":a["room_preference"],"time_preference":a["time_preference"],
            "preference_cost":a["base_cost"],"ml_score":a["ml_score"]} for cid,a in assigned.items()])
        out=out.sort_values("class_id")
        out.to_csv(OUT/f"timetable_{mode}_repaired.csv",index=False)
        return {"mode":mode,"seed":seed,"scheduled_classes":len(assigned),"total_classes":len(class_df),
            "unassigned_classes":len(class_df)-len(assigned),"newly_repaired_classes":len(repair_success),
            "room_overlap_pairs":room_conf,"instructor_overlap_pairs":instr_conf,
            "preference_cost_sum":float(out.preference_cost.sum()),"output":f"timetable_{mode}_repaired.csv"}

    results=[]
    for mode in ["baseline","ml"]:
        results.append(build(2026,mode))
    # Multi-seed repeats: rerun randomized ordering of repair on each seed starting from base timetable.
    for mode in ["baseline","ml"]:
        for seed in [7,21,77]:
            results.append(build(seed,mode))
    pd.DataFrame(results).to_csv(OUT/"repair_and_seed_results.csv",index=False)
    summary={
        "stage":"repair heuristic and multi-seed checks",
        "runs":results,
        "limitations":[
            "Greedy repair tries direct insertions and one-level ejection of up to two conflicting classes.",
            "Group constraints, date exceptions, and complete student conflict semantics remain unimplemented.",
            "Multiple seeds here vary repair order only; they are not independent datasets.",
            "This is an engineering prototype, not proof of globally optimal or fully valid timetable."
        ],
        "elapsed_seconds":round(time.time()-t0,2)
    }
    (OUT/"repair_stage_summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
