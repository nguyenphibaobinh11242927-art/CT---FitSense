"""Local-only per-profile weekly plan/events persistence for Streamlit demo.

Not a production multi-user database: use an authenticated backend in deployment.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from src.adaptive_weekly_plan import week_key

STORE = Path(__file__).resolve().parents[1] / "data" / "private" / "weekly_plans"


def _user_key(state) -> str | None:
    profile = state.get("user_profile") or {}
    email = str(profile.get("email") or "").strip().lower()
    if not state.get("is_logged_in") or not email:
        return None
    return sha256(email.encode("utf-8")).hexdigest()


def _file(state, directory: Path = STORE) -> Path | None:
    user = _user_key(state)
    if not user:
        return None
    return directory / f"{user}_{week_key(date.today())}.json"


def load_week_state(state, directory: Path = STORE) -> bool:
    """Load once per identity per week; never load data for another account."""
    path = _file(state, directory)
    if path is None:
        return False
    marker = str(path)
    if state.get("_weekly_state_loaded_path") == marker:
        return False
    state["_weekly_state_loaded_path"] = marker
    if not path.is_file():
        state["workout_event_history"] = []
        return False
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(doc, dict):
        return False
    schedule = doc.get("weekly_schedule")
    if isinstance(schedule, list) and len(schedule) == 7 and all(isinstance(x, dict) for x in schedule):
        state["weekly_schedule"] = deepcopy(schedule)
    history = doc.get("workout_event_history")
    if isinstance(history, list):
        state["workout_event_history"] = deepcopy(history)
        state["session_history"] = deepcopy(history)
    return True


def save_week_state(state, directory: Path = STORE) -> bool:
    path = _file(state, directory)
    if path is None:
        return False
    plan = state.get("weekly_schedule", [])
    history = state.get("workout_event_history", [])
    if not isinstance(plan, list) or len(plan) != 7 or not isinstance(history, list):
        return False
    payload = {"week_start": week_key(date.today()), "weekly_schedule": plan,
               "workout_event_history": history}
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         suffix=".tmp", delete=False) as stream:
            temp_name = stream.name
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        os.replace(temp_name, path)
        state["_weekly_state_loaded_path"] = str(path)
        return True
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
