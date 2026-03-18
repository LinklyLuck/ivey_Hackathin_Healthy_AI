"""
Southlake Medical AI Agent — Data I/O
"""
import json
import os
import csv
import pandas as pd
from datetime import datetime


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


# ─── CSV helpers ───

def load_csv(filename: str) -> pd.DataFrame:
    """Load a CSV file from the data directory."""
    p = _path(filename)
    if not os.path.exists(p):
        return pd.DataFrame()
    return pd.read_csv(p)


def save_csv(filename: str, df: pd.DataFrame):
    """Save a DataFrame to the data directory."""
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(_path(filename), index=False)


def append_row_csv(filename: str, row: dict):
    """Append a single row to a CSV file."""
    p = _path(filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ─── JSON helpers (for session-level temp data) ───

def load_json(path: str, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Convenience loaders ───

def load_patient_records() -> pd.DataFrame:
    """Load the main 3000-record patient dataset."""
    return load_csv("patient_records.csv")

def load_patients() -> pd.DataFrame:
    return load_csv("patients.csv")

def load_cases() -> pd.DataFrame:
    return load_csv("cases.csv")

def load_discharge_summaries() -> pd.DataFrame:
    return load_csv("discharge_summaries.csv")

def load_followup_results() -> pd.DataFrame:
    return load_csv("followup_results.csv")

def load_doctor_queue() -> pd.DataFrame:
    return load_csv("doctor_queue.csv")

def get_next_id(prefix: str, filename: str, id_col: str) -> str:
    """Generate next sequential ID like P013, CASE013, etc."""
    df = load_csv(filename)
    if df.empty:
        return f"{prefix}001"
    last_num = df[id_col].str.extract(r'(\d+)').astype(int).max().values[0]
    return f"{prefix}{last_num + 1:03d}"

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── Synthetic Data Run History ───
import json as _json

RUNS_DIR = os.path.join(DATA_DIR, "runs")


def save_generation_run(run_id: str, df: pd.DataFrame, contract: dict, trace: list, audits: dict):
    """Save a complete generation run for history and comparison."""
    os.makedirs(RUNS_DIR, exist_ok=True)
    run_path = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_path, exist_ok=True)
    df.to_csv(os.path.join(run_path, "data.csv"), index=False)
    with open(os.path.join(run_path, "meta.json"), "w") as f:
        _json.dump({"run_id": run_id, "contract": contract, "trace": trace, "audits": audits,
                     "records": len(df), "created_at": now_str()}, f, default=str, indent=2)


def load_generation_history() -> list[dict]:
    """List all past generation runs."""
    if not os.path.exists(RUNS_DIR):
        return []
    runs = []
    for d in sorted(os.listdir(RUNS_DIR), reverse=True):
        meta_path = os.path.join(RUNS_DIR, d, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                runs.append(_json.load(f))
    return runs


def load_run_data(run_id: str) -> pd.DataFrame:
    """Load generated CSV from a past run."""
    p = os.path.join(RUNS_DIR, run_id, "data.csv")
    if os.path.exists(p):
        return pd.read_csv(p)
    return pd.DataFrame()
