"""Adaptive scheduling, recovery hints, and an optional OpenAI-compatible optimizer.

Pure Python: independent of Streamlit, no secrets in source, AI output never
receives permission to alter past/today or inject unapproved exercises.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from itertools import permutations
from collections import Counter
import json
import os
from urllib.request import Request, urlopen

DAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]


def week_key(today: date) -> str:
    return (today - timedelta(days=today.weekday())).isoformat()


def muscle_tags(day: dict) -> set[str]:
    """Conservatively normalize Vietnamese/English primary and secondary muscles."""
    result = set()
    words = {
        "chest": ("ngực", "chest", "pec"),
        "back": ("lưng", "xô", "back", "lat", "row"),
        "shoulder": ("vai", "shoulder", "deltoid"),
        "triceps": ("tay sau", "triceps"),
        "biceps": ("tay trước", "biceps"),
        "quads": ("đùi trước", "quads", "quadriceps"),
        "hamstrings": ("đùi sau", "hamstring"),
        "glutes": ("mông", "glutes"),
        "calves": ("bắp chân", "calf", "calves"),
        "core": ("bụng", "core", "abs"),
    }
    for exercise in day.get("exercises", []):
        if not isinstance(exercise, dict):
            continue
        text = " ".join(str(exercise.get(k, "")) for k in ("primary_muscle", "secondary_muscle")).lower()
        for group, aliases in words.items():
            if any(alias in text for alias in aliases):
                result.add(group)
    return result


def recovery_warnings(source: dict, today: date, history: list[dict], schedule: list[dict]) -> list[str]:
    """Advisory only: uses actual recorded dates; never blocks a workout."""
    target = muscle_tags(source)
    if not target:
        return []
    alerts = []
    # Prior real sessions, including last week, take priority.
    for event in history:
        try:
            past = date.fromisoformat(str(event["actual_date"]))
        except (KeyError, TypeError, ValueError):
            continue
        delta = (today - past).days
        if 0 <= delta < 2 and event.get("status") == "completed":
            overlap = target & set(event.get("muscle_tags", []))
            if overlap:
                alerts.append(f"Đã tập {', '.join(sorted(overlap))} cách đây {delta} ngày (lịch sử thực tế).")
    # Weekly labels are not proof of past workouts: inspect completed only.
    for idx, previous in enumerate(schedule):
        if idx >= today.weekday() or previous.get("workout_status") != "completed":
            continue
        delta = today.weekday() - idx
        overlap = target & muscle_tags(previous)
        if delta < 2 and overlap:
            message = f"Ngày {DAYS[idx]} đã ghi hoàn thành nhóm cơ {', '.join(sorted(overlap))} ({delta} ngày trước)."
            if message not in alerts:
                alerts.append(message)
    return list(dict.fromkeys(alerts))


def _day_penalty(left: dict, right: dict, distance: int = 1) -> int:
    overlap = muscle_tags(left) & muscle_tags(right)
    if not overlap:
        return 0
    return (16 if distance == 1 else 6) * len(overlap)


def _score(prefix: list[dict], future: list[dict], original: list[dict]) -> int:
    seq = prefix + future
    penalty = sum(_day_penalty(seq[i-1], seq[i]) for i in range(1, len(seq)))
    penalty += sum(_day_penalty(seq[i-2], seq[i], 2) for i in range(2, len(seq)))
    penalty += sum(2 for a, b in zip(future, original) if a.get("focus") != b.get("focus"))
    return penalty


def _future_candidates(original_today: dict, future: list[dict], changed: bool) -> list[dict]:
    """Displaced today's workout enters candidate pool without increasing future slots."""
    candidates = deepcopy(future)
    if changed and original_today.get("exercises") and not original_today.get("is_rest"):
        candidates.append(deepcopy(original_today))
    return candidates


def _valid_future(candidate: list[dict], old_future: list[dict]) -> bool:
    if len(candidate) != len(old_future):
        return False
    # Preserve the number of recovery days already planned in the future.
    if sum(bool(x.get("is_rest")) for x in candidate) != sum(bool(x.get("is_rest")) for x in old_future):
        return False
    for old, new in zip(old_future, candidate):
        if old.get("workout_status") in ("completed", "in_progress", "abandoned") and old != new:
            return False
    return True


def _select_future(prefix: list[dict], future: list[dict], displaced: dict, changed: bool) -> list[dict]:
    candidates = _future_candidates(displaced, future, changed)
    n = len(future)
    if n == 0:
        return []
    # <= 6 future slots. Permutations are bounded (P(6,5) <= 720).
    best, best_score = deepcopy(future), _score(prefix, future, future)
    for indexes in permutations(range(len(candidates)), n):
        trial = [deepcopy(candidates[i]) for i in indexes]
        if not _valid_future(trial, future):
            continue
        score = _score(prefix, trial, future)
        if score < best_score:
            best, best_score = trial, score
    return best


def _ai_choice(prefix: list[dict], future: list[dict], displaced: dict, changed: bool,
               *, timeout: float = 9.0) -> list[dict] | None:
    """Optional AI reorder: return indices only; never trust AI-supplied workouts."""
    key = os.environ.get("FITAI_API_KEY", "").strip()
    if not key:
        return None
    base = os.environ.get("FITAI_BASE_URL", "https://api-fit.hcmus.edu.vn/v1").rstrip("/")
    model = os.environ.get("FITAI_MODEL", "Qwen-27B")
    candidates = _future_candidates(displaced, future, changed)
    n = len(future)
    context = {
        "recent_days": [{"day": x.get("day"), "focus": x.get("focus"), "muscles": sorted(muscle_tags(x))} for x in prefix[-3:]],
        "candidates": [{"index": i, "focus": x.get("focus"), "is_rest": x.get("is_rest"),
                        "muscles": sorted(muscle_tags(x))} for i, x in enumerate(candidates)],
        "future_slots": n,
        "locked_positions": [i for i, x in enumerate(future) if x.get("workout_status") in ("completed", "in_progress", "abandoned")],
    }
    body = {
        "model": model, "temperature": 0,
        "messages": [
            {"role": "system", "content": "You reorder existing workout candidate indices to reduce repeated muscle training on adjacent days, preserve rest and existing completed slots. Reply ONLY with JSON {\"indices\":[...]} of distinct integer candidate indices matching future_slots. Never invent exercises."},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
    }
    try:
        req = Request(base + "/chat/completions", data=json.dumps(body).encode(),
                      headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read(131072))
        raw = payload["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        indices = json.loads(raw)["indices"]
        if (not isinstance(indices, list) or len(indices) != n
                or any(type(i) is not int or not 0 <= i < len(candidates) for i in indices)
                or len(set(indices)) != n):
            return None
        trial = [deepcopy(candidates[i]) for i in indices]
        if not _valid_future(trial, future):
            return None
        # Don't accept an AI schedule worse than original.
        if _score(prefix, trial, future) > _score(prefix, future, future):
            return None
        return trial
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None


def start_actual_workout(schedule: list[dict], source_day: str, today: date,
                         *, use_ai: bool = True) -> tuple[list[dict], dict, str]:
    """Copy source workout into today, protect original day, optimize ONLY future days.

    Already completed days remain untouched. Repeated starts on the same day do
    not erase the recorded history (stored independently in event history).
    """
    if not isinstance(schedule, list) or len(schedule) != 7:
        raise ValueError("Kế hoạch tuần cần đủ 7 ngày.")
    names = [x.get("day") for x in schedule]
    if names != DAYS:
        raise ValueError("Kế hoạch tuần phải có thứ tự Thứ 2 đến Chủ nhật.")
    source = next((x for x in schedule if x["day"] == source_day), None)
    if source is None or source.get("is_rest") or not source.get("exercises"):
        raise ValueError("Ngày đã chọn không có giáo án tập.")
    idx = today.weekday()
    updated = deepcopy(schedule)
    old_today = deepcopy(updated[idx])
    source_copy = deepcopy(source)
    # Keep historical source untouched, and redirect results to today's date.
    new_today = {k: v for k, v in source_copy.items()
                 if k not in ("workout_status", "workout_completed_at", "workout_actual_reps")}
    new_today["day"] = DAYS[idx]
    new_today["workout_status"] = "in_progress"
    new_today["copied_from_day"] = source_day
    new_today["actual_date"] = today.isoformat()
    updated[idx] = new_today
    future = deepcopy(updated[idx+1:])
    changed = (source_day != DAYS[idx])
    prefix = updated[:idx+1]
    candidate = _ai_choice(prefix, future, old_today, changed) if use_ai else None
    method = "AI" if candidate is not None else "Thuật toán dự phòng"
    if candidate is None:
        candidate = _select_future(prefix, future, old_today, changed)
    for i, entry in enumerate(candidate, start=idx+1):
        entry["day"] = DAYS[i]
        updated[i] = entry
    return updated, updated[idx], method


def add_workout_event(history: list[dict], *, session_id: str, actual_date: date,
                      workout: dict, reps: int, status: str, finished_at: str) -> list[dict]:
    """Append (idempotently by session_id) an actual session, never overwrite earlier results."""
    updated = deepcopy(history)
    if any(x.get("session_id") == session_id for x in updated):
        return updated
    updated.append({
        "session_id": str(session_id), "actual_date": actual_date.isoformat(),
        "source_day": workout.get("copied_from_day", workout.get("day")),
        "focus": workout.get("focus", ""), "muscle_tags": sorted(muscle_tags(workout)),
        "reps": max(0, int(reps)), "status": status, "finished_at": finished_at,
    })
    return updated
