#!/usr/bin/env python3
"""
Train a reference-placement ranking model and generate two timetables:
1) non-ML greedy baseline
2) ML-ranked greedy scheduler

This is a prototype, not a full UniTime-equivalent solver.
Hard constraints enforced in the scheduler: weekly room overlap and instructor overlap.
Shared-student conflicts are included as a soft ranking penalty where derivable.
Group constraints, date exceptions, all room-sharing semantics, and multi-room
classes are not fully enforced. Outputs report these limitations.
"""
from pathlib import Path
import json, time, warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (precision_score, recall_score, f1_score, roc_auc_score,
                             average_precision_score, confusion_matrix, classification_report)

import os

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("UNITIME_ROOT", SCRIPT_DIR.parent))
DATA = ROOT / "unitime_cleaned"
FEATURE_FILE = ROOT / "unitime_validation_stage" / "candidate_placement_features.csv"
OUT = Path(os.environ.get("UNITIME_OUT", SCRIPT_DIR))
OUT.mkdir(exist_ok=True)

def day_indices(mask):
    # UniTime stores the weekly day pattern as a seven-character bit mask.
    s = str(mask).split(".")[0].zfill(7)[-7:]
    return [i for i, ch in enumerate(s) if ch == "1"]

def overlap(d1, s1, l1, d2, s2, l2):
    return bool(set(day_indices(d1)).intersection(day_indices(d2))) and int(s1) < int(s2)+int(l2) and int(s2) < int(s1)+int(l1)

def parse_list(value):
    if pd.isna(value) or not str(value).strip():
        return []
    return [x.strip() for x in str(value).split(";") if x.strip()]

def read_solution():
    df = pd.read_csv(DATA / "committed_solution_assignments.csv")
    rows=[]
    for _,r in df.iterrows():
        raw=r.get("selected_time_options")
        time_options=[]
        if pd.notna(raw):
            for item in str(raw).split(";"):
                parts=item.split("|")
                if len(parts)>=3:
                    try:
                        time_options.append((int(parts[0]),int(parts[1]),int(parts[2])))
                    except ValueError: pass
        room_ids=[int(x) for x in parse_list(r.get("selected_room_ids")) if x.isdigit()]
        # One row per class; if more than one time/room, retain all to expose complexity.
        rows.append({"class_id":int(r["class_id"]), "room_ids":room_ids, "time_options":time_options})
    return rows

def main():
    start_time=time.time()
    features=pd.read_csv(FEATURE_FILE)
    classes=pd.read_csv(DATA/"classes.csv")
    rooms=pd.read_csv(DATA/"rooms.csv")
    room_opts=pd.read_csv(DATA/"candidate_room_options.csv")
    time_opts=pd.read_csv(DATA/"candidate_time_options.csv")
    instructors=pd.read_csv(DATA/"class_instructors.csv")
    solution=read_solution()

    # Candidate feature rows are all valid room-option x time-option pairs within class.
    # Exclude reference-schedule-derived features to prevent target leakage.
    target_map={}
    solution_rows={}
    for s in solution:
        solution_rows[s["class_id"]]=s
        # target positive = exact room + time placement selected in committed solution
        for room in s["room_ids"]:
            for d,st,ln in s["time_options"]:
                target_map[(s["class_id"],room,str(d).zfill(7),st,ln)]=1

    features["target_selected_reference"] = [
        int(target_map.get((int(r.class_id),int(r.room_id),str(r.days_mask).zfill(7),int(r.start_slot),int(r.length_slots)),0))
        for r in features.itertuples(index=False)
    ]
    # Exclude IDs and any reference-solution-derived features. Use only assignment attributes.
    categorical=["department_id","subpart_id","days_mask"]
    numeric=[
        "start_minutes","duration_minutes","break_time","class_limit","room_capacity",
        "capacity_surplus","capacity_ratio","room_preference","time_preference",
        "room_is_discouraged","instructor_count","group_constraint_count",
        "group_type_count_BTB","group_type_count_BTB_TIME","group_type_count_CAN_SHARE_ROOM",
        "group_type_count_DIFF_TIME","group_type_count_MEET_WITH","group_type_count_NHB(1.5)",
        "group_type_count_NHB_GTE(1)","group_type_count_SAME_DAYS","group_type_count_SAME_INSTR",
        "group_type_count_SAME_ROOM","group_type_count_SAME_START","group_type_count_SAME_STUDENTS",
        "group_type_count_SAME_TIME","group_type_count_SPREAD"
    ]
    X=features[categorical+numeric].copy()
    y=features["target_selected_reference"].astype(int).values
    groups=features["class_id"].values

    # Group split by class so candidate rows from one class never cross split boundaries.
    gss=GroupShuffleSplit(n_splits=1,test_size=0.20,random_state=42)
    train_idx,test_idx=next(gss.split(X,y,groups))
    # A second group split from train into train/validation.
    gss2=GroupShuffleSplit(n_splits=1,test_size=0.1875,random_state=43)
    subtrain_rel,val_rel=next(gss2.split(X.iloc[train_idx],y[train_idx],groups[train_idx]))
    fit_idx=train_idx[subtrain_rel]; val_idx=train_idx[val_rel]

    pre=ColumnTransformer([
        ("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),
                         ("onehot",OneHotEncoder(handle_unknown="ignore"))]),categorical),
        ("num",Pipeline([("impute",SimpleImputer(strategy="median")),
                         ("scale",StandardScaler())]),numeric)
    ])
    model=Pipeline([("preprocess",pre),("model",LogisticRegression(
        max_iter=1000,class_weight="balanced",solver="liblinear",random_state=42))])
    model.fit(X.iloc[fit_idx],y[fit_idx])
    val_prob=model.predict_proba(X.iloc[val_idx])[:,1]
    # Ranking quality matters more than threshold classification for a sparse positive target.
    test_prob=model.predict_proba(X.iloc[test_idx])[:,1]
    test_pred=(test_prob>=0.5).astype(int)
    metrics={
        "target":"whether this exact class-room-time placement appears in the committed reference solution",
        "positive_definition":"exact selected room + selected time match from committed solution",
        "negative_definition":"candidate not selected in this one reference solution; not necessarily a bad placement",
        "split":"GroupShuffleSplit by class_id: train/validation/test approximately 65/15/20",
        "n_examples":int(len(features)),
        "n_positive":int(y.sum()),
        "positive_rate":float(y.mean()),
        "n_train":int(len(fit_idx)),
        "n_validation":int(len(val_idx)),
        "n_test":int(len(test_idx)),
        "test_classes":int(features.iloc[test_idx].class_id.nunique()),
        "test_precision_at_0_5":float(precision_score(y[test_idx],test_pred,zero_division=0)),
        "test_recall_at_0_5":float(recall_score(y[test_idx],test_pred,zero_division=0)),
        "test_f1_at_0_5":float(f1_score(y[test_idx],test_pred,zero_division=0)),
        "test_roc_auc":float(roc_auc_score(y[test_idx],test_prob)) if len(np.unique(y[test_idx]))>1 else None,
        "test_average_precision":float(average_precision_score(y[test_idx],test_prob)),
        "test_confusion_matrix_labels_0_1":confusion_matrix(y[test_idx],test_pred,labels=[0,1]).tolist(),
        "critical_limitations":[
            "This is a reference-placement ranking model, not a true conflict-risk model.",
            "Unselected placements are not necessarily poor; there may be many equally valid schedules.",
            "One benchmark solution does not establish cross-university generalization.",
            "Reference-derived student-overlap features are excluded to prevent leakage.",
            "The trained model ranks placements only; hard constraints are handled by scheduler code."
        ]
    }
    (OUT/"model_evaluation.json").write_text(json.dumps(metrics,indent=2))
    # Save test predictions and a compact model pipeline using joblib.
    import joblib
    joblib.dump(model,OUT/"reference_placement_ranker.joblib")
    test_out=features.iloc[test_idx][["class_id","room_id","days_mask","start_slot","length_slots","target_selected_reference"]].copy()
    test_out["predicted_reference_score"]=test_prob
    test_out.to_csv(OUT/"test_predictions.csv",index=False)

    # Build scheduling entities. To keep this prototype tractable, use top K candidates
    # by preferences for baseline and model rank for ML, while preserving diverse days/times.
    # Build candidate records from feature table.
    feature_cols=categorical+numeric
    # Predict scores in batches.
    all_scores=model.predict_proba(X)[:,1]
    features["ml_score"]=all_scores
    features["base_cost"]=features["room_preference"].fillna(0)+features["time_preference"].fillna(0)
    # Soft penalty: room preference/time preference are native data fields; keep transparent.
    # Candidate order is sorted by lower preference cost, then ML score tie-break.
    # Build instructor map and offering student sets.
    instr_map=instructors.groupby("class_id")["instructor_id"].apply(lambda s:set(map(str,s))).to_dict()
    cls_lookup=classes.set_index("id").to_dict("index")
    # student offering enrollment -> offering IDs per student; shared students inferred at offering level.
    so=pd.read_csv(DATA/"student_offerings.csv")
    offering_students=so.groupby("offering_id")["student_id"].apply(lambda s:set(map(int,s))).to_dict()
    class_offering={int(r.id):int(r.offering) if pd.notna(r.offering) else -1 for r in classes.itertuples()}
    shared_student_counts={}
    # only pairs among offerings represented by classes; compute pairwise intersections
    offering_ids=sorted(set(v for v in class_offering.values() if v>=0))
    offering_sets={oid:offering_students.get(oid,set()) for oid in offering_ids}
    # Efficient inverted index: student -> offerings
    student_offers={}
    for oid, studs in offering_sets.items():
        for stu in studs:
            student_offers.setdefault(stu,[]).append(oid)
    from collections import Counter
    pair_counts=Counter()
    for stu,oids in student_offers.items():
        unique=sorted(set(oids))
        for i in range(len(unique)):
            for j in range(i+1,len(unique)):
                pair_counts[(unique[i],unique[j])]+=1
    for (o1,o2),n in pair_counts.items():
        shared_student_counts[(o1,o2)]=n
        shared_student_counts[(o2,o1)]=n

    # A candidate is represented by room+time. For a class with no room option, we
    # allow a roomless assignment using its available time options.
    room_map={int(k):g for k,g in room_opts.groupby("class_id")}
    time_map={int(k):g for k,g in time_opts.groupby("class_id")}
    candidate_map={}
    feature_groups = {int(k): g for k, g in features.groupby("class_id", sort=False)}
    for cid in sorted(cls_lookup):
        rg=room_map.get(cid)
        tg=time_map.get(cid)
        if tg is None or tg.empty:
            candidate_map[cid]=[]
            continue
        opts=[]
        if rg is None or rg.empty:
            for t in tg.itertuples(index=False):
                opts.append({"class_id":cid,"room_id":None,"days":int(t.days),"start_slot":int(t.start_slot),
                             "length_slots":int(t.length_slots),"break_time":int(t.break_time),
                             "room_preference":0.0,"time_preference":float(t.preference),
                             "ml_score":0.0,"base_cost":float(t.preference)})
        else:
            # Candidate pairs from matching class room/time options.
            fg=feature_groups.get(cid, pd.DataFrame())
            # Avoid more than all candidates, but 220k total is manageable.
            for r in fg.itertuples(index=False):
                opts.append({"class_id":cid,"room_id":int(r.room_id),"days":int(str(r.days_mask)),
                             "start_slot":int(r.start_slot),"length_slots":int(r.length_slots),
                             "break_time":int(r.break_time),"room_preference":float(r.room_preference),
                             "time_preference":float(r.time_preference),"ml_score":float(r.ml_score),
                             "base_cost":float(r.base_cost)})
        candidate_map[cid]=opts

    # Only enforce room and instructor conflicts as hard constraints. Shared students
    # are soft costs, because a feasible zero-student-conflict timetable may be difficult
    # and the source's student-conflict semantics are approximate.
    def schedule(mode, seed=42, max_candidates=180):
        rng=np.random.default_rng(seed)
        assigned={}
        room_index={} # (room_id,day) -> assignments
        instr_index={} # (instructor_id,day) -> assignments
        unassigned=[]
        # choose most constrained classes first; tie-break by instructor count and class limit.
        cids=list(candidate_map)
        def priority(cid):
            opts=candidate_map[cid]
            return (len(opts), -len(instr_map.get(cid,set())), -float(cls_lookup[cid].get("classLimit") or 0))
        cids.sort(key=priority)
        def conflicts(opt, cid):
            room_conf=0; instr_conf=0
            for day in day_indices(opt["days"]):
                if opt["room_id"] is not None:
                    for a in room_index.get((opt["room_id"],day),[]):
                        if overlap(opt["days"],opt["start_slot"],opt["length_slots"],a["days"],a["start_slot"],a["length_slots"]):
                            room_conf+=1
                for iid in instr_map.get(cid,set()):
                    for a in instr_index.get((iid,day),[]):
                        if overlap(opt["days"],opt["start_slot"],opt["length_slots"],a["days"],a["start_slot"],a["length_slots"]):
                            instr_conf+=1
            return room_conf,instr_conf
        def shared_penalty(cid, opt):
            # Candidate-time overlap with currently assigned classes sharing students.
            offering=class_offering.get(cid,-1)
            if offering<0: return 0
            count=0
            for other_cid,a in assigned.items():
                if class_offering.get(other_cid,-1)==offering:
                    # same offering's different subparts can have different students; only
                    # apply shared-student penalty if offering-level enrollment says overlap.
                    shared=1
                else:
                    shared=shared_student_counts.get((offering,class_offering.get(other_cid,-1)),0)
                if shared and overlap(opt["days"],opt["start_slot"],opt["length_slots"],a["days"],a["start_slot"],a["length_slots"]):
                    count += min(shared,100)
            return count
        for cid in cids:
            opts=candidate_map[cid]
            if not opts:
                unassigned.append(cid); continue
            if mode=="baseline":
                ranked=sorted(opts,key=lambda o:(o["base_cost"], -min(2.0, max(0.0,(float(cls_lookup[cid].get("classLimit") or 0)-(rooms.set_index("id").loc[o["room_id"],"capacity"] if o["room_id"] is not None else 0))*0.001)), rng.random()))
            else:
                ranked=sorted(opts,key=lambda o:(-o["ml_score"],o["base_cost"],rng.random()))
            ranked=ranked[:max_candidates] if len(ranked)>max_candidates else ranked
            best=None; best_cost=None
            for opt in ranked:
                rc,ic=conflicts(opt,cid)
                if rc or ic: continue
                # Soft objective: native preferences + scaled shared-student overlap.
                cost=opt["base_cost"]+0.05*shared_penalty(cid,opt)
                # ML ranker uses predicted reference score as a preference, not as a constraint.
                if mode=="ml":
                    cost += -0.25*opt["ml_score"]
                if best is None or cost<best_cost:
                    best,best_cost=opt,cost
            if best is None:
                unassigned.append(cid)
                continue
            assigned[cid]=best
            for day in day_indices(best["days"]):
                if best["room_id"] is not None:
                    room_index.setdefault((best["room_id"],day),[]).append(best)
                for iid in instr_map.get(cid,set()):
                    instr_index.setdefault((iid,day),[]).append(best)
        # Validation metrics
        room_pairs=[]; instr_pairs=[]; student_pairs=0
        ids=list(assigned)
        for i in range(len(ids)):
            c1=ids[i]; a=assigned[c1]
            for c2 in ids[i+1:]:
                b=assigned[c2]
                if not overlap(a["days"],a["start_slot"],a["length_slots"],b["days"],b["start_slot"],b["length_slots"]):
                    continue
                if a["room_id"] is not None and a["room_id"]==b["room_id"]:
                    room_pairs.append((c1,c2))
                if instr_map.get(c1,set()) & instr_map.get(c2,set()):
                    instr_pairs.append((c1,c2))
                o1,o2=class_offering.get(c1,-1),class_offering.get(c2,-1)
                if o1>=0 and o2>=0 and (o1==o2 or shared_student_counts.get((o1,o2),0)>0):
                    student_pairs+=1
        sched=[]
        for cid,opt in assigned.items():
            sched.append({"class_id":cid,"room_id":opt["room_id"],"days_mask":str(opt["days"]).zfill(7),
                          "start_slot":opt["start_slot"],"length_slots":opt["length_slots"],
                          "start_minutes":opt["start_slot"]*5,"duration_minutes":opt["length_slots"]*5,
                          "room_preference":opt["room_preference"],"time_preference":opt["time_preference"],
                          "preference_cost":opt["base_cost"],"ml_score":opt["ml_score"]})
        sdf=pd.DataFrame(sched).sort_values("class_id")
        sdf.to_csv(OUT/f"timetable_{mode}.csv",index=False)
        return {"mode":mode,"scheduled_classes":len(assigned),"total_classes":len(cls_lookup),
                "unassigned_classes":len(unassigned),"unassigned_class_ids":unassigned,
                "room_overlap_pairs":len(room_pairs),"instructor_overlap_pairs":len(instr_pairs),
                "shared_student_overlap_pairs_proxy":int(student_pairs),
                "soft_preference_cost":float(sdf["preference_cost"].sum()) if len(sdf) else None,
                "runtime_seconds":None,"notes":"Hard constraints enforced by greedy placement are room and instructor overlaps only. Student overlap is a proxy soft penalty; group constraints/date exceptions are not enforced. Not a complete UniTime solver."}

    sched_results=[]
    for mode in ["baseline","ml"]:
        t=time.time()
        result=schedule(mode,seed=42)
        result["runtime_seconds"]=round(time.time()-t,2)
        sched_results.append(result)
    # Evaluation summary and README.
    eval_out={"dataset":"Purdue Fall 2007 LLR UniTime benchmark",
              "model_evaluation":metrics,
              "scheduler_results":sched_results,
              "interpretation":[
                  "This is a greedy prototype, not an optimal solver.",
                  "Baseline and ML-guided scheduling use the same room/instructor hard checks.",
                  "ML model target is selected-in-reference placement; unselected does not mean invalid.",
                  "No claim of full UniTime constraint satisfaction should be made.",
                  "The independent validation in this prototype covers room/instructor overlap only plus a student-overlap proxy."
              ]}
    (OUT/"scheduler_evaluation.json").write_text(json.dumps(eval_out,indent=2))
    print(json.dumps({"model_metrics":metrics,"scheduler_results":sched_results},indent=2))
    print(f"Total elapsed seconds: {time.time()-start_time:.1f}")

if __name__=="__main__":
    main()
