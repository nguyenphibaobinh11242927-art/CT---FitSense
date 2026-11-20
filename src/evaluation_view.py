"""Module Đánh giá Sau Buổi tập & Thích ứng Thể lực (Evaluation View - SCRUM-22).

Phân hệ CT D7: Post-Workout Evaluation & Adaptive AI (Yêu cầu 69 – 71).
Thu thập điểm gắng sức RPE (thang Borg 1-10, mặc định 5, kèm emoji), mức độ mỏi cơ DOMS,
hiển thị tỷ lệ hoàn thành rho khách quan do AI đối chiếu (cố định), đưa ra lời khuyên phục hồi
(bài tập giãn cơ, giờ nghỉ sinh học, bù nước) và kích hoạt thuật toán Thích ứng Tải trọng (CT 4.4).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any
import streamlit as st

from src.weekly_plan_storage import save_week_state


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

DOMS_SEVERITY_OPTIONS = {
    "normal": "🟢 Bình thường (Căng cơ nhẹ, phục hồi nhanh)",
    "moderate": "🟡 Vừa phải (Mỏi rõ rệt sau bài tập, cần nghỉ ngơi)",
    "intense": "🔴 Đau nhức (Căng cứng khó chịu, cần giãn cơ & chườm)",
}

SATISFACTION_OPTIONS = {
    "very_satisfied": "🌟 Rất hài lòng (Đúng kế hoạch, thể lực sung mãn)",
    "satisfied": "👍 Hài lòng (Hoàn thành tốt các hiệp chính)",
    "neutral": "😐 Bình thường (Đạt yêu cầu tối thiểu)",
    "unsatisfied": "⚡ Cần cải thiện (Đuối sức hoặc đứt quãng)",
}

RECOVERY_RECOMMENDATIONS = {
    "Cơ đùi trước (Quads)": {
        "rest_hours": 48,
        "stretch_name": "Standing Quad Stretch (Giãn cơ đùi trước đứng)",
        "guide": "Đứng thẳng một chân, gập chân kia về sau và dùng tay giữ cổ chân kéo sát mông, giữ 30 giây mỗi bên.",
    },
    "Cơ mông (Glutes)": {
        "rest_hours": 48,
        "stretch_name": "Pigeon Pose / Figure-4 Stretch (Giãn mông chữ 4)",
        "guide": "Nằm ngửa hoặc ngồi gác mắt cá chân lên đùi đối diện, ôm đùi kéo nhẹ về phía ngực, giữ 30–45 giây.",
    },
    "Cơ ngực (Chest)": {
        "rest_hours": 48,
        "stretch_name": "Doorway Chest Stretch (Giãn ngực khung cửa)",
        "guide": "Đặt cẳng tay vuông góc vào mép cửa, bước nhẹ một chân lên trước và xoay người mở rộng lồng ngực 30 giây.",
    },
    "Lưng & Cột sống": {
        "rest_hours": 48,
        "stretch_name": "Cat-Cow & Child's Pose (Tư thế đứa trẻ & Con mèo)",
        "guide": "Quỳ gối hạ mông chạm gót chân, vươn dài hai tay ra phía trước thả lỏng toàn bộ sống lưng trong 45–60 giây.",
    },
    "Khớp gối": {
        "rest_hours": 48,
        "stretch_name": "Calf & Hamstring Gentle Stretch (Thả lỏng bắp chân & gân kheo)",
        "guide": "Ngồi duỗi thẳng chân, nghiêng nhẹ người về phía mũi chân không khóa cứng gối; chườm mát nếu thấy sưng nóng.",
    },
    "Cổ tay": {
        "rest_hours": 24,
        "stretch_name": "Wrist Flexor & Extensor Stretch (Giãn duỗi cổ tay)",
        "guide": "Duỗi thẳng một tay về trước, dùng tay kia bẻ nhẹ các ngón tay ngược về sau rồi gập xuống dưới, 20 giây mỗi chiều.",
    },
    "Không đau mỏi gì đặc biệt": {
        "rest_hours": 24,
        "stretch_name": "Full Body Light Shakeout (Thả lỏng toàn thân & Hít thở sâu)",
        "guide": "Đi bộ chậm 2–3 phút, xoay nhẹ các khớp chính và hít thở sâu bằng cơ hoành để hạ nhịp tim về trạng thái nghỉ.",
    },
}


def format_session_label(result: dict, sid: str = "", index: int = 1) -> str:
    """Định dạng nhãn buổi tập gồm tên buổi tập + thời gian thực (thay cho mã UUID ngắn)."""
    mode_text = (
        "AI Vision"
        if result.get("mode") == "ai"
        else ("Chế độ Tự do" if result.get("mode") == "manual" else str(result.get("mode", "Buổi tập")))
    )
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
    """AI tự tính tỉ lệ hoàn thành dựa trên dữ liệu buổi tập thực tế (CT Section 4.4).

    rho = Reps_actual / Reps_planned * 100%
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


