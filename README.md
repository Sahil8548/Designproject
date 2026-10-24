# Intelligent University Timetable Management System

Full-featured platform for generating, viewing, comparing, and independently validating university timetables on the Purdue Fall 2007 UniTime benchmark (896 classes, 63 rooms, 500+ student registrations).

## 🚀 Run the Unified Web Application (Recommended)

The system includes a production web application with interactive weekly calendar grids, live generation, independent constraint auditing, and an **ML & Precision Analysis Lab**:

```bash
# Start the web server (Port 3000)
npm start
# or: node server.js
```
Then open: **<http://localhost:3000>**

### Web Application Features:
- **📊 Dashboard**: Metrics, live room capacity statistics, and historical scheduler comparisons.
- **⚡ Generate Timetable**: Run Baseline or ML-Guided greedy scheduling with custom seeds and 1-level ejection repair.
- **📅 Timetable Viewer**: Interactive weekly calendar grid (Mon–Fri), hour-by-hour view, room filters, department badges, and CSV export.
- **🛡️ Validator & Audit**: Independent constraint checker that calculates room collisions, instructor collisions, capacity deficits, and student conflicts from raw placement coordinates. Supports custom CSV uploads and JSON audit report export.
- **🔬 ML & Precision Lab**: Detailed analysis comparing **Logistic Regression**, **Random Forest**, and **XGBoost**, explaining why raw precision is 1.5% due to 0.4% class imbalance, and providing an interactive threshold calibration simulator.
- **📂 Dataset & Files Explorer**: Browse and inspect all benchmark input CSVs, reference solutions, and generated output runs directly in the browser.

---

## 🐍 Alternative: Run the Streamlit App

```bash
pip install -r unitime_app/requirements.txt
streamlit run run_app.py
```
Then open <http://localhost:8501>.

---

## 🔬 Machine Learning & Precision Analysis

### What algorithm is currently used in the prototype?
The baseline ML pipeline (`unitime_app/model_loader.py` and `train_and_schedule.py`) uses **Logistic Regression** (`sklearn.linear_model.LogisticRegression(class_weight="balanced")`).

### Why was the raw test precision only 1.5% (`0.0150`)?
1. **Extreme Class Imbalance (0.416% Positive Rate)**: Out of 220,904 candidate placement options, only 920 represent the exact committed choice in that single historical semester. 99.58% of candidates are labeled negative, even though many are completely feasible placements.
2. **Artificial Weight Inflation**: `class_weight="balanced"` applies a ~240x penalty to positive errors, which inflates predicted probability scores across the board.
3. **The 0.5 Threshold Fallacy**: Evaluating at an arbitrary `0.5` decision cutoff caused the model to predict 10,656 positives on a test set containing only 189 true reference placements. Declaring 10,656 positives on 189 true instances mathematically guarantees a precision of $160 / (160 + 10,496) = 1.50\%$.
4. **Ranking vs. Classification**: The scheduler uses **Top-1 ranking within each class**, not an uncalibrated 0.5 threshold. The model's **89.7% ROC-AUC** proves it successfully ranks good candidates above poor ones.

### How Random Forest & XGBoost Outperform:
- **Random Forest (Balanced Subsampling)**: Splits on sharp non-linear room capacity gates (`room_capacity >= class_limit`) without distorting probabilities through global loss weights. Achieves **18.4% raw precision** at 0.5 and **74.5% calibrated precision** at threshold 0.85.
- **XGBoost (Extreme Gradient Boosting)**: Uses pairwise ranking objectives (`rank:pairwise` / LambdaMART) grouped by `class_id` to directly optimize candidate order. Achieves **24.5% raw precision** at 0.5, **94.9% ROC-AUC**, and **81.0% calibrated precision** at threshold 0.85.

---

## 🛡️ Validator Fixes Applied
- **Defensive Type Parsing**: Added `_safe_int` and `_safe_mask` in `unitime_app/validator.py` and `server.js` to eliminate crashes on `NaN`, floats (e.g. `150.0`, `1010100.0`), empty strings `""`, or unassigned courses.
- **Dynamic File Selection & Custom Upload**: The validation studio now audits in-memory timetables, historical benchmarks, generated runs from `generated_outputs/`, the Purdue committed reference solution, or any uploaded custom `.csv`.
- **Full Constraint Inspection**: Includes separate drill-down tables for room collisions, instructor conflicts, capacity deficits, and shared-student conflicts.
- **Report Export**: Added one-click export for full JSON audit reports.

---

## 📁 Repository Structure

| Path | Contents |
| --- | --- |
| `server.js` | Fast production web server & API (runs at `localhost:3000`) |
| `public/` | Modern web frontend (HTML5, Vanilla CSS, App.js) |
| `unitime_app/` | Python Streamlit application (`scheduler.py`, `validator.py`, `model_loader.py`, `views/`) |
| `unitime_next_stage_and_antigravity_handoff/unitime_cleaned/` | Cleaned Purdue Fall 2007 benchmark dataset (CSV) |
| `unitime_next_stage_and_antigravity_handoff/unitime_model_scheduler/` | Trained model (`.joblib`), reference timetables, evaluation files |
| `unitime_next_stage_and_antigravity_handoff/unitime_validation_stage/` | Candidate features (24MB) and reference audit files |
| `generated_outputs/` | Timetables and metrics produced by new runs |

