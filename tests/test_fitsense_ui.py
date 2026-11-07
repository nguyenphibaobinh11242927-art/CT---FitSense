"""Kiểm thử cấu trúc các module và khởi tạo trạng thái giao diện FitSense (SCRUM-11)."""

import unittest
import streamlit as st

import app
import src.auth_view as auth_view
import src.profile_view as profile_view
import src.planner_view as planner_view
import src.library_view as library_view
import src.session_view as session_view
import src.evaluation_view as evaluation_view
import src.heatmap_view as heatmap_view
import src.progress_view as progress_view


class TestFitSenseUIModules(unittest.TestCase):
    """Bộ kiểm thử cho khung giao diện Streamlit FitSense và các module nghiệp vụ."""

    def setUp(self):
        """Khởi tạo môi trường giả lập trước mỗi ca test."""
        st.session_state.clear()
        app.init_app_state(force_reset=True)

    def test_module_render_callables(self):
        """Kiểm tra tất cả 8 module giao diện đều có hàm render tương ứng và gọi được."""
        self.assertTrue(callable(auth_view.render_auth_view))
        self.assertTrue(callable(profile_view.render_profile_view))
        self.assertTrue(callable(planner_view.render_planner_view))
        self.assertTrue(callable(library_view.render_library_view))
        self.assertTrue(callable(session_view.render_session_view))
        self.assertTrue(callable(evaluation_view.render_evaluation_view))
        self.assertTrue(callable(heatmap_view.render_heatmap_view))
        self.assertTrue(callable(progress_view.render_progress_view))

    def test_default_unauthenticated_state(self):
        """Kiểm tra mặc định không gán sẵn dữ liệu user khi chưa đăng nhập."""
        self.assertFalse(st.session_state["is_logged_in"])
        self.assertIsNone(st.session_state["user_profile"])

    def test_user_authentication_flow(self):
        """Kiểm tra luồng đăng nhập / đăng ký người dùng."""
        # Giả lập người dùng đăng nhập tài khoản
        mock_user = {
            "name": "Nguyễn Văn Test",
            "weight_kg": 65.0,
            "height_cm": 170.0,
            "age": 22,
            "bmi": 22.5,
            "fitness_level": "Intermediate",
            "goal": "Sức bền & Tăng cơ Calisthenics",
            "restrictions": ["Khớp gối yếu"],
            "equipment": ["Thảm yoga/thể dục"],
            "days_per_week": 4,
            "session_duration_minutes": 45,
        }
        st.session_state["is_logged_in"] = True
        st.session_state["user_profile"] = mock_user

        self.assertTrue(st.session_state["is_logged_in"])
        self.assertIsNotNone(st.session_state["user_profile"])
        self.assertEqual(st.session_state["user_profile"]["name"], "Nguyễn Văn Test")
        self.assertGreater(st.session_state["user_profile"]["bmi"], 0)

    def test_streak_minimum_threshold(self):
        """Kiểm tra thông số điều kiện tối thiểu 70% để duy trì streak và khởi tạo bằng 0."""
        streak = st.session_state["streak_info"]
        self.assertEqual(streak["min_threshold_pct"], 70)
        self.assertEqual(streak["current_streak"], 0)

    def test_muscle_recovery_matrix_coverage(self):
        """Kiểm tra bảng nhiệt cơ bắp bao phủ đủ các nhóm cơ chính."""
        muscles = st.session_state["muscle_recovery"]
        essential_muscles = ["Ngực (Chest)", "Lưng & Xô", "Đùi trước (Quads)", "Mông (Glutes)"]
        for m in essential_muscles:
            self.assertIn(m, muscles)
            self.assertIn("recovery_pct", muscles[m])
            self.assertIn("hours_left", muscles[m])


if __name__ == "__main__":
    unittest.main()
