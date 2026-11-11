"""Module Phòng tập Rảnh tay & Điều hành Phiên tập Thời gian thực (Session HUD View).

Quản lý chế độ Camera AI Vision (MediaPipe, đếm reps FSM, cử chỉ kép) và Chế độ Tự do Không Camera.
"""

import base64
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.fsm_rep_counter import RepCounterFSM
from src.workout_session import WorkoutSession, finish_session, start_session


ROOT = Path(__file__).resolve().parents[1]
webcam = components.declare_component("fitsense_webcam", path=str(ROOT / "assets" / "webcam"))
SHALLOW_ATTEMPT_ANGLE = 135
SHALLOW_TRACKING_GRACE_FRAMES = 2
logger = logging.getLogger(__name__)


@st.cache_data
def webcam_model():
    model = ROOT / "models" / "pose_landmarker_lite.task"
    return base64.b64encode(model.read_bytes()).decode("ascii")


@dataclass
class SquatCorrection:
    deepest_angle: float | None = None
    missing_frames: int = 0

    def reset(self) -> None:
        self.deepest_angle = None
        self.missing_frames = 0

    def update(self, angle: float | None, rep_fsm: RepCounterFSM) -> bool:
        if angle is None:
            self.missing_frames += 1
            if self.missing_frames > SHALLOW_TRACKING_GRACE_FRAMES:
                self.reset()
            return False

        self.missing_frames = 0
        if angle >= rep_fsm.up_thresh:
            deepest_angle = self.deepest_angle
            self.deepest_angle = None
            return deepest_angle is not None and rep_fsm.down_thresh < deepest_angle <= SHALLOW_ATTEMPT_ANGLE

        # The rep FSM waits for an upright frame after tracking loss. Keep the
        # depth of an ongoing attempt through brief gaps for form feedback.
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
            result = rep_fsm.update(knee_angle)
            if voice_events is None:
                continue
            if correction is not None and frame.get("tracking_interrupted") is True:
                correction.reset()
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

    def consume(self, session: WorkoutSession, batch) -> None:
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
        switched = self.stream_id is not None and self.stream_id != stream_id
        if switched:
            self.retired_streams.add(self.stream_id)
        self.stream_id = stream_id

        if switched or first > session.last_event_id + 1:
            self.rep.update(None)
            self.correction.reset()
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


def _on_webcam_change(key: str) -> None:
    session = st.session_state.get("workout_session")
    pose = st.session_state.get("pose_session")
    if session is None or pose is None:
        return
    try:
        pose.consume(session, st.session_state.get(key))
    except ValueError as error:
        st.error(f"Không thể xử lý dữ liệu camera: {error}")


def save_result(session, outcome, manual=None):
    finish_session(session, outcome)
    results = st.session_state.setdefault("workout_results", {})
    results.setdefault(session.session_id, {
        "mode": session.mode, "status": session.status,
        "reps": session.ai_reps if manual is None else manual["squat"] + manual["pushup"],
        "manual": manual,
    })
    st.session_state["review_session_id"] = session.session_id
    if session.status == "completed":
        st.session_state["has_worked_out_today"] = True
    st.session_state["pending_navigation"] = "📝 Đánh giá Sau Buổi tập"
    st.rerun()


