"""Module Phòng tập Rảnh tay & Điều hành Phiên tập Thời gian thực (Session HUD View).

Quản lý chế độ Camera AI Vision (MediaPipe, đếm reps FSM, cử chỉ kép) và Chế độ Tự do Không Camera.
"""

import base64
from datetime import datetime
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

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


ROOT = Path(__file__).resolve().parents[1]
webcam = components.declare_component("fitsense_webcam", path=str(ROOT / "assets" / "webcam"))
SHALLOW_ATTEMPT_ANGLE = 130
logger = logging.getLogger(__name__)


@st.cache_data
def webcam_model():
    model = ROOT / "models" / "pose_landmarker_lite.task"
    return base64.b64encode(model.read_bytes()).decode("ascii")


@dataclass
class SquatCorrection:
    deepest_angle: float = 180

    def update(self, angle, previous_state, result):
        if angle is None or result["state"] == RepCounterFSM.STATE_DOWN or result["rep_incremented"]:
            self.deepest_angle = 180
        elif result["state"] == RepCounterFSM.STATE_GOING_DOWN:
            self.deepest_angle = min(self.deepest_angle, angle)
        elif previous_state == RepCounterFSM.STATE_GOING_DOWN and result["state"] == RepCounterFSM.STATE_UP:
            attempted_squat = self.deepest_angle <= SHALLOW_ATTEMPT_ANGLE
            self.deepest_angle = 180
            return attempted_squat
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

        if not session_started:
            start_result = start_fsm.update(start_detected)
            if start_result["triggered"]:
                session_started = True
            continue

        stop_result = stop_fsm.update(x_detected, head_detected)
        if not stop_result["is_rep_locked"]:
            previous_state = rep_fsm.state
            result = rep_fsm.update(knee_angle)
            if voice_events is None:
                continue
            needs_cue = correction is not None and correction.update(knee_angle, previous_state, result)
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

        if switched or first > session.last_event_id + 1:
            previous_state = self.rep.state
            self.correction.update(None, previous_state, self.rep.update(None))
            self.start.update(False)
            self.stop.update(False, False)
            session.status = "paused"

        voice_events = []
        for seq, frame in enumerate(frames, first):
            if seq <= session.last_event_id:
                continue
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
            if not tracking:
                voice_events.clear()
            session.status = "active" if tracking and self.started and not self.stop.is_rep_locked else "paused"
            session.last_event_id = seq

        self.voice_feedback = {
            "session_id": session.session_id,
            "stream_id": stream_id,
            "sequence": end,
            "events": voice_events,
            "stopped": self.stop.is_rep_locked or (self.started and not tracking),
        }


def _resolve_plan_day() -> dict | None:
    """Tìm buổi tập đang kích hoạt, buổi được chọn, hoặc tự khớp theo Thứ hôm nay trên máy tính."""
    active = st.session_state.get("active_workout")
    if isinstance(active, dict):
        return active
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
    return None


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
    reps_done = session.ai_reps if manual is None else manual["squat"] + manual["pushup"]
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
    })
    st.session_state["last_session_summary"] = {
        "session_name": session_name,
        "mode": "AI Vision" if session.mode == "ai" else "Chế độ Tự do",
        "actual_reps": reps_done,
        "target_reps": target_reps,
        "finished_at": finished_at,
    }
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


