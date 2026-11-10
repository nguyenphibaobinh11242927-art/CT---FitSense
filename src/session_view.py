"""Module Phòng tập Rảnh tay & Điều hành Phiên tập Thời gian thực (Session HUD View).

Quản lý chế độ Camera AI Vision (MediaPipe, đếm reps FSM, cử chỉ kép) và Chế độ Tự do Không Camera.
"""

import base64
import math
from dataclasses import dataclass
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.fsm_rep_counter import RepCounterFSM


ROOT = Path(__file__).resolve().parents[1]
webcam = components.declare_component("fitsense_webcam", path=str(ROOT / "assets" / "webcam"))
WEBCAM_KEY = "live_pose"
SHALLOW_ATTEMPT_ANGLE = 130
SHALLOW_ATTEMPTS_TO_CUE = 2


@st.cache_data
def webcam_model():
    model = ROOT / "models" / "pose_landmarker_lite.task"
    return base64.b64encode(model.read_bytes()).decode("ascii")


@dataclass
class SquatCorrection:
    deepest_angle: float = 180
    shallow_attempts: int = 0

    def update(self, angle, previous_state, result):
        if angle is None or result["state"] == RepCounterFSM.STATE_DOWN or result["rep_incremented"]:
            self.deepest_angle = 180
            self.shallow_attempts = 0
        elif result["state"] == RepCounterFSM.STATE_GOING_DOWN:
            self.deepest_angle = min(self.deepest_angle, angle)
        elif previous_state == RepCounterFSM.STATE_GOING_DOWN and result["state"] == RepCounterFSM.STATE_UP:
            attempted_squat = self.deepest_angle <= SHALLOW_ATTEMPT_ANGLE
            self.deepest_angle = 180
            self.shallow_attempts = self.shallow_attempts + 1 if attempted_squat else 0
            if self.shallow_attempts >= SHALLOW_ATTEMPTS_TO_CUE:
                self.shallow_attempts = 0
                return True
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


def _handle_webcam_value(value) -> None:
    if not isinstance(value, dict):
        return

    stream_id = value.get("stream_id")
    sequence = value.get("sequence")
    frames = value.get("frames")
    if (
        not isinstance(stream_id, str)
        or type(sequence) is not int
        or sequence < 0
        or not isinstance(frames, list)
        or len(frames) > 100
    ):
        st.error("Dữ liệu nhận được từ camera không đúng định dạng.")
        return

    if (
        stream_id == st.session_state.get("scrum16_stream_id")
        and sequence <= st.session_state.get("scrum16_stream_sequence", -1)
    ):
        return

    if stream_id != st.session_state.get("scrum16_stream_id"):
        st.session_state["voice_correction"] = SquatCorrection()
    correction = st.session_state.setdefault("voice_correction", SquatCorrection())
    voice_events = []
    try:
        st.session_state["scrum16_session_started"] = process_pose_frames(
            frames,
            st.session_state["scrum16_rep_fsm"],
            st.session_state["scrum16_start_fsm"],
            st.session_state["scrum16_stop_fsm"],
            st.session_state["scrum16_session_started"],
            voice_events=voice_events,
            correction=correction,
        )
    except ValueError as error:
        st.error(f"Không thể xử lý dữ liệu camera: {error}")
        return

    st.session_state["scrum16_stream_id"] = stream_id
    st.session_state["scrum16_stream_sequence"] = sequence
    st.session_state["voice_feedback"] = {
        "stream_id": stream_id,
        "sequence": sequence,
        "event": voice_events[-1] if voice_events else None,
        "stopped": st.session_state["scrum16_stop_fsm"].is_rep_locked,
    }


def _on_webcam_change() -> None:
    # Streamlit invokes this before rerendering, so feedback rides the same rerun.
    _handle_webcam_value(st.session_state.get(WEBCAM_KEY))


def render_session_view():
    """Hiển thị HUD điều hành buổi tập trực tiếp rảnh tay hoặc tự nhập sau khi tập."""
    if "scrum16_rep_fsm" not in st.session_state:
        st.session_state["scrum16_rep_fsm"] = RepCounterFSM()
        st.session_state["scrum16_start_fsm"] = StartGestureFSM()
        st.session_state["scrum16_stop_fsm"] = StopGestureFSM()
        st.session_state["scrum16_session_started"] = False

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
        with col_left:
            st.subheader("Màn hình Giám sát Chuyển động AI (Live Feed)")
            webcam(
                model=webcam_model(),
                voice_feedback=st.session_state.get("voice_feedback"),
                key=WEBCAM_KEY,
                on_change=_on_webcam_change,
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
                    st.metric(
                        label="Số Reps AI đếm",
                        value=f"{st.session_state['scrum16_rep_fsm'].rep_count} Reps",
                    )

                if st.session_state["scrum16_session_started"]:
                    st.success("Đã bắt đầu buổi tập bằng cử chỉ giơ tay.")
                else:
                    start_fsm = st.session_state["scrum16_start_fsm"]
                    st.info(
                        "Giơ một tay cao hơn đầu để bắt đầu "
                        f"({start_fsm.active_frames}/{start_fsm.required_frames} khung hình)."
                    )

                stop_fsm = st.session_state["scrum16_stop_fsm"]
                st.progress(
                    stop_fsm.active_frames / stop_fsm.required_frames,
                    text=(
                        "Giữ hai tay thành chữ X để dừng: "
                        f"{stop_fsm.active_frames}/{stop_fsm.required_frames} khung hình"
                    ),
                )
                if stop_fsm.is_rep_locked:
                    st.warning("Đã xác nhận dừng; số reps đã được khóa.")

            if st.button("Đặt lại phiên tập", key="scrum16_reset_session"):
                st.session_state["scrum16_rep_fsm"].reset()
                st.session_state["scrum16_start_fsm"].reset()
                st.session_state["scrum16_stop_fsm"].reset()
                st.session_state["scrum16_session_started"] = False
                st.session_state.pop("voice_correction", None)
                st.session_state.pop("voice_feedback", None)
                st.rerun()

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
                st.session_state["has_worked_out_today"] = True
                st.session_state["nav_selection"] = "📝 Đánh giá Sau Buổi tập"
                st.rerun()

    else:
        # Chế độ Tự do Không Camera
        with col_left:
            st.subheader("Ghi nhận Kết quả Buổi tập (Không Camera)")
            st.success("🌱 Bạn đang ở Chế độ Tự do: Thoải mái tập luyện ngoài công viên hoặc không gian riêng tư mà không cần bật webcam.")

            with st.form("manual_session_form"):
                st.markdown("#### Nhập kết quả thực tế từng bài:")
                st.number_input("1. Squat Thể dục — Số reps hoàn thành:", min_value=0, max_value=100, value=36)
                st.number_input("2. Push-up — Số reps hoàn thành:", min_value=0, max_value=100, value=30)
                st.number_input("3. Plank tĩnh — Tổng giây giữ được:", min_value=0, max_value=300, value=120)

                submitted = st.form_submit_button("Lưu & Kết thúc Buổi tập", type="primary")
                if submitted:
                    st.session_state["has_worked_out_today"] = True
                    st.success("Đã ghi nhận toàn bộ kết quả vào nhật ký!")
                    st.session_state["nav_selection"] = "📝 Đánh giá Sau Buổi tập"
                    st.rerun()

        with col_right:
            st.subheader("Hướng dẫn buổi tập")
            st.info("Hãy hoàn thành bài tập theo khả năng của bạn. Nếu mệt giữa chừng, bạn có thể nghỉ sớm; AI sẽ dựa vào tỉ lệ hoàn thành thực tế để điều chỉnh kế hoạch tiếp theo.")
