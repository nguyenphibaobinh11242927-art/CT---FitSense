"""Module Đánh giá Sau Buổi tập & Thích ứng Thể lực (Evaluation View).

Ghi nhận mức độ gắng sức RPE (1-10), cảm giác mỏi mệt và thuật toán AI tự động tính tỉ lệ hoàn thành + điều chỉnh tải trọng buổi sau.
"""

from datetime import datetime
import streamlit as st


RPE_DESCRIPTIONS = {
    1: "😌 Rất nhẹ (Gần như không thấy mệt)",
    2: "🙂 Nhẹ nhàng, hít thở rất thoải mái",
    3: "😊 Vừa phải (Bắt đầu làm nóng cơ thể)",
    4: "😉 Hơi thử thách nhẹ, còn rất nhiều sức",
    5: "😤 Vừa sức lý tưởng (Nhịp tập ổn định)",
    6: "😅 Khá mệt nhưng vẫn kiểm soát kỹ thuật tốt",
    7: "😓 Nặng (Cơ bắp bắt đầu mỏi rõ rệt)",
    8: "😫 Rất mệt (Cần tập trung cao độ, thở dốc)",
    9: "🥵 Cực kỳ nặng (Gần ngưỡng chịu đựng tối đa)",
    10: "🤯 Kiệt sức hoàn toàn (Không thể làm thêm 1 rep)",
}


def format_session_label(result: dict, sid: str = "", index: int = 1) -> str:
    """Định dạng nhãn buổi tập gồm tên buổi tập + thời gian thực (thay cho mã UUID ngắn)."""
    mode_text = "AI Vision" if result.get("mode") == "ai" else ("Chế độ Tự do" if result.get("mode") == "manual" else str(result.get("mode", "Buổi tập")))
    name = (
        result.get("session_name")
        or result.get("focus")
        or f"Buổi tập {mode_text} #{index}"
    )
    timestamp = (
        result.get("finished_at")
        or result.get("timestamp")
        or result.get("created_at")
        or datetime.now().strftime("%H:%M %d/%m/%Y")
    )
    reps = result.get("reps", result.get("actual_reps", 0))
    return f"{name} · 🕒 {timestamp} ({reps} rep)"


def compute_ai_completion_rate(
    session_state: dict,
    selected_result: dict | None = None,
) -> tuple[int, str, str]:
    """AI tự tính tỉ lệ hoàn thành dựa trên dữ liệu buổi tập thực tế.

    Trả về: (completion_pct, session_display_label, detail_caption)
    """
    if isinstance(selected_result, dict):
        actual = max(0, int(selected_result.get("reps", selected_result.get("actual_reps", 0))))
        default_target = 66 if selected_result.get("mode") == "manual" else 36
        target = max(1, int(selected_result.get("target_reps", default_target)))
        pct = min(100, round(actual * 100 / target))
        label = format_session_label(selected_result)
        detail = f"AI đối chiếu dữ liệu buổi tập: {actual}/{target} reps ({selected_result.get('mode', 'ai')})."
        return pct, label, detail

    summary = session_state.get("last_session_summary")
    if isinstance(summary, dict):
        actual = max(0, int(summary.get("actual_reps", summary.get("reps", 0))))
        target = max(1, int(summary.get("target_reps", 36)))
        pct = min(100, round(actual * 100 / target))
        label = format_session_label(summary)
        detail = f"AI đối chiếu {actual}/{target} reps ({summary.get('mode', 'HUD')})."
        return pct, label, detail

    workout_session = session_state.get("workout_session")
    if workout_session is not None and getattr(workout_session, "ai_reps", 0) > 0:
        actual = int(workout_session.ai_reps)
        target = 36
        pct = min(100, round(actual * 100 / target))
        now_label = datetime.now().strftime("%H:%M %d/%m/%Y")
        return pct, f"Buổi tập AI Vision hiện tại · 🕒 {now_label}", f"AI ghi nhận {actual}/{target} reps từ phiên tập."

    now_label = datetime.now().strftime("%H:%M %d/%m/%Y")
    return 0, f"Chưa ghi nhận dữ liệu buổi tập · 🕒 {now_label}", "Hãy tập qua HUD hoặc Chế độ Tự do để AI chấm tỉ lệ tự động."


