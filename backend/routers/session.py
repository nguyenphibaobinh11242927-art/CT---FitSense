"""Live Workout AI Session and FSM Rep Counter Router."""

import base64
import re
import uuid
from pathlib import Path
from threading import Lock
from typing import Any
from fastapi import APIRouter, HTTPException

from backend.schemas import (
    FSMRepRequest,
    SessionFinishRequest,
    SessionPauseRequest,
    SessionStartRequest,
    SessionSwitchExerciseRequest,
)
from backend.routers.exercises import get_catalog
from src.fsm_rep_counter import RepCounterFSM
from src.session_view import DEFAULT_SESSION_EXERCISES
from src.squat_correction import SquatCorrection

router = APIRouter(prefix="/api/session", tags=["Workout Session"])

ACTIVE_SESSIONS: dict[str, dict[str, Any]] = {}

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "pose_landmarker_lite.task"
_CACHED_MODEL_B64 = None


@router.get("/model")
def get_session_model():
    global _CACHED_MODEL_B64
    if _CACHED_MODEL_B64 is None:
        if MODEL_PATH.exists():
            _CACHED_MODEL_B64 = base64.b64encode(MODEL_PATH.read_bytes()).decode("ascii")
        else:
            raise HTTPException(status_code=404, detail="Model file not found")
    return {"model": _CACHED_MODEL_B64}


@router.get("/default-exercises")
def get_default_exercises():
    """Trả về danh mục bài tập mặc định cho buổi tập khi chưa có giáo án tuần (SCRUM-19)."""
    normalized = []
    id_map = {
        "Squat Thể dục (Bodyweight)": "squat",
        "Chống đẩy (Push-up)": "pushup",
        "Plank Tĩnh (Core Plank)": "plank",
    }
    for ex in DEFAULT_SESSION_EXERCISES:
        item = dict(ex)
        item["id"] = ex.get("id") or id_map.get(ex.get("name"), "squat")
        normalized.append(item)
    return {"exercises": normalized}


@router.post("/start")
def start_session(payload: SessionStartRequest):
    catalog = get_catalog()
    exercise = next((ex for ex in catalog if ex["id"] == payload.exercise_id), None)
    ex_name = exercise["name"] if exercise else payload.exercise_id
    
    session_id = str(uuid.uuid4())
    exercise_index = payload.exercise_index
    current_set = payload.current_set or 1
    total_sets = payload.total_sets or 3
    if not 1 <= current_set <= total_sets:
        raise HTTPException(status_code=422, detail="Hiệp tập không hợp lệ.")

    planned_targets = {
        index: _positive_int(exercise.get("sets"), 3) * _positive_int(exercise.get("reps"), payload.target_reps)
        for index, exercise in enumerate(payload.exercise_list or [])
    }
    planned_targets[exercise_index] = payload.target_reps * total_sets
    session = ACTIVE_SESSIONS[session_id] = {
        "session_id": session_id,
        "exercise_id": payload.exercise_id,
        "exercise_name": ex_name,
        "target_reps": payload.target_reps,
        "current_set": current_set,
        "total_sets": total_sets,
        "exercise_index": exercise_index,
        "planned_targets": planned_targets,
        "mode": payload.mode,
        "day": payload.day,
        "status": "active",
        "user_paused": False,
        "last_frame_id": 0,
        "set_reps": {},
        "lock": Lock(),
        "fsm": RepCounterFSM(),
        "correction": SquatCorrection() if payload.exercise_id == "squat" else None,
    }
    return {
        "success": True,
        **_summary(session),
        "exercise_name": ex_name,
        "total_sets": total_sets,
        "message": f"Đã khởi động buổi tập {ex_name}!",
    }


def _positive_int(value, default: int) -> int:
    match = re.match(r"\s*[0-9]+", str(value))
    return max(1, int(match.group())) if match else default


def _session(session_id: str):
    session = ACTIVE_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên tập.")
    return session


