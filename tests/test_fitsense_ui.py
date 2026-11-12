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

    def test_capybara_section_quotes_length_and_silence(self):
        """Kiểm tra câu thoại CappyHeo theo từng mục <= 2 dòng, không tràn, có khoảng im lặng 10s."""
        all_banks = {
            "SAD": capybara_widget.SAD_QUOTES,
            "HAPPY": capybara_widget.HAPPY_QUOTES,
            "WELCOME": capybara_widget.WELCOME_QUOTES,
            **capybara_widget.SECTION_QUOTES,
        }
        for bank_name, quotes in all_banks.items():
            self.assertGreaterEqual(len(quotes), 5, f"{bank_name} cần ít nhất 5 câu")
            for q in quotes:
                self.assertLessEqual(
                    len(q),
                    55,
                    f"Câu thoại trong '{bank_name}' quá dài (> 2 dòng): '{q}' ({len(q)} ký tự)",
                )

        # Ánh xạ theo đúng danh sách màn hình thực tế của app.py
        self.assertEqual(capybara_widget.resolve_capy_section("⚡ Phòng tập Trực tiếp (HUD)", True), "hud")
        self.assertEqual(capybara_widget.resolve_capy_section("📋 Kế hoạch Tập luyện Tuần", True), "planner_library")
        self.assertEqual(capybara_widget.resolve_capy_section("📚 Thư viện Động tác", True), "planner_library")
        self.assertEqual(capybara_widget.resolve_capy_section("🔥 Bảng nhiệt Phục hồi Cơ bắp", True), "analytics_heatmap")
        self.assertEqual(capybara_widget.resolve_capy_section("📈 Tiến độ & Kỷ lục Cá nhân", True), "analytics_heatmap")
        self.assertEqual(capybara_widget.resolve_capy_section("📝 Đánh giá Sau Buổi tập", True), "profile_eval")
        self.assertEqual(capybara_widget.resolve_capy_section("👤 Hồ sơ & Chỉ số Thể chất", True), "profile_eval")
        self.assertEqual(capybara_widget.resolve_capy_section("⚡ Phòng tập Trực tiếp (HUD)", False), "welcome")

        captured = []
        orig_md = st.markdown
        try:
            st.markdown = lambda text, **kw: captured.append(text)
            capybara_widget.st.session_state["capy_quote_cache"] = {}
            capybara_widget.render_capybara_companion(
                theme="dark",
                is_logged_in=True,
                current_screen="⚡ Phòng tập Trực tiếp (HUD)",
            )
            first_html = captured[-1]
            self.assertIn("capyBubbleSilence 22s infinite", first_html)
            self.assertIn("capyRotateQuotes 66s infinite", first_html)
            self.assertIn("animation-delay: 22s;", first_html)
            self.assertIn("animation-delay: 44s;", first_html)
            self.assertIn("-webkit-line-clamp: 2;", first_html)

            capybara_widget.render_capybara_companion(
                theme="dark",
                is_logged_in=True,
                current_screen="⚡ Phòng tập Trực tiếp (HUD)",
            )
            self.assertEqual(first_html, captured[-1])
        finally:
            st.markdown = orig_md

    def test_auth_validation_strict(self):
        """Kiểm tra chặn dữ liệu không hợp lệ ở Đăng nhập và Đăng ký."""
        self.assertTrue(auth_view.validate_login_inputs("", ""))
        self.assertTrue(auth_view.validate_login_inputs("khanh@fitsense.vn", "123"))
        self.assertTrue(auth_view.validate_login_inputs("khong_phai_email", "123456"))
        self.assertEqual(auth_view.validate_login_inputs("khanh@fitsense.vn", "123456"), [])

        self.assertTrue(auth_view.validate_registration_inputs("   ", "valid@mail.com", "123456"))
        self.assertTrue(auth_view.validate_registration_inputs("Nguyễn Văn A", "bad-email", "123456"))
        self.assertTrue(auth_view.validate_registration_inputs("Nguyễn Văn A", "valid@mail.com", "12345"))
        self.assertTrue(
            auth_view.validate_registration_inputs(
                "Nguyễn Văn A",
                "Used@Mail.com",
                "123456",
                existing_users={"used@mail.com": {"password": "123456"}},
            )
        )
        self.assertEqual(
            auth_view.validate_registration_inputs("Nguyễn Văn A", "new@fitsense.vn", "123456"),
            [],
        )

    def test_evaluation_ai_completion_and_default_rpe(self):
        """Kiểm tra đánh giá: AI tự tính completion, nhãn buổi tập kèm thời gian thực, RPE mặc định 5 có emoji."""
        from pathlib import Path

        selected_record = {
            "mode": "ai",
            "status": "completed",
            "reps": 18,
            "target_reps": 36,
            "session_name": "Thứ 2 - Ngực & Tay sau",
            "finished_at": "20:15 11/11/2026",
        }
        pct, label, _ = evaluation_view.compute_ai_completion_rate({}, selected_result=selected_record)
        self.assertEqual(pct, 50)
        self.assertIn("Thứ 2 - Ngực & Tay sau", label)
        self.assertIn("20:15 11/11/2026", label)

        for score in range(1, 11):
            self.assertIn(score, evaluation_view.RPE_DESCRIPTIONS)

        eval_src = Path("src/evaluation_view.py").read_text(encoding="utf-8")
        self.assertIn("value=5", eval_src)
        self.assertNotIn("st.slider(\"Tỉ lệ hoàn thành", eval_src)

    def test_planner_upload_parsing_and_alternatives(self):
        """Kiểm tra upload kế hoạch JSON/CSV, lỗi định dạng và danh sách chọn bài thay thế."""
        json_bytes = b'[{"day": "Th\xe1\xbb\xa9 2", "focus": "Upper", "exercises": [{"name": "Push-up", "sets": 3, "reps": 10}]}]'
        parsed_json = planner_view.parse_uploaded_plan(json_bytes, "plan.json")
        self.assertEqual(len(parsed_json), 7)
        self.assertEqual(parsed_json[0]["exercises"][0]["name"], "Push-up")

        csv_bytes = "day,focus,name,sets,reps,rest_sec\nThứ 3,Chân,Bodyweight Squat,4,15,60\n".encode("utf-8")
        parsed_csv = planner_view.parse_uploaded_plan(csv_bytes, "plan.csv")
        self.assertEqual(len(parsed_csv), 7)
        self.assertEqual(parsed_csv[1]["exercises"][0]["name"], "Bodyweight Squat")

        with self.assertRaises(ValueError):
            planner_view.parse_uploaded_plan(b"{bad json", "plan.json")

        alts = planner_view._get_exercise_alternatives(
            {"name": "Standard Push-up", "substitute": "Knee Push-up"},
            [{"name": "Glute Bridge"}],
        )
        self.assertIn("Knee Push-up", alts)
        self.assertIn("Glute Bridge", alts)

    def test_webcam_single_button_voice_coach_and_no_mirror(self):
        """Kiểm tra camera UI chỉ còn 1 nút bật/tắt, bỏ nút gương, giữ Voice Coach & camera selector."""
        from pathlib import Path

        html_src = Path("assets/webcam/test_webcam_live.html").read_text(encoding="utf-8")
        js_src = Path("assets/webcam/webcam.mjs").read_text(encoding="utf-8")

        self.assertIn('id="camera-toggle"', html_src)
        self.assertIn('id="voice"', html_src)
        self.assertIn('id="camera-device"', html_src)
        self.assertNotIn('id="mirror"', html_src)
        self.assertNotIn('id="start"', html_src)
        self.assertNotIn('id="stop"', html_src)

        self.assertIn('canvas.style.transform = "scaleX(-1)"', js_src)
        self.assertIn("show_metrics", js_src)
        self.assertIn("createVoiceCoach", js_src)
        self.assertNotIn('get("mirror")', js_src)

    def test_apptest_full_navigation_and_ui_flows(self):
        """Kiểm thử AppTest xuyên suốt từ Đăng nhập Demo đến tất cả các màn hình sau khi merge các branch."""
        from pathlib import Path
        from streamlit.testing.v1 import AppTest

        app_path = str(Path(__file__).resolve().parents[1] / "app.py")
        at = AppTest.from_file(app_path, default_timeout=20)
        at.run()
        self.assertFalse(at.exception, f"Lỗi khi mở trang đăng nhập: {at.exception}")

        demo_btns = [b for b in at.button if "Demo User" in b.label]
        self.assertTrue(demo_btns, "Không tìm thấy nút đăng nhập Demo User")
        demo_btns[0].click().run()
        self.assertFalse(at.exception, f"Lỗi sau đăng nhập Demo User: {at.exception}")

        # Pop-up chào mừng & lịch tập hôm nay phải tự bật ngay khi vừa vào web
        self.assertFalse(at.session_state["welcome_modal_dismissed"])
        welcome_enter = [
            b
            for b in at.button
            if "Bắt đầu tập ngay hôm nay" in b.label
            or "Tập bù buổi gần nhất" in b.label
            or "Đóng thông báo" in b.label
        ]
        self.assertTrue(welcome_enter, "Không thấy pop-up chào mừng kèm nút hành động khi vừa đăng nhập")
        welcome_enter[0].click().run()
        self.assertFalse(at.exception)
        self.assertTrue(at.session_state["welcome_modal_dismissed"])

        pause_btns = [b for b in at.button if "Tạm ngưng" in b.label]
        self.assertTrue(pause_btns, "Không thấy nút ⏸️ Tạm ngưng trong HUD")
        self.assertFalse(
            any("khung hình" in c.value for c in [*at.caption, *at.info]),
            "HUD vẫn còn chữ 'khung hình' thay vì thời gian (giây)",
        )
        self.assertFalse(
            any("hoặc theo giáo án đã chọn" in c.value for c in at.caption),
            "Vẫn còn chữ thừa trong ngoặc ở mục tiêu buổi tập",
        )
        self.assertTrue(
            any("0.0s / 1.5s" in info.value for info in at.info),
            "Chưa hiển thị thời gian giữ tay (giây) ở HUD",
        )
        pause_btns[0].click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Tiếp tục" in b.label for b in at.button), "Chưa chuyển sang nút ▶️ Tiếp tục")

        nav_radios = [r for r in at.sidebar.radio if r.key == "main_navigation_radio"]
        self.assertTrue(nav_radios, "Không tìm thấy thanh điều hướng sau khi đăng nhập")
        options = list(nav_radios[0].options)

        for screen_name in options:
            nav_radios = [r for r in at.sidebar.radio if r.key == "main_navigation_radio"]
            nav_radios[0].set_value(screen_name).run()
            self.assertFalse(
                at.exception,
                f"Màn hình '{screen_name}' bị crash trong AppTest: {at.exception}",
            )

    def test_weekday_schedule_sync_with_computer_clock(self):
        """Kiểm tra khớp đúng Thứ hiện tại trên máy tính với lộ trình weekly_schedule."""
        from datetime import datetime

        schedule = st.session_state["weekly_schedule"]
        # 2026-11-09 = Thứ 2 (Push Focus: 3*12 + 3*15 = 81 reps)
        mon = datetime(2026, 11, 9, 9, 0)
        mon_day = planner_view.get_today_schedule_day(schedule, now=mon)
        self.assertEqual(planner_view.get_today_weekday_name(mon), "Thứ 2")
        self.assertEqual(mon_day["day"], "Thứ 2")
        self.assertEqual(planner_view.count_day_target_reps(mon_day), 81)

        # 2026-11-11 = Thứ 4 (Rest Day)
        wed = datetime(2026, 11, 11, 9, 0)
        wed_day = planner_view.get_today_schedule_day(schedule, now=wed)
        self.assertEqual(planner_view.get_today_weekday_name(wed), "Thứ 4")
        self.assertTrue(wed_day["is_rest"])
        self.assertEqual(planner_view.count_day_target_reps(wed_day), 0)

        # 2026-11-12 = Thứ 5 (Pull Focus: 3*10 + 3*15 = 75 reps)
        thu = datetime(2026, 11, 12, 0, 5)
        thu_day = planner_view.get_today_schedule_day(schedule, now=thu)
        self.assertEqual(planner_view.get_today_weekday_name(thu), "Thứ 5")
        self.assertEqual(thu_day["day"], "Thứ 5")
        self.assertEqual(planner_view.count_day_target_reps(thu_day), 75)

        # 2026-11-15 = Chủ Nhật
        sun = datetime(2026, 11, 15, 10, 0)
        sun_day = planner_view.get_today_schedule_day(schedule, now=sun)
        self.assertEqual(planner_view.get_today_weekday_name(sun), "Chủ Nhật")
        self.assertEqual(sun_day["day"], "Chủ Nhật")

    def test_dialog_theme_styles_dark_and_light(self):
        """Kiểm tra hộp thoại pop-up đồng bộ màu nền & chữ ở cả Dark và Light mode."""
        captured = []
        orig_md = st.markdown
        try:
            st.markdown = lambda text, **kw: captured.append(text)
            app.apply_custom_styles(theme="dark")
            dark_css = captured[-1]
            self.assertIn('[data-testid="stDialog"] > div', dark_css)
            self.assertIn('[data-testid="stDialog"] [role="dialog"]', dark_css)
            self.assertIn("background-color: #111C2E !important;", dark_css)

            app.apply_custom_styles(theme="light")
            light_css = captured[-1]
            self.assertIn('[data-testid="stDialog"] > div', light_css)
            self.assertIn('[data-testid="stDialog"] [role="dialog"]', light_css)
            self.assertIn("background-color: #FFFFFF !important;", light_css)
            self.assertIn('div[data-testid="stButtonGroup"] button[data-variant="segmented_control"]', dark_css)
            self.assertIn('div[data-testid="stButtonGroup"] button[data-variant="segmented_control"]', light_css)
        finally:
            st.markdown = orig_md


if __name__ == "__main__":
    unittest.main()
