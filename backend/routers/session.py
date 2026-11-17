"""Live Workout AI Session and FSM Rep Counter Router."""

import base64
import uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException

from backend.schemas import FSMRepRequest, SessionFinishRequest, SessionStartRequest
from backend.routers.exercises import get_catalog
from src.fsm_rep_counter import RepCounterFSM

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


@router.post("/start")
def start_session(payload: SessionStartRequest):
    catalog = get_catalog()
    exercise = next((ex for ex in catalog if ex["id"] == payload.exercise_id), None)
    ex_name = exercise["name"] if exercise else payload.exercise_id
    
    session_id = str(uuid.uuid4())
    fsm = RepCounterFSM()
    
    ACTIVE_SESSIONS[session_id] = {
        "session_id": session_id,
        "exercise_id": payload.exercise_id,
        "exercise_name": ex_name,
        "target_reps": payload.target_reps,
        "fsm": fsm,
        "rep_count": 0,
        "history_angles": [],
    }
    
    return {
        "success": True,
        "session_id": session_id,
        "exercise_id": payload.exercise_id,
        "exercise_name": ex_name,
        "target_reps": payload.target_reps,
        "message": f"Đã khởi động buổi tập {ex_name}!",
    }


@router.post("/fsm-rep")
def process_frame_angle(payload: FSMRepRequest):
    session = ACTIVE_SESSIONS.get(payload.session_id)
    if not session:
        # If session timed out or not found, create a lightweight fallback FSM
        fsm = RepCounterFSM()
        session = {
            "session_id": payload.session_id,
            "fsm": fsm,
            "rep_count": 0,
            "target_reps": 10,
        }
        ACTIVE_SESSIONS[payload.session_id] = session
        
    fsm: RepCounterFSM = session["fsm"]
    angle = payload.angle
    
    if angle is None:
        result = fsm.update(None)
        return {
            "rep_count": fsm.rep_count,
            "state": result["state"],
            "rep_incremented": False,
            "depth_pct": 0,
            "cue": None,
        }
    
    # Clamp angle to [0, 180]
    clamped_angle = max(0.0, min(180.0, float(angle)))
    result = fsm.update(clamped_angle)
    
    # Calculate depth percentage (180deg = 0% depth; 90deg = 100% depth)
    depth_pct = max(0.0, min(100.0, (180.0 - clamped_angle) / (180.0 - 90.0) * 100.0))
    
    voice_cue = None
    if result["rep_incremented"]:
        voice_cue = f"Tốt lắm! Lần {fsm.rep_count} hoàn thành!"
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
    }


@router.post("/finish")
def finish_session(payload: SessionFinishRequest):
    from backend.routers.progress import record_workout
    
    # Estimate calories burned (Calisthenics ~ 0.35 kcal / rep or ~ 6 kcal / min)
    est_calories = round(payload.completed_reps * 0.4 + (payload.duration_seconds / 60) * 4, 1)

    completion_rate = 100.0
    if payload.target_reps and payload.target_reps > 0:
        completion_rate = min(100.0, round((payload.completed_reps / payload.target_reps) * 100, 1))

    record = record_workout(
        exercise_id=payload.exercise_id,
        reps=payload.completed_reps,
        duration_sec=payload.duration_seconds,
        rpe=payload.rpe,
        notes=payload.feedback_notes or "Tập luyện AI HUD",
        calories=est_calories,
        day=payload.day,
        completion_rate=completion_rate,
    )
    
    # Cleanup session
    if payload.session_id in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[payload.session_id]
        
    return {
        "success": True,
        "message": f"Chúc mừng bạn đã hoàn thành {payload.completed_reps} reps!",
        "calories_burned": est_calories,
        "record": record,
    }
