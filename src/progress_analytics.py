"""SCRUM-21: Pandas-based workout progress analytics, PRs, and Plank progression.

Decoupled from FastAPI/UI for deterministic unit testing.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
import pandas as pd


PLANK_KEYWORDS = ("plank", "side_plank", "forearm plank")


def _is_plank_exercise(exercise_id: str, exercise_name: str) -> bool:
    combined = f"{exercise_id} {exercise_name}".lower()
    return any(k in combined for k in PLANK_KEYWORDS)


def _format_duration(seconds: int) -> str:
    sec = max(0, int(seconds))
    mins, rem = divmod(sec, 60)
    if mins > 0:
        return f"{mins}p {rem}s"
    return f"{rem}s"


def _get_series(df: pd.DataFrame, col: str, default: Any) -> pd.Series:
    """Safely extract a column as a Pandas Series even if the column is missing."""
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


def _count_unique_sessions(df: pd.DataFrame) -> int:
    """Count unique workout sessions.

    If records include a non-empty `session_id`, exercises sharing the same
    `session_id` are counted as a single session. Records without `session_id`
    fall back to their own record `id` (or row index).
    """
    if df.empty:
        return 0

    session_ids = _get_series(df, "session_id", "").fillna("").astype(str).str.strip()
    record_ids = _get_series(df, "id", "").fillna("").astype(str).str.strip()

    effective_keys = []
    for idx in df.index:
        sid = session_ids.loc[idx]
        if sid:
            effective_keys.append(f"session:{sid}")
        else:
            rid = record_ids.loc[idx]
            effective_keys.append(f"record:{rid}" if rid else f"row:{idx}")

    return len(set(effective_keys))


def compute_personal_records(
    history: list[dict[str, Any]],
    reference_date: date | None = None,
) -> dict[str, str]:
    """Compute genuine Personal Records (PRs) from valid, non-future workout history."""
    default_prs = {
        "Squat Thể dục": "Chưa ghi nhận",
        "Standard Push-up": "Chưa ghi nhận",
        "Plank Tĩnh": "Chưa ghi nhận",
        "Dips trên ghế": "Chưa ghi nhận",
    }
    if not history:
        return default_prs

    today = reference_date or date.today()
    df = pd.DataFrame(history)
    if df.empty:
        return default_prs

    # Only include records with valid dates <= today
    parsed_ts = pd.to_datetime(_get_series(df, "actual_date", None), errors="coerce")
    df = df[parsed_ts.notna()].copy()
    if df.empty:
        return default_prs

    df["parsed_date"] = parsed_ts[parsed_ts.notna()].dt.date
    df = df[df["parsed_date"] <= today].copy()
    if df.empty:
        return default_prs

    df["exercise_id"] = _get_series(df, "exercise_id", "").fillna("").astype(str).str.lower()
    df["exercise_name"] = _get_series(df, "exercise_name", "").fillna("").astype(str)
    df["reps"] = pd.to_numeric(_get_series(df, "reps", 0), errors="coerce").fillna(0).astype(int)
    df["duration_sec"] = pd.to_numeric(_get_series(df, "duration_sec", 0), errors="coerce").fillna(0).astype(int)

    # 1. Squat PR (reps)
    squat_df = df[df["exercise_id"].str.contains("squat") | df["exercise_name"].str.lower().str.contains("squat")]
    if not squat_df.empty and squat_df["reps"].max() > 0:
        default_prs["Squat Thể dục"] = f"{int(squat_df['reps'].max())} reps"

    # 2. Push-up PR (reps)
    push_df = df[
        df["exercise_id"].str.contains("push_up")
        | df["exercise_name"].str.lower().str.contains("push-up|hít đất")
    ]
    if not push_df.empty and push_df["reps"].max() > 0:
        default_prs["Standard Push-up"] = f"{int(push_df['reps'].max())} reps"

    # 3. Plank PR (duration in seconds)
    plank_mask = df.apply(lambda r: _is_plank_exercise(r["exercise_id"], r["exercise_name"]), axis=1)
    plank_df = df[plank_mask]
    if not plank_df.empty and plank_df["duration_sec"].max() > 0:
        default_prs["Plank Tĩnh"] = _format_duration(int(plank_df["duration_sec"].max()))

    # 4. Bench Dip PR (reps)
    dip_df = df[df["exercise_id"].str.contains("dip") | df["exercise_name"].str.lower().str.contains("dip")]
    if not dip_df.empty and dip_df["reps"].max() > 0:
        default_prs["Dips trên ghế"] = f"{int(dip_df['reps'].max())} reps"

    return default_prs

def build_progress_analytics(
    history: list[dict[str, Any]],
    timeframe: str = "week",
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Aggregate workout history with Pandas for Plotly charts (Reps & Plank hold).

    Args:
        history: List of workout records.
        timeframe: 'week' (last 7 days), 'month' (last 30 days), or 'all'.
        reference_date: Optional reference date for deterministic testing.
    """
    tf = timeframe if timeframe in {"week", "month", "all"} else "week"
    today = reference_date or date.today()
    prs = compute_personal_records(history, reference_date=today)

    def _empty_result(invalid_count: int = 0) -> dict[str, Any]:
        return {
            "timeframe": tf,
            "labels": [],
            "reps_series": [],
            "plank_series": [],
            "duration_min_series": [],
            "personal_records": prs,
            "filtered_history": [],
            "summary": {
                "total_sessions": 0,
                "total_reps": 0,
                "best_plank_sec": 0,
                "avg_rpe": 0.0,
                "invalid_date_records": invalid_count,
            },
        }

    if not history:
        return _empty_result()

    df = pd.DataFrame(history)
    if df.empty:
        return _empty_result()

    # Parse dates strictly: invalid or missing dates become NaT and are excluded (never coerced to today)
    parsed_ts = pd.to_datetime(_get_series(df, "actual_date", None), errors="coerce")
    invalid_date_count = int(parsed_ts.isna().sum())
    df["parsed_date"] = parsed_ts.dt.date

    # Safe numeric/string normalization even when columns are absent
    df["reps"] = pd.to_numeric(_get_series(df, "reps", 0), errors="coerce").fillna(0).astype(int)
    df["duration_sec"] = pd.to_numeric(_get_series(df, "duration_sec", 0), errors="coerce").fillna(0).astype(int)
    df["rpe"] = pd.to_numeric(_get_series(df, "rpe", 7), errors="coerce").fillna(7).astype(float)
    df["exercise_id"] = _get_series(df, "exercise_id", "").fillna("").astype(str)
    df["exercise_name"] = _get_series(df, "exercise_name", "").fillna("").astype(str)

    # Exclude invalid dates and future dates (> today) from completed workout statistics
    valid_df = df[parsed_ts.notna()].copy()
    if valid_df.empty:
        return _empty_result(invalid_date_count)

    valid_df = valid_df[valid_df["parsed_date"] <= today].copy()
    if valid_df.empty:
        return _empty_result(invalid_date_count)

    # Filter by timeframe lower bound
    if tf == "week":
        cutoff = today - timedelta(days=6)
        filtered_df = valid_df[valid_df["parsed_date"] >= cutoff].copy()
    elif tf == "month":
        cutoff = today - timedelta(days=29)
        filtered_df = valid_df[valid_df["parsed_date"] >= cutoff].copy()
    else:
        filtered_df = valid_df.copy()

    if filtered_df.empty:
        return _empty_result(invalid_date_count)

    filtered_df["is_plank"] = filtered_df.apply(
        lambda r: _is_plank_exercise(r["exercise_id"], r["exercise_name"]), axis=1
    )
    filtered_df["plank_sec"] = filtered_df.apply(
        lambda r: int(r["duration_sec"]) if r["is_plank"] else 0, axis=1
    )

    # Group by date (sorted chronologically for Plotly line/bar progression)
    grouped = (
        filtered_df.groupby("parsed_date", as_index=False)
        .agg(
            total_reps=("reps", "sum"),
            max_plank_sec=("plank_sec", "max"),
            total_duration_sec=("duration_sec", "sum"),
        )
        .sort_values("parsed_date")
    )

    labels = [d.strftime("%d/%m") for d in grouped["parsed_date"]]
    reps_series = [int(v) for v in grouped["total_reps"].tolist()]
    plank_series = [int(v) for v in grouped["max_plank_sec"].tolist()]
    duration_min_series = [round(v / 60.0, 1) for v in grouped["total_duration_sec"].tolist()]

    # Filtered history rows preserving original dict fields
    filtered_indices = set(filtered_df.index.tolist())
    filtered_history = [row for idx, row in enumerate(history) if idx in filtered_indices]

    return {
        "timeframe": tf,
        "labels": labels,
        "reps_series": reps_series,
        "plank_series": plank_series,
        "duration_min_series": duration_min_series,
        "personal_records": prs,
        "filtered_history": filtered_history,
        "summary": {
            "total_sessions": _count_unique_sessions(filtered_df),
            "total_reps": int(filtered_df["reps"].sum()),
            "best_plank_sec": int(filtered_df["plank_sec"].max()),
            "avg_rpe": round(float(filtered_df["rpe"].mean()), 1),
            "invalid_date_records": invalid_date_count,
        },
    }

STREAK_MIN_COMPLETION = 50

def compute_streak(history: list[dict[str, Any]], reference_date: date | None = None) -> dict[str, Any]:
    """Count distinct qualifying calendar days; yesterday remains active until today ends."""
    today = reference_date or date.today()
    days = set()
    for record in history:
        try:
            day = date.fromisoformat(record.get("actual_date", ""))
            rate = float(record.get("completion_rate"))
        except (TypeError, ValueError):
            continue
        if day <= today and STREAK_MIN_COMPLETION <= rate <= 100:
            days.add(day)
    longest = run = 0
    previous = None
    for day in sorted(days):
        run = run + 1 if previous is not None and (day - previous).days == 1 else 1
        longest = max(longest, run)
        previous = day
    current = run if previous is not None and (today - previous).days <= 1 else 0
    return {"current_streak_days": current, "longest_streak_days": longest,
            "has_worked_out_today": today in days}
