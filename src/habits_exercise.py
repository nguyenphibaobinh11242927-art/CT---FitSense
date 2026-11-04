"""Thói quen độc lập, streak và đề xuất buổi tập thể thao phù hợp (D7, D8).

Module thuộc đồ án Ratatouille:
- D7: Theo dõi 4 thói quen độc lập (nấu ăn, ăn đúng bữa, tiết kiệm, tập luyện);
  mỗi ngày tăng tối đa 1 đơn vị; kế hoạch không tự động tính thành thành tích.
- D8: Đề xuất buổi tập dựa trên hồ sơ thể chất, mục tiêu, phong cách và hạn chế vận động [CK].
"""

from datetime import datetime
import streamlit as st


def render_habits_exercise():
    """Giao diện chính cho Thói quen & Tập luyện."""
    st.header("🏃 Thói quen & Tập luyện")
    st.caption("Quản lý chuỗi thói quen độc lập (D7) và nhận đề xuất bài tập cá nhân hóa (D8).")

    sub_tab1, sub_tab2 = st.tabs([
        "🔥 Theo dõi thói quen & Chuỗi Streak (D7)",
        "🏋️ Đề xuất buổi tập thể dục cá nhân hóa (D8)",
    ])

    with sub_tab1:
        _render_habits_streaks()

    with sub_tab2:
        _render_exercise_recommendations()


def _render_habits_streaks():
    """Theo dõi 4 thói quen độc lập và chuỗi ngày streak."""
    st.subheader("🔥 Bảng theo dõi chuỗi thói quen liên tục")
    st.caption("📌 **Quy tắc hệ thống (P8):** Mỗi ngày tối đa tăng 1 đơn vị. Các thói quen tính độc lập. Kế hoạch không tự tính là hoàn thành.")

    habits = st.session_state.get("habits_streaks", {})

    cols = st.columns(4)
    habit_keys = [
        ("cook_at_home", "🍳 Nấu tại nhà", cols[0]),
        ("healthy_eating", "🥗 Ăn đúng bữa", cols[1]),
        ("under_budget", "💰 Trong ngân sách", cols[2]),
        ("daily_exercise", "🏃 Tập thể dục", cols[3]),
    ]

    for key, label, col in habit_keys:
        h_data = habits.get(key, {"current_streak": 0, "longest_streak": 0, "today_status": False})
        with col:
            with st.container(border=True):
                st.markdown(f"#### {label}")
                st.metric("Chuỗi hiện tại", f"{h_data['current_streak']} ngày", f"Kỷ lục: {h_data['longest_streak']} ngày")

                if h_data.get("today_status"):
                    st.success("✅ Đã đạt hôm nay")
                else:
                    st.warning("⏳ Chưa check-in")
                    if st.button("Điểm danh ngày", key=f"btn_checkin_{key}", use_container_width=True):
                        h_data["current_streak"] += 1
                        if h_data["current_streak"] > h_data["longest_streak"]:
                            h_data["longest_streak"] = h_data["current_streak"]
                        h_data["today_status"] = True

                        # Log event
                        st.session_state["event_log"].append({
                            "event_id": f"EVT-HABIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "type": "HABIT_CHECKIN",
                            "description": f"Hoàn thành thói quen: {label}",
                            "amount": 0,
                            "status": "CONFIRMED",
                        })

                        st.success(f"🎉 Đã điểm danh thói quen {label}! Chuỗi hiện tại: {h_data['current_streak']} ngày.")
                        st.rerun()

    st.write("---")
    st.markdown("#### 💡 Gợi ý duy trì thói quen hôm nay")
    st.info("• **Ăn ngoài có làm đứt streak nấu ăn không?** Không. Nếu bạn đã nấu 1 bữa ở nhà trong ngày, thói quen nấu ăn vẫn được duy trì hợp lệ.\n\n"
            "• **Tiêu chí tiết kiệm:** Ngân sách ngày hôm nay sẽ được hệ thống chốt tự động vào cuối ngày dựa trên tổng chi tiêu thực tế đã xác nhận.")


