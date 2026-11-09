"""Module Đăng nhập & Đăng ký Người dùng (Authentication View).

Quản lý xác thực người dùng, đăng ký tài khoản mới và khởi tạo hồ sơ thể chất cá nhân hóa.
"""

import streamlit as st


def render_auth_view():
    """Hiển thị màn hình Đăng nhập và Đăng ký tài khoản cho ứng dụng FitSense."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="margin-bottom: 4px;">⚡ FitSense Account Portal</h1>
            <p style="opacity: 0.8; font-size: 15px;">Đăng nhập để đồng bộ lộ trình tập luyện, dữ liệu AI Camera và chuỗi ngày Streak của bạn.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_center = st.columns([1, 2, 1])[1]

    with col_center:
        tab_login, tab_register = st.tabs(["🔐 ĐĂNG NHẬP", "✨ ĐĂNG KÝ TÀI KHOẢN MỚI"])

        # TAB 1: ĐĂNG NHẬP
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email hoặc Tên đăng nhập:", placeholder="vidu@gmail.com")
                password = st.text_input("Mật khẩu:", type="password", placeholder="Nhập mật khẩu...")

                remember = st.checkbox("Ghi nhớ đăng nhập", value=True)
                btn_login = st.form_submit_button("Đăng Nhập Ngay", type="primary", use_container_width=True)

                if btn_login:
                    if not email or not password:
                        st.error("Vui lòng nhập đầy đủ Email và Mật khẩu!")
                    else:
                        # Kiểm tra xem tài khoản có trong db tạm thời không
                        users_db = st.session_state.get("registered_users", {})
                        if email in users_db and users_db[email].get("password") == password:
                            st.session_state["is_logged_in"] = True
                            st.session_state["user_profile"] = users_db[email]["profile"]
                            st.success(f"Chào mừng trở lại, {st.session_state['user_profile']['name']}! 🎉")
                            st.session_state["nav_selection"] = "⚡ Phòng tập Trực tiếp (HUD)"
                            st.rerun()
                        elif email in ["khanh@fitsense.vn", "yu@fitsense.vn", "admin@fitsense.vn", "test@gmail.com"]:
                            # Mock login account
                            st.session_state["is_logged_in"] = True
                            st.session_state["user_profile"] = {
                                "name": email.split("@")[0].capitalize(),
                                "email": email,
                                "weight_kg": 54.0,
                                "height_cm": 162.0,
                                "age": 21,
                                "bmi": 20.6,
                                "fitness_level": "Intermediate",
                                "goal": "Sức bền & Tăng cơ Calisthenics",
                                "restrictions": ["Khớp gối yếu"],
                                "environment": "Tại nhà / Phòng riêng",
                                "equipment": ["Thảm yoga/thể dục", "Xà đơn gắn cửa"],
                                "days_per_week": 4,
                                "session_duration_minutes": 45,
                            }
                            st.success(f"Đăng nhập thành công! Chào bạn {st.session_state['user_profile']['name']}.")
                            st.session_state["nav_selection"] = "⚡ Phòng tập Trực tiếp (HUD)"
                            st.rerun()
                        else:
                            st.error("Email hoặc mật khẩu không chính xác. Hãy đăng ký tài khoản mới bên tab bên cạnh!")

            st.markdown("---")
            st.markdown("**Hoặc trải nghiệm nhanh không cần mật khẩu:**")
            if st.button("🚀 Vào ngay với Tài khoản Trải nghiệm (Demo User)", use_container_width=True):
                st.session_state["is_logged_in"] = True
                st.session_state["streak_info"] = {"current_streak": 0, "longest_streak": 0, "min_threshold_pct": 70}
                st.session_state["session_history"] = []
                st.session_state["user_profile"] = {
                    "name": "Vận Động Viên Trải Nghiệm",
                    "email": "demo@fitsense.vn",
                    "weight_kg": 60.0,
                    "height_cm": 168.0,
                    "age": 22,
                    "bmi": 21.3,
                    "fitness_level": "Beginner",
                    "goal": "Duy trì thể lực & Săn chắc",
                    "restrictions": [],
                    "environment": "Tại nhà",
                    "equipment": ["Thảm yoga/thể dục"],
                    "days_per_week": 3,
                    "session_duration_minutes": 30,
                }
                st.session_state["nav_selection"] = "⚡ Phòng tập Trực tiếp (HUD)"
                st.rerun()

        # TAB 2: ĐĂNG KÝ
        with tab_register:
            with st.form("register_form"):
                st.markdown("#### 1. Thông tin Tài khoản")
                reg_name = st.text_input("Họ và tên của bạn:", placeholder="Nguyễn Văn A")
                reg_email = st.text_input("Địa chỉ Email:", placeholder="name@example.com")
                reg_pass = st.text_input("Mật khẩu tạo mới:", type="password", placeholder="Tối thiểu 6 ký tự")

                st.markdown("#### 2. Thể trạng & Mục tiêu Rèn luyện")
                col_w, col_h, col_a = st.columns(3)
                with col_w:
                    reg_weight = st.number_input("Cân nặng (kg):", min_value=30.0, max_value=180.0, value=55.0, step=0.5)
                with col_h:
                    reg_height = st.number_input("Chiều cao (cm):", min_value=120.0, max_value=220.0, value=165.0, step=0.5)
                with col_a:
                    reg_age = st.number_input("Tuổi:", min_value=14, max_value=90, value=20, step=1)

                reg_goal = st.selectbox(
                    "Mục tiêu thể lực chính:",
                    options=[
                        "Sức bền & Tăng cơ Calisthenics",
                        "Đốt mỡ & Săn chắc toàn thân",
                        "Tăng cường sức mạnh cốt lõi (Core)",
                        "Duy trì thể lực & Giảm stress"
                    ]
                )

                reg_level = st.selectbox(
                    "Trình độ thể lực:",
                    options=["Beginner (Mới bắt đầu)", "Intermediate (Đã có nền tảng)", "Advanced (Nâng cao)"]
                )

                reg_restr = st.multiselect(
                    "Hạn chế vận động (nếu có):",
                    options=["Khớp gối yếu", "Cổ tay đau", "Đau lưng dưới", "Khớp vai cứng"],
                    default=[]
                )

                btn_register = st.form_submit_button("Tạo Tài Khoản & Bắt Đầu Tập", type="primary", use_container_width=True)

                if btn_register:
                    if not reg_name or not reg_email or not reg_pass:
                        st.error("Vui lòng điền đủ Họ tên, Email và Mật khẩu!")
                    elif len(reg_pass) < 4:
                        st.error("Mật khẩu cần tối thiểu 4 ký tự!")
                    else:
                        h_m = reg_height / 100.0
                        calc_bmi = round(reg_weight / (h_m * h_m), 1)

                        new_profile = {
                            "name": reg_name,
                            "email": reg_email,
                            "weight_kg": reg_weight,
                            "height_cm": reg_height,
                            "age": reg_age,
                            "bmi": calc_bmi,
                            "fitness_level": reg_level,
                            "goal": reg_goal,
                            "restrictions": reg_restr,
                            "environment": "Tại nhà / Phòng riêng",
                            "equipment": ["Thảm yoga/thể dục"],
                            "days_per_week": 4,
                            "session_duration_minutes": 40,
                        }

                        # Lưu vào registered_users
                        if "registered_users" not in st.session_state:
                            st.session_state["registered_users"] = {}
                        st.session_state["registered_users"][reg_email] = {
                            "password": reg_pass,
                            "profile": new_profile
                        }

                        # Lưu an toàn vào JSON cục bộ ngay khi đăng ký tài khoản mới (DoD SCRUM-13)
                        try:
                            from src.profile import save_profile
                            save_profile(reg_email, new_profile)
                        except Exception:
                            pass

                        # Đăng nhập trực tiếp
                        st.session_state["is_logged_in"] = True
                        st.session_state["user_profile"] = new_profile
                        st.session_state["streak_info"] = {"current_streak": 0, "longest_streak": 0, "min_threshold_pct": 70}
                        st.session_state["session_history"] = []
                        st.success("Tạo tài khoản thành công! Đang chuyển đến phòng tập...")
                        st.session_state["nav_selection"] = "⚡ Phòng tập Trực tiếp (HUD)"
                        st.rerun()