def _require_open(session: dict) -> None:
    if session["status"] in ("completed", "abandoned"):
        raise HTTPException(status_code=409, detail="Phiên tập đã kết thúc.")


def _set_key(session: dict) -> tuple[int, str, int]:
    return session["exercise_index"], session["exercise_id"], session["current_set"]


def _summary(session: dict) -> dict:
    sets = [
        {"exercise_index": index, "exercise_id": exercise, "set": number, "reps": reps}
        for (index, exercise, number), reps in session["set_reps"].items()
    ]
    return {
        "session_id": session["session_id"],
        "mode": session["mode"],
        "status": session["status"],
        "exercise_id": session["exercise_id"],
        "exercise_index": session["exercise_index"],
        "current_set": session["current_set"],
        "target_reps": session["target_reps"],
        "total_target_reps": sum(session["planned_targets"].values()),
        "rep_count": session["fsm"].rep_count,
        "total_reps": session["result"]["record"]["reps"] if "result" in session else sum(entry["reps"] for entry in sets),
        "sets": sets,
    }


def _reset_tracking(session: dict) -> None:
    session["fsm"].update(None)
    if session["correction"] is not None:
        session["correction"].interrupt_tracking()


def _open_set(session: dict) -> None:
    session["fsm"] = RepCounterFSM()
    session["fsm"].rep_count = session["set_reps"].get(_set_key(session), 0)
    session["correction"] = SquatCorrection() if session["exercise_id"] == "squat" else None
    _reset_tracking(session)


@router.get("/summary/{session_id}")
def session_summary(session_id: str):
    session = _session(session_id)
    with session["lock"]:
        return _summary(session)


@router.post("/pause")
def set_session_pause(payload: SessionPauseRequest):
    session = _session(payload.session_id)
    with session["lock"]:
        _require_open(session)
        if session["user_paused"] != payload.paused:
            _reset_tracking(session)
            session["user_paused"] = payload.paused
        session["status"] = "paused" if payload.paused or session["mode"] == "ai" else "active"
        return _summary(session)


@router.post("/switch-exercise")
def switch_session_exercise(payload: SessionSwitchExerciseRequest):
    if payload.current_set > payload.total_sets:
        raise HTTPException(status_code=422, detail="Hiệp tập không hợp lệ.")
    session = _session(payload.session_id)
    catalog = get_catalog()
    exercise = next((ex for ex in catalog if ex["id"] == payload.exercise_id), None)
    ex_name = payload.exercise_name or (exercise["name"] if exercise else payload.exercise_id)
    with session["lock"]:
        _require_open(session)
        index = payload.exercise_index
        if index is None:
            index = session["exercise_index"] + (payload.exercise_id != session["exercise_id"])
        session.update(
            exercise_id=payload.exercise_id, exercise_name=ex_name, target_reps=payload.target_reps,
            exercise_index=index, current_set=payload.current_set, total_sets=payload.total_sets,
        )
        session["planned_targets"][index] = payload.target_reps * payload.total_sets
        _open_set(session)
        return {
            "success": True, **_summary(session), "exercise_name": ex_name, "total_sets": payload.total_sets,
        }


@router.post("/fsm-rep")
def process_frame_angle(payload: FSMRepRequest):
    session = _session(payload.session_id)
    with session["lock"]:
        _require_open(session)
        if session["mode"] != "ai" or session["user_paused"]:
            raise HTTPException(status_code=409, detail="Phiên không nhận khung hình AI lúc này.")
        if payload.exercise_index is not None and payload.exercise_index != session["exercise_index"]:
            raise HTTPException(status_code=409, detail="Khung hình không thuộc bài đang tập.")
        if payload.frame_id is not None and payload.frame_id <= session["last_frame_id"]:
            raise HTTPException(status_code=409, detail="Khung hình đã được xử lý.")
        feedback = _process_frame(session, payload)
        if payload.frame_id is not None:
            session["last_frame_id"] = payload.frame_id
        return feedback


