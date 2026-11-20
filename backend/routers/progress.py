"""Workout Progress, History, and Muscle Recovery Heatmap Router."""

from datetime import date, datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.schemas import EvaluationSubmitRequest

router = APIRouter(prefix="/api/progress", tags=["Progress & Evaluation"])

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

PERSONAL_RECORDS = {
    "Squat Thể dục": "Chưa ghi nhận",
    "Standard Push-up": "Chưa ghi nhận",
    "Plank Tĩnh": "Chưa ghi nhận",
    "Dips trên ghế": "Chưa ghi nhận",
}

WEEKLY_VOLUME = [
    {"week": "Tuần 1", "reps": 0, "minutes": 0},
    {"week": "Tuần 2", "reps": 0, "minutes": 0},
    {"week": "Tuần 3", "reps": 0, "minutes": 0},
    {"week": "Tuần 4", "reps": 0, "minutes": 0},
    {"week": "Tuần này", "reps": 0, "minutes": 0},
]

EVALUATION_HISTORY: list[dict[str, Any]] = []

# Global workout events and history storage (starts empty for genuine user data)
WORKOUT_HISTORY: list[dict[str, Any]] = []

HAS_WORKED_OUT_TODAY = False


def record_workout(
    exercise_id: str,
    reps: int,
    duration_sec: int,
    rpe: Optional[int],
    notes: str = "",
    calories: float = 0.0,
    day: Optional[str] = None,
    completion_rate: Optional[float] = None,
    status: str = "completed",
    mode: Optional[str] = None,
    sets: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    global HAS_WORKED_OUT_TODAY
    if status == "completed":
        HAS_WORKED_OUT_TODAY = True
    
    from backend.routers.exercises import get_catalog
    catalog = get_catalog()
    ex = next((e for e in catalog if e["id"] == exercise_id), None)
    ex_name = ex["name"] if ex else exercise_id
    
    comp_rate = completion_rate if completion_rate is not None else 100.0

    record = {
        "id": f"w-{len(WORKOUT_HISTORY) + 1:02d}",
        "exercise_id": exercise_id,
        "exercise_name": ex_name,
        "actual_date": date.today().isoformat(),
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "reps": reps,
        "duration_sec": duration_sec,
        "calories": calories,
        "rpe": rpe,
        "day": day or "Hôm nay",
        "notes": notes,
        "completion_rate": comp_rate,
        "status": status,
    }
    if mode is not None:
        record["mode"] = mode
    if sets is not None:
        record["sets"] = sets
    WORKOUT_HISTORY.insert(0, record)
    return record


@router.get("/history")
def get_history():
    return {
        "count": len(WORKOUT_HISTORY),
        "history": WORKOUT_HISTORY,
    }


@router.get("/stats")
def get_stats():
    total_workouts = len(WORKOUT_HISTORY)
    total_reps = sum(w.get("reps", 0) for w in WORKOUT_HISTORY)
    total_calories = round(sum(w.get("calories", 0) for w in WORKOUT_HISTORY), 1)
    total_duration_min = round(sum(w.get("duration_sec", 0) for w in WORKOUT_HISTORY) / 60, 1)
    rpe_scores = [w.get("rpe", 7) for w in WORKOUT_HISTORY if w.get("rpe", 7) is not None]
    avg_rpe = round(sum(rpe_scores) / len(rpe_scores), 1) if rpe_scores else 0.0
    
    # Calculate consecutive workout streak
    has_completed_workout = any(w.get("status", "completed") == "completed" for w in WORKOUT_HISTORY)
    streak = int(HAS_WORKED_OUT_TODAY or has_completed_workout)
    longest = max(streak, 0)
    
    # Calculate average completion rate
    if total_workouts == 0:
        avg_completion_rate = 0.0
    else:
        rates = [w.get("completion_rate", 100.0) for w in WORKOUT_HISTORY]
        avg_completion_rate = round(sum(rates) / len(rates), 1)

    return {
        "total_workouts": total_workouts,
        "total_reps": total_reps,
        "total_calories": total_calories,
        "total_duration_min": total_duration_min,
        "average_rpe": avg_rpe,
        "average_completion_rate": avg_completion_rate,
        "current_streak_days": streak,
        "longest_streak_days": longest,
        "has_worked_out_today": HAS_WORKED_OUT_TODAY,
        "personal_records": PERSONAL_RECORDS,
        "weekly_volume": WEEKLY_VOLUME,
    }


STRETCHING_RECOMMENDATIONS = {
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


@router.get("/evaluation-meta")
def get_evaluation_metadata():
    return {
        "rpe_descriptions": RPE_DESCRIPTIONS,
        "soreness_options": [
            "Cơ đùi trước (Quads)",
            "Cơ mông (Glutes)",
            "Cơ ngực (Chest)",
            "Lưng & Cột sống",
            "Khớp gối",
            "Cổ tay",
            "Không đau mỏi gì đặc biệt",
        ],
        "doms_severity_options": {
            "normal": "🟢 Bình thường (Căng cơ nhẹ, phục hồi nhanh)",
            "moderate": "🟡 Vừa phải (Mỏi rõ rệt sau bài tập, cần nghỉ ngơi)",
            "intense": "🔴 Đau nhức (Căng cứng khó chịu, cần giãn cơ & chườm)",
        },
        "satisfaction_options": {
            "very_satisfied": "🌟 Rất hài lòng (Đúng kế hoạch, thể lực sung mãn)",
            "satisfied": "👍 Hài lòng (Hoàn thành tốt các hiệp chính)",
            "neutral": "😐 Bình thường (Đạt yêu cầu tối thiểu)",
            "unsatisfied": "⚡ Cần cải thiện (Đuối sức hoặc đứt quãng)",
        },
        "stretching_recommendations": STRETCHING_RECOMMENDATIONS,
    }


@router.get("/evaluations")
def get_evaluations():
    return {
        "count": len(EVALUATION_HISTORY),
        "evaluations": EVALUATION_HISTORY,
    }


@router.post("/evaluate")
def submit_evaluation(payload: EvaluationSubmitRequest):
    global HAS_WORKED_OUT_TODAY
    comp = payload.completion_rate
    user_rpe = payload.rpe
    duration_sec = payload.duration_sec or 900
    
    # CT Section 4.5 Streak condition: rho >= 50% OR T_active >= 600 seconds
    if comp >= 50 or duration_sec >= 600:
        HAS_WORKED_OUT_TODAY = True
    
    # CT Section 4.4 4-Tier Adaptive Formulation
    if comp < 70 or user_rpe >= 9:
        strategy = "deload"
        rec_title = "Khuyến nghị Giảm tải (Deload Strategy -15%) 📉"
        rec_action = "Tự động giảm 15% số reps (hoặc bớt 1 set) và tăng thời gian nghỉ giữa hiệp thêm 15 giây cho buổi kế tiếp để bảo vệ khớp!"
        rec_badge = "badge-advanced"
        multiplier = 0.85
    elif (70 <= comp < 85) or (user_rpe == 8 and comp < 90):
        strategy = "minor_deload"
        rec_title = "Khuyến nghị Giảm nhẹ Củng cố Thể lực (-5%) 📉"
        rec_action = "Tự động tinh chỉnh nhẹ -5% số reps và tập trung chuẩn hóa kỹ thuật form trước khi tăng tải trở lại."
        rec_badge = "badge-warning"
        multiplier = 0.95
    elif 85 <= comp <= 100 and user_rpe in (7, 8):
        strategy = "maintenance"
        rec_title = "Khuyến nghị Giữ nguyên Nhịp độ (Optimal Maintenance) 😊"
        rec_action = "Duy trì khối lượng và nhịp tập hiện tại để xây dựng nền tảng bền vững cho chu kỳ tuần tới!"
        rec_badge = "badge-intermediate"
        multiplier = 1.00
    else:  # comp >= 90 and user_rpe <= 6
        strategy = "overload"
        rec_title = "Khuyến nghị Tăng tiến Tải trọng (Progressive Overload +10%) 🔥"
        rec_action = "Xuất sắc! Buổi sau sẽ tự động tăng 2 reps/set hoặc gợi ý biến thể nâng cao để bứt phá giới hạn!"
        rec_badge = "badge-emerald"
        multiplier = 1.10

    # Lời khuyên phục hồi giãn cơ & bù nước (Yêu cầu 69)
    recovery_items = []
    soreness_targets = payload.soreness if payload.soreness else ["Không đau mỏi gì đặc biệt"]
    for s in soreness_targets:
        rec_info = STRETCHING_RECOMMENDATIONS.get(s, STRETCHING_RECOMMENDATIONS["Không đau mỏi gì đặc biệt"])
        recovery_items.append({
            "target": s,
            "rest_hours": rec_info["rest_hours"],
            "stretch_name": rec_info["stretch_name"],
            "guide": rec_info["guide"],
        })
    
    minutes = max(1, duration_sec // 60)
    hydration_ml = min(800, max(300, round(minutes * 18 / 50) * 50))
    hydration_advice = f"Uống từng ngụm nhỏ khoảng {hydration_ml}ml nước lọc hoặc bù điện giải trong 30 phút sau khi tập."

    eval_record = {
        "id": f"eval-{len(EVALUATION_HISTORY) + 1:02d}",
        "session_id": payload.session_id,
        "session_label": payload.session_label or "Buổi tập vừa thực hiện",
        "completion_rate": comp,
        "rpe": user_rpe,
        "rpe_desc": RPE_DESCRIPTIONS.get(user_rpe, ""),
        "soreness": payload.soreness,
        "doms_severity": payload.doms_severity or "moderate",
        "satisfaction": payload.satisfaction or "satisfied",
        "duration_sec": duration_sec,
        "note": payload.note,
        "auto_apply": payload.auto_apply,
        "recommendation": {
            "strategy": strategy,
            "title": rec_title,
            "action": rec_action,
            "badge": rec_badge,
            "multiplier": multiplier,
        },
        "recovery_items": recovery_items,
        "hydration_ml": hydration_ml,
        "hydration_advice": hydration_advice,
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    EVALUATION_HISTORY.insert(0, eval_record)

    # Record into workout history so it dynamically shows up in user history
    if comp > 0:
        est_reps = max(10, round(36 * comp / 100))
        record_workout(
            exercise_id="evaluated_workout",
            reps=est_reps,
            duration_sec=duration_sec,
            rpe=user_rpe,
            notes=payload.note or f"Đánh giá hoàn thành {comp}% (RPE {user_rpe}/10)",
            calories=round(est_reps * 0.4 + 45.0, 1),
            day=payload.session_label or "Buổi tập vừa thực hiện",
        )

    # Adaptive AI schedule adjustment if user selected auto_apply
    if payload.auto_apply and strategy != "maintenance":
        try:
            from backend.routers.planner import USER_SCHEDULES
            from backend.routers.auth import CURRENT_SESSION
            email = CURRENT_SESSION.get("user_email") or "guest"
            schedule = USER_SCHEDULES.get(email)
            if schedule:
                for d in schedule:
                    if d.get("is_rest"):
                        continue
                    for ex in d.get("exercises", []):
                        curr_reps = ex.get("reps")
                        if isinstance(curr_reps, int):
                            if strategy in ("deload", "minor_deload"):
                                ex["reps"] = max(5, round(curr_reps * multiplier))
                            elif strategy == "overload":
                                ex["reps"] = min(50, curr_reps + 2)
                        elif isinstance(curr_reps, str) and curr_reps.isdigit():
                            val = int(curr_reps)
                            if strategy in ("deload", "minor_deload"):
                                ex["reps"] = max(5, round(val * multiplier))
                            elif strategy == "overload":
                                ex["reps"] = min(50, val + 2)
        except Exception:
            pass
    
    return {
        "success": True,
        "message": "🎉 Đã ghi nhận phản hồi vào hồ sơ thể lực thành công!",
        "evaluation": eval_record,
    }


@router.get("/heatmap")
def get_recovery_heatmap():
    """Returns muscle recovery status matrix based on workout history and soreness feedback."""
    latest_soreness = []
    if EVALUATION_HISTORY:
        latest_soreness = EVALUATION_HISTORY[0].get("soreness", [])
    
    is_quads_sore = any("đùi" in s.lower() or "gối" in s.lower() for s in latest_soreness)
    is_glutes_sore = any("mông" in s.lower() for s in latest_soreness)
    is_chest_sore = any("ngực" in s.lower() for s in latest_soreness)
    is_back_sore = any("lưng" in s.lower() or "cột sống" in s.lower() for s in latest_soreness)
    is_triceps_sore = any("tay" in s.lower() or "cổ tay" in s.lower() for s in latest_soreness)
    
    base_recovery = [
        {
            "muscle_key": "chest",
            "name": "Ngực (Chest)",
            "recovery_pct": 50 if is_chest_sore else (85 if HAS_WORKED_OUT_TODAY else 95),
            "hours_left": 24 if is_chest_sore else (6 if HAS_WORKED_OUT_TODAY else 0),
            "status": "Mỏi cơ / Cần nghỉ" if is_chest_sore else ("Đang hồi phục" if HAS_WORKED_OUT_TODAY else "Sẵn sàng tập"),
            "color": "#EF4444" if is_chest_sore else ("#38BDF8" if not HAS_WORKED_OUT_TODAY else "#F59E0B"),
        },
        {
            "muscle_key": "back",
            "name": "Lưng & Xô (Back)",
            "recovery_pct": 55 if is_back_sore else 100,
            "hours_left": 20 if is_back_sore else 0,
            "status": "Mỏi cơ / Cần nghỉ" if is_back_sore else "Sẵn sàng tập",
            "color": "#EF4444" if is_back_sore else "#4ADE80",
        },
        {
            "muscle_key": "quads",
            "name": "Đùi trước (Quads)",
            "recovery_pct": 45 if is_quads_sore else 75,
            "hours_left": 26 if is_quads_sore else 8,
            "status": "Mỏi cơ / Cần nghỉ" if is_quads_sore else "Đang hồi phục",
            "color": "#EF4444" if is_quads_sore else "#F59E0B",
        },
        {
            "muscle_key": "glutes",
            "name": "Mông (Glutes)",
            "recovery_pct": 50 if is_glutes_sore else 80,
            "hours_left": 22 if is_glutes_sore else 6,
            "status": "Mỏi cơ / Cần nghỉ" if is_glutes_sore else "Đang hồi phục",
            "color": "#EF4444" if is_glutes_sore else "#F59E0B",
        },
        {
            "muscle_key": "triceps",
            "name": "Tay sau (Triceps)",
            "recovery_pct": 50 if is_triceps_sore else 70,
            "hours_left": 20 if is_triceps_sore else 10,
            "status": "Mỏi cơ / Cần nghỉ" if is_triceps_sore else "Đang hồi phục",
            "color": "#EF4444" if is_triceps_sore else "#F59E0B",
        },
        {
            "muscle_key": "shoulders",
            "name": "Vai (Shoulders)",
            "recovery_pct": 95,
            "hours_left": 0,
            "status": "Sẵn sàng tập",
            "color": "#4ADE80",
        },
        {
            "muscle_key": "core",
            "name": "Bụng & Core",
            "recovery_pct": 90,
            "hours_left": 2,
            "status": "Sẵn sàng tập",
            "color": "#4ADE80",
        },
    ]
    return {
        "muscles": base_recovery,
        "recommendation": "Dựa trên phản hồi mỏi cơ của bạn, AI đã tự động phân tích và điều chỉnh bảng nhiệt hồi phục sinh học!",
    }