@st.fragment
def _render_ai_vision_hud_fragment() -> None:
    """Cô lập vùng Camera AI + HUD để khi camera gửi batch không làm cả trang web bị rerun/nhấp nháy."""
    session = st.session_state["workout_session"]
    pose = st.session_state["pose_session"]
    user_paused = bool(st.session_state.get("session_user_paused", False))
    session_name, target_reps = _compute_target_reps_from_active()

    col_left, col_right = st.columns([1.6, 1], gap="medium")

    with col_left:
        h_col1, h_col2 = st.columns([2.2, 1.3])
        with h_col1:
            st.subheader("Màn hình Giám sát Chuyển động AI (Live Feed)")
        with h_col2:
            show_metrics = st.toggle(
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

    with col_right:
        st.subheader("Bảng Điều hành Phiên tập (HUD)")

        if user_paused:
            paused_info = st.session_state.get("paused_progress", {})
            st.warning(
                f"⏸️ Buổi tập đang tạm ngưng — Đã lưu tiến trình **{paused_info.get('reps', session.ai_reps)} Reps**."
            )

        with st.container(border=True):
            st.markdown(f"### Bài tập Hiện tại: **{session_name}**")
            plan_day = _resolve_plan_day()
            is_rest_plan = bool(plan_day and (plan_day.get("is_rest") or not plan_day.get("exercises")))
            if is_rest_plan:
                st.caption("Mục tiêu buổi tập: **0 Reps (Ngày Nghỉ Phục Hồi)**")
            else:
                st.caption(f"Mục tiêu buổi tập: **{target_reps} Reps**")

            c1, c2 = st.columns([1.15, 1])
            with c1:
                status_badge = (
                    "⏸️ Tạm ngưng"
                    if user_paused
                    else ("🔥 Đang tập" if session.status == "active" else "⏳ Chờ bắt đầu")
                )
                st.markdown(
                    "<div style='font-size: 14px; opacity: 0.78; margin-bottom: 4px;'>Trạng thái</div>"
                    f"<div style='font-size: 20px; font-weight: 700; line-height: 1.35; white-space: normal;'>{status_badge}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.metric(label="Số Reps AI đếm", value=f"{session.ai_reps} Reps")

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
        with st.container(border=True):
            st.markdown("### ⏱️ Đồng hồ Nghỉ Giữa Hiệp (Rest Timer)")
            st.progress(60 / 60, text="Thời gian nghỉ: 60s còn lại")
            st.caption("🔊 Trợ lý Giọng nói sẽ đếm ngược 3... 2... 1... khi sắp hết giờ nghỉ!")

        with st.container(border=True):
            st.markdown("### 📋 Danh sách Bài tập Hôm nay")
            exercises = plan_day.get("exercises", []) if plan_day else []
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
            elif exercises:
                for idx, ex in enumerate(exercises, 1):
                    reps_label = ex.get("reps")
                    unit = "" if isinstance(reps_label, str) and not reps_label.isdigit() else " reps"
                    st.write(f"{idx}. **{ex.get('name')}** — {ex.get('sets')} sets × {reps_label}{unit}")
            else:
                st.write("1. **Squat Thể dục (Bodyweight)** — 3 sets × 12 reps")

        st.markdown("---")
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if not user_paused:
                if st.button("⏸️ Tạm ngưng", key="hud_pause_btn", use_container_width=True):
                    st.session_state["session_user_paused"] = True
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
        session.status = "paused"  # Chờ camera nhìn thấy người lần đầu.
        st.session_state["workout_session"] = session
        st.session_state["pose_session"] = PoseSession()
    if "session_user_paused" not in st.session_state:
        st.session_state["session_user_paused"] = False
    if "hud_show_metrics" not in st.session_state:
        st.session_state["hud_show_metrics"] = True

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
                try:
                    st.rerun(scope="app")
                except TypeError:
                    st.rerun()
            return
        _render_ai_vision_hud_fragment()

    else:
        col_left, col_right = st.columns([1.6, 1], gap="medium")
        # Chế độ Tự do Không Camera
        with col_left:
            st.subheader("Ghi nhận Kết quả Buổi tập (Không Camera)")
            st.success("🌱 Bạn đang ở Chế độ Tự do: Thoải mái tập luyện ngoài công viên hoặc không gian riêng tư mà không cần bật webcam.")

            with st.form("manual_session_form"):
                st.markdown("#### Nhập kết quả thực tế từng bài:")
                squat = st.number_input("1. Squat Thể dục — Số reps hoàn thành:", min_value=0, max_value=100, value=36)
                pushup = st.number_input("2. Push-up — Số reps hoàn thành:", min_value=0, max_value=100, value=30)
                plank = st.number_input("3. Plank tĩnh — Tổng giây giữ được:", min_value=0, max_value=300, value=120)

                submitted = st.form_submit_button("🏁 Kết thúc & Lưu Buổi tập", type="primary")
                if submitted:
                    manual_session = start_session(mode="manual")
                    save_result(
                        manual_session,
                        "completed",
                        {"squat": squat, "pushup": pushup, "plank_seconds": plank},
                    )

        with col_right:
            st.subheader("Hướng dẫn buổi tập")
            st.info("Hãy hoàn thành bài tập theo khả năng của bạn. Nếu mệt giữa chừng, bạn có thể nghỉ sớm; AI sẽ dựa vào tỉ lệ hoàn thành thực tế để điều chỉnh kế hoạch tiếp theo.")