def calculate_hydration_advice(duration_sec: int) -> tuple[int, str]:
    """Tính lượng nước bù khoáng khuyến nghị sau buổi tập dựa trên thời lượng vận động."""
    minutes = max(1, duration_sec // 60) if duration_sec else 20
    recommended_ml = min(800, max(300, round(minutes * 18 / 50) * 50))
    advice = (
        f"Uống từng ngụm nhỏ khoảng {recommended_ml}ml nước lọc hoặc nước điện giải "
        f"trong vòng 30 phút sau khi kết thúc buổi tập để bù khoáng và hạ nhiệt cơ thể."
    )
    return recommended_ml, advice


def get_recovery_advice(soreness_list: list[str]) -> list[dict[str, Any]]:
    """Tổng hợp lời khuyên phục hồi và bài tập giãn cơ dựa trên vùng cơ mỏi."""
    if not soreness_list:
        soreness_list = ["Không đau mỏi gì đặc biệt"]
    advice_items = []
    for s in soreness_list:
        info = RECOVERY_RECOMMENDATIONS.get(s, RECOVERY_RECOMMENDATIONS["Không đau mỏi gì đặc biệt"])
        advice_items.append({
            "target": s,
            "rest_hours": info["rest_hours"],
            "stretch_name": info["stretch_name"],
            "guide": info["guide"],
        })
    return advice_items


def compute_adaptive_adjustment(rho: float, rpe: int) -> dict[str, Any]:
    """Mô hình toán học Đánh giá sau buổi & Thích ứng Tải trọng (CT Section 4.4).

    V_next =
      - V_plan * 0.85  khi rho < 0.70 hoặc RPE >= 9 (Deload -15%)
      - V_plan * 0.95  khi 0.70 <= rho < 0.85 hoặc (RPE == 8 và rho < 0.90) (Giảm nhẹ -5%)
      - V_plan * 1.00  khi 0.85 <= rho <= 1.00 và RPE in [7, 8] (Duy trì tối ưu 1.00x)
      - V_plan * 1.10  khi rho >= 0.90 và RPE <= 6 (Tăng tiến Overload +10%)
    """
    if rho < 70 or rpe >= 9:
        return {
            "strategy": "deload",
            "multiplier": 0.85,
            "title": "🩹 Khuyến nghị Giảm tải (Deload Strategy -15%) 📉",
            "action": (
                "AI phát hiện bạn đã đuối sức hoặc gặp thử thách nặng. "
                "Tự động giảm 15% số reps (hoặc bớt 1 set) và tăng thời gian nghỉ giữa hiệp thêm 15 giây "
                "cho buổi tiếp theo để phục hồi hệ thần kinh và bảo vệ khớp!"
            ),
            "rep_delta": -2,
            "badge_type": "error",
        }
    elif (70 <= rho < 85) or (rpe == 8 and rho < 90):
        return {
            "strategy": "minor_deload",
            "multiplier": 0.95,
            "title": "🛡️ Khuyến nghị Giảm nhẹ Củng cố Thể lực (-5%) 📉",
            "action": (
                "Khối lượng tập vừa qua hơi vượt ngưỡng nhẹ. "
                "Tự động tinh chỉnh giảm nhẹ -5% số reps và tập trung chuẩn hóa kỹ thuật form động tác "
                "trước khi tăng tải ở chu kỳ kế tiếp."
            ),
            "rep_delta": -1,
            "badge_type": "warning",
        }
    elif 85 <= rho <= 100 and rpe in (7, 8):
        return {
            "strategy": "maintenance",
            "multiplier": 1.00,
            "title": "⚖️ Khuyến nghị Giữ nguyên Nhịp độ (Optimal Maintenance) 😊",
            "action": (
                "Hiệu suất vận động của bạn đạt điểm cân bằng sinh học hoàn hảo! "
                "Duy trì nguyên khối lượng và nhịp tập hiện tại để xây dựng nền tảng thể lực bền vững."
            ),
            "rep_delta": 0,
            "badge_type": "info",
        }
    else:  # rho >= 90 and rpe <= 6
        return {
            "strategy": "overload",
            "multiplier": 1.10,
            "title": "🚀 Khuyến nghị Tăng tiến Tải trọng (Progressive Overload +10%) 🔥",
            "action": (
                "Xuất sắc! Bạn hoàn thành xuất sắc giáo án với cảm giác thể lực rất sung sức. "
                "Tự động tăng 2 reps/set hoặc đề xuất bài tập biến thể nâng cao cho buổi sau để bứt phá giới hạn!"
            ),
            "rep_delta": 2,
            "badge_type": "success",
        }


def apply_adaptive_adjustment_to_schedule(
    schedule: list[dict],
    strategy_info: dict[str, Any],
) -> tuple[list[dict], int]:
    """Tự động cập nhật số reps vào các buổi tập kế tiếp trong Kế hoạch tuần (CT Section 4.4)."""
    if not isinstance(schedule, list):
        return schedule, 0

    updated = deepcopy(schedule)
    strategy = strategy_info.get("strategy", "maintenance")
    rep_delta = strategy_info.get("rep_delta", 0)
    multiplier = strategy_info.get("multiplier", 1.0)
    modified_count = 0

    if strategy == "maintenance" or multiplier == 1.0:
        return updated, 0

    for day in updated:
        if not isinstance(day, dict) or day.get("is_rest"):
            continue
        # Không sửa các buổi đã hoàn thành trong quá khứ
        if day.get("workout_status") == "completed":
            continue

        for ex in day.get("exercises", []):
            if not isinstance(ex, dict):
                continue
            curr_reps = ex.get("reps")
            if isinstance(curr_reps, int):
                if strategy in ("deload", "minor_deload"):
                    new_reps = max(5, round(curr_reps * multiplier))
                elif strategy == "overload":
                    new_reps = min(50, curr_reps + rep_delta)
                else:
                    new_reps = curr_reps
                if new_reps != curr_reps:
                    ex["reps"] = new_reps
                    modified_count += 1
            elif isinstance(curr_reps, str) and curr_reps.isdigit():
                val = int(curr_reps)
                if strategy in ("deload", "minor_deload"):
                    new_reps = max(5, round(val * multiplier))
                elif strategy == "overload":
                    new_reps = min(50, val + rep_delta)
                else:
                    new_reps = val
                if new_reps != val:
                    ex["reps"] = new_reps
                    modified_count += 1

    return updated, modified_count


def check_is_streak_earned(rho: float, duration_sec: int, is_completed: bool = False) -> bool:
    """Kiểm tra điều kiện tích lũy/bảo toàn chuỗi Streak theo CT Section 4.5.

    Is_Streak_Earned = True nếu (rho >= 50%) OR (T_active >= 600 giây)
    """
    return bool(rho >= 50 or duration_sec >= 600 or is_completed)


def render_evaluation_view():
    """Hiển thị Màn hình Đánh giá toàn diện sau buổi tập (Post-Workout Evaluation - SCRUM-22)."""
    st.header("📝 Đánh giá Sau Buổi tập & Tối ưu Thích ứng Thể lực")
    st.caption(
        "AI tự động đối chiếu tỉ lệ hoàn thành rho, thu thập điểm gắng sức Borg RPE (1-10) "
        "và mỏi cơ DOMS để điều chỉnh tải trọng buổi tập kế tiếp."
    )

    results = st.session_state.get("workout_results", {})
    result = None
    selected_id = None

    if isinstance(results, dict) and results:
        ids = list(reversed(results))
        selected_id = st.selectbox(
            "Buổi tập cần đánh giá (Tên & Thời gian thực):",
            ids,
            format_func=lambda sid: format_session_label(results[sid], sid=sid),
            key="review_session_id",
        )
        result = results[selected_id]

    # Tính toán thông số buổi tập
    completion_rate, session_label, session_detail = compute_ai_completion_rate(
        st.session_state, selected_result=result
    )

    reps_done = result.get("reps", 0) if result else 0
    duration_sec = result.get("duration_seconds", result.get("duration_sec", 900)) if result else 900
    minutes = duration_sec // 60
    seconds = duration_sec % 60
    calories = result.get("calories", round(reps_done * 0.4 + 45.0, 1)) if result else round(reps_done * 0.4 + 45.0, 1)

    # Bảng tóm tắt thành tích buổi tập (Yêu cầu 69)
    with st.container(border=True):
        st.subheader("📊 Bảng Tóm tắt Thành tích Buổi tập (AI Performance Summary)")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🏋️ Reps thực hiện", f"{reps_done} reps")
        m2.metric("⏱️ Thời gian tập", f"{minutes}p {seconds}s")
        m3.metric("🔥 Calo tiêu hao", f"{calories} kcal")
        m4.metric("🤖 Tỉ lệ hoàn thành (ρ)", f"{completion_rate}%")

        st.progress(
            max(0.0, min(1.0, completion_rate / 100.0)),
            text=f"🔒 AI Verified: {session_detail}",
        )

    col1, col2 = st.columns([1.2, 1], gap="medium")

    with col1:
        st.subheader("1. Khảo sát Cảm nhận & Mỏi cơ Sau Buổi tập")

        rpe = st.select_slider(
            "Thang đo Mức độ Gắng sức RPE (Borg Scale 1 - 10):",
            options=list(range(1, 11)),
            value=5,
            help="1: Rất nhẹ 😌 -> 5: Vừa sức 😤 -> 8: Rất mệt 😫 -> 10: Kiệt sức 🤯.",
        )

        st.info(f"📊 Mức RPE {rpe}/10: **{RPE_DESCRIPTIONS.get(rpe)}**")

        muscle_soreness = st.multiselect(
            "Bộ phận cảm thấy mỏi hoặc căng cơ nhiều nhất (DOMS):",
            options=[
                "Cơ đùi trước (Quads)",
                "Cơ mông (Glutes)",
                "Cơ ngực (Chest)",
                "Lưng & Cột sống",
                "Khớp gối",
                "Cổ tay",
                "Không đau mỏi gì đặc biệt",
            ],
            default=["Không đau mỏi gì đặc biệt"],
        )

        doms_severity_key = st.radio(
            "Mức độ mỏi cơ cục bộ:",
            options=list(DOMS_SEVERITY_OPTIONS.keys()),
            format_func=lambda k: DOMS_SEVERITY_OPTIONS[k],
            index=1,
            horizontal=True,
        )

        satisfaction_key = st.radio(
            "Mức độ hài lòng về buổi tập vừa qua:",
            options=list(SATISFACTION_OPTIONS.keys()),
            format_func=lambda k: SATISFACTION_OPTIONS[k],
            index=1,
            horizontal=True,
        )

        user_note = st.text_area(
            "Ghi chú cảm xúc & thể trạng cá nhân (tùy chọn):",
            placeholder="Ví dụ: Hôm nay cơ đùi trước căng mỏi rất đã, kỹ thuật xuống sâu ổn định 💪...",
        )

        auto_apply = st.checkbox(
            "✨ Tự động áp dụng khuyến nghị Adaptive AI vào Kế hoạch tuần tới",
            value=True,
            help="Khi chọn, số reps các buổi tập sau sẽ tự động được điều chỉnh theo thuật toán CT 4.4.",
        )

        if st.button("💾 Gửi Đánh giá & Xem Đề xuất AI", type="primary", use_container_width=True):
            # 1. Tính toán Streak theo CT 4.5
            is_completed = bool(result and result.get("status") == "completed")
            streak_earned = check_is_streak_earned(completion_rate, duration_sec, is_completed)
            if streak_earned:
                st.session_state["has_worked_out_today"] = True

            # 2. Tính toán khuyến nghị thích ứng tải trọng
            strategy_info = compute_adaptive_adjustment(completion_rate, rpe)
            recovery_items = get_recovery_advice(muscle_soreness)
            hyd_ml, hyd_text = calculate_hydration_advice(duration_sec)

            eval_record = {
                "session_id": selected_id or "current",
                "session_label": session_label,
                "completion_rate": completion_rate,
                "rpe": rpe,
                "rpe_desc": RPE_DESCRIPTIONS.get(rpe),
                "soreness": muscle_soreness,
                "doms_severity": doms_severity_key,
                "satisfaction": satisfaction_key,
                "note": user_note,
                "auto_apply": auto_apply,
                "strategy": strategy_info,
                "recovery_items": recovery_items,
                "hydration_ml": hyd_ml,
                "hydration_text": hyd_text,
                "submitted_at": datetime.now().strftime("%H:%M %d/%m/%Y"),
            }

            st.session_state["last_eval"] = eval_record

            # Lưu vào danh sách lịch sử đánh giá CSDL
            eval_history = st.session_state.setdefault("evaluation_history", [])
            eval_history.insert(0, eval_record)

            # Cập nhật kết quả buổi tập nếu có
            if result is not None:
                result["rpe"] = rpe
                result["evaluation"] = eval_record

            # 3. Tự động áp dụng vào kế hoạch tuần nếu người dùng đồng ý
            modified_count = 0
            if auto_apply:
                schedule = st.session_state.get("weekly_schedule")
                if isinstance(schedule, list):
                    updated_schedule, modified_count = apply_adaptive_adjustment_to_schedule(
                        schedule, strategy_info
                    )
                    st.session_state["weekly_schedule"] = updated_schedule
                    save_week_state(st.session_state)

            if modified_count > 0:
                st.success(
                    f"🎉 Đã ghi nhận phản hồi vào hồ sơ thể lực và tự động điều chỉnh {modified_count} "
                    f"bài tập trong Kế hoạch tuần! CappyHeo đang đồng hành cùng bạn nhé 🥰"
                )
            else:
                st.success("🎉 Đã ghi nhận phản hồi vào hồ sơ thể lực thành công! CappyHeo rất tự hào về bạn 🥰")

    with col2:
        st.subheader("2. Khuyến nghị Tự động của Adaptive AI")

        eval_data = st.session_state.get("last_eval")
        if eval_data:
            comp = eval_data.get("completion_rate", completion_rate)
            user_rpe = eval_data.get("rpe", rpe)
            soreness_selected = eval_data.get("soreness", muscle_soreness)
            strat = eval_data.get("strategy") or compute_adaptive_adjustment(comp, user_rpe)
        else:
            comp = completion_rate
            user_rpe = rpe
            soreness_selected = muscle_soreness
            strat = compute_adaptive_adjustment(comp, user_rpe)

        with st.container(border=True):
            if strat["strategy"] == "deload":
                st.error(f"{strat['title']}")
                st.write(f"- **Chỉ số:** Hoàn thành **{comp}%** · Độ gắng sức **RPE {user_rpe}/10** 😮‍💨.")
                st.write(f"- **Hành động AI:** {strat['action']}")
            elif strat["strategy"] == "minor_deload":
                st.warning(f"{strat['title']}")
                st.write(f"- **Chỉ số:** Hoàn thành **{comp}%** · Độ gắng sức **RPE {user_rpe}/10** 😐.")
                st.write(f"- **Hành động AI:** {strat['action']}")
            elif strat["strategy"] == "overload":
                st.success(f"{strat['title']}")
                st.write(f"- **Chỉ số:** Hoàn thành **{comp}%** · Độ gắng sức **RPE {user_rpe}/10** 💪.")
                st.write(f"- **Hành động AI:** {strat['action']}")
            else:
                st.info(f"{strat['title']}")
                st.write(f"- **Chỉ số:** Hoàn thành **{comp}%** · Độ gắng sức **RPE {user_rpe}/10** ✨.")
                st.write(f"- **Hành động AI:** {strat['action']}")

        # Khối Lời khuyên Phục hồi cá nhân hóa từ AI (Yêu cầu 69)
        with st.container(border=True):
            st.subheader("🧘 Lời khuyên Phục hồi Sinh học (Recovery Advice)")
            rec_items = get_recovery_advice(soreness_selected)
            for item in rec_items:
                st.markdown(f"**• {item['target']}** (Nghỉ sinh học khuyến nghị: **{item['rest_hours']}h**):")
                st.caption(f"👉 *{item['stretch_name']}:* {item['guide']}")

            hyd_ml, hyd_text = calculate_hydration_advice(duration_sec)
            st.info(f"💧 **Nhắc nhở bù nước:** {hyd_text}")