def render_session_view():
    """Hiển thị HUD điều hành buổi tập trực tiếp rảnh tay hoặc tự nhập sau khi tập."""
    if "workout_session" not in st.session_state:
        session = start_session(mode="ai")
        session.status = "paused"  # Chờ camera nhìn thấy người lần đầu.
        st.session_state["workout_session"] = session
        st.session_state["pose_session"] = PoseSession()

    session = st.session_state["workout_session"]
    pose = st.session_state["pose_session"]
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

    col_left, col_right = st.columns([1.6, 1], gap="medium")

    if mode == "🤖 Chế độ AI Vision (Camera Rảnh tay)":
        if session.status in ("completed", "abandoned"):
            st.info("Phiên tập đã kết thúc.")
            if st.button("Bắt đầu buổi mới"):
                del st.session_state["workout_session"]
                st.rerun()
            return
        with col_left:
            st.subheader("Màn hình Giám sát Chuyển động AI (Live Feed)")
            widget_key = f"live_pose_{session.session_id}"
            webcam(
                model=webcam_model(),
                session_id=session.session_id,
                last_event_id=session.last_event_id,
                voice_feedback=pose.voice_feedback,
                key=widget_key,
                on_change=lambda: _on_webcam_change(widget_key),
            )

        with col_right:
            st.subheader("Bảng Điều hành Phiên tập (HUD)")

            with st.container(border=True):
                st.markdown("### Bài tập Hiện tại: **Squat Thể dục (Bodyweight)**")
                st.caption("Mục tiêu buổi tập: 3 Sets × 12 Reps")

                c1, c2 = st.columns(2)
                with c1:
                    st.metric(label="Hiệp hiện tại", value="Set 2 / 3")
                with c2:
                    st.metric(label="Số Reps AI đếm", value=f"{session.ai_reps} Reps")
                    status = "Đang tập" if session.status == "active" else "Tạm dừng"
                    st.caption(f"Trạng thái: {status}")

                if pose.started:
                    st.success("Đã bắt đầu buổi tập bằng cử chỉ giơ tay.")
                else:
                    st.info(
                        "Giơ một tay cao hơn đầu để bắt đầu "
                        f"({pose.start.active_frames}/{pose.start.required_frames} khung hình)."
                    )
                st.progress(
                    pose.stop.active_frames / pose.stop.required_frames,
                    text=("Giữ hai tay thành chữ X để dừng: "
                          f"{pose.stop.active_frames}/{pose.stop.required_frames} khung hình"),
                )
                if pose.stop.is_rep_locked:
                    st.warning("Đã xác nhận dừng; số reps đã được khóa.")
            with st.container(border=True):
                st.markdown("### ⏱️ Đồng hồ Nghỉ Giữa Hiệp (Rest Timer)")
                st.progress(60 / 60, text="Thời gian nghỉ: 60s còn lại")
                st.caption("🔊 Trợ lý Giọng nói sẽ đếm ngược 3... 2... 1... khi sắp hết giờ nghỉ!")

            with st.container(border=True):
                st.markdown("### 📋 Danh sách Bài kế tiếp (Up Next)")
                st.write("1. **Push-up (Hít đất)** — 3 sets × 10 reps")
                st.write("2. **Plank Tĩnh** — 3 sets × 45s")
                st.write("3. **Glute Bridge** — 3 sets × 15 reps")

            st.markdown("---")
            if st.button("🏁 Hoàn tất Buổi tập & Sang Đánh giá", type="primary", use_container_width=True):
                save_result(session, "completed")
            if st.button("Bỏ dở buổi tập", use_container_width=True):
                save_result(session, "abandoned")

    else:
        # Chế độ Tự do Không Camera
        with col_left:
            st.subheader("Ghi nhận Kết quả Buổi tập (Không Camera)")
            st.success("🌱 Bạn đang ở Chế độ Tự do: Thoải mái tập luyện ngoài công viên hoặc không gian riêng tư mà không cần bật webcam.")

            with st.form("manual_session_form"):
                st.markdown("#### Nhập kết quả thực tế từng bài:")
                squat = st.number_input("1. Squat Thể dục — Số reps hoàn thành:", min_value=0, max_value=100, value=36)
                pushup = st.number_input("2. Push-up — Số reps hoàn thành:", min_value=0, max_value=100, value=30)
                plank = st.number_input("3. Plank tĩnh — Tổng giây giữ được:", min_value=0, max_value=300, value=120)

                submitted = st.form_submit_button("Lưu & Kết thúc Buổi tập", type="primary")
                abandoned = st.form_submit_button("Lưu buổi bỏ dở")
                if submitted or abandoned:
                    manual_session = start_session(mode="manual")
                    save_result(manual_session, "completed" if submitted else "abandoned",
                                {"squat": squat, "pushup": pushup, "plank_seconds": plank})

        with col_right:
            st.subheader("Hướng dẫn buổi tập")
            st.info("Hãy hoàn thành bài tập theo khả năng của bạn. Nếu mệt giữa chừng, bạn có thể nghỉ sớm; AI sẽ dựa vào tỉ lệ hoàn thành thực tế để điều chỉnh kế hoạch tiếp theo.")
