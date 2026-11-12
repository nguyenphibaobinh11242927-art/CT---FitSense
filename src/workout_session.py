from dataclasses import dataclass
from typing import Literal
from uuid import uuid4


SessionMode = Literal["ai", "manual"]
SessionStatus = Literal["active", "paused", "completed", "abandoned"]
EventType = Literal["rep_completed", "tracking_lost", "tracking_restored"]


@dataclass
class WorkoutSession:
    session_id: str
    mode: SessionMode
    status: SessionStatus = "active"
    ai_reps: int = 0
    last_event_id: int = 0


def start_session(mode: SessionMode = "ai") -> WorkoutSession:
    if mode not in ("ai", "manual"):
        raise ValueError("Chế độ tập không hợp lệ.")

    return WorkoutSession(session_id=uuid4().hex, mode=mode)


def apply_event(
    session: WorkoutSession,
    *,
    session_id: str,
    event_id: int,
    event_type: EventType,
) -> None:
    if session_id != session.session_id or session.mode != "ai":
        return

    if session.status in ("completed", "abandoned"):
        return

    if event_type not in ("rep_completed", "tracking_lost", "tracking_restored"):
        raise ValueError("Loại sự kiện không hợp lệ.")

    if event_id <= session.last_event_id:
        return

    session.last_event_id = event_id

    if event_type == "tracking_lost":
        session.status = "paused"
    elif event_type == "tracking_restored":
        session.status = "active"
    elif event_type == "rep_completed" and session.status == "active":
        session.ai_reps += 1


def finish_session(
    session: WorkoutSession,
    outcome: Literal["completed", "abandoned"],
) -> None:
    if outcome not in ("completed", "abandoned"):
        raise ValueError("Kết quả buổi tập không hợp lệ.")

    if session.status in ("completed", "abandoned"):
        return

    session.status = outcome