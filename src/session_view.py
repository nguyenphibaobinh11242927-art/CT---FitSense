"""Module Phòng tập Rảnh tay & Điều hành Phiên tập Thời gian thực (Session HUD View - SCRUM-19).

Quản lý giao diện HUD điều khiển phiên tập, đồng hồ đếm ngược thời gian nghỉ giữa hiệp (Rest Timer)
kèm âm thanh / giọng nói nhắc nhở, và danh sách bài tập kế tiếp (Up Next List).
Hỗ trợ cả Chế độ Camera AI Vision (MediaPipe, đếm reps FSM, cử chỉ kép) và Chế độ Tự do Không Camera.
"""

import base64
from datetime import datetime, date
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
import time

import streamlit as st
import streamlit.components.v1 as components

from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.fsm_rep_counter import RepCounterFSM
from src.planner_view import (
    count_day_target_reps,
    get_next_active_schedule_day,
    get_today_schedule_day,
)
from src.workout_session import WorkoutSession, finish_session, start_session
from src.weekly_plan_sync import finish_planned_day
from src.adaptive_weekly_plan import add_workout_event
from src.weekly_plan_storage import save_week_state


ROOT = Path(__file__).resolve().parents[1]
webcam = components.declare_component("fitsense_webcam", path=str(ROOT / "assets" / "webcam"))
SHALLOW_ATTEMPT_ANGLE = 135
SHALLOW_TRACKING_GRACE_FRAMES = 2
logger = logging.getLogger(__name__)

# Danh mục bài tập chuẩn hóa mặc định cho buổi tập khi chưa có giáo án tuần
DEFAULT_SESSION_EXERCISES = [
    {
        "name": "Squat Thể dục (Bodyweight)",
        "sets": 3,
        "reps": 12,
        "rest_sec": 60,
        "primary_muscle": "Đùi trước & Mông",
        "secondary_muscle": "Core",
        "equipment": "Bodyweight",
        "difficulty": "Beginner",
        "substitute": "Wall Squat (Tựa tường)",
        "form_tip": "Giữ lưng thẳng, hạ đùi song song sàn, gối không chụm vào trong.",
    },
    {
        "name": "Chống đẩy (Push-up)",
        "sets": 3,
        "reps": 10,
        "rest_sec": 60,
        "primary_muscle": "Ngực & Tay sau",
        "secondary_muscle": "Cơ vai",
        "equipment": "Bodyweight",
        "difficulty": "Beginner",
        "substitute": "Knee Push-up (Chống đẩy quỳ gối)",
        "form_tip": "Thân người tạo thành một đường thẳng, siết chặt cơ bụng và mông.",
    },
    {
        "name": "Plank Tĩnh (Core Plank)",
        "sets": 3,
        "reps": 30,
        "rest_sec": 45,
        "primary_muscle": "Cơ bụng & Lõi (Core)",
        "secondary_muscle": "Cơ vai",
        "equipment": "Bodyweight",
        "difficulty": "Beginner",
        "substitute": "Knee Plank (Plank quỳ gối)",
        "form_tip": "Khuỷu tay vuông góc dưới vai, không võng thắt lưng hoặc nhô mông.",
    },
]


@st.cache_data
def webcam_model():
    model = ROOT / "models" / "pose_landmarker_lite.task"
    return base64.b64encode(model.read_bytes()).decode("ascii")


@dataclass
class SquatCorrection:
    deepest_angle: float | None = None
    missing_frames: int = 0

    @property
    def tracking_lost(self) -> bool:
        return self.missing_frames > SHALLOW_TRACKING_GRACE_FRAMES

    def interrupt_tracking(self) -> None:
        self.deepest_angle = None
        self.missing_frames = SHALLOW_TRACKING_GRACE_FRAMES + 1

    def update(self, angle: float | None, rep_fsm: RepCounterFSM) -> bool:
        if angle is None:
            if not self.tracking_lost:
                self.missing_frames += 1
                if self.tracking_lost:
                    self.interrupt_tracking()
            return False

        self.missing_frames = 0
        if angle >= rep_fsm.up_thresh:
            deepest_angle = self.deepest_angle
            self.deepest_angle = None
            return deepest_angle is not None and rep_fsm.down_thresh < deepest_angle <= SHALLOW_ATTEMPT_ANGLE

        if self.deepest_angle is not None:
            self.deepest_angle = min(self.deepest_angle, angle)
        elif rep_fsm.state == RepCounterFSM.STATE_GOING_DOWN:
            self.deepest_angle = angle
        return False


def process_pose_frames(
    frames: list[dict],
    rep_fsm: RepCounterFSM,
    start_fsm: StartGestureFSM,
    stop_fsm: StopGestureFSM,
    session_started: bool,
    *,
    voice_events: list[dict] | None = None,
    correction: SquatCorrection | None = None,
) -> bool:
    """Apply a webcam batch to the FSMs and return the updated session status."""
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("Mẫu pose không đúng định dạng.")

        start_detected = frame.get("start_detected")
        x_detected = frame.get("x_detected")
        head_detected = frame.get("head_detected")
        knee_angle = frame.get("knee_angle")
        captured_at = frame.get("captured_at")
        if (
            type(start_detected) is not bool
            or type(x_detected) is not bool
            or type(head_detected) is not bool
        ):
            raise ValueError("Trạng thái cử chỉ phải là kiểu đúng/sai.")
        if knee_angle is not None and (
            isinstance(knee_angle, bool)
            or not isinstance(knee_angle, (int, float))
            or not math.isfinite(knee_angle)
            or not 0 <= knee_angle <= 180
        ):
            raise ValueError("Góc gối phải nằm trong khoảng 0 đến 180 độ.")
        if captured_at is not None and (
            isinstance(captured_at, bool)
            or not isinstance(captured_at, (int, float))
            or not math.isfinite(captured_at)
            or captured_at < 0
        ):
            raise ValueError("Thời điểm khung hình phải là số mili-giây hợp lệ.")

        if not session_started:
            start_result = start_fsm.update(start_detected, captured_at)
            if start_result["triggered"]:
                session_started = True
            continue

        stop_result = stop_fsm.update(x_detected, head_detected, captured_at)
        if not stop_result["is_rep_locked"]:
            result = rep_fsm.update(knee_angle)
            if voice_events is None:
                continue
            needs_cue = correction is not None and correction.update(knee_angle, rep_fsm)
            if result["rep_incremented"]:
                event = {"kind": "rep", "count": result["rep_count"]}
            elif needs_cue:
                event = {"kind": "shallow_squat"}
            else:
                continue
            captured_at = frame.get("captured_at")
            if type(captured_at) in (int, float) and 0 <= captured_at < math.inf:
                event["captured_at"] = captured_at
            voice_events.append(event)
    return session_started


@dataclass
class PoseSession:
    rep: RepCounterFSM = field(default_factory=RepCounterFSM)
    start: StartGestureFSM = field(default_factory=StartGestureFSM)
    stop: StopGestureFSM = field(default_factory=StopGestureFSM)
    started: bool = False
    correction: SquatCorrection = field(default_factory=SquatCorrection)
    stream_id: str | None = None
    retired_streams: set[str] = field(default_factory=set)
    voice_feedback: dict | None = None

    def interrupt_tracking(self) -> None:
        self.rep.update(None)
        self.correction.interrupt_tracking()
        self.start.update(False)
        self.stop.update(False, False)

    def consume(self, session: WorkoutSession, batch, *, user_paused: bool = False) -> None:
        if not isinstance(batch, dict) or batch.get("session_id") != session.session_id:
            return
        if session.status in ("completed", "abandoned") or session.mode != "ai":
            return
        stream_id = batch.get("stream_id")
        end = batch.get("sequence")
        frames = batch.get("frames")
        if (
            not isinstance(stream_id, str) or not stream_id or stream_id in self.retired_streams
            or type(end) is not int or not isinstance(frames, list) or not 0 < len(frames) <= 100
        ):
            return
        first = end - len(frames) + 1
        if end <= session.last_event_id or first < 1:
            return
        if user_paused:
            self.interrupt_tracking()
            session.last_event_id = end
            session.status = "paused"
            self.voice_feedback = {
                "session_id": session.session_id,
                "stream_id": stream_id,
                "sequence": end,
                "events": [],
                "stopped": True,
            }
            return
        switched = self.stream_id is not None and self.stream_id != stream_id
        if switched:
            self.retired_streams.add(self.stream_id)
        self.stream_id = stream_id

        interrupted = switched or first > session.last_event_id + 1
        if interrupted:
            self.interrupt_tracking()
            session.status = "paused"

        voice_events = []
        for seq, frame in enumerate(frames, first):
            if seq <= session.last_event_id:
                continue
            if isinstance(frame, dict) and frame.get("tracking_interrupted") is True:
                self.correction.interrupt_tracking()
                interrupted = True
            previous_event_count = len(voice_events)
            self.started = process_pose_frames(
                [frame], self.rep, self.start, self.stop, self.started,
                voice_events=voice_events, correction=self.correction,
            )
            if len(voice_events) > previous_event_count and voice_events[-1]["kind"] == "shallow_squat":
                event = voice_events[-1]
                event["frame_sequence"] = seq
                logger.debug("Detected shallow squat at frame %s (%s ms)", seq, event.get("captured_at"))
            session.ai_reps = self.rep.rep_count
            tracking = frame.get("knee_angle") is not None
            audio_paused = not tracking and self.started and self.correction.tracking_lost
            if audio_paused:
                interrupted = True
                voice_events.clear()
            session.status = "active" if tracking and self.started and not self.stop.is_rep_locked else "paused"
            session.last_event_id = seq

        self.voice_feedback = {
            "session_id": session.session_id,
            "stream_id": stream_id,
            "sequence": end,
            "events": voice_events,
            "stopped": self.stop.is_rep_locked or audio_paused,
            "interrupted": interrupted,
        }


def _resolve_plan_day() -> dict | None:
    """Tìm buổi tập đang kích hoạt, buổi được chọn, hoặc tự khớp theo Thứ hôm nay trên máy tính."""
    schedule = st.session_state.get("weekly_schedule")
    if isinstance(schedule, list):
        selected_day = st.session_state.get("selected_session_day")
        if selected_day:
            for day in schedule:
                if isinstance(day, dict) and day.get("day") == selected_day:
                    return day
        today_day = get_today_schedule_day(schedule)
        if today_day is not None:
            return today_day
        return get_next_active_schedule_day(schedule)
    active = st.session_state.get("active_workout")
    return active if isinstance(active, dict) else None


def _get_session_exercises() -> list[dict]:
    """Lấy danh sách bài tập cho buổi tập hiện tại (từ giáo án hoặc danh sách mặc định)."""
    custom = st.session_state.get("hud_custom_exercises")
    if isinstance(custom, list) and custom:
        return custom
    plan_day = _resolve_plan_day()
    if plan_day and isinstance(plan_day.get("exercises"), list) and plan_day["exercises"]:
        clean = []
        for ex in plan_day["exercises"]:
            if isinstance(ex, dict) and ex.get("name"):
                sets_v = ex.get("sets", 3)
                reps_v = ex.get("reps", 12)
                rest_v = ex.get("rest_sec", 60)
                clean.append({
                    "name": str(ex["name"]).strip(),
                    "sets": int(sets_v) if str(sets_v).isdigit() else 3,
                    "reps": reps_v,
                    "rest_sec": int(rest_v) if str(rest_v).isdigit() else 60,
                    "primary_muscle": str(ex.get("primary_muscle", "Toàn thân")),
                    "secondary_muscle": str(ex.get("secondary_muscle", "Core")),
                    "equipment": str(ex.get("equipment", "Bodyweight")),
                    "difficulty": str(ex.get("difficulty", "Beginner")),
                    "substitute": str(ex.get("substitute", "Wall Squat (Tựa tường)")),
                    "form_tip": str(ex.get("form_tip", "Giữ đúng kỹ thuật chuẩn, kiểm soát nhịp thở.")),
                })
        if clean:
            return clean
    return [dict(e) for e in DEFAULT_SESSION_EXERCISES]


def _init_hud_state():
    """Khởi tạo trạng thái bộ điều hành HUD, đồng hồ nghỉ và tiến trình hiệp."""
    if "hud_current_ex_idx" not in st.session_state:
        st.session_state["hud_current_ex_idx"] = 0
    if "hud_current_set" not in st.session_state:
        st.session_state["hud_current_set"] = 1
    if "hud_is_resting" not in st.session_state:
        st.session_state["hud_is_resting"] = False
    if "hud_rest_duration" not in st.session_state:
        st.session_state["hud_rest_duration"] = 60
    if "hud_rest_start_time" not in st.session_state:
        st.session_state["hud_rest_start_time"] = None
    if "hud_rest_remaining" not in st.session_state:
        st.session_state["hud_rest_remaining"] = 60
    if "hud_rest_paused" not in st.session_state:
        st.session_state["hud_rest_paused"] = False
    if "hud_completed_sets" not in st.session_state:
        st.session_state["hud_completed_sets"] = {}
    if "hud_custom_rest_sec" not in st.session_state:
        st.session_state["hud_custom_rest_sec"] = None


def _advance_hud_set(exercises: list[dict]):
    """Hoàn thành hiệp hiện tại, kích hoạt đồng hồ nghỉ giữa hiệp hoặc chuyển bài mới."""
    cur_idx = st.session_state.get("hud_current_ex_idx", 0)
    cur_set = st.session_state.get("hud_current_set", 1)
    if cur_idx >= len(exercises):
        return

    cur_ex = exercises[cur_idx]
    total_sets = cur_ex.get("sets", 3)
    custom_rest = st.session_state.get("hud_custom_rest_sec")
    rest_time = custom_rest if custom_rest is not None else cur_ex.get("rest_sec", 60)

    # Đánh dấu hoàn thành hiệp này
    st.session_state["hud_completed_sets"][f"{cur_idx}_{cur_set}"] = True

    if cur_set < total_sets:
        # Sang hiệp tiếp theo trong cùng bài
        st.session_state["hud_is_resting"] = True
        st.session_state["hud_rest_duration"] = rest_time
        st.session_state["hud_rest_remaining"] = rest_time
        st.session_state["hud_rest_start_time"] = time.time()
        st.session_state["hud_rest_paused"] = False
        st.session_state["hud_next_target"] = f"Hiệp {cur_set + 1}/{total_sets} — {cur_ex['name']}"
    else:
        # Đã hoàn thành tất cả các hiệp của bài hiện tại
        if cur_idx + 1 < len(exercises):
            next_ex = exercises[cur_idx + 1]
            st.session_state["hud_is_resting"] = True
            st.session_state["hud_rest_duration"] = rest_time
            st.session_state["hud_rest_remaining"] = rest_time
            st.session_state["hud_rest_start_time"] = time.time()
            st.session_state["hud_rest_paused"] = False
            st.session_state["hud_next_target"] = f"Bài tiếp theo: {next_ex['name']} (Hiệp 1/{next_ex.get('sets', 3)})"
        else:
            # Đã hoàn thành toàn bộ bài tập trong buổi!
            st.session_state["hud_is_resting"] = False
            st.session_state["hud_all_completed"] = True


def _finish_rest_period(exercises: list[dict]):
    """Kết thúc thời gian nghỉ, vào hiệp mới hoặc bài tập mới."""
    st.session_state["hud_is_resting"] = False
    st.session_state["hud_rest_start_time"] = None
    cur_idx = st.session_state.get("hud_current_ex_idx", 0)
    cur_set = st.session_state.get("hud_current_set", 1)
    if cur_idx < len(exercises):
        total_sets = exercises[cur_idx].get("sets", 3)
        if cur_set < total_sets:
            st.session_state["hud_current_set"] = cur_set + 1
        else:
            if cur_idx + 1 < len(exercises):
                st.session_state["hud_current_ex_idx"] = cur_idx + 1
                st.session_state["hud_current_set"] = 1


def _skip_to_next_exercise(exercises: list[dict]):
    """Bỏ qua bài tập hiện tại và chuyển sang bài tiếp theo trong Up Next list."""
    cur_idx = st.session_state.get("hud_current_ex_idx", 0)
    if cur_idx + 1 < len(exercises):
        st.session_state["hud_current_ex_idx"] = cur_idx + 1
        st.session_state["hud_current_set"] = 1
        st.session_state["hud_is_resting"] = False
        st.session_state["hud_rest_start_time"] = None
    else:
        st.session_state["hud_all_completed"] = True


def _compute_target_reps_from_active() -> tuple[str, int]:
    """Lấy tên buổi tập và tổng số reps mục tiêu từ lộ trình AI khớp lịch hôm nay."""
    plan_day = _resolve_plan_day()
    if plan_day is not None:
        session_name = f"{plan_day.get('day', '')} - {plan_day.get('focus', 'Buổi tập')}".strip(" -")
        if plan_day.get("is_rest") or not plan_day.get("exercises"):
            return session_name, 0
        total = count_day_target_reps(plan_day)
        return session_name, total if total > 0 else 36
    return "Squat Thể dục (Bodyweight)", 36


def _format_hold_time(active_frames: int, required_frames: int, fps: float = 30.0) -> str:
    """Chuyển đổi tiến trình giữ cử chỉ thành thời gian (giây) thân thiện thay cho số khung hình."""
    total_sec = max(0.5, required_frames / fps)
    elapsed_sec = min(total_sec, (active_frames / max(1, required_frames)) * total_sec)
    return f"{elapsed_sec:.1f}s / {total_sec:.1f}s"


def _on_webcam_change(key: str) -> None:
    session = st.session_state.get("workout_session")
    pose = st.session_state.get("pose_session")
    if session is None or pose is None:
        return
    try:
        pose.consume(
            session,
            st.session_state.get(key),
            user_paused=bool(st.session_state.get("session_user_paused", False)),
        )
        # Widget đã mount và có sẵn model trong iframe; tránh gửi lại 7.5MB base64 mỗi 200ms.
        st.session_state["_webcam_batch_rerun_key"] = key
    except ValueError as error:
        st.error(f"Không thể xử lý dữ liệu camera: {error}")


def save_result(session, outcome, manual=None):
    finish_session(session, outcome)
    session_name, target_reps = _compute_target_reps_from_active()
    finished_at = datetime.now().strftime("%H:%M %d/%m/%Y")
    if manual is None:
        reps_done = session.ai_reps
    else:
        if "squat" in manual and "pushup" in manual:
            reps_done = manual["squat"] + manual["pushup"]
        else:
            reps_done = sum(v for k, v in manual.items() if isinstance(v, (int, float)) and k != "plank_seconds")
    effective_target = max(1, target_reps if manual is None else max(target_reps, 66))
    results = st.session_state.setdefault("workout_results", {})
    results.setdefault(session.session_id, {
        "mode": session.mode,
        "status": session.status,
        "reps": reps_done,
        "target_reps": effective_target,
        "session_name": session_name,
        "finished_at": finished_at,
        "manual": manual,
        "completed_sets": st.session_state.get("hud_completed_sets", {}),
    })
    st.session_state["last_session_summary"] = {
        "session_name": session_name,
        "mode": "AI Vision" if session.mode == "ai" else "Chế độ Tự do",
        "actual_reps": reps_done,
        "target_reps": target_reps,
        "finished_at": finished_at,
    }
    selected_workout = st.session_state.get("active_workout") or {}
    actual_date_value = st.session_state.get("selected_session_actual_date")
    try:
        actual_day = date.fromisoformat(actual_date_value) if actual_date_value else date.today()
    except (TypeError, ValueError):
        actual_day = date.today()
    event_history = st.session_state.get("workout_event_history", [])
    st.session_state["workout_event_history"] = add_workout_event(
        event_history, session_id=str(session.session_id), actual_date=actual_day,
        workout=selected_workout, reps=reps_done, status=session.status,
        finished_at=finished_at,
    )
    st.session_state["session_history"] = list(st.session_state["workout_event_history"])
    weekly_schedule = st.session_state.get("weekly_schedule")
    if isinstance(weekly_schedule, list):
        day_name = st.session_state.get("selected_session_day")
        updated = finish_planned_day(
            weekly_schedule, day_name,
            completed=session.status == "completed",
            actual_reps=reps_done, finished_at=finished_at,
        )
        st.session_state["weekly_schedule"] = updated
        st.session_state["active_workout"] = next(
            (day for day in updated if isinstance(day, dict) and day.get("day") == day_name),
            st.session_state.get("active_workout"),
        )
    save_week_state(st.session_state)
    st.session_state["session_user_paused"] = False
    st.session_state.pop("paused_progress", None)
    st.session_state["review_session_id"] = session.session_id
    if session.status == "completed":
        st.session_state["has_worked_out_today"] = True
    st.session_state["pending_navigation"] = "📝 Đánh giá Sau Buổi tập"
    st.session_state["nav_selection"] = "📝 Đánh giá Sau Buổi tập"
    try:
        st.rerun(scope="app")
    except TypeError:
        st.rerun()


def _render_rest_timer_widget(
    remaining_seconds: int,
    total_seconds: int,
    is_paused: bool = False,
    next_info: str = "",
) -> None:
    """Widget đồng hồ đếm ngược nghỉ ngơi thời gian thực với Web Audio & giọng nói nhắc nhở."""
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        background: transparent;
        color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 6px 10px;
      }}
      .timer-card {{
        width: 100%;
        background: linear-gradient(135deg, rgba(16, 29, 49, 0.95), rgba(30, 41, 59, 0.95));
        border: 1px solid #38bdf8;
        box-shadow: 0 0 16px rgba(56, 189, 248, 0.2);
        border-radius: 12px;
        padding: 14px 18px;
        text-align: center;
      }}
      .timer-title {{
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #94a3b8;
        margin-bottom: 4px;
        font-weight: 700;
      }}
      .timer-display {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 44px;
        font-weight: 900;
        color: #38bdf8;
        line-height: 1.1;
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
      }}
      .progress-bg {{
        width: 100%;
        height: 8px;
        background: #0f172a;
        border-radius: 999px;
        margin: 10px 0 8px;
        overflow: hidden;
        border: 1px solid #334155;
      }}
      .progress-bar {{
        height: 100%;
        width: {(remaining_seconds / max(1, total_seconds)) * 100}%;
        background: linear-gradient(90deg, #38bdf8, #22c55e);
        border-radius: 999px;
        transition: width 0.25s ease-out;
      }}
      .next-info {{
        font-size: 13px;
        color: #e2e8f0;
        font-weight: 600;
        margin-top: 2px;
      }}
      .sound-note {{
        font-size: 11px;
        color: #94a3b8;
        margin-top: 4px;
      }}
      .finished-alert {{
        display: none;
        background: #22c55e;
        color: #0f172a;
        font-weight: 800;
        padding: 6px;
        border-radius: 6px;
        margin-top: 8px;
        font-size: 13px;
      }}
    </style>
    </head>
    <body>
      <div class="timer-card">
        <div class="timer-title">⏱️ ĐỒNG HỒ NGHỈ GIỮA HIỆP (REST TIMER)</div>
        <div id="countdown" class="timer-display">
          {remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}
        </div>
        <div class="progress-bg">
          <div id="p-bar" class="progress-bar"></div>
        </div>
        <div class="next-info">
          🎯 {next_info or "Chuẩn bị cho hiệp tiếp theo"}
        </div>
        <div class="sound-note">
          🔊 Âm thanh đếm ngược 3... 2... 1... và chuông báo khi hết giờ
        </div>
        <div id="fin-alert" class="finished-alert">
          🔔 HẾT GIỜ NGHỈ! Hãy sẵn sàng bắt đầu hiệp mới!
        </div>
      </div>

      <script>
        let total = {total_seconds};
        let rem = {remaining_seconds};
        let isPaused = {str(is_paused).lower()};
        const elTimer = document.getElementById("countdown");
        const elBar = document.getElementById("p-bar");
        const elAlert = document.getElementById("fin-alert");

        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        let audioCtx = null;
        function getAudio() {{
          if (!audioCtx && AudioCtx) audioCtx = new AudioCtx();
          if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
          return audioCtx;
        }}

        function beep(freq, duration, type='sine') {{
          try {{
            const ctx = getAudio();
            if (!ctx) return;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, ctx.currentTime);
            gain.gain.setValueAtTime(0.25, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + duration);
          }} catch(e) {{}}
        }}

        function chime() {{
          try {{
            [523.25, 659.25, 783.99, 1046.50].forEach((f, i) => {{
              setTimeout(() => beep(f, 0.4, 'triangle'), i * 110);
            }});
          }} catch(e) {{}}
        }}

        function speak(text) {{
          if ('speechSynthesis' in window) {{
            try {{
              const u = new SpeechSynthesisUtterance(text);
              u.lang = 'vi-VN';
              u.rate = 1.05;
              window.speechSynthesis.speak(u);
            }} catch(e) {{}}
          }}
        }}

        function format(s) {{
          const m = Math.floor(s / 60);
          const sec = s % 60;
          return String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
        }}

        let soundPlayed = {{ 3: false, 2: false, 1: false, 0: false }};

        const interval = setInterval(() => {{
          if (isPaused) return;
          rem = Math.max(0, rem - 1);
          elTimer.textContent = format(rem);
          const pct = Math.max(0, Math.min(100, (rem / Math.max(1, total)) * 100));
          elBar.style.width = pct + '%';

          if (rem <= 5) {{
            elBar.style.background = 'linear-gradient(90deg, #f59e0b, #ef4444)';
            elTimer.style.color = '#f87171';
          }}

          if (rem === 3 && !soundPlayed[3]) {{
            soundPlayed[3] = true;
            beep(587, 0.2);
            speak("Ba");
          }} else if (rem === 2 && !soundPlayed[2]) {{
            soundPlayed[2] = true;
            beep(659, 0.2);
            speak("Hai");
          }} else if (rem === 1 && !soundPlayed[1]) {{
            soundPlayed[1] = true;
            beep(880, 0.25);
            speak("Một");
          }} else if (rem === 0 && !soundPlayed[0]) {{
            soundPlayed[0] = true;
            chime();
            speak("Hết giờ nghỉ! Vào hiệp mới nào!");
            elAlert.style.display = 'block';
            clearInterval(interval);
          }}
        }}, 1000);
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=195, scrolling=False)


def _render_up_next_list(
    exercises: list[dict],
    cur_idx: int,
    cur_set: int,
    is_rest_plan: bool,
    plan_day: dict | None,
):
    """Hiển thị danh sách thứ tự bài tập của buổi hôm nay (Up Next List)."""
    with st.container(border=True):
        st.markdown("### 📋 Danh sách Bài tập Hôm nay (Up Next List)")
        if is_rest_plan and plan_day is not None:
            st.success("🌱 Hôm nay là Ngày Nghỉ Phục Hồi theo lịch tuần trên máy.")
            st.write("- Gợi ý: Đi bộ nhẹ nhàng 20 phút, giãn cơ hoặc bật camera tập thêm tùy chọn.")
            if st.button("📋 Chọn buổi tập bù từ Kế hoạch", key="hud_open_planner_rest_btn", use_container_width=True):
                st.session_state["pending_navigation"] = "📋 Kế hoạch Tập luyện Tuần"
                st.session_state["nav_selection"] = "📋 Kế hoạch Tập luyện Tuần"
                try:
                    st.rerun(scope="app")
                except TypeError:
                    st.rerun()
            return

        for idx, ex in enumerate(exercises, 1):
            ex_idx = idx - 1
            reps_label = ex.get("reps")
            unit = "" if isinstance(reps_label, str) and not str(reps_label).isdigit() else " reps"
            total_sets = ex.get("sets", 3)
            rest_sec = ex.get("rest_sec", 60)
            primary = ex.get("primary_muscle", "Toàn thân")

            if ex_idx < cur_idx:
                # Bài đã hoàn thành
                with st.container(border=False):
                    st.markdown(
                        f"<div style='padding: 8px 12px; background: rgba(34, 197, 94, 0.08); border-left: 4px solid #22c55e; border-radius: 6px; margin-bottom: 6px;'>"
                        f"<div style='display: flex; justify-content: space-between; align-items: center;'>"
                        f"<span style='font-weight: 700; color: #22c55e;'>✅ {idx}. {ex.get('name')}</span>"
                        f"<span style='font-size: 11px; background: #22c55e; color: #0f172a; font-weight: 800; padding: 2px 8px; border-radius: 10px;'>ĐÃ HOÀN THÀNH</span>"
                        f"</div>"
                        f"<div style='font-size: 12px; opacity: 0.8; margin-top: 2px;'>{total_sets}/{total_sets} sets · {reps_label}{unit} · {primary}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            elif ex_idx == cur_idx:
                # Bài đang tập
                with st.container(border=False):
                    st.markdown(
                        f"<div style='padding: 10px 14px; background: rgba(56, 189, 248, 0.12); border-left: 4px solid #38bdf8; border-radius: 8px; margin-bottom: 8px; box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);'>"
                        f"<div style='display: flex; justify-content: space-between; align-items: center;'>"
                        f"<span style='font-weight: 800; font-size: 15px; color: #38bdf8;'>🎯 {idx}. {ex.get('name')}</span>"
                        f"<span style='font-size: 11px; background: #38bdf8; color: #0f172a; font-weight: 800; padding: 2px 8px; border-radius: 10px;'>ĐANG TẬP</span>"
                        f"</div>"
                        f"<div style='font-size: 13px; font-weight: 600; margin-top: 4px; color: #f8fafc;'>"
                        f"Tiến độ: Hiệp {cur_set}/{total_sets} · Mục tiêu: {reps_label}{unit} · Nghỉ giữa hiệp: {rest_sec}s"
                        f"</div>"
                        f"<div style='font-size: 12px; opacity: 0.85; margin-top: 2px;'>Nhóm cơ: {primary} · {ex.get('difficulty', 'Beginner')}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                # Bài sắp tới (Up Next)
                with st.container(border=False):
                    c_up1, c_up2 = st.columns([3, 1])
                    with c_up1:
                        st.markdown(
                            f"<div style='padding: 8px 12px; background: rgba(148, 163, 184, 0.06); border-left: 4px solid #64748b; border-radius: 6px; margin-bottom: 6px;'>"
                            f"<div style='display: flex; justify-content: space-between; align-items: center;'>"
                            f"<span style='font-weight: 600; opacity: 0.9;'>⏳ {idx}. {ex.get('name')}</span>"
                            f"<span style='font-size: 11px; background: #334155; color: #cbd5e1; font-weight: 600; padding: 2px 6px; border-radius: 10px;'>SẮP TỚI</span>"
                            f"</div>"
                            f"<div style='font-size: 12px; opacity: 0.75; margin-top: 2px;'>{total_sets} sets × {reps_label}{unit} · Nghỉ: {rest_sec}s · {primary}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with c_up2:
                        if st.button("Tập ngay", key=f"hud_jump_btn_{ex_idx}", help=f"Chuyển ngay sang bài {ex.get('name')}", use_container_width=True):
                            st.session_state["hud_current_ex_idx"] = ex_idx
                            st.session_state["hud_current_set"] = 1
                            st.session_state["hud_is_resting"] = False
                            st.toast(f"Đã chuyển sang bài: {ex.get('name')}!", icon="🎯")
                            st.rerun()


@st.fragment
def _render_ai_vision_hud_fragment() -> None:
    """Cô lập vùng Camera AI + HUD để khi camera gửi batch không làm cả trang web bị rerun/nhấp nháy."""
    session = st.session_state["workout_session"]
    pose = st.session_state["pose_session"]
    user_paused = bool(st.session_state.get("session_user_paused", False))
    _init_hud_state()

    exercises = _get_session_exercises()
    cur_idx = min(st.session_state.get("hud_current_ex_idx", 0), max(0, len(exercises) - 1))
    cur_set = st.session_state.get("hud_current_set", 1)
    is_resting = bool(st.session_state.get("hud_is_resting", False))
    current_ex = exercises[cur_idx] if exercises else DEFAULT_SESSION_EXERCISES[0]
    total_sets = current_ex.get("sets", 3)

    session_name, target_reps = _compute_target_reps_from_active()
    plan_day = _resolve_plan_day()
    is_rest_plan = bool(plan_day and (plan_day.get("is_rest") or not plan_day.get("exercises")))

    col_left, col_right = st.columns([1.6, 1], gap="medium")

    with col_left:
        h_col1, h_col2 = st.columns([2.2, 1.3])
        with h_col1:
            st.subheader("Màn hình Giám sát Chuyển động AI (Live Feed)")
        with h_col2:
            show_metrics = st.checkbox(
                "⚙️ Hiện thông số kỹ thuật",
                key="hud_show_metrics",
                help="Bật/tắt hiển thị FPS và các góc khớp thời gian thực bên dưới khung hình.",
            )
        widget_key = f"live_pose_{session.session_id}"
        skip_model = st.session_state.pop("_webcam_batch_rerun_key", None) == widget_key
        webcam(
            model=None if skip_model else webcam_model(),
            session_id=session.session_id,
            last_event_id=session.last_event_id,
            voice_feedback=pose.voice_feedback,
            show_metrics=show_metrics,
            key=widget_key,
            on_change=lambda: _on_webcam_change(widget_key),
        )

        with st.container(border=True):
            st.markdown(
                "<div style='font-size: 13px; line-height: 1.6;'>"
                "<b>💡 Hướng dẫn Cử chỉ Rảnh tay:</b><br>"
                "• 🙋 <b>Giơ một tay cao hơn đầu:</b> Bắt đầu bài tập hoặc kết thúc nghỉ sớm để vào hiệp mới.<br>"
                "• 🙅 <b>Bắt chéo hai tay chữ X trước ngực:</b> Kết thúc hiệp đang tập và tự động bật Đồng hồ Nghỉ (Rest Timer)."
                "</div>",
                unsafe_allow_html=True,
            )

    with col_right:
        st.subheader("Bảng Điều hành Phiên tập (HUD)")

        if user_paused:
            paused_info = st.session_state.get("paused_progress", {})
            st.warning(
                f"⏸️ Buổi tập đang tạm ngưng — Đã lưu tiến trình **{paused_info.get('reps', session.ai_reps)} Reps**."
            )

        # Tính toán thời gian nghỉ nếu đang nghỉ
        custom_rest = st.session_state.get("hud_custom_rest_sec")
        rest_total = custom_rest if custom_rest is not None else current_ex.get("rest_sec", 60)

        if is_resting:
            if user_paused or st.session_state.get("hud_rest_paused", False):
                rem = st.session_state.get("hud_rest_remaining", rest_total)
            else:
                start_t = st.session_state.get("hud_rest_start_time")
                if start_t is None:
                    start_t = time.time()
                    st.session_state["hud_rest_start_time"] = start_t
                elapsed = time.time() - start_t
                rem = max(0, int(rest_total - elapsed))
                st.session_state["hud_rest_remaining"] = rem

            with st.container(border=True):
                st.markdown("### ⏱️ Đồng hồ Nghỉ Giữa Hiệp (Rest Timer)")
                next_target_label = st.session_state.get(
                    "hud_next_target",
                    f"Hiệp {cur_set + 1}/{total_sets} — {current_ex['name']}"
                )
                _render_rest_timer_widget(
                    remaining_seconds=rem,
                    total_seconds=rest_total,
                    is_paused=user_paused or st.session_state.get("hud_rest_paused", False),
                    next_info=next_target_label,
                )
                st.caption("💧 **Mẹo phục hồi:** Hít sâu bằng mũi, thở chậm bằng miệng, uống từng ngụm nước nhỏ.")

                c_r1, c_r2, c_r3 = st.columns([1.6, 1, 1])
                with c_r1:
                    if st.button("⏭️ Vào hiệp ngay", key="hud_skip_rest_btn", type="primary", use_container_width=True):
                        _finish_rest_period(exercises)
                        if pose.stop.is_rep_locked:
                            pose.stop.reset()
                        st.toast("Đã kết thúc nghỉ, bắt đầu hiệp mới!", icon="🔥")
                        st.rerun()
                with c_r2:
                    if st.button("+15s Nghỉ", key="hud_rest_plus15", use_container_width=True):
                        st.session_state["hud_rest_duration"] = rest_total + 15
                        st.session_state["hud_rest_remaining"] = rem + 15
                        if st.session_state.get("hud_rest_start_time"):
                            st.session_state["hud_rest_start_time"] += 15
                        st.rerun()
                with c_r3:
                    if st.button("-15s Nghỉ", key="hud_rest_minus15", use_container_width=True):
                        new_dur = max(10, rest_total - 15)
                        st.session_state["hud_rest_duration"] = new_dur
                        st.session_state["hud_rest_remaining"] = max(0, rem - 15)
                        if st.session_state.get("hud_rest_start_time"):
                            st.session_state["hud_rest_start_time"] = max(0, st.session_state["hud_rest_start_time"] - 15)
                        st.rerun()
        else:
            with st.container(border=True):
                st.markdown("### ⏱️ Đồng hồ Nghỉ Giữa Hiệp (Rest Timer)")
                st.progress(60 / 60, text=f"Thời gian nghỉ: {rest_total}s còn lại")
                st.caption("🔊 Trợ lý Giọng nói sẽ đếm ngược 3... 2... 1... khi sắp hết giờ nghỉ!")

                st.markdown("<div style='font-size: 13px; font-weight: 600; margin-bottom: 4px;'>Tùy chỉnh thời gian nghỉ theo thể trạng:</div>", unsafe_allow_html=True)
                p_cols = st.columns(5)
                for p_col, dur in zip(p_cols, [30, 45, 60, 90, 120]):
                    with p_col:
                        is_active = (rest_total == dur)
                        label = f"⭐ {dur}s" if is_active else f"{dur}s"
                        if st.button(label, key=f"hud_preset_{dur}", use_container_width=True):
                            st.session_state["hud_custom_rest_sec"] = dur
                            st.rerun()

                if st.button("⏱️ Bắt đầu nghỉ giữa hiệp ngay", key="hud_manual_start_rest_btn", use_container_width=True):
                    _advance_hud_set(exercises)
                    st.rerun()

        # Thẻ thông tin bài tập hiện tại & bộ đếm
        with st.container(border=True):
            st.markdown(f"### Bài tập Hiện tại: **{current_ex['name']}**")
            if is_rest_plan:
                st.caption("Mục tiêu buổi tập: **0 Reps (Ngày Nghỉ Phục Hồi)**")
            else:
                st.caption(f"Mục tiêu buổi tập: **{target_reps} Reps** · Tiến độ: **Hiệp {cur_set}/{total_sets}**")

            st.markdown(
                f"<div style='font-size: 13px; margin-bottom: 8px;'>"
                f"<span style='background: #1e293b; color: #38bdf8; padding: 2px 8px; border-radius: 6px; font-weight: 600; margin-right: 6px;'>🎯 {current_ex.get('primary_muscle', 'Toàn thân')}</span>"
                f"<span style='background: #1e293b; color: #94a3b8; padding: 2px 8px; border-radius: 6px; font-weight: 600; margin-right: 6px;'>⚡ {current_ex.get('difficulty', 'Beginner')}</span>"
                f"<span style='background: #1e293b; color: #94a3b8; padding: 2px 8px; border-radius: 6px; font-weight: 600;'>🏋️ {current_ex.get('equipment', 'Bodyweight')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.info(f"💡 **Mẹo kỹ thuật:** {current_ex.get('form_tip', 'Kiểm soát nhịp thở, giữ đúng biên độ.')}")

            c1, c2 = st.columns([1.15, 1])
            with c1:
                status_badge = (
                    "⏸️ Tạm ngưng"
                    if user_paused
                    else (
                        "⏱️ Đang nghỉ"
                        if is_resting
                        else ("🔥 Đang tập" if session.status == "active" else "⏳ Chờ bắt đầu")
                    )
                )
                st.markdown(
                    "<div style='font-size: 14px; opacity: 0.78; margin-bottom: 4px;'>Trạng thái</div>"
                    f"<div style='font-size: 20px; font-weight: 700; line-height: 1.35; white-space: normal;'>{status_badge}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.metric(label="Số Reps AI đếm", value=f"{session.ai_reps} Reps")

            # Hiển thị các chấm tiến độ hiệp
            set_badges = []
            for s_num in range(1, total_sets + 1):
                if s_num < cur_set:
                    set_badges.append(f"✅ Hiệp {s_num}")
                elif s_num == cur_set:
                    set_badges.append(f"🔥 Hiệp {s_num} (Đang tập)")
                else:
                    set_badges.append(f"⏳ Hiệp {s_num}")
            st.markdown(
                f"<div style='font-size: 13px; color: #cbd5e1; margin-bottom: 8px;'>"
                f"<b>Tiến trình hiệp:</b> {' &nbsp;|&nbsp; '.join(set_badges)}"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Thanh tiến trình tổng thể buổi tập
            rep_pct = min(1.0, session.ai_reps / max(1, target_reps))
            st.progress(rep_pct, text=f"Tổng tiến độ buổi tập: {session.ai_reps}/{target_reps} Reps ({int(rep_pct * 100)}%)")

            if pose.started:
                st.success("Đã bắt đầu buổi tập bằng cử chỉ giơ tay.")
            else:
                st.info(
                    "Giơ một tay cao hơn đầu để bắt đầu "
                    f"({_format_hold_time(pose.start.active_frames, pose.start.required_frames)})."
                )
            st.progress(
                pose.stop.active_frames / pose.stop.required_frames,
                text=(
                    "Giữ hai tay thành chữ X để dừng: "
                    f"{_format_hold_time(pose.stop.active_frames, pose.stop.required_frames)}"
                ),
            )
            if pose.stop.is_rep_locked:
                st.warning("Đã xác nhận dừng; số reps đã được khóa.")

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("✅ Hoàn thành hiệp", key="hud_complete_set_btn", type="primary", use_container_width=True):
                    _advance_hud_set(exercises)
                    st.rerun()
            with col_s2:
                if st.button("⏭️ Bỏ qua bài này", key="hud_skip_exercise_btn", use_container_width=True):
                    _skip_to_next_exercise(exercises)
                    st.rerun()

        # Danh sách bài tập hôm nay & Up Next List
        _render_up_next_list(exercises, cur_idx, cur_set, is_rest_plan, plan_day)

        st.markdown("---")
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if not user_paused:
                if st.button("⏸️ Tạm ngưng", key="hud_pause_btn", use_container_width=True):
                    st.session_state["session_user_paused"] = True
                    pose.interrupt_tracking()
                    session.status = "paused"
                    st.session_state["paused_progress"] = {
                        "reps": session.ai_reps,
                        "paused_at": datetime.now().strftime("%H:%M:%S"),
                        "session_name": session_name,
                    }
                    st.toast("Đã tạm ngưng buổi tập và lưu tiến trình!", icon="⏸️")
                    st.rerun()
            else:
                if st.button("▶️ Tiếp tục", key="hud_resume_btn", type="primary", use_container_width=True):
                    st.session_state["session_user_paused"] = False
                    if pose.started and not pose.stop.is_rep_locked:
                        session.status = "active"
                    st.toast("Tiếp tục ghi nhận buổi tập!", icon="▶️")
                    st.rerun()

        with btn_col2:
            if st.button("🏁 Kết thúc", key="hud_finish_btn", type="primary", use_container_width=True):
                save_result(session, "completed")


def render_session_view():
    """Hiển thị HUD điều hành buổi tập trực tiếp rảnh tay hoặc tự nhập sau khi tập."""
    if "workout_session" not in st.session_state:
        session = start_session(mode="ai")
        session.status = "paused"
        st.session_state["workout_session"] = session
        st.session_state["pose_session"] = PoseSession()
    if "session_user_paused" not in st.session_state:
        st.session_state["session_user_paused"] = False
    if "hud_show_metrics" not in st.session_state:
        st.session_state["hud_show_metrics"] = True
    _init_hud_state()

    session = st.session_state["workout_session"]
    st.header("⚡ Phòng tập Trực tiếp (Workout HUD)")

    c_empty_l, c_center, c_empty_r = st.columns([1, 2.8, 1])
    with c_center:
        st.markdown("<div style='text-align: center; font-weight: 700; font-size: 15px; margin-bottom: 8px;'>Lựa chọn Chế độ Giám sát:</div>", unsafe_allow_html=True)
        mode = st.radio(
            "Lựa chọn Chế độ Giám sát:",
            options=["🤖 Chế độ AI Vision (Camera Rảnh tay)", "📝 Chế độ Tự do (Không dùng Camera)"],
            horizontal=True,
            label_visibility="collapsed",
            key="session_mode_selector"
        )

    if mode == "🤖 Chế độ AI Vision (Camera Rảnh tay)":
        if session.status in ("completed", "abandoned"):
            st.info("Phiên tập đã kết thúc.")
            if st.button("Bắt đầu buổi mới"):
                del st.session_state["workout_session"]
                st.session_state["session_user_paused"] = False
                st.session_state.pop("paused_progress", None)
                for k in list(st.session_state.keys()):
                    if k.startswith("hud_"):
                        st.session_state.pop(k, None)
                try:
                    st.rerun(scope="app")
                except TypeError:
                    st.rerun()
            return
        _render_ai_vision_hud_fragment()

    else:
        col_left, col_right = st.columns([1.6, 1], gap="medium")
        exercises = _get_session_exercises()
        cur_idx = min(st.session_state.get("hud_current_ex_idx", 0), max(0, len(exercises) - 1))
        cur_set = st.session_state.get("hud_current_set", 1)
        plan_day = _resolve_plan_day()
        is_rest_plan = bool(plan_day and (plan_day.get("is_rest") or not plan_day.get("exercises")))

        with col_left:
            st.subheader("Ghi nhận Kết quả Buổi tập (Không Camera)")
            st.success("🌱 Bạn đang ở Chế độ Tự do: Thoải mái tập luyện ngoài công viên hoặc không gian riêng tư mà không cần bật webcam.")

            with st.form("manual_session_form"):
                st.markdown("#### Nhập kết quả thực tế từng bài:")
                inputs = {}
                for idx, ex in enumerate(exercises, 1):
                    reps_def = ex.get("reps", 12)
                    default_val = int(reps_def) if str(reps_def).isdigit() else 12
                    inputs[ex.get("name", f"Bài {idx}")] = st.number_input(
                        f"{idx}. {ex.get('name')} — Số reps hoàn thành:",
                        min_value=0, max_value=300, value=default_val * ex.get("sets", 3),
                        key=f"manual_input_{idx}",
                    )

                submitted = st.form_submit_button("🏁 Kết thúc & Lưu Buổi tập", type="primary")
                if submitted:
                    manual_session = start_session(mode="manual")
                    save_result(
                        manual_session,
                        "completed",
                        inputs,
                    )

        with col_right:
            st.subheader("Bảng Theo dõi & Đồng hồ Nghỉ (Manual HUD)")
            is_resting = bool(st.session_state.get("hud_is_resting", False))
            current_ex = exercises[cur_idx] if exercises else DEFAULT_SESSION_EXERCISES[0]
            rest_total = current_ex.get("rest_sec", 60)

            if is_resting:
                rem = st.session_state.get("hud_rest_remaining", rest_total)
                _render_rest_timer_widget(
                    remaining_seconds=rem,
                    total_seconds=rest_total,
                    is_paused=False,
                    next_info=f"Hiệp {cur_set}/{current_ex.get('sets', 3)} — {current_ex['name']}",
                )
                if st.button("⏭️ Vào hiệp tiếp theo", key="manual_skip_rest_btn", type="primary", use_container_width=True):
                    _finish_rest_period(exercises)
                    st.rerun()
            else:
                with st.container(border=True):
                    st.markdown("### ⏱️ Đồng hồ Nghỉ Giữa Hiệp")
                    st.progress(60 / 60, text=f"Thời gian nghỉ: {rest_total}s còn lại")
                    if st.button("⏱️ Bắt đầu đếm thời gian nghỉ giữa hiệp", key="manual_start_rest_btn", use_container_width=True):
                        st.session_state["hud_is_resting"] = True
                        st.session_state["hud_rest_duration"] = rest_total
                        st.session_state["hud_rest_remaining"] = rest_total
                        st.session_state["hud_rest_start_time"] = time.time()
                        st.rerun()

            _render_up_next_list(exercises, cur_idx, cur_set, is_rest_plan, plan_day)
