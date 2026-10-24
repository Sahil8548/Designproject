"""Path and environment configuration for the UniTime application."""
import os
from pathlib import Path

# Workspace base directories
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

# Dataset and model directories inside handoff folder
HANDOFF_DIR = PROJECT_ROOT / "unitime_next_stage_and_antigravity_handoff"
DATA_DIR = Path(os.environ.get("UNITIME_DATA_DIR", HANDOFF_DIR / "unitime_cleaned"))
VAL_DIR = Path(os.environ.get("UNITIME_VAL_DIR", HANDOFF_DIR / "unitime_validation_stage"))
MODEL_DIR = Path(os.environ.get("UNITIME_MODEL_DIR", HANDOFF_DIR / "unitime_model_scheduler"))

# Separate output directory for newly generated runs (preserves historical files)
GENERATED_DIR = Path(os.environ.get("UNITIME_GEN_DIR", PROJECT_ROOT / "generated_outputs"))
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# Key file paths
FEATURE_FILE = VAL_DIR / "candidate_placement_features.csv"
MODEL_FILE = MODEL_DIR / "reference_placement_ranker.joblib"
MODEL_EVAL_FILE = MODEL_DIR / "model_evaluation.json"
SCHEDULER_EVAL_FILE = MODEL_DIR / "scheduler_evaluation.json"
SCHEDULER_COMP_FILE = MODEL_DIR / "scheduler_comparison.csv"
REPAIR_SUMMARY_FILE = MODEL_DIR / "repair_stage_summary.json"

HISTORICAL_TIMETABLES = {
    "Baseline (Greedy)": MODEL_DIR / "timetable_baseline.csv",
    "ML-Guided (Greedy)": MODEL_DIR / "timetable_ml.csv",
    "Baseline (Repaired)": MODEL_DIR / "timetable_baseline_repaired.csv",
    "ML-Guided (Repaired)": MODEL_DIR / "timetable_ml_repaired.csv",
}

# Day bit-mask labels (UniTime 7-character bit pattern: Mon -> Sun)
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def decode_days_mask(mask: str | int) -> str:
    """Convert bit mask like '1010100' to human-readable 'Mon, Wed, Fri'."""
    s = str(mask).split(".")[0].zfill(7)[-7:]
    active = [DAY_NAMES[i] for i, ch in enumerate(s) if ch == "1"]
    return ", ".join(active) if active else "None"

def slot_to_time_str(slot: int) -> str:
    """Convert 5-minute slot index to HH:MM format."""
    total_minutes = int(slot) * 5
    hours = (total_minutes // 60) % 24
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"