def render_evaluation_view():
    """Hiển thị form đánh giá cảm giác thể lực sau buổi và phản hồi của thuật toán Adaptive AI."""
    st.header("📝 Đánh giá Sau Buổi tập & Tối ưu Thích ứng Thể lực")
    st.caption("AI tự động tính tỉ lệ hoàn thành từ dữ liệu buổi tập và kết hợp RPE để điều chỉnh giáo án kế tiếp.")

    results = st.session_state.get("workout_results", {})
    result = None
    if isinstance(results, dict) and results:
        ids = list(reversed(results))
        selected = st.selectbox(
            "Buổi tập cần đánh giá (Tên & Thời gian thực):",
            ids,
            format_func=lambda sid: format_session_label(results[sid], sid=sid),
            key="review_session_id",
        )
        result = results[selected]
        outcome = "✅ Hoàn thành" if result.get("status") == "completed" else "⏸️ Kết thúc sớm"
        mode_str = "AI Vision" if result.get("mode") == "ai" else "Tự do"
        st.write(f"**{outcome}** · {mode_str} · {result.get('reps', 0)} rep · 🕒 {result.get('finished_at', 'Vừa xong')}")
        if result.get("manual"):
            counts = result["manual"]
            st.caption(f"Squat: {counts['squat']} · Push-up: {counts['pushup']} · Plank: {counts['plank_seconds']} giây")

    col1, col2 = st.columns([1.2, 1], gap="medium")

    with col1:
        st.subheader("1. Khảo sát Cảm nhận Sau Buổi tập")

        completion_rate, session_label, session_detail = compute_ai_completion_rate(
            st.session_state, selected_result=result
        )
        with st.container(border=True):
            st.markdown(f"**📋 Buổi tập:** {session_label}")
            st.metric(label="🤖 Tỉ lệ hoàn thành do AI đánh giá", value=f"{completion_rate}%")
            st.progress(max(0.0, min(1.0, completion_rate / 100.0)), text=session_detail)

        rpe = st.select_slider(
            "Thang đo Mức độ Gắng sức RPE (Borg Scale 1 - 10):",
            options=list(range(1, 11)),
            value=5,
            help="1: Rất nhẹ 😌 -> 5: Vừa sức 😤 -> 8: Rất mệt 😫 -> 10: Kiệt sức 🤯.",
        )

        st.info(f"📊 Mức RPE {rpe}/10: **{RPE_DESCRIPTIONS.get(rpe)}**")

        muscle_soreness = st.multiselect(
            "Bộ phận cảm thấy mỏi hoặc căng cơ nhiều nhất:",
            options=["Cơ đùi trước (Quads)", "Cơ mông (Glutes)", "Cơ ngực (Chest)", "Lưng & Cột sống", "Khớp gối", "Cổ tay", "Không đau mỏi gì đặc biệt"],
            default=["Không đau mỏi gì đặc biệt"],
        )

        user_note = st.text_area(
            "Ghi chú cảm xúc & thể trạng cá nhân (tùy chọn):",
            placeholder="Ví dụ: Hôm nay hơi căng bắp chân nhưng tinh thần rất sung 💪...",
        )

        if st.button("💾 Gửi Đánh giá & Xem Đề xuất AI", type="primary", use_container_width=True):
            if result is None or result.get("status") == "completed":
                st.session_state["has_worked_out_today"] = True
            st.session_state["last_eval"] = {
                "session_label": session_label,
                "completion_rate": completion_rate,
                "rpe": rpe,
                "soreness": muscle_soreness,
                "note": user_note,
                "submitted_at": datetime.now().strftime("%H:%M %d/%m/%Y"),
            }
            st.success("🎉 Đã ghi nhận phản hồi vào hồ sơ thể lực! CappyHeo đang ăn mừng cùng bạn nè 🥰")

    with col2:
        st.subheader("2. Khuyến nghị Tự động của Adaptive AI")

        eval_data = st.session_state.get(
            "last_eval",
            {"completion_rate": completion_rate, "rpe": rpe, "soreness": muscle_soreness},
        )
        comp = eval_data.get("completion_rate", completion_rate)
        user_rpe = eval_data.get("rpe", rpe)

        with st.container(border=True):
            if comp < 70 or user_rpe >= 9:
                st.error("🩹 **Khuyến nghị Giảm tải (Deload Strategy -15%) 📉:**")
                st.write(f"- AI ghi nhận mức hoàn thành **{comp}%** với độ gắng sức **{user_rpe}/10** 😮‍💨.")
                st.write("- **Hành động AI:** Tự động giảm 1–2 sets hoặc tăng thời gian nghỉ giữa hiệp thêm 15 giây cho buổi kế tiếp để bảo vệ khớp nhé! 💚")
            elif comp >= 90 and user_rpe <= 6:
                st.success("🚀 **Khuyến nghị Tăng tiến Tải trọng (Progressive Overload +10%) 🔥:**")
                st.write(f"- Xuất sắc! Bạn đạt **{comp}%** giáo án mà vẫn giữ nhịp độ rất tốt (**RPE {user_rpe}/10**) 💪.")
                st.write("- **Hành động AI:** Buổi sau sẽ tự động tăng 2 reps/set hoặc gợi ý biến thể nâng cao để bứt phá giới hạn! ⭐")
            else:
                st.info("⚖️ **Khuyến nghị Giữ nguyên Nhịp độ (Optimal Maintenance) 😊:**")
                st.write(f"- Hiệu suất cân bằng tuyệt vời (**{comp}%**, **RPE {user_rpe}/10**) ✨.")
                st.write("- **Hành động AI:** Duy trì khối lượng và nhịp tập hiện tại để xây dựng nền tảng bền vững cho chu kỳ tuần tới! 🦫")

            st.markdown("---")
            st.checkbox("✨ Xác nhận tự động áp dụng thay đổi này vào Kế hoạch tuần tới", value=True)
