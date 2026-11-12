"""Module Phòng tập Rảnh tay & Điều hành Phiên tập Thời gian thực (Session HUD View).

Quản lý chế độ Camera AI Vision (MediaPipe, đếm reps FSM, cử chỉ kép) và Chế độ Tự do Không Camera.
"""

import math
import time
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.fsm_rep_counter import RepCounterFSM
from src.workout_session import WorkoutSession


ROOT = Path(__file__).resolve().parents[1]
webcam = components.declare_component("fitsense_webcam", path=str(ROOT / "assets" / "webcam"))


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
        timestamp_ms = frame.get("timestamp_ms")
        if timestamp_ms is not None and (
            isinstance(timestamp_ms, bool) or not isinstance(timestamp_ms, (int, float))
            or not math.isfinite(timestamp_ms) or timestamp_ms < 0
        ):
            raise ValueError("Thời gian khung hình không hợp lệ.")
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
            start_result = start_fsm.update(start_detected, timestamp_ms)
            if start_result["triggered"]:
                session_started = True
            continue

        stop_result = stop_fsm.update(x_detected, head_detected, timestamp_ms)
        if not stop_result["is_rep_locked"]:
            rep_fsm.update(knee_angle)
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

    workout = st.session_state["fitsense_workout"]
    if workout.phase in {"resting", "paused", "finished"}:
        st.session_state["scrum16_stream_id"] = stream_id
        st.session_state["scrum16_stream_sequence"] = sequence
        return
    try:
        st.session_state["scrum16_session_started"] = process_pose_frames(
            frames,
            st.session_state["scrum16_rep_fsm"],
            st.session_state["scrum16_start_fsm"],
            st.session_state["scrum16_stop_fsm"],
            st.session_state["scrum16_session_started"],
        )
    except ValueError as error:
        st.error(f"Không thể xử lý dữ liệu camera: {error}")
        return

    st.session_state["scrum16_stream_id"] = stream_id
    st.session_state["scrum16_stream_sequence"] = sequence
    latest = frames[-1] if frames else {}
    if st.session_state["scrum16_session_started"]:
        workout.start()
        workout.update_reps(st.session_state["scrum16_rep_fsm"].rep_count)
    stop_fsm = st.session_state["scrum16_stop_fsm"]
    if stop_fsm.is_rep_locked and workout.phase == "active":
        workout.finish_set(time.monotonic())
    timestamp = latest.get("timestamp_ms")
    st.session_state["scrum16_stop_progress"] = (
        min(1.0, max(0.0, (timestamp - stop_fsm._hold_start_ms) / (1000 * stop_fsm.hold_seconds)))
        if timestamp is not None and stop_fsm._hold_start_ms is not None
        else stop_fsm.active_frames / stop_fsm.required_frames
    )


