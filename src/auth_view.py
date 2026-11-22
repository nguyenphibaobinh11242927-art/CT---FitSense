"""Module Đăng nhập & Đăng ký Người dùng (Authentication View).

Quản lý xác thực người dùng, đăng ký tài khoản mới và khởi tạo hồ sơ thể chất cá nhân hóa.
"""

import re
import streamlit as st


EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
)
MOCK_DEMO_EMAILS = {"khanh@fitsense.vn", "yu@fitsense.vn", "admin@fitsense.vn", "test@gmail.com", "demo@fitsense.vn"}


def populate_demo_user_session(state: dict) -> None:
    """Khởi tạo đầy đủ dữ liệu demo phong phú cho tài khoản trải nghiệm (SCRUM-22)."""
    state["is_logged_in"] = True
    state["user_profile"] = {
        "name": "Vận Động Viên Trải Nghiệm",
        "email": "demo@fitsense.vn",
        "gender": "Nam",
        "weight_kg": 65.0,
        "height_cm": 172.0,
        "age": 22,
        "bmi": 22.0,
        "fitness_level": "Intermediate (Người đã có nền tảng)",
        "goal": "Sức bền & Tăng cơ Calisthenics",
        "restrictions": ["Khớp gối yếu (Tránh Squat quá sâu, Jumping)"],
        "environment": "Tại nhà / Phòng riêng",
        "equipment": ["Thảm yoga/thể dục", "Xà đơn gắn cửa"],
        "days_per_week": 4,
        "session_duration_minutes": 35,
    }
    state["streak_info"] = {
        "current_streak": 4,
        "longest_streak": 6,
        "min_threshold_pct": 70,
    }
    state["personal_records"] = {
        "Squat liên tục": "45 Reps",
        "Push-up chuẩn": "36 Reps",
        "Plank giữ tối đa": "75 Giây",
        "Buổi tập dài nhất": "32 Phút",
    }
    state["has_worked_out_today"] = True
    state["session_history"] = [
        {"Ngày": "16/11/2026", "Bài tập": "Standard Push-up", "Số reps": 36, "Thời lượng": "14 phút", "Calo (kcal)": 78.5, "RPE": 6, "Tỉ lệ hoàn thành": "100%"},
        {"Ngày": "17/11/2026", "Bài tập": "Squat Thể dục", "Số reps": 45, "Thời lượng": "16 phút", "Calo (kcal)": 95.0, "RPE": 7, "Tỉ lệ hoàn thành": "90%"},
        {"Ngày": "20/11/2026", "Bài tập": "Dips trên ghế", "Số reps": 30, "Thời lượng": "12 phút", "Calo (kcal)": 65.0, "RPE": 8, "Tỉ lệ hoàn thành": "85%"},
        {"Ngày": "22/11/2026", "Bài tập": "Plank Tĩnh", "Số reps": 60, "Thời lượng": "10 phút", "Calo (kcal)": 55.0, "RPE": 5, "Tỉ lệ hoàn thành": "100%"},
    ]
    state["workout_results"] = {
        "demo-sess-04": {
            "session_id": "demo-sess-04",
            "session_name": "Plank Tĩnh (Core Stability)",
            "mode": "ai",
            "reps": 60,
            "target_reps": 60,
            "duration_seconds": 600,
            "calories": 55.0,
            "finished_at": "17:45 22/11/2026",
            "completion_rate": 100.0,
        },
        "demo-sess-03": {
            "session_id": "demo-sess-03",
            "session_name": "Dips trên ghế (Bench Dips)",
            "mode": "ai",
            "reps": 30,
            "target_reps": 35,
            "duration_seconds": 720,
            "calories": 65.0,
            "finished_at": "18:00 20/11/2026",
            "completion_rate": 85.7,
        },
        "demo-sess-02": {
            "session_id": "demo-sess-02",
            "session_name": "Squat Thể dục (Bodyweight Squat)",
            "mode": "ai",
            "reps": 45,
            "target_reps": 50,
            "duration_seconds": 960,
            "calories": 95.0,
            "finished_at": "19:15 17/11/2026",
            "completion_rate": 90.0,
        },
        "demo-sess-01": {
            "session_id": "demo-sess-01",
            "session_name": "Standard Push-up (Hít đất chuẩn)",
            "mode": "ai",
            "reps": 36,
            "target_reps": 36,
            "duration_seconds": 840,
            "calories": 78.5,
            "finished_at": "18:30 16/11/2026",
            "completion_rate": 100.0,
        },
    }
    state["workout_event_history"] = [
        {"session_id": "demo-sess-01", "actual_date": "2026-11-16", "source_day": "Thứ 2", "focus": "Thân trên: Ngực & Tay sau", "muscle_tags": ["Ngực (Chest)", "Tay sau"], "reps": 36, "status": "completed", "finished_at": "18:30 16/11/2026", "completion_rate": 100.0},
        {"session_id": "demo-sess-02", "actual_date": "2026-11-17", "source_day": "Thứ 3", "focus": "Thân dưới & Mông", "muscle_tags": ["Đùi trước (Quads)", "Mông (Glutes)"], "reps": 45, "status": "completed", "finished_at": "19:15 17/11/2026", "completion_rate": 90.0},
        {"session_id": "demo-sess-03", "actual_date": "2026-11-20", "source_day": "Thứ 6", "focus": "Thân trên: Tay sau & Ngực", "muscle_tags": ["Tay sau (Triceps)"], "reps": 30, "status": "completed", "finished_at": "18:00 20/11/2026", "completion_rate": 85.7},
        {"session_id": "demo-sess-04", "actual_date": "2026-11-22", "source_day": "Chủ Nhật", "focus": "Bụng & Core Thể lực", "muscle_tags": ["Bụng & Core"], "reps": 60, "status": "completed", "finished_at": "17:45 22/11/2026", "completion_rate": 100.0},
    ]
    try:
        from src.weekly_plan_storage import load_week_state
        load_week_state(state)
    except Exception:
        pass


