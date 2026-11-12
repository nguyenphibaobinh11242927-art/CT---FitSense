"""Live workout HUD with browser-side pose and workout state machines."""

import base64
import html
import math
from pathlib import Path
import time
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.fsm_rep_counter import RepCounterFSM


ROOT = Path(__file__).resolve().parents[1]
webcam = components.declare_component("fitsense_webcam", path=str(ROOT / "assets" / "webcam"))
_EVENT_TYPES = {
    "TRACKING_LOST",
    "TRACKING_RESTORED",
    "START_EXERCISE",
    "REP_COMPLETED",
    "END_SET",
    "REST_COMPLETE",
    "EXERCISE_READY",
    "WORKOUT_COMPLETE",
}


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
    """Apply timestamped pose samples to the Python FSMs for unit-level integrations."""
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("Mẫu pose không đúng định dạng.")

        start_detected = frame.get("start_detected")
        x_detected = frame.get("x_detected")
        head_detected = frame.get("head_detected")
        knee_angle = frame.get("knee_angle")
        now_ms = frame.get("now_ms")
        if (
            type(start_detected) is not bool
            or type(x_detected) is not bool
            or type(head_detected) is not bool
        ):
            raise ValueError("Trạng thái cử chỉ phải là kiểu đúng/sai.")
        if (
            isinstance(now_ms, bool)
            or not isinstance(now_ms, (int, float))
            or not math.isfinite(now_ms)
        ):
            raise ValueError("Mỗi mẫu pose phải có mốc thời gian hợp lệ.")
        if knee_angle is not None and (
            isinstance(knee_angle, bool)
            or not isinstance(knee_angle, (int, float))
            or not math.isfinite(knee_angle)
            or not 0 <= knee_angle <= 180
        ):
            raise ValueError("Góc gối phải nằm trong khoảng 0 đến 180 độ.")

        if not session_started:
            start_result = start_fsm.update(start_detected, now_ms)
            if start_result["triggered"]:
                session_started = True
            continue

        stop_result = stop_fsm.update(x_detected, head_detected, now_ms)
        if not stop_result["is_rep_locked"]:
            rep_fsm.update(knee_angle)
    return session_started


def _session_exercises() -> list[dict]:
    schedule = st.session_state.get("weekly_schedule", [])
    selected_day = st.session_state.get("selected_session_day")
    day_plan = next(
        (day for day in schedule if day.get("day") == selected_day and day.get("exercises")),
        None,
    )
    if day_plan is None:
        day_plan = next(
            (
                day for day in schedule
                if not day.get("is_rest")
                and any("squat" in str(item.get("name", "")).lower()
                        for item in day.get("exercises", []))
            ),
            None,
        )
    if day_plan is None:
        return [{"name": "Squat", "sets": 3, "target_reps": 12,
                 "rest_seconds": 60, "tracks_squat": True}]

    exercises = []
    for exercise in day_plan.get("exercises", []):
        reps = exercise.get("reps")
        exercises.append({
            "name": str(exercise.get("name", "Bài tập")),
            "sets": exercise.get("sets", 1),
            "target_reps": reps if isinstance(reps, int) and not isinstance(reps, bool) else None,
            "rest_seconds": exercise.get("rest_sec", exercise.get("rest_seconds", 60)),
            "tracks_squat": "squat" in str(exercise.get("name", "")).lower(),
        })
    return exercises or [{"name": "Squat", "sets": 3, "target_reps": 12,
                          "rest_seconds": 60, "tracks_squat": True}]


