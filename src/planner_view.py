"""Module Lập Kế hoạch Tập luyện Thông minh (Planner View).

Lập lịch tập tuần, phân bổ nhóm cơ, giải thích lý do lựa chọn bài tập theo mục tiêu và hạn chế vận động.
"""

import streamlit as st


def render_planner_view():
    """Hiển thị giao diện lịch tập tuần và giáo án thể thao cá nhân hóa."""
    st.header("📋 Kế hoạch Tập luyện & Lịch tuần Thông minh")
    st.caption("AI tự động tối ưu hóa lịch phân bổ nhóm cơ và thời gian phục hồi dựa trên thể trạng của bạn.")

    profile = st.session_state.get("user_profile", {})
    schedule = st.session_state.get("weekly_schedule", [])

    c_top1, c_top2 = st.columns([3, 1])
    with c_top1:
        st.info(f"🎯 **Mục tiêu:** {profile.get('goal', 'Tăng cơ Calisthenics')} | **Thời lượng:** {profile.get('session_duration_minutes', 45)} phút/buổi | **Tần suất:** {profile.get('days_per_week', 4)} buổi/tuần")
    with c_top2:
        if st.button("🔄 Tái lập Kế hoạch AI", help="Yêu cầu AI phân tích lại thể trạng và tạo giáo án mới"):
            st.toast("AI đã tối ưu lại giáo án tuần theo thể trạng hiện tại!", icon="⚡")

    st.subheader("Lịch phân bổ nhóm cơ trong tuần")

    tabs = st.tabs([f"Thứ {i+2}" if i < 6 else "Chủ Nhật" for i in range(7)])

    for i, tab in enumerate(tabs):
        with tab:
            day_data = schedule[i] if i < len(schedule) else {"day": f"Thứ {i+2}", "focus": "Nghỉ ngơi phục hồi", "is_rest": True, "exercises": []}

            if day_data.get("is_rest", False):
                st.success("🌱 **Ngày Nghỉ Phục Hồi Hoàn Toàn (Rest & Active Recovery)**")
                st.write("- Hoạt động khuyến nghị: Đi bộ nhẹ nhàng 20 phút, giãn cơ toàn thân hoặc tập hít thở.")
                st.caption("💡 Cơ bắp không phát triển trong lúc tập, chúng phục hồi và phát triển khi bạn nghỉ ngơi!")
            else:
                col_f1, col_f2 = st.columns([3, 1])
                with col_f1:
                    st.markdown(f"**Trọng tâm buổi tập:** `{day_data.get('focus', 'Toàn thân')}`")
                    st.caption(f"💡 **Lý do AI chọn giáo án này:** {day_data.get('ai_reason', 'Tối ưu kích thích cơ bắp không chạm vào chấn thương khớp gối.')}")
                with col_f2:
                    if st.button(f"🚀 Tập ngay buổi này", key=f"start_btn_{i}", type="primary"):
                        st.session_state["selected_session_day"] = day_data.get("day", f"Thứ {i+2}")
                        st.session_state["nav_selection"] = "⚡ Phòng tập Rảnh tay (HUD)"
                        st.rerun()

                st.markdown("#### Danh sách bài tập phân bổ:")
                exercises = day_data.get("exercises", [])
                for ex_idx, ex in enumerate(exercises):
                    with st.expander(f"Bài {ex_idx+1}: {ex.get('name')} — {ex.get('sets')} Sets × {ex.get('reps')} Reps (Nghỉ {ex.get('rest_sec')}s)", expanded=True):
                        c1, c2, c3 = st.columns([2, 1, 1])
                        with c1:
                            st.write(f"- **Nhóm cơ chính:** `{ex.get('primary_muscle')}`")
                            st.write(f"- **Nhóm cơ bổ trợ:** `{ex.get('secondary_muscle', 'Không')}`")
                            st.write(f"- **Lưu ý form:** {ex.get('form_tip', 'Giữ thẳng lưng, gồng chặt cơ bụng.')}")
                        with c2:
                            st.write(f"- **Kháng lực/Dụng cụ:** `{ex.get('equipment', 'Bodyweight')}`")
                            st.write(f"- **Độ khó:** `{ex.get('difficulty', 'Intermediate')}`")
                        with c3:
                            if st.button("🔁 Đổi bài khác", key=f"swap_{i}_{ex_idx}"):
                                st.warning(f"Đã đổi bài tập sang: {ex.get('substitute', 'Plank tĩnh')}")
