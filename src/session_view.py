"""Module Phòng tập Rảnh tay & Điều hành Phiên tập Thời gian thực (Session HUD View).

Quản lý chế độ Camera AI Vision (MediaPipe, đếm reps FSM, cử chỉ kép) và Chế độ Tự do Không Camera.
"""

from src.workout_session import finish_session, start_session
from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.fsm_rep_counter import RepCounterFSM
from dataclasses import dataclass, field
import math
import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parents[1]
webcam = components.declare_component("fitsense_webcam", path=str(ROOT / "assets" / "webcam"))


@st.cache_data
def webcam_model():
    model = ROOT / "models" / "pose_landmarker_lite.task"
    return base64.b64encode(model.read_bytes()).decode("ascii")


def process_pose_frames(
    frames: list[dict],
    rep_fsm: RepCounterFSM,
    start_fsm: StartGestureFSM,
    stop_fsm: StopGestureFSM,
    session_started: bool,
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
            rep_fsm.update(knee_angle)
    return session_started


@dataclass
class PoseSession:
    rep: RepCounterFSM = field(default_factory=RepCounterFSM)
    start: StartGestureFSM = field(default_factory=StartGestureFSM)
    stop: StopGestureFSM = field(default_factory=StopGestureFSM)
    started: bool = False

    def consume(self, session, batch):
        if not batch or batch.get("session_id") != session.session_id:
            return
        if session.status in ("completed", "abandoned") or session.mode != "ai":
            return
        end = batch.get("sequence")
        frames = batch.get("frames")
        if type(end) is not int or not isinstance(frames, list) or not 0 < len(frames) <= 100:
            return
        first = end - len(frames) + 1
        if end <= session.last_event_id or first < 1:
            return
        if first > session.last_event_id + 1:
            self.rep.update(None)
            self.start.update(False)
            self.stop.update(False, False)
        for seq, frame in enumerate(frames, first):
            if seq <= session.last_event_id:
                continue
            self.started = process_pose_frames([frame], self.rep, self.start, self.stop, self.started)
            session.ai_reps = self.rep.rep_count
            tracking = frame["knee_angle"] is not None
            session.status = "active" if tracking and self.started and not self.stop.is_rep_locked else "paused"
            session.last_event_id = seq


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
            event = webcam(
                model=webcam_model(),
                session_id=session.session_id,
                last_event_id=session.last_event_id,
                key=f"live_pose_{session.session_id}",
            )

            pose = st.session_state.setdefault("pose_session", PoseSession())
            pose.consume(session, event)
            if pose.stop.is_rep_locked:
                st.warning("Cử chỉ chữ X đã khóa số rep.")
            elif not pose.started:
                st.info(f"Giơ tay cao để bắt đầu: {pose.start.active_frames}/{pose.start.required_frames}")
            else:
                st.caption(f"Đã bắt đầu · Giữ chữ X để khóa: {pose.stop.active_frames}/{pose.stop.required_frames}")

        with col_right:
            st.subheader("Bảng Điều hành Phiên tập (HUD)")

            with st.container(border=True):
                st.markdown("### Bài tập Hiện tại: **Squat Thể dục (Bodyweight)**")
                st.caption("Mục tiêu buổi tập: 3 Sets × 12 Reps")

                c1, c2 = st.columns(2)
                with c1:
                    st.metric(label="Hiệp hiện tại", value="Set 2 / 3")
                with c2:
                    st.metric("Số Reps AI đếm", session.ai_reps)
                    status_labels = {
                        "paused": "Tạm dừng",
                        "active": "Đang tập",
                        "completed": "Đã hoàn thành",
                        "abandoned": "Đã bỏ dở",
                    }
                    st.caption(f"Trạng thái: {status_labels[session.status]}")
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