def _process_frame(session: dict, payload: FSMRepRequest):
    current_set = session["current_set"]
    if payload.current_set is not None:
        if not current_set <= payload.current_set <= session["total_sets"]:
            raise HTTPException(status_code=409, detail="Khung hình không thuộc hiệp đang tập.")
        if payload.current_set != current_set:
            session["current_set"] = payload.current_set
            _open_set(session)
    fsm: RepCounterFSM = session["fsm"]
    correction: SquatCorrection | None = session.get("correction")
    angle = None if payload.tracking_interrupted else payload.angle
    
    if angle is None:
        if correction is not None:
            if payload.tracking_interrupted:
                correction.interrupt_tracking()
            correction.update(None, fsm)
        result = fsm.update(None)
        session["status"] = "paused"
        return {
            "rep_count": fsm.rep_count,
            "state": result["state"],
            "rep_incremented": False,
            "depth_pct": 0,
            "angle": None,
            "cue": None,
            "tracking_lost": correction is None or correction.tracking_lost,
            "status": session["status"],
        }
    
    # Clamp angle to [0, 180]
    clamped_angle = max(0.0, min(180.0, float(angle)))
    result = fsm.update(clamped_angle)
    shallow = correction is not None and correction.update(clamped_angle, fsm)
    session["status"] = "paused" if fsm.state == fsm.WAITING_FOR_UP else "active"
    
    # Calculate depth percentage (180deg = 0% depth; 90deg = 100% depth)
    depth_pct = max(0.0, min(100.0, (180.0 - clamped_angle) / (180.0 - 90.0) * 100.0))
    
    voice_cue = None
    voice_event = None
    if result["rep_incremented"]:
        session["set_reps"][_set_key(session)] = fsm.rep_count
        voice_cue = f"Tốt lắm! Lần {fsm.rep_count} hoàn thành!"
        voice_event = {"kind": "rep", "count": fsm.rep_count}
    elif shallow:
        voice_cue = "Hạ thấp hơn nếu thấy thoải mái."
        voice_event = {"kind": "shallow_squat"}
    elif result["state"] == "STATE_GOING_DOWN" and clamped_angle > 110:
        voice_cue = "Hạ thấp trọng tâm thêm một chút!"
    elif result["state"] == "STATE_DOWN":
        voice_cue = "Độ sâu chuẩn! Đẩy người đứng thẳng lên!"
        
    return {
        "rep_count": fsm.rep_count,
        "state": result["state"],
        "rep_incremented": result["rep_incremented"],
        "angle": clamped_angle,
        "depth_pct": round(depth_pct, 1),
        "cue": voice_cue,
        "voice_event": voice_event,
        "status": session["status"],
    }


@router.post("/finish")
def finish_session(payload: SessionFinishRequest):
    from backend.routers.progress import record_workout

    session = _session(payload.session_id)
    with session["lock"]:
        if "result" in session:
            return session["result"]

        summary = _summary(session)
        reps = summary["total_reps"] if session["mode"] == "ai" else payload.completed_reps
        est_calories = round(reps * 0.4 + (payload.duration_seconds / 60) * 4, 1)
        completion_rate = min(100.0, reps / summary["total_target_reps"] * 100)
        record = record_workout(
            exercise_id=session["exercise_id"],
            reps=reps,
            duration_sec=payload.duration_seconds,
            rpe=payload.rpe if payload.outcome == "completed" else None,
            notes=payload.feedback_notes or "",
            calories=est_calories,
            day=session["day"] or payload.day,
            completion_rate=completion_rate,
            status=payload.outcome,
            mode=session["mode"],
            sets=summary["sets"],
        )
        session["status"] = payload.outcome
        session["result"] = {
            "success": True, "calories_burned": est_calories, "record": record,
            "message": "Đã lưu buổi tập bỏ dở." if payload.outcome == "abandoned" else f"Đã ghi nhận {reps} reps!",
        }
        return session["result"]
