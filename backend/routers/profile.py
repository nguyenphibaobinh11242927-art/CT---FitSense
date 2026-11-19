"""Profile and Biometrics API Router."""

from fastapi import APIRouter, HTTPException
from backend.schemas import BMICalculationRequest, BMICalculationResponse, ProfileSchema
from backend.routers.auth import CURRENT_SESSION
from backend.routers.planner import realign_schedule_with_profile
from src.profile import load_profile, save_profile, validate_profile

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.post("/bmi", response_model=BMICalculationResponse)
def calculate_bmi(payload: BMICalculationRequest):
    height_m = payload.height_cm / 100.0
    bmi = payload.weight_kg / (height_m * height_m)
    
    # Healthy weight range (BMI 18.5 - 24.9)
    min_healthy = 18.5 * (height_m * height_m)
    max_healthy = 24.9 * (height_m * height_m)
    
    if bmi < 18.5:
        category = "Gầy / Cần tăng cơ"
        desc = "Chỉ số BMI dưới mức tiêu chuẩn. Khuyến nghị tập các bài Calisthenics xây dựng khối cơ và bổ sung dinh dưỡng giàu protein."
    elif bmi < 25.0:
        category = "Cân đối lý tưởng"
        desc = "Chỉ số BMI lý tưởng! Hãy duy trì phong độ với lịch rèn luyện Calisthenics toàn diện."
    elif bmi < 30.0:
        category = "Thừa cân / Cần đốt mỡ"
        desc = "Chỉ số BMI hơi cao. Khuyến nghị tập trung vào các bài Calisthenics nhịp độ cao (HIIT/Circuit) để tiêu hao năng lượng."
    else:
        category = "Béo phì / Cần kiểm soát"
        desc = "Khuyến nghị ưu tiên các bài tập an toàn cho khớp (tránh nhảy cao) và chế độ ăn thâm hụt calo lành mạnh."

    return BMICalculationResponse(
        bmi=round(bmi, 1),
        category=category,
        healthy_weight_min=round(min_healthy, 1),
        healthy_weight_max=round(max_healthy, 1),
        description=desc,
    )


@router.get("")
def get_profile():
    email = CURRENT_SESSION.get("user_email")
    if not email:
        return None
    profile = load_profile(email)
    if not profile:
        profile = {
            "name": "FitSense Athlete",
            "email": email,
            "age": 22,
            "gender": "Nam",
            "height_cm": 170.0,
            "weight_kg": 65.0,
            "days_per_week": 4,
            "session_duration_minutes": 45,
            "goal": "Tăng cơ & Sức mạnh",
            "fitness_level": "Beginner (Người mới bắt đầu)",
            "environment": "Tại nhà (Home Workout)",
            "restrictions": ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
            "equipment": ["Không có dụng cụ (Chỉ tập Bodyweight)"],
        }
    return profile


@router.put("")
@router.post("")
def update_profile(payload: ProfileSchema):
    profile_data = payload.model_dump()
    errors = validate_profile(profile_data)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))
    
    email = CURRENT_SESSION.get("user_email") or profile_data.get("email") or "guest"
    try:
        save_profile(email, profile_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể lưu hồ sơ: {str(exc)}")
    
    # Automatically check and realign weekly plan with any new injury / physical limitations
    schedule_changes = realign_schedule_with_profile(email, profile_data)
    message = "Cập nhật hồ sơ thể chất thành công!"
    if schedule_changes:
        message += f" AI đã tự động cập nhật {len(schedule_changes)} bài tập trong kế hoạch tuần để bảo vệ bạn khỏi chấn thương."

    return {
        "success": True,
        "message": message,
        "profile": profile_data,
        "schedule_updated": bool(schedule_changes),
        "schedule_changes": schedule_changes,
    }
