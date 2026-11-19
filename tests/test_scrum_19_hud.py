"""Kiểm thử toàn diện cho Module Session HUD, Đồng hồ nghỉ Rest Timer & Up Next List (SCRUM-19)."""

import unittest
from datetime import date
import streamlit as st
from streamlit.testing.v1 import AppTest

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
        st.session_state["hud_is_resting"] = True
        st.session_state["hud_rest_duration"] = 60
        st.session_state["hud_rest_remaining"] = 60

        # Tăng +15s
        session_view._adjust_rest_timer(15)
        self.assertEqual(st.session_state["hud_rest_duration"], 75)
        self.assertEqual(st.session_state["hud_rest_remaining"], 75)

        # Giảm -15s
        session_view._adjust_rest_timer(-15)
        self.assertEqual(st.session_state["hud_rest_duration"], 60)
        self.assertEqual(st.session_state["hud_rest_remaining"], 60)

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
        session_view._advance_hud_set(exercises)
        st.session_state["hud_rest_start_time"] = time.time() - 50
        st.session_state["session_user_paused"] = True

        # Khi pause, auto-advance không được phép kích hoạt
        advanced = session_view._check_auto_advance_rest_timer(exercises)
        self.assertFalse(advanced)
        self.assertTrue(st.session_state["hud_is_resting"])
        self.assertEqual(st.session_state["hud_current_set"], 1)

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
        self.assertTrue(st.session_state["hud_all_completed"])

        # Khi khởi tạo phiên tập mới, không bị dính cờ cũ tồn đọng
        session_view._init_hud_state()
        self.assertFalse(st.session_state["hud_is_resting"])
        self.assertFalse(st.session_state["hud_all_completed"])
        self.assertEqual(st.session_state["hud_current_ex_idx"], 0)
        self.assertEqual(st.session_state["hud_current_set"], 1)


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
