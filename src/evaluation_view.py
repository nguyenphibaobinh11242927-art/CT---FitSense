"""Module Đánh giá Sau Buổi tập & Thích ứng Thể lực (Evaluation View).

Ghi nhận mức độ gắng sức RPE (1-10), cảm giác mỏi mệt và thuật toán AI tự động điều chỉnh tải trọng buổi sau.
"""

import streamlit as st


def render_evaluation_view():
    """Hiển thị form đánh giá cảm giác thể lực sau buổi và phản hồi của thuật toán Adaptive AI."""
    st.header("📝 Đánh giá Sau Buổi tập & Tối ưu Thích ứng Thể lực")
    st.caption("AI lắng nghe phản hồi sinh học của bạn để điều chỉnh độ khó cho các buổi kế tiếp.")

    col1, col2 = st.columns([1.2, 1], gap="medium")

    with col1:
        st.subheader("1. Khảo sát Cảm nhận Sau Buổi tập")

        completion_rate = st.slider("Tỉ lệ hoàn thành khối lượng giáo án hôm nay (%):", min_value=10, max_value=100, value=75, step=5, help="Ví dụ bạn mệt và dừng sớm ở mức 70-75% giáo án.")

        rpe = st.select_slider(
            "Thang đo Mức độ Gắng sức RPE (Borg Scale 1 - 10):",
            options=list(range(1, 11)),
            value=8,
            help="1: Rất nhẹ -> 5: Vừa sức -> 8: Rất mệt/Gắng sức cao -> 10: Kiệt sức hoàn toàn."
        )

        rpe_descriptions = {
            1: "Rất nhẹ (Gần như không thấy mệt)",
            2: "Nhẹ nhàng",
            3: "Vừa phải (Bắt đầu nóng người)",
            4: "Hơi thử thách",
            5: "Vừa sức lý tưởng",
            6: "Khá mệt nhưng vẫn kiểm soát tốt",
            7: "Nặng (Cơ bắp bắt đầu mỏi nhiều)",
            8: "Rất mệt (Cần tập trung cao độ, thở dốc)",
            9: "Cực kỳ nặng (Gần ngưỡng chịu đựng)",
            10: "Kiệt sức hoàn toàn (Không thể làm thêm 1 rep nào nữa)"
        }
        st.info(f"📊 Mức RPE {rpe}: **{rpe_descriptions.get(rpe)}**")

        muscle_soreness = st.multiselect(
            "Bộ phận cảm thấy mỏi hoặc căng cơ nhiều nhất:",
            options=["Cơ đùi trước (Quads)", "Cơ mông (Glutes)", "Cơ ngực (Chest)", "Lưng & Cột sống", "Khớp gối", "Cổ tay", "Không đau mỏi gì đặc biệt"],
            default=["Cơ đùi trước (Quads)", "Cơ mông (Glutes)"]
        )

        user_note = st.text_area("Ghi chú cá nhân (tùy chọn):", placeholder="Hôm nay trời hơi oi bức, hiệp cuối Squat bị mỏi gối nhẹ nên dừng sớm...")

        if st.button("💾 Gửi Đánh giá & Xem Đề xuất AI", type="primary", use_container_width=True):
            st.session_state["has_worked_out_today"] = True
            st.session_state["last_eval"] = {
                "completion_rate": completion_rate,
                "rpe": rpe,
                "soreness": muscle_soreness,
                "note": user_note
            }
            st.success("✅ Đã ghi nhận phản hồi vào hồ sơ thể lực! Chú Capybara đang ăn mừng cùng bạn kìa 🥰")

    with col2:
        st.subheader("2. Khuyến nghị Tự động của Adaptive AI")

        # Thuật toán thích ứng dựa trên Completion Rate và RPE
        eval_data = st.session_state.get("last_eval", {"completion_rate": 75, "rpe": 8, "soreness": ["Cơ đùi trước (Quads)"]})
        comp = eval_data.get("completion_rate", 75)
        user_rpe = eval_data.get("rpe", 8)

        with st.container(border=True):
            if comp < 70 or user_rpe >= 9:
                st.error("📉 **Khuyến nghị Giảm tải (Deload Strategy -15%):**")
                st.write(f"- Hệ thống nhận thấy bạn đạt mức **{comp}%** giáo án với độ gắng sức cao (**RPE {user_rpe}**).")
                st.write("- **Hành động AI:** Tự động giảm $1-2$ sets hoặc tăng thời gian nghỉ giữa hiệp thêm 15 giây cho buổi chân tiếp theo để tránh chấn thương và quá tải cơ xương khớp.")
            elif comp >= 90 and user_rpe <= 6:
                st.success("📈 **Khuyến nghị Tăng tiến Tải trọng (Progressive Overload +10%):**")
                st.write(f"- Bạn hoàn thành xuất sắc **{comp}%** buổi tập ở mức vừa sức (**RPE {user_rpe}**).")
                st.write("- **Hành động AI:** Buổi sau sẽ tự động tăng $2$ reps/set hoặc chuyển sang biến thể nâng cao để tiếp tục kích thích cơ bắp.")
            else:
                st.info("⚖️ **Khuyến nghị Giữ nguyên Nhịp độ (Optimal Maintenance):**")
                st.write(f"- Hiệu suất buổi tập ở mức cân bằng hoàn hảo (**{comp}%**, **RPE {user_rpe}**).")
                st.write("- **Hành động AI:** Duy trì khối lượng và bài tập tương đương cho chu kỳ tuần tới.")

            st.markdown("---")
            st.checkbox("Xác nhận tự động áp dụng thay đổi này vào Kế hoạch tuần tới", value=True)