def is_valid_email(email: str) -> bool:
    """Kiểm tra định dạng Email hợp lệ nhất quán với chuẩn lưu hồ sơ."""
    return isinstance(email, str) and bool(EMAIL_REGEX.fullmatch(email.strip()))


def validate_login_inputs(email: str, password: str) -> list[str]:
    """Xác thực dữ liệu đầu vào ở màn hình Đăng nhập."""
    errors: list[str] = []
    clean_email = (email or "").strip()
    if not clean_email or not password:
        errors.append("Vui lòng nhập đầy đủ Email và Mật khẩu!")
        return errors
    if not is_valid_email(clean_email):
        errors.append("Email không đúng định dạng (ví dụ: ten@domain.com)!")
    if len(password) < 6 or not password.strip():
        errors.append("Mật khẩu phải có tối thiểu 6 ký tự hợp lệ!")
    return errors


def validate_registration_inputs(
    name: str,
    email: str,
    password: str,
    existing_users: dict | None = None,
) -> list[str]:
    """Xác thực dữ liệu đầu vào khi Đăng ký tài khoản mới."""
    errors: list[str] = []
    clean_name = (name or "").strip()
    clean_email = (email or "").strip().lower()
    if not clean_name or not clean_email or not password:
        errors.append("Vui lòng điền đủ Họ tên, Email và Mật khẩu!")
        return errors
    if len(clean_name) < 2:
        errors.append("Họ và tên phải có tối thiểu 2 ký tự (không chỉ khoảng trắng)!")
    if not is_valid_email(clean_email):
        errors.append("Địa chỉ Email không hợp lệ (ví dụ: name@example.com)!")
    if len(password) < 6 or password != password.strip():
        errors.append("Mật khẩu cần tối thiểu 6 ký tự và không có khoảng trắng ở hai đầu!")
    if isinstance(existing_users, dict):
        lower_keys = {k.strip().lower() for k in existing_users.keys() if isinstance(k, str)}
        if clean_email in lower_keys:
            errors.append("Email này đã được đăng ký! Vui lòng chuyển sang tab Đăng nhập.")
    return errors


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
                email = st.text_input("Email đăng nhập:", placeholder="vidu@gmail.com")
                password = st.text_input("Mật khẩu:", type="password", placeholder="Tối thiểu 6 ký tự...")

                remember = st.checkbox("Ghi nhớ đăng nhập", value=True)
                btn_login = st.form_submit_button("Đăng Nhập Ngay", type="primary", use_container_width=True)

                if btn_login:
                    login_errors = validate_login_inputs(email, password)
                    if login_errors:
                        for err in login_errors:
                            st.error(err)
                    else:
                        clean_email = email.strip().lower()
                        # Kiểm tra xem tài khoản có trong db tạm thời không
                        users_db = st.session_state.get("registered_users", {})
                        matched_record = users_db.get(clean_email) or users_db.get(email.strip())
                        if matched_record and matched_record.get("password") == password:
                            st.session_state["is_logged_in"] = True
                            st.session_state["user_profile"] = matched_record["profile"]
                            st.success(f"Chào mừng trở lại, {st.session_state['user_profile']['name']}! 🎉")
                            st.session_state["nav_selection"] = "⚡ Phòng tập Trực tiếp (HUD)"
                            st.rerun()
                        elif matched_record:
                            st.error("Mật khẩu không chính xác! Vui lòng kiểm tra lại.")
                        elif clean_email == "demo@fitsense.vn":
                            populate_demo_user_session(st.session_state)
                            st.success(f"Đăng nhập thành công! Chào mừng bạn {st.session_state['user_profile']['name']}.")
                            st.session_state["nav_selection"] = "⚡ Phòng tập Trực tiếp (HUD)"
                            st.rerun()
                        elif clean_email in MOCK_DEMO_EMAILS:
                            # Mock login account (đã qua kiểm tra email & mật khẩu >= 6 ký tự)
                            st.session_state["is_logged_in"] = True
                            st.session_state["user_profile"] = {
                                "name": clean_email.split("@")[0].capitalize(),
                                "email": clean_email,
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
            st.caption("🔑 Tài khoản Demo: `demo@fitsense.vn` | Mật khẩu: `demo123` (hoặc bấm nút dưới để vào ngay)")
            if st.button("🚀 Vào ngay với Tài khoản Trải nghiệm (Demo User)", use_container_width=True):
                populate_demo_user_session(st.session_state)
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
                    users_db = st.session_state.get("registered_users", {})
                    reg_errors = validate_registration_inputs(
                        reg_name, reg_email, reg_pass, existing_users=users_db
                    )
                    if reg_errors:
                        for err in reg_errors:
                            st.error(err)
                    else:
                        clean_name = reg_name.strip()
                        clean_email = reg_email.strip().lower()
                        h_m = reg_height / 100.0
                        calc_bmi = round(reg_weight / (h_m * h_m), 1)

                        new_profile = {
                            "name": clean_name,
                            "email": clean_email,
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

                        # Lưu vào registered_users theo email chuẩn hóa
                        if "registered_users" not in st.session_state:
                            st.session_state["registered_users"] = {}
                        st.session_state["registered_users"][clean_email] = {
                            "password": reg_pass,
                            "profile": new_profile
                        }

                        # Lưu an toàn vào JSON cục bộ ngay khi đăng ký tài khoản mới (DoD SCRUM-13)
                        try:
                            from src.profile import save_profile
                            save_profile(clean_email, new_profile)
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