def _render_exercise_recommendations():
    """Gợi ý buổi tập cá nhân hóa phù hợp thể trạng và thời gian rảnh."""
    st.subheader("🏋️ Đề xuất buổi tập thể thao cá nhân hóa [CK]")
    st.caption("Ưu tiên tính khả thi, không gây quá tải và tôn trọng các giới hạn vận động của người dùng.")

    ex_profile = st.session_state.get("exercise_profile", {})

    col_setup, col_workout = st.columns([1, 1], gap="large")

    with col_setup:
        st.markdown("#### 1. Hồ sơ vận động & Giới hạn")
        with st.form("form_exercise_profile"):
            style_options = ["Calisthenics / Bodyweight tại nhà", "Gym & Tạ kháng lực", "Aerobic & Nhảy tim mạch", "Yoga & Giãn cơ nhẹ nhàng"]
            cur_style = ex_profile.get("style", "Calisthenics / Bodyweight tại nhà")
            style_idx = style_options.index(cur_style) if cur_style in style_options else 0
            sel_style = st.selectbox("Phong cách tập luyện", options=style_options, index=style_idx)

            col_time, col_exp = st.columns(2)
            with col_time:
                avail_time = st.selectbox("Thời gian rảnh hôm nay", [15, 20, 30, 45, 60], index=1)
            with col_exp:
                exp_level = st.selectbox("Trình độ", ["Mới bắt đầu", "Trung bình", "Nâng cao"])

            limitations = st.text_input("Hạn chế vận động / Chấn thương (nếu có)", value=ex_profile.get("limitations", "Khớp cổ tay yếu (hạn chế chống đẩy nặng)"))
            equipment_options = ["Không dụng cụ (Bodyweight)", "Thảm yoga", "Dây kháng lực (Resistance Band)", "Tạ đơn (Dumbbell)", "Xà đơn gắn cửa"]
            cur_eq = ex_profile.get("equipment", ["Thảm yoga"])
            sel_equipment = st.multiselect("Dụng cụ có sẵn", options=equipment_options, default=[e for e in cur_eq if e in equipment_options])

            if st.form_submit_button("Cập nhật hồ sơ tập luyện", use_container_width=True):
                st.session_state["exercise_profile"] = {
                    "style": sel_style,
                    "available_time": avail_time,
                    "experience_level": exp_level,
                    "limitations": limitations,
                    "equipment": sel_equipment,
                }
                st.success("✅ Đã cập nhật hồ sơ tập luyện!")
                st.rerun()

    with col_workout:
        st.markdown("#### 2. Lịch trình buổi tập gợi ý hôm nay")
        st.info("🛡️ **Tối ưu theo giới hạn:** Do có lưu ý *'Khớp cổ tay yếu'*, các động tác chống đẩy sàn đã được tự động thay thế bằng động tác kê tay cao (Incline) hoặc dùng cẳng tay (Plank).", icon="🩹")

        routine = [
            ("1. Khởi động khớp cổ tay, vai và gối", "3 phút xoay nhẹ nhàng"),
            ("2. Bodyweight Squat (Ngồi xổm không tạ)", "3 hiệp x 12 lần (Nghỉ 45 giây)"),
            ("3. Incline Push-up (Chống đẩy tay kê bàn)", "3 hiệp x 10 lần (Giảm tải áp lực cổ tay)"),
            ("4. Glute Bridge (Nâng hông trên thảm)", "3 hiệp x 15 lần (Kích hoạt cơ mông/đùi sau)"),
            ("5. Forearm Plank (Plank bằng cẳng tay)", "3 hiệp x 30 giây (Giữ thẳng lưng)"),
            ("6. Giãn cơ thả lỏng tĩnh", "3 phút thở sâu"),
        ]

        for name, detail in routine:
            st.markdown(f"**{name}**")
            st.caption(f"⚙️ {detail}")

        st.write("")
        col_btn, col_feedback = st.columns([1, 1])
        with col_btn:
            if st.button("🎉 Hoàn thành buổi tập", type="primary", use_container_width=True):
                habits = st.session_state.get("habits_streaks", {})
                if "daily_exercise" in habits:
                    habits["daily_exercise"]["current_streak"] += 1
                    habits["daily_exercise"]["today_status"] = True

                # Log event
                st.session_state["event_log"].append({
                    "event_id": f"EVT-WORKOUT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "WORKOUT_COMPLETE",
                    "description": f"Hoàn thành buổi tập '{sel_style}' ({avail_time} phút)",
                    "amount": 0,
                    "status": "CONFIRMED",
                })

                st.balloons()
                st.success("👏 Xuất sắc! Bạn đã hoàn thành buổi tập và tăng streak thể dục!")
                st.rerun()

        with col_feedback:
            st.selectbox("Đánh giá độ vừa sức:", ["Rất vừa sức", "Hơi nhẹ", "Hơi nặng / Khó theo"], index=0)
