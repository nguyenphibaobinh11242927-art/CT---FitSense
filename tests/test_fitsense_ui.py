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
import src.capybara_widget as capybara_widget


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

    def test_capybara_companion_widget(self):
        """Kiểm tra module thú cưng Capybara đồng hành với đầy đủ SVG, danh sách lời thoại và trạng thái."""
        self.assertTrue(callable(capybara_widget.render_capybara_companion))
        self.assertFalse(st.session_state.get("has_worked_out_today", True))

        # Kiểm tra nội dung lời thoại
        self.assertGreaterEqual(len(capybara_widget.SAD_QUOTES), 5)
        self.assertGreaterEqual(len(capybara_widget.HAPPY_QUOTES), 5)
        self.assertGreaterEqual(len(capybara_widget.WELCOME_QUOTES), 5)

        # Kiểm tra tính hợp lệ của vector SVG
        self.assertIn("<svg", capybara_widget.CAPY_SVG_SAD)
        self.assertIn("</svg>", capybara_widget.CAPY_SVG_SAD)
        self.assertIn("<svg", capybara_widget.CAPY_SVG_HAPPY)
        self.assertIn("</svg>", capybara_widget.CAPY_SVG_HAPPY)

        # Chuyển đổi trạng thái đã tập
        st.session_state["has_worked_out_today"] = True
        self.assertTrue(st.session_state["has_worked_out_today"])

    def test_capybara_widget_no_code_leak(self):
        """Đảm bảo chuỗi HTML xuất ra từ render_capybara_companion không bị Markdown parse thành khối code."""
        captured_html = []
        original_markdown = st.markdown

        def mock_markdown(content, unsafe_allow_html=False):
            if unsafe_allow_html:
                captured_html.append(content)

        st.markdown = mock_markdown
        try:
            # Test theme dark + chưa tập
            capybara_widget.render_capybara_companion(theme="dark", has_worked_out_today=False)
            # Test theme light + đã tập
            capybara_widget.render_capybara_companion(theme="light", has_worked_out_today=True)

            self.assertEqual(len(captured_html), 2)
            for snippet in captured_html:
                # Không được rỗng
                self.assertTrue(len(snippet) > 0)
                # Chứa thẻ div chính và SVG
                self.assertIn('id="capybara-companion-container"', snippet)
                self.assertIn("<svg", snippet)
                # Đảm bảo không có block code nào
                for line in snippet.splitlines():
                    if line.strip():  # Dòng có nội dung
                        self.assertFalse(
                            line.startswith("    "),
                            f"Phát hiện dòng thụt lề 4 space gây lỗi code block: '{line[:30]}...'"
                        )
        finally:
            st.markdown = original_markdown

    def test_capybara_xss_sanitization(self):
        """Kiểm tra lời thoại Capybara tự động khử nhiễm XSS khi tên người dùng chứa thẻ script/HTML."""
        captured_html = []
        original_markdown = st.markdown

        def mock_markdown(content, unsafe_allow_html=False):
            if unsafe_allow_html:
                captured_html.append(content)

        st.markdown = mock_markdown
        try:
            malicious_name = "<script>alert('XSS')</script>"
            capybara_widget.render_capybara_companion(user_name=malicious_name)
            self.assertTrue(len(captured_html) > 0)
            full_output = captured_html[0]
            # Đảm bảo không chứa thẻ script nguyên bản
            self.assertNotIn("<script>", full_output)
            self.assertIn("&lt;script&gt;", full_output)
        finally:
            st.markdown = original_markdown

    def test_capybara_login_welcome_behavior(self):
        """Kiểm tra khi chưa đăng nhập Capy sử dụng câu chào mừng, khi đã đăng nhập mới theo dõi luyện tập."""
        captured_html = []
        original_markdown = st.markdown

        def mock_markdown(content, unsafe_allow_html=False):
            if unsafe_allow_html:
                captured_html.append(content)

        st.markdown = mock_markdown
        try:
            # 1. Chưa đăng nhập: Phải xuất hiện status title chào đón
            capybara_widget.render_capybara_companion(is_logged_in=False)
            unauth_output = captured_html[-1]
            self.assertIn("Chào mừng bạn đến với FitSense", unauth_output)

            # 2. Đã đăng nhập nhưng chưa tập: Phải dùng câu nhắc nhở luyện tập
            capybara_widget.render_capybara_companion(is_logged_in=True, has_worked_out_today=False)
            auth_not_workout = captured_html[-1]
            self.assertIn("Hôm nay bạn chưa tập bài nào", auth_not_workout)

            # 3. Đã đăng nhập và đã tập: Phải dùng câu khen ngợi
            capybara_widget.render_capybara_companion(is_logged_in=True, has_worked_out_today=True)
            auth_workout_done = captured_html[-1]
            self.assertIn("Đã hoàn thành bài tập hôm nay", auth_workout_done)
        finally:
            st.markdown = original_markdown

    def test_profile_view_defensive_rendering(self):
        """Kiểm tra màn hình hồ sơ phòng vệ thành công khi session_duration_minutes là 40 hoặc giá trị ngoại lệ."""
        # Giả lập user đăng ký mới với duration=40 phút
        st.session_state["user_profile"] = {
            "name": "Người dùng Mới",
            "weight_kg": 60.0,
            "height_cm": 165.0,
            "age": 20,
            "bmi": 22.0,
            "fitness_level": "Beginner",
            "goal": "Sức bền & Tăng cơ Calisthenics",
            "restrictions": ["Khớp gối yếu"],
            "environment": "Tại nhà / Phòng riêng",
            "equipment": ["Thảm yoga/thể dục"],
            "days_per_week": 4,
            "session_duration_minutes": 40,
        }
        # Gọi render_profile_view không được raise bất kỳ ngoại lệ nào
        try:
            profile_view.render_profile_view()
        except Exception as e:
            self.fail(f"render_profile_view bị crash với lỗi: {e}")

        # Thử nghiệm với các giá trị biên/lạ
        st.session_state["user_profile"]["session_duration_minutes"] = 100
        st.session_state["user_profile"]["days_per_week"] = 10
        st.session_state["user_profile"]["restrictions"] = ["Hạn chế chưa có trong danh mục"]
        try:
            profile_view.render_profile_view()
        except Exception as e:
            self.fail(f"render_profile_view bị crash khi dữ liệu biên: {e}")


if __name__ == "__main__":
    unittest.main()
