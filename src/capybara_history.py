"""Persistent per-user Capybara AI chat history storage (SCRUM-34).

Stores each user's conversation history in an isolated JSON file keyed by the
SHA-256 hash of their normalized email address under ``data/private/capybara_chat``.
Writes are atomic (temporary file + ``os.replace``) so concurrent async requests
never corrupt stored history.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

DEFAULT_HISTORY_DIR = Path(__file__).resolve().parents[1] / "data" / "private" / "capybara_chat"
MAX_MESSAGES_PER_USER = 100
MAX_CONTENT_LENGTH = 4000
VALID_ROLES = {"user", "assistant"}


def normalize_user_email(user_email: str | None) -> str:
    """Return a normalized lowercase email string or empty string if invalid."""
    if not isinstance(user_email, str):
        return ""
    return user_email.strip().lower()


def user_history_key(user_email: str | None) -> str:
    """Return a deterministic SHA-256 storage key for the given user email."""
    normalized = normalize_user_email(user_email)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _history_file_path(user_email: str, storage_dir: Path | None = None) -> Path:
    base_dir = Path(storage_dir) if storage_dir is not None else DEFAULT_HISTORY_DIR
    key = user_history_key(user_email)
    if not key:
        raise ValueError("user_email is required to access chat history")
    return base_dir / f"{key}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def normalize_message(raw: Any) -> dict[str, Any] | None:
    """Validate and sanitize a single chat message entry."""
    if not isinstance(raw, dict):
        return None

    role = str(raw.get("role", "")).strip().lower()
    if role not in VALID_ROLES:
        return None

    content = raw.get("content")
    if content is None:
        content = raw.get("reply")
    if not isinstance(content, str):
        return None
    content = content.strip()
    if not content:
        return None
    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH]

    entry: dict[str, Any] = {
        "role": role,
        "content": content,
        "time": str(raw.get("time") or _now_hhmm())[:16],
        "timestamp": str(raw.get("timestamp") or _now_iso())[:40],
    }

    if role == "assistant":
        emotion = raw.get("emotion") or raw.get("mood")
        entry["emotion"] = str(emotion)[:32] if isinstance(emotion, str) and emotion.strip() else "happy"

        intent = raw.get("intent")
        if isinstance(intent, str) and intent.strip():
            entry["intent"] = intent.strip()[:64]

        action = raw.get("action")
        if isinstance(action, str) and action.strip():
            entry["action"] = action.strip()[:64]

        action_card = raw.get("actionCard") if "actionCard" in raw else raw.get("action_card")
        entry["actionCard"] = action_card if isinstance(action_card, dict) else None

        diff = raw.get("diff")
        if isinstance(diff, dict):
            entry["diff"] = diff

    return entry


def load_chat_history(
    user_email: str | None,
    storage_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Load persisted chat messages for a specific user (empty list if none)."""
    normalized = normalize_user_email(user_email)
    if not normalized:
        return []

    path = _history_file_path(normalized, storage_dir=storage_dir)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        try:
            payload = json.load(f)
        except (ValueError, TypeError):
            return []

    raw_messages = payload.get("messages") if isinstance(payload, dict) else payload
    if not isinstance(raw_messages, list):
        return []

    cleaned: list[dict[str, Any]] = []
    for item in raw_messages:
        msg = normalize_message(item)
        if msg is not None:
            cleaned.append(msg)
    return cleaned[-MAX_MESSAGES_PER_USER:]


def save_chat_history(
    user_email: str,
    messages: list[dict[str, Any]],
    storage_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Atomically persist a user's sanitized chat history to disk."""
    normalized = normalize_user_email(user_email)
    if not normalized:
        raise ValueError("user_email is required to save chat history")

    cleaned: list[dict[str, Any]] = []
    for item in messages or []:
        msg = normalize_message(item)
        if msg is not None:
            cleaned.append(msg)
    cleaned = cleaned[-MAX_MESSAGES_PER_USER:]

    path = _history_file_path(normalized, storage_dir=storage_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "schema_version": 1,
        "user_key": user_history_key(normalized),
        "updated_at": _now_iso(),
        "messages": cleaned,
    }

    fd, tmp_path = tempfile.mkstemp(prefix=".capy_chat_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(record, tmp_file, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise

    return cleaned


def append_chat_exchange(
    user_email: str | None,
    user_message: str,
    reply_payload: dict[str, Any],
    storage_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Append a user prompt and assistant reply to the user's persisted history."""
    normalized = normalize_user_email(user_email)
    if not normalized:
        return []

    history = load_chat_history(normalized, storage_dir=storage_dir)
    now_time = _now_hhmm()
    now_iso = _now_iso()

    history.append({
        "role": "user",
        "content": user_message,
        "time": now_time,
        "timestamp": now_iso,
    })

    intent = reply_payload.get("intent")
    action = reply_payload.get("action")
    emotion = reply_payload.get("emotion") or reply_payload.get("mood")
    if not emotion:
        if intent == "INJURY_REPORT":
            emotion = "worried"
        elif action in {"move_workout_day", "apply_instant_deload"}:
            emotion = "thinking"
        else:
            emotion = "happy"

    assistant_entry: dict[str, Any] = {
        "role": "assistant",
        "content": reply_payload.get("reply") or reply_payload.get("content") or "",
        "time": now_time,
        "timestamp": now_iso,
        "emotion": emotion,
        "intent": intent,
        "action": action,
        "actionCard": reply_payload.get("actionCard"),
    }
    if isinstance(reply_payload.get("diff"), dict):
        assistant_entry["diff"] = reply_payload["diff"]

    history.append(assistant_entry)
    return save_chat_history(normalized, history, storage_dir=storage_dir)


def clear_chat_history(
    user_email: str | None,
    storage_dir: Path | None = None,
) -> bool:
    """Delete persisted chat history for the specified user only."""
    normalized = normalize_user_email(user_email)
    if not normalized:
        return False

    path = _history_file_path(normalized, storage_dir=storage_dir)
    if not path.exists():
        return False
    path.unlink()
    return True