def _handle_webcam_value(value) -> None:
    if not isinstance(value, dict):
        return
    session_id = value.get("session_id")
    sequence = value.get("sequence")
    events = value.get("events")
    snapshot = value.get("snapshot")
    if (
        not isinstance(session_id, str)
        or type(sequence) is not int
        or sequence < 1
        or not isinstance(events, list)
        or len(events) > 20
        or not isinstance(snapshot, dict)
        or any(
            not isinstance(event, dict)
            or not isinstance(event.get("type"), str)
            or event["type"] not in _EVENT_TYPES
            for event in events
        )
        or not isinstance(snapshot.get("phase"), str)
        or snapshot.get("phase") not in {
            "WAITING_FOR_START", "ACTIVE", "RESTING", "COMPLETE"
        }
        or any(
            type(snapshot.get(key)) is not int or snapshot[key] < 0
            for key in ("exercise_index", "set_number", "sets_total", "reps")
        )
        or type(snapshot.get("tracking")) is not bool
    ):
        st.error("Dữ liệu sự kiện nhận diện từ camera không đúng định dạng.")
        return

    for event in events:
        if event["type"] == "END_SET" and (
            not isinstance(event.get("exercise_name"), str)
            or type(event.get("exercise_index")) is not int
            or type(event.get("set_number")) is not int
            or type(event.get("reps")) is not int
            or event["reps"] < 0
            or type(event.get("rest_seconds")) is not int
            or event["rest_seconds"] < 0
        ):
            st.error("Sự kiện END_SET thiếu thông tin hiệp hoặc thời gian nghỉ hợp lệ.")
            return

    if session_id != st.session_state.get("scrum16_session_id"):
        return
    if sequence <= st.session_state.get("scrum16_event_sequence", 0):
        return

    st.session_state["scrum16_event_sequence"] = sequence
    st.session_state["scrum16_snapshot"] = snapshot
    for event in events:
        if event["type"] == "END_SET":
            control_event = {
                **event,
                "event_id": f"{session_id}:{sequence}:END_SET",
            }
            st.session_state["workout_control_event"] = control_event
            st.session_state.setdefault("scrum16_completed_sets", []).append(control_event)
            st.session_state["scrum16_rest_timer"] = {
                "status": "running",
                "duration_seconds": event["rest_seconds"],
                "deadline": time.time() + event["rest_seconds"],
                "set_number": event["set_number"],
                "reps": event["reps"],
            }
        elif event["type"] == "REST_COMPLETE":
            st.session_state["workout_control_event"] = {
                **event,
                "event_id": f"{session_id}:{sequence}:REST_COMPLETE",
            }
            timer = st.session_state.get("scrum16_rest_timer")
            if timer is not None:
                timer["status"] = "complete"
        elif event["type"] == "WORKOUT_COMPLETE":
            st.session_state["workout_control_event"] = {
                **event,
                "event_id": f"{session_id}:{sequence}:{event['type']}",
            }


def _reset_session() -> None:
    st.session_state["scrum16_session_id"] = str(uuid4())
    st.session_state["scrum16_event_sequence"] = 0
    st.session_state["scrum16_snapshot"] = None
    st.session_state["scrum16_completed_sets"] = []
    st.session_state["scrum16_rest_timer"] = None
    st.session_state.pop("workout_control_event", None)


def _render_rest_countdown(timer: dict | None) -> None:
    if not timer:
        st.caption("Đồng hồ bắt đầu khi camera gửi sự kiện END_SET.")
        return

    if timer["status"] == "complete":
        st.success("Hết giờ nghỉ — sẵn sàng cho hiệp tiếp theo.")
        return

    remaining = max(0.0, timer["deadline"] - time.time())
    duration = timer["duration_seconds"]
    if duration == 0:
        st.info("Không cần nghỉ; đang chuyển tiếp sang hiệp tiếp theo.")
        return

    progress = min(1.0, remaining / duration)
    remaining_label = html.escape(f"{math.ceil(remaining)} giây")
    bar_width = round(progress * 100)
    components.html(
        f"""
        <div style="font-family: sans-serif; color:#f1f5f9; background:#101d31;
                    border-radius:8px; padding:10px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <strong>Thời gian nghỉ</strong><strong id="rest-remaining">{remaining_label}</strong>
          </div>
          <div style="height:10px; background:#25364a; border-radius:8px; overflow:hidden;">
            <div id="rest-progress" style="height:100%; width:{bar_width}%;
                 background:#42c982; transition:width .25s linear;"></div>
          </div>
          <script>
            const deadline = Date.now() + {remaining:.3f} * 1000;
            const duration = {duration};
            const remainingLabel = document.getElementById("rest-remaining");
            const progressBar = document.getElementById("rest-progress");
            function updateRestTimer() {{
              const secondsLeft = Math.max(0, (deadline - Date.now()) / 1000);
              remainingLabel.textContent = Math.ceil(secondsLeft) + " giây";
              progressBar.style.width =
                Math.min(100, secondsLeft / duration * 100) + "%";
            }}
            updateRestTimer();
            setInterval(updateRestTimer, 250);
          </script>
        </div>
        """,
        height=62,
        scrolling=False,
    )