def render_session_view():
    """Hiển thị HUD điều hành buổi tập trực tiếp rảnh tay hoặc tự nhập sau khi tập."""
    if "scrum16_rep_fsm" not in st.session_state:
        st.session_state["scrum16_rep_fsm"] = RepCounterFSM()
        st.session_state["scrum16_start_fsm"] = StartGestureFSM()
        st.session_state["scrum16_stop_fsm"] = StopGestureFSM(dropout_grace_ms=180.0)
        st.session_state["scrum16_session_started"] = False
    if "fitsense_workout" not in st.session_state:
        st.session_state["fitsense_workout"] = WorkoutSession()
    workout = st.session_state["fitsense_workout"]

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
            webcam_value = webcam(key="live_pose")
            _handle_webcam_value(webcam_value)

        with col_right:
            st.subheader("Bảng Điều hành Phiên tập (HUD)")

            with st.container(border=True):
                st.markdown("### Bài tập Hiện tại: **Squat Thể dục (Bodyweight)**")
                st.caption(f"Mục tiêu: {workout.total_sets} hiệp × {workout.target_reps} reps; nghỉ {workout.rest_seconds}s")

                c1, c2 = st.columns(2)
                with c1:
                    st.metric(label="Hiệp hiện tại", value=f"Set {workout.set_number} / {workout.total_sets}")
                with c2:
                    st.metric(
                        label="Số Reps AI đếm",
                        value=f"{workout.current_reps} Reps",
                    )

                if workout.phase == "active":
                    st.success("Đang tập. Cử chỉ chữ X sẽ kết thúc hiệp hiện tại.")
                elif workout.phase == "resting":
                    st.info("Đã kết thúc hiệp. Hãy nghỉ trước khi tập tiếp.")
                elif workout.phase == "paused":
                    st.warning("Buổi tập đang tạm ngưng.")
                elif workout.phase == "finished":
                    st.success("Buổi tập đã kết thúc.")
                else:
                    start_fsm = st.session_state["scrum16_start_fsm"]
                    st.info(
                        "Giơ một tay cao hơn đầu và giữ liên tục khoảng 1,5 giây "
                        "(tiến trình được tính theo thời gian camera)."
                    )

                stop_fsm = st.session_state["scrum16_stop_fsm"]
                st.progress(
                    st.session_state.get("scrum16_stop_progress", 0.0),
                    text="Giữ hai tay chéo chữ X liên tục 1,5 giây để dừng",
                )
                if stop_fsm.is_rep_locked:
                    st.caption("Cử chỉ X đã ghi nhận kết thúc hiệp.")

            if st.button("Đặt lại phiên tập", key="scrum16_reset_session"):
                st.session_state["scrum16_rep_fsm"].reset()
                st.session_state["scrum16_start_fsm"].reset()
                st.session_state["scrum16_stop_fsm"].reset()
                st.session_state["scrum16_session_started"] = False
                st.session_state["scrum16_stop_progress"] = 0.0
                st.session_state["fitsense_workout"] = WorkoutSession()
                st.rerun()

            with st.container(border=True):
                st.markdown("### ⏱️ Đồng hồ Nghỉ Giữa Hiệp")
                now = time.monotonic()
                if workout.phase == "resting":
                    remaining = workout.rest_remaining(now)
                    st.progress(min(1.0, remaining / max(1, workout.rest_seconds)),
                                text=f"Còn {math.ceil(remaining)} giây")
                    if remaining <= 0 and st.button("▶️ Bắt đầu hiệp kế tiếp", key="fitsense_next_set"):
                        if workout.resume_after_rest(time.monotonic()):
                            st.session_state["scrum16_rep_fsm"].reset()
                            st.session_state["scrum16_stop_fsm"].reset()
                            st.session_state["scrum16_stop_progress"] = 0.0
                            st.rerun()
                    elif remaining > 0:
                        st.caption("Thời gian nghỉ được tính theo đồng hồ thực; dùng nút Làm mới để cập nhật số hiển thị.")
                elif workout.phase == "paused":
                    st.info("Đã tạm dừng đồng hồ.")
                else:
                    st.caption("Đồng hồ sẽ bắt đầu sau khi kết thúc hiệp.")

            a1, a2, a3 = st.columns(3)
            with a1:
                if workout.phase in {"active", "resting"} and st.button("⏸️ Tạm ngưng", key="fitsense_pause"):
                    workout.pause(time.monotonic())
                    st.rerun()
                elif workout.phase == "paused" and st.button("▶️ Tiếp tục", key="fitsense_resume"):
                    workout.resume(time.monotonic())
                    st.rerun()
            with a2:
                if workout.phase == "active" and st.button("✅ Kết thúc hiệp", key="fitsense_finish_set"):
                    workout.update_reps(st.session_state["scrum16_rep_fsm"].rep_count)
                    workout.finish_set(time.monotonic())
                    st.rerun()
                if workout.phase == "resting" and st.button("🔄 Làm mới giờ nghỉ", key="fitsense_refresh_rest"):
                    st.rerun()
            with a3:
                if workout.phase != "finished" and st.button("⏹️ Kết thúc buổi", key="fitsense_end"):
                    workout.end_early()
                    st.rerun()
            st.caption(f"Đã ghi nhận {workout.total_reps} / {workout.total_sets * workout.target_reps} reps dự kiến.")

            with st.container(border=True):
                st.markdown("### 📋 Bài tập trong giáo án (tham khảo)")
                selected_day = st.session_state.get("selected_session_day")
                days = st.session_state.get("weekly_schedule", [])
                selected_plan = next(
                    (day for day in days if day.get("day") == selected_day),
                    None,
                )
                if selected_plan:
                    for number, ex in enumerate(selected_plan.get("exercises", []), start=1):
                        st.write(f"{number}. **{ex.get('name', 'Bài tập')}** — "
                                 f"{ex.get('sets', 3)} hiệp × {ex.get('reps', 10)} reps")
                else:
                    st.caption("Chưa chọn ngày tập trong giáo án. Vào Kế hoạch và chọn 'Tập ngay buổi này'.")
                st.caption("Lưu ý: Bộ đếm camera hiện hỗ trợ Squat; các bài khác cần thuật toán đếm riêng.")

            st.markdown("---")
            if st.button("🏁 Lưu kết quả & Sang Đánh giá", type="primary", use_container_width=True,
                         disabled=workout.phase != "finished"):
                st.session_state["fitsense_session_summary"] = workout.summary()
                st.session_state["has_worked_out_today"] = workout.total_reps > 0
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