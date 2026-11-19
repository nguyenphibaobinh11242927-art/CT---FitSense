"""Kiểm thử toàn diện cho Module Session HUD, Đồng hồ nghỉ Rest Timer & Up Next List (SCRUM-19)."""

import unittest
from datetime import date
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.session_view import PoseSession
import src.session_view as session_view
from src.workout_session import start_session


class Scrum19SessionHudTests(unittest.TestCase):
    """Bộ ca kiểm thử cho các chức năng nghiệp vụ của SCRUM-19."""

    def setUp(self):
        """Khởi tạo trạng thái trước mỗi bài test."""
        st.session_state.clear()
        session_view._init_hud_state()

    def test_default_session_exercises_structure(self):
        """Kiểm tra danh mục bài tập mặc định đầy đủ các trường thông tin."""
        exercises = session_view.DEFAULT_SESSION_EXERCISES
        self.assertGreaterEqual(len(exercises), 3)
        for ex in exercises:
            self.assertIn("name", ex)
            self.assertIn("sets", ex)
            self.assertIn("reps", ex)
            self.assertIn("rest_sec", ex)
            self.assertIn("primary_muscle", ex)
            self.assertIn("form_tip", ex)
            self.assertIn("substitute", ex)
            self.assertGreater(ex["sets"], 0)
            self.assertGreater(ex["rest_sec"], 0)

    def test_hud_state_initialization(self):
        """Kiểm tra khởi tạo trạng thái HUD đầy đủ các biến điều khiển."""
        self.assertEqual(st.session_state["hud_current_ex_idx"], 0)
        self.assertEqual(st.session_state["hud_current_set"], 1)
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_rest_duration"], 60)
        self.assertEqual(st.session_state["hud_rest_remaining"], 60)
        self.assertIsNone(st.session_state["hud_rest_start_time"])
        self.assertFalse(st.session_state["hud_rest_paused"])
        self.assertEqual(st.session_state["hud_completed_sets"], {})

    def test_get_session_exercises_with_custom_override(self):
        """Kiểm tra danh sách bài tập ưu tiên custom exercises nếu người dùng đổi bài."""
        custom = [
            {"name": "Hít đất vỗ tay", "sets": 4, "reps": 8, "rest_sec": 90},
        ]
        st.session_state["hud_custom_exercises"] = custom
        resolved = session_view._get_session_exercises()
        self.assertEqual(resolved[0]["name"], "Hít đất vỗ tay")
        self.assertEqual(resolved[0]["sets"], 4)
        self.assertEqual(resolved[0]["rest_sec"], 90)

    def test_advance_set_within_same_exercise(self):
        """Khi hoàn thành hiệp 1/3, HUD bật đồng hồ nghỉ và chuẩn bị hiệp 2."""
        exercises = [
            {"name": "Squat", "sets": 3, "reps": 12, "rest_sec": 45},
            {"name": "Push-up", "sets": 3, "reps": 10, "rest_sec": 60},
        ]
        session_view._advance_hud_set(exercises)
        self.assertTrue(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_rest_duration"], 45)
        self.assertEqual(st.session_state["hud_rest_remaining"], 45)
        self.assertIsNotNone(st.session_state["hud_rest_start_time"])
        self.assertIn("0_1", st.session_state["hud_completed_sets"])
        self.assertIn("Hiệp 2/3", st.session_state["hud_next_target"])

        # Kết thúc thời gian nghỉ -> Vào hiệp 2
        session_view._finish_rest_period(exercises)
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_current_set"], 2)
        self.assertEqual(st.session_state["hud_current_ex_idx"], 0)

    def test_x_ends_set_records_reps_and_hand_starts_next_set(self):
        exercises = [
            {"name": "Squat", "sets": 2, "reps": 12, "rest_sec": 45},
        ]
        session = start_session()
        pose = PoseSession(
            start=StartGestureFSM(required_frames=1),
            stop=StopGestureFSM(required_frames=1),
        )
        st.session_state["workout_session"] = session
        st.session_state["pose_session"] = pose
        st.session_state["hud_custom_exercises"] = exercises
        st.session_state["camera_batch"] = {
            "session_id": session.session_id,
            "stream_id": "test-camera",
            "sequence": 7,
            "frames": [
                {"start_detected": True, "x_detected": False, "head_detected": True, "knee_angle": None},
                *[
                    {"start_detected": False, "x_detected": False, "head_detected": True, "knee_angle": angle}
                    for angle in (165, 145, 90, 120, 165)
                ],
                {"start_detected": False, "x_detected": True, "head_detected": True, "knee_angle": None},
            ],
        }

        session_view._on_webcam_change("camera_batch")

        self.assertTrue(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_completed_set_reps"]["0_1"], 1)
        self.assertFalse(st.session_state["hud_set_started"])
        self.assertFalse(pose.started)
        self.assertEqual(session.ai_reps, 1)

        # A duplicate batch must not record or advance this set a second time.
        session_view._on_webcam_change("camera_batch")
        self.assertEqual(st.session_state["hud_completed_set_reps"], {"0_1": 1})
        self.assertEqual(st.session_state["hud_current_set"], 1)

        st.session_state["camera_batch"] = {
            "session_id": session.session_id,
            "stream_id": "test-camera",
            "sequence": 8,
            "frames": [
                {"start_detected": True, "x_detected": False, "head_detected": True, "knee_angle": None},
            ],
        }
        session_view._on_webcam_change("camera_batch")

        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_current_set"], 2)
        self.assertTrue(st.session_state["hud_set_started"])
        self.assertTrue(pose.started)
        self.assertEqual(st.session_state["hud_set_rep_start"], 1)

    def test_rest_timer_expiry_waits_for_hand_gesture(self):
        exercises = [{"name": "Squat", "sets": 2, "reps": 12, "rest_sec": 1}]
        session_view._advance_hud_set(exercises)
        pose = PoseSession(start=StartGestureFSM(required_frames=1))
        st.session_state["hud_rest_duration"] = 1
        st.session_state["hud_rest_start_time"] = 90

        with patch("src.session_view.time.time", return_value=92):
            self.assertTrue(session_view._check_auto_advance_rest_timer(exercises, pose))

        self.assertEqual(st.session_state["hud_current_set"], 2)
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertFalse(st.session_state["hud_set_started"])

    def test_advance_to_next_exercise_after_final_set(self):
        """Khi hoàn thành hiệp cuối cùng (3/3) của bài 1, HUD kích hoạt nghỉ chuyển bài sang bài 2."""
        exercises = [
            {"name": "Squat", "sets": 3, "reps": 12, "rest_sec": 60},
            {"name": "Push-up", "sets": 3, "reps": 10, "rest_sec": 60},
        ]
        st.session_state["hud_current_set"] = 3
        session_view._advance_hud_set(exercises)

        self.assertTrue(st.session_state["hud_is_resting"])
        self.assertIn("Push-up", st.session_state["hud_next_target"])

        # Kết thúc nghỉ -> Sang bài tiếp theo (index 1), hiệp 1
        session_view._finish_rest_period(exercises)
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_current_ex_idx"], 1)
        self.assertEqual(st.session_state["hud_current_set"], 1)

    def test_all_exercises_completed(self):
        """Khi hoàn thành bài tập cuối cùng trong danh sách, đánh dấu hoàn tất toàn bộ."""
        exercises = [
            {"name": "Squat", "sets": 2, "reps": 12, "rest_sec": 60},
        ]
        st.session_state["hud_current_ex_idx"] = 0
        st.session_state["hud_current_set"] = 2
        session_view._advance_hud_set(exercises)

        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertTrue(st.session_state.get("hud_all_completed"))

    def test_skip_to_next_exercise(self):
        """Kiểm tra chức năng bỏ qua bài tập hiện tại để chuyển sang bài kế tiếp."""
        exercises = [
            {"name": "Squat", "sets": 3, "reps": 12, "rest_sec": 60},
            {"name": "Push-up", "sets": 3, "reps": 10, "rest_sec": 45},
            {"name": "Plank", "sets": 3, "reps": 30, "rest_sec": 30},
        ]
        st.session_state["hud_current_ex_idx"] = 0
        st.session_state["hud_current_set"] = 2
        session_view._skip_to_next_exercise(exercises)

        self.assertEqual(st.session_state["hud_current_ex_idx"], 1)
        self.assertEqual(st.session_state["hud_current_set"], 1)
        self.assertFalse(st.session_state["hud_is_resting"])

    def test_custom_rest_presets(self):
        """Kiểm tra tùy chỉnh thời gian nghỉ theo thể trạng người dùng."""
        exercises = [
            {"name": "Squat", "sets": 3, "reps": 12, "rest_sec": 60},
        ]
        st.session_state["hud_custom_rest_sec"] = 90
        session_view._advance_hud_set(exercises)

        self.assertEqual(st.session_state["hud_rest_duration"], 90)
        self.assertEqual(st.session_state["hud_rest_remaining"], 90)

    def test_adjust_rest_timer_plus_minus_15s(self):
        """Kiểm tra nút +15s và -15s tăng/giảm thời gian nghỉ và giới hạn biên tối thiểu 10s."""
        exercises = [
            {"name": "Squat", "sets": 3, "reps": 12, "rest_sec": 60},
        ]
        st.session_state["hud_is_resting"] = True
        st.session_state["hud_rest_duration"] = 60
        st.session_state["hud_rest_remaining"] = 50
        st.session_state["hud_rest_start_time"] = 90

        with patch("src.session_view.time.time", return_value=100):
            session_view._adjust_rest_timer(15)
            self.assertEqual(st.session_state["hud_rest_duration"], 75)
            self.assertEqual(st.session_state["hud_rest_remaining"], 65)
            self.assertFalse(session_view._check_auto_advance_rest_timer(exercises))
            self.assertEqual(st.session_state["hud_rest_remaining"], 65)

            session_view._adjust_rest_timer(-15)
            self.assertEqual(st.session_state["hud_rest_duration"], 60)
            self.assertEqual(st.session_state["hud_rest_remaining"], 50)
            self.assertFalse(session_view._check_auto_advance_rest_timer(exercises))
            self.assertEqual(st.session_state["hud_rest_remaining"], 50)

            # Giảm liên tục kiểm tra giới hạn dưới (min 10s không bị âm)
            session_view._adjust_rest_timer(-60)
            self.assertEqual(st.session_state["hud_rest_duration"], 10)
            self.assertEqual(st.session_state["hud_rest_remaining"], 0)

    def test_auto_advance_rest_timer_when_countdown_reaches_zero(self):
        """Khi wall-clock đếm hết thời gian nghỉ, hệ thống tự động chuyển hiệp mà không cần bấm thủ công."""
        import time
        exercises = [
            {"name": "Squat", "sets": 3, "reps": 12, "rest_sec": 45},
        ]
        session_view._advance_hud_set(exercises)
        self.assertTrue(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_current_set"], 1)

        # Giả lập wall-clock trôi qua 50 giây (lớn hơn 45s thời gian nghỉ)
        st.session_state["hud_rest_start_time"] = time.time() - 50

        # Kích hoạt kiểm tra auto-advance
        advanced = session_view._check_auto_advance_rest_timer(exercises)
        self.assertTrue(advanced)
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_current_set"], 2)
        self.assertIsNone(st.session_state["hud_rest_start_time"])

    def test_auto_advance_frozen_when_timer_paused(self):
        """Khi buổi tập đang tạm dừng (user_paused hoặc hud_rest_paused), không tự động chuyển hiệp."""
        import time
        exercises = [
            {"name": "Squat", "sets": 3, "reps": 12, "rest_sec": 45},
        ]
        for paused_key in ("session_user_paused", "hud_rest_paused"):
            with self.subTest(paused_key=paused_key):
                session_view._init_hud_state(force=True)
                session_view._advance_hud_set(exercises)
                st.session_state["hud_rest_start_time"] = time.time() - 50
                st.session_state["session_user_paused"] = False
                st.session_state["hud_rest_paused"] = False
                st.session_state[paused_key] = True

                advanced = session_view._check_auto_advance_rest_timer(exercises)
                self.assertFalse(advanced)
                self.assertTrue(st.session_state["hud_is_resting"])
                self.assertEqual(st.session_state["hud_current_set"], 1)

    def test_rest_timer_fragment_auto_advances(self):
        """The runtime timer fragment advances once the stored wall-clock deadline passes."""
        script = """
import time
import streamlit as st
from src.session_view import _init_hud_state, _run_rest_timer_tick

if not st.session_state.get("_timer_test_initialized"):
    _init_hud_state()
    st.session_state["_timer_test_initialized"] = True
    st.session_state["hud_is_resting"] = True
    st.session_state["hud_current_set"] = 1
    st.session_state["hud_rest_duration"] = 1
    st.session_state["hud_rest_start_time"] = time.time() - 2
_run_rest_timer_tick([{"name": "Squat", "sets": 3, "reps": 12, "rest_sec": 1}])
"""
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["hud_is_resting"])
        self.assertEqual(app.session_state["hud_current_set"], 2)

    def test_skip_last_exercise_while_resting_cleans_timer_state(self):
        """Bỏ qua bài tập cuối cùng khi đang nghỉ phải dọn dẹp sạch sẽ timer, không leak sang phiên sau."""
        exercises = [
            {"name": "Squat", "sets": 2, "reps": 12, "rest_sec": 60},
        ]
        # Bắt đầu nghỉ ở bài cuối cùng
        session_view._advance_hud_set(exercises)
        self.assertTrue(st.session_state["hud_is_resting"])
        self.assertIsNotNone(st.session_state["hud_rest_start_time"])

        # Bấm bỏ qua bài này
        session_view._skip_to_next_exercise(exercises)

        # Xác minh: Toàn bộ cờ nghỉ và timer được xóa sạch
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertIsNone(st.session_state["hud_rest_start_time"])
        self.assertEqual(st.session_state["hud_rest_remaining"], 0)
        self.assertFalse(st.session_state["hud_rest_paused"])
        self.assertIsNone(st.session_state["hud_rest_paused_at"])
        self.assertNotIn("hud_next_target", st.session_state)
        self.assertTrue(st.session_state["hud_all_completed"])

        # A normal render must not clear completion state; a new session explicitly resets it.
        session_view._init_hud_state()
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertTrue(st.session_state["hud_all_completed"])

        session_view._init_hud_state(force=True)
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertFalse(st.session_state["hud_all_completed"])
        self.assertEqual(st.session_state["hud_current_ex_idx"], 0)
        self.assertEqual(st.session_state["hud_current_set"], 1)
        self.assertEqual(st.session_state["hud_rest_duration"], 60)
        self.assertEqual(st.session_state["hud_rest_remaining"], 60)


class Scrum19AppIntegrationTests(unittest.TestCase):
    """Kiểm thử tích hợp giao diện AppTest cho HUD và Rest Timer."""

    def test_render_session_view_ai_vision_mode(self):
        """Chạy giao diện Phòng tập Trực tiếp qua AppTest và xác minh các thành phần HUD."""
        script = """
import streamlit as st
from src.session_view import render_session_view
render_session_view()
"""
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)

        # Kiểm tra sự tồn tại của các nút điều khiển chính
        pause_btns = [b for b in app.button if "Tạm ngưng" in b.label]
        self.assertEqual(len(pause_btns), 1)

        finish_btns = [b for b in app.button if "Kết thúc" in b.label]
        self.assertEqual(len(finish_btns), 1)

        # Kiểm tra nút Hoàn thành hiệp & Bật nghỉ
        set_done_btns = [b for b in app.button if "Hoàn thành hiệp" in b.label]
        self.assertEqual(len(set_done_btns), 1)

        # Kiểm tra nút Bỏ qua bài này
        skip_btns = [b for b in app.button if "Bỏ qua bài này" in b.label]
        self.assertEqual(len(skip_btns), 1)

    def test_ai_hud_auto_advances_expired_rest(self):
        """The AI HUD timer fragment advances an expired rest during a real view render."""
        script = """
import time
import streamlit as st
from src.session_view import render_session_view

if not st.session_state.get("_timer_test_initialized"):
    st.session_state["_timer_test_initialized"] = True
    st.session_state["hud_is_resting"] = True
    st.session_state["hud_current_set"] = 1
    st.session_state["hud_rest_duration"] = 1
    st.session_state["hud_rest_start_time"] = time.time() - 2
render_session_view()
"""
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["hud_is_resting"])
        self.assertEqual(app.session_state["hud_current_set"], 2)

    def test_manual_hud_auto_advances_expired_rest(self):
        """The manual HUD uses the same server-side timer and advances without a button click."""
        script = """
import time
import streamlit as st
from src.session_view import render_session_view

if not st.session_state.get("_timer_test_initialized"):
    st.session_state["_timer_test_initialized"] = True
    st.session_state["session_mode_selector"] = "📝 Chế độ Tự do (Không dùng Camera)"
    st.session_state["hud_is_resting"] = True
    st.session_state["hud_current_set"] = 1
    st.session_state["hud_rest_duration"] = 1
    st.session_state["hud_rest_start_time"] = time.time() - 2
render_session_view()
"""
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["hud_is_resting"])
        self.assertEqual(app.session_state["hud_current_set"], 2)

    def test_pause_and_resume_flow_in_app(self):
        """Bấm Tạm ngưng và Tiếp tục giữ nguyên tiến trình phiên tập."""
        script = """
import streamlit as st
from src.session_view import render_session_view
render_session_view()
"""
        app = AppTest.from_string(script).run()
        session = app.session_state["workout_session"]
        session.ai_reps = 5

        # Bấm Tạm ngưng
        app.button(key="hud_pause_btn").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["session_user_paused"])
        self.assertEqual(app.session_state["paused_progress"]["reps"], 5)

        # Bấm Tiếp tục
        app.button(key="hud_resume_btn").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["session_user_paused"])

    def test_manual_mode_renders_cleanly(self):
        """Chế độ Tự do Không Camera render mượt mà kèm Up Next list và form nhập."""
        script = """
import streamlit as st
from src.session_view import render_session_view
st.session_state["session_mode_selector"] = "📝 Chế độ Tự do (Không dùng Camera)"
render_session_view()
"""
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        submit_btns = [b for b in app.form_submit_button if "Kết thúc & Lưu" in b.label]
        self.assertEqual(len(submit_btns), 1)


if __name__ == "__main__":
    unittest.main()