@st.fragment
def render_session_view():
    """Render the session HUD in an isolated Streamlit fragment."""
    if "scrum16_session_id" not in st.session_state:
        _reset_session()

    exercises = _session_exercises()
    session_id = st.session_state["scrum16_session_id"]
    st.header("⚡ Phòng tập Trực tiếp (Workout HUD)")

    c_empty_l, c_center, c_empty_r = st.columns([1, 2.8, 1])
    with c_center:
        st.markdown(
            "<div style='text-align: center; font-weight: 700; font-size: 15px; "
            "margin-bottom: 8px;'>Lựa chọn Chế độ Giám sát:</div>",
            unsafe_allow_html=True,
        )
        mode = st.radio(
            "Lựa chọn Chế độ Giám sát:",
            options=["🤖 Chế độ AI Vision (Camera Rảnh tay)", "📝 Chế độ Tự do (Không dùng Camera)"],
            horizontal=True,
            label_visibility="collapsed",
            key="session_mode_selector",
        )

    col_left, col_right = st.columns([1.6, 1], gap="medium")
    if mode == "🤖 Chế độ AI Vision (Camera Rảnh tay)":
        with col_left:
            st.subheader("Màn hình Giám sát Chuyển động AI (Live Feed)")
            webcam_value = webcam(
                model=webcam_model(),
                session_id=session_id,
                exercises=exercises,
                key=f"live_pose_{session_id}",
            )
            _handle_webcam_value(webcam_value)

        snapshot = st.session_state.get("scrum16_snapshot") or {}
        current_index = min(snapshot.get("exercise_index", 0), len(exercises) - 1)
        current_exercise = exercises[current_index]
        with col_right:
            st.subheader("Bảng Điều hành Phiên tập (HUD)")
            with st.container(border=True):
                st.markdown(f"### Bài tập hiện tại: **{current_exercise['name']}**")
                st.caption("Nhận diện squat và cử chỉ chạy trực tiếp trên trình duyệt.")
                c1, c2 = st.columns(2)
                c1.metric(
                    "Hiệp hiện tại",
                    f"{snapshot.get('set_number', 1)} / {snapshot.get('sets_total', current_exercise['sets'])}",
                )
                c2.metric("Số Reps AI đếm", f"{snapshot.get('reps', 0)} Reps")
                phase = snapshot.get("phase", "WAITING_FOR_START")
                if phase == "WAITING_FOR_START":
                    st.info("Giơ một tay cao hơn đầu trong 1,5 giây để bắt đầu bài tập.")
                elif phase == "ACTIVE":
                    st.success("Đang tập. Giữ chữ X trong 1,5 giây để kết thúc hiệp.")
                elif phase == "RESTING":
                    st.info(
                        "Hiệp đã chốt. Đồng hồ nghỉ đang chạy bên dưới."
                    )
                elif phase == "COMPLETE":
                    st.success("Đã hoàn thành kế hoạch tập hôm nay.")
                elif snapshot.get("tracking") is False:
                    st.warning("Mất dấu cơ thể; đứng thẳng trong khung hình để tiếp tục an toàn.")

                if not current_exercise["tracks_squat"]:
                    st.warning("Bài tập này chưa được hỗ trợ đếm reps bằng pose squat.")

            if st.button("Đặt lại phiên tập", key="scrum16_reset_session"):
                _reset_session()
                st.rerun()

            with st.container(border=True):
                st.markdown("### ⏱️ Đồng hồ Nghỉ Giữa Hiệp")
                _render_rest_countdown(st.session_state.get("scrum16_rest_timer"))

            with st.container(border=True):
                st.markdown("### 📋 Bài tập trong kế hoạch")
                for index, exercise in enumerate(exercises):
                    st.write(f"{index + 1}. **{exercise['name']}** — "
                             f"{exercise['sets']} hiệp, nghỉ {exercise['rest_seconds']} giây")

            st.markdown("---")
            if st.button(
                "🏁 Hoàn tất Buổi tập & Sang Đánh giá",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["has_worked_out_today"] = True
                st.session_state["nav_selection"] = "📝 Đánh giá Sau Buổi tập"
                st.rerun()
    else:
        with col_left:
            st.subheader("Ghi nhận Kết quả Buổi tập (Không Camera)")
            st.success(
                "🌱 Bạn đang ở Chế độ Tự do: Thoải mái tập luyện mà không cần bật webcam."
            )
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
            st.info(
                "Hãy hoàn thành bài tập theo khả năng của bạn. Nếu mệt giữa chừng, "
                "bạn có thể nghỉ sớm; AI sẽ dựa vào tỉ lệ hoàn thành thực tế để điều chỉnh kế hoạch."
            )
