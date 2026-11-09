"""Module Hồ sơ Thể chất & Hạn chế Vận động (Profile View).

Quản lý hồ sơ cá nhân, thể trạng, mục tiêu thể thao, tình trạng chấn thương và dụng cụ tập luyện.
"""

import html
import streamlit as st

from src.profile import (
    NO_EQUIPMENT, NO_RESTRICTIONS, load_profile, save_profile, validate_profile,
)


def render_profile_view():
    """Hiển thị và quản lý form thông tin thể chất, chấn thương và mục tiêu thể thao."""
    st.header("👤 Hồ sơ Thể chất & Mục tiêu Rèn luyện")
    st.caption("Cập nhật thông số cơ thể và thể trạng thực tế để AI tối ưu hóa giáo án cá nhân cho riêng bạn.")

    if not st.session_state.get("is_logged_in", False):
        st.warning("⚠️ Bạn đang xem dưới chế độ Khách. Vui lòng đăng nhập hoặc đăng ký tài khoản để lưu trữ hồ sơ thể chất vĩnh viễn!")
        c_l, c_r = st.columns([1, 3])
        with c_l:
            if st.button("🔐 Đi đến trang Đăng nhập / Đăng ký", type="primary"):
                st.session_state["nav_selection"] = "🔐 Đăng nhập / Đăng ký"
                st.rerun()
        st.markdown("---")

    profile = st.session_state.get("user_profile") or {}
    # Load only once per signed-in user; keep the UI's existing data contract.
    identifier = profile.get("email") or profile.get("name") or "demo_user"
    loaded_key = f"profile_loaded:{identifier}"
    if identifier and not st.session_state.get(loaded_key):
        try:
            saved = load_profile(identifier)
            if saved:
                profile = {**profile, **saved}
                st.session_state["user_profile"] = profile
        except ValueError as exc:
            st.warning(str(exc) + " Bạn có thể nhập lại và lưu hồ sơ mới.")
        st.session_state[loaded_key] = True

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        st.subheader("1. Thông số Sinh trắc học & Trình độ")
        name = st.text_input("Họ và tên của bạn:", value=profile.get("name", ""))

        c_w, c_h, c_a = st.columns(3)
        with c_w:
            weight = st.number_input("Cân nặng (kg):", min_value=30.0, max_value=200.0, value=float(profile.get("weight_kg", 60.0)), step=0.5)
        with c_h:
            height = st.number_input("Chiều cao (cm):", min_value=100.0, max_value=230.0, value=float(profile.get("height_cm", 168.0)), step=0.5)
        with c_a:
            age = st.number_input("Tuổi:", min_value=12, max_value=90, value=int(profile.get("age", 22)), step=1)

        # Tính BMI tự động
        height_m = height / 100.0
        bmi = weight / (height_m * height_m)
        theme = st.session_state.get("app_theme", "dark")
        bmi_normal_color = "#38BDF8" if theme == "dark" else "#854D0E"

        if bmi < 18.5:
            bmi_status = "Gầy / Cần tăng cơ"
            bmi_color = "#38BDF8"
        elif bmi >= 25.0:
            bmi_status = "Thừa cân / Cần đốt mỡ"
            bmi_color = "#EF4444"
        else:
            bmi_status = "Cân đối lý tưởng"
            bmi_color = bmi_normal_color

        safe_bmi_status = html.escape(str(bmi_status))
        safe_bmi_color = html.escape(str(bmi_color))

        st.markdown(
            f"""
            <div class="fitsense-stat-card" style="padding: 12px 16px; border-radius: 8px; margin: 12px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span>📊 <b>Chỉ số BMI tự động:</b></span>
                <span class="stat-highlight">{bmi:.1f}</span>
                <span>— Tình trạng: <b style="color: {safe_bmi_color};">{safe_bmi_status}</b></span>
            </div>
            """,
            unsafe_allow_html=True
        )

        level_options = ["Beginner (Mới bắt đầu)", "Intermediate (Trung cấp / Đã có nền tảng)", "Advanced (Nâng cao / Calisthenics thuần thục)"]
        curr_level = profile.get("fitness_level", "Intermediate")
        level_idx = 1
        for i, opt in enumerate(level_options):
            if curr_level.split(" ")[0].lower() in opt.lower():
                level_idx = i
                break

        level = st.selectbox(
            "Trình độ thể lực hiện tại:",
            options=level_options,
            index=level_idx,
            help="AI sẽ điều chỉnh độ khó bài tập và số reps mục tiêu phù hợp."
        )

        goal_options = [
            "Sức bền & Tăng cơ Calisthenics",
            "Đốt mỡ & Săn chắc toàn thân",
            "Dẻo dai & Tăng cường sức mạnh cốt lõi (Core)",
            "Duy trì thể lực & Giảm căng thẳng công việc"
        ]
        curr_goal = profile.get("goal", goal_options[0])
        goal_idx = goal_options.index(curr_goal) if curr_goal in goal_options else 0

        goal = st.selectbox("Mục tiêu rèn luyện chính:", options=goal_options, index=goal_idx)

    with col2:
        st.subheader("2. Hạn chế Vận động & Dụng cụ Tập")

        restrictions = st.multiselect(
            "⚠️ Tiền sử chấn thương hoặc hạn chế vận động (AI sẽ tự động tránh các bài tác động xấu):",
            options=[
                "Khớp gối yếu (Tránh Squat quá sâu, Jumping)",
                "Cổ tay đau (Hạn chế Push-up sàn phẳng)",
                "Đau lưng dưới / Thoát vị nhẹ (Tránh gập lưng nặng)",
                "Khớp vai cứng / Chấn thương xoay vai",
                "Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"
            ],
            default=[x for x in profile.get("restrictions", []) if x in ["Khớp gối yếu (Tránh Squat quá sâu, Jumping)", "Cổ tay đau (Hạn chế Push-up sàn phẳng)", "Đau lưng dưới / Thoát vị nhẹ (Tránh gập lưng nặng)", "Khớp vai cứng / Chấn thương xoay vai", NO_RESTRICTIONS]]
        )

        environment_options = ["Tại nhà / Phòng riêng", "Khuôn viên ngoài trời / Công viên"]
        previous_environment = profile.get("environment", environment_options[0])
        environment = st.radio(
            "Môi trường tập luyện phổ biến:",
            options=environment_options,
            index=environment_options.index(previous_environment) if previous_environment in environment_options else 0,
            horizontal=True
        )

        equipment = st.multiselect(
            "Dụng cụ thể thao hiện có:",
            options=["Thảm yoga/thể dục", "Xà đơn gắn cửa", "Dây kháng lực (Resistance Band)", "Con lăn bụng (Ab Roller)", "Dây nhảy thể lực", "Không có dụng cụ (Chỉ tập Bodyweight)"],
            default=[x for x in profile.get("equipment", ["Thảm yoga/thể dục"]) if x in ["Thảm yoga/thể dục", "Xà đơn gắn cửa", "Dây kháng lực (Resistance Band)", "Con lăn bụng (Ab Roller)", "Dây nhảy thể lực", NO_EQUIPMENT]]
        )

        c_days, c_dur = st.columns(2)
        with c_days:
            days = st.slider("Số ngày tập mỗi tuần:", min_value=2, max_value=6, value=int(profile.get("days_per_week", 4)))
        with c_dur:
            duration = st.select_slider("Thời gian mỗi buổi (phút):", options=[20, 30, 45, 60, 75], value=min([20, 30, 45, 60, 75], key=lambda x: abs(x - int(profile.get("session_duration_minutes", 45)))))

    st.markdown("---")
    if st.button("💾 Lưu và Cập nhật Hồ sơ Thể chất", type="primary", use_container_width=True):
        updated = {
            **profile,
            "name": name.strip(),
            "weight_kg": weight,
            "height_cm": height,
            "age": age,
            "bmi": round(bmi, 1),
            "fitness_level": level,
            "goal": goal,
            "restrictions": restrictions,
            "environment": environment,
            "equipment": equipment,
            "days_per_week": days,
            "session_duration_minutes": duration,
        }
        errors = validate_profile(updated)
        if not identifier:
            errors.append("Chưa có mã người dùng/email. Vui lòng đăng nhập trước khi lưu.")
        if errors:
            for message in errors:
                st.error(message)
        else:
            try:
                save_profile(identifier, updated)
            except (OSError, ValueError) as exc:
                st.error(f"Không thể lưu hồ sơ: {exc}")
            else:
                st.session_state["user_profile"] = updated
                st.success("✅ Đã lưu hồ sơ vào phiên làm việc và JSON cục bộ.")
                st.rerun()
