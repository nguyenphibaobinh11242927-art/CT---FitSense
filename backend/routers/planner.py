"""Smart Weekly Planner API Router."""

from datetime import date, datetime
from typing import Any
from copy import deepcopy
from fastapi import APIRouter, HTTPException

from backend.schemas import (
    DayUpdateRequest,
    ExerciseSwapRequest,
    PlanGenerationRequest,
    PlanUploadRequest,
    StartDayWorkoutRequest,
)
from backend.routers.auth import CURRENT_SESSION
from backend.routers.exercises import get_catalog
from src.profile import load_profile
from src.planner_generation import DEFAULT_DAYS, generate_ai_schedule, planner_profile_filters, profile_goal_id
from src.school_ai import FitAIServiceError, complete_with_school_ai
from src.adaptive_weekly_plan import DAYS, recovery_warnings, start_actual_workout
from src.exercise_library import compatible_replacements, resolve_exercise
from src.planner_view import parse_uploaded_plan
from src.workout_planner import WorkoutPlanError

router = APIRouter(prefix="/api/planner", tags=["Planner"])

DEFAULT_WEEKLY_SCHEDULE = [
    {
        "day": "Thứ 2",
        "focus": "Thân trên: Ngực & Tay sau (Push Focus)",
        "is_rest": False,
        "is_completed": False,
        "ai_reason": "Tập trung nhóm cơ đẩy; kích thích sợi cơ nhanh và xây dựng sức mạnh cơ bản.",
        "exercises": [
            {
                "id": "push_up",
                "name": "Standard Push-up (Hít đất chuẩn)",
                "sets": 3,
                "reps": "12",
                "rest_sec": 60,
                "primary_muscle": "Ngực (Chest)",
                "secondary_muscle": "Tay sau, Vai",
                "equipment": "Bodyweight",
                "difficulty": "Intermediate",
                "substitute": "Knee Push-up",
            },
            {
                "id": "bench_dip",
                "name": "Dips trên ghế (Bench Dips)",
                "sets": 3,
                "reps": "15",
                "rest_sec": 45,
                "primary_muscle": "Tay sau (Triceps)",
                "secondary_muscle": "Ngực dưới",
                "equipment": "Ghế / Giường",
                "difficulty": "Beginner",
                "substitute": "Diamond Push-up",
            },
            {
                "id": "plank",
                "name": "Plank Tĩnh (Core Stability)",
                "sets": 3,
                "reps": "45s",
                "rest_sec": 45,
                "primary_muscle": "Bụng & Core",
                "secondary_muscle": "Lưng dưới",
                "equipment": "Thảm",
                "difficulty": "Beginner",
                "substitute": "Dead Bug",
            },
        ],
    },
    {
        "day": "Thứ 3",
        "focus": "Thân dưới & Mông (Lower Body)",
        "is_rest": False,
        "is_completed": False,
        "ai_reason": "Kiểm soát góc gối tối ưu để phát triển cơ đùi trước và cơ mông săn chắc.",
        "exercises": [
            {
                "id": "squat",
                "name": "Squat Thể dục (Bodyweight Squat)",
                "sets": 4,
                "reps": "15",
                "rest_sec": 60,
                "primary_muscle": "Đùi trước (Quads)",
                "secondary_muscle": "Mông",
                "equipment": "Bodyweight",
                "difficulty": "Beginner",
                "substitute": "Wall Sit (Ngồi tựa tường)",
            },
            {
                "id": "glute_bridge",
                "name": "Glute Bridge (Nâng mông trên thảm)",
                "sets": 3,
                "reps": "20",
                "rest_sec": 45,
                "primary_muscle": "Mông (Glutes)",
                "secondary_muscle": "Đùi sau",
                "equipment": "Thảm",
                "difficulty": "Beginner",
                "substitute": "Single Leg Bridge",
            },
            {
                "id": "calf_raise",
                "name": "Calf Raises (Nhón bắp chân)",
                "sets": 3,
                "reps": "25",
                "rest_sec": 30,
                "primary_muscle": "Bắp chân",
                "secondary_muscle": "Cổ chân",
                "equipment": "Bodyweight",
                "difficulty": "Beginner",
                "substitute": "Seated Calf Raise",
            },
        ],
    },
    {
        "day": "Thứ 4",
        "focus": "Nghỉ ngơi phục hồi cơ bắp (Rest Day)",
        "is_rest": True,
        "is_completed": False,
        "ai_reason": "Chu kỳ 48h để cơ bắp tổng hợp protein và tái tạo glycogen năng lượng.",
        "exercises": [],
    },
    {
        "day": "Thứ 5",
        "focus": "Thân trên: Lưng xô & Tay trước (Pull Focus)",
        "is_rest": False,
        "is_completed": False,
        "ai_reason": "Cân bằng cơ đối kháng thân trên, cải thiện tư thế đứng thẳng chống gù lưng.",
        "exercises": [
            {
                "id": "inverted_row",
                "name": "Inverted Rows (Hít xà nghiêng)",
                "sets": 3,
                "reps": "10",
                "rest_sec": 60,
                "primary_muscle": "Lưng & Xô",
                "secondary_muscle": "Tay trước",
                "equipment": "Xà đơn / Khăn",
                "difficulty": "Intermediate",
                "substitute": "Band Pull-Apart",
            },
            {
                "id": "lat_band_pulldown",
                "name": "Dây kháng lực kéo xô (Lat Band Pulldown)",
                "sets": 3,
                "reps": "15",
                "rest_sec": 45,
                "primary_muscle": "Lưng & Xô",
                "secondary_muscle": "Vai sau",
                "equipment": "Dây kháng lực",
                "difficulty": "Beginner",
                "substitute": "Superman Hold",
            },
        ],
    },
    {
        "day": "Thứ 6",
        "focus": "Toàn thân & Sức bền tim mạch (Fullbody Endurance)",
        "is_rest": False,
        "is_completed": False,
        "ai_reason": "Đốt mỡ chuyển hóa và tăng cường dung tích thông khí của phổi.",
        "exercises": [
            {
                "id": "jumping_jack",
                "name": "Jumping Jacks (Nhảy dang tay chân nhẹ)",
                "sets": 3,
                "reps": "40s",
                "rest_sec": 45,
                "primary_muscle": "Toàn thân & Tim mạch",
                "secondary_muscle": "Bắp chân",
                "equipment": "Bodyweight",
                "difficulty": "Beginner",
                "substitute": "Step Jacks",
            },
            {
                "id": "mountain_climber",
                "name": "Mountain Climbers (Leo núi trên thảm)",
                "sets": 3,
                "reps": "20",
                "rest_sec": 45,
                "primary_muscle": "Bụng & Core",
                "secondary_muscle": "Vai",
                "equipment": "Thảm",
                "difficulty": "Intermediate",
                "substitute": "Plank Shoulder Tap",
            },
        ],
    },
    {
        "day": "Thứ 7",
        "focus": "Nghỉ ngơi phục hồi (Rest Day)",
        "is_rest": True,
        "is_completed": False,
        "ai_reason": "Thư giãn hệ thống thần kinh và dây chằng.",
        "exercises": [],
    },
    {
        "day": "Chủ Nhật",
        "focus": "Giãn cơ & Khớp dẻo dai (Active Recovery)",
        "is_rest": True,
        "is_completed": False,
        "ai_reason": "Giải phóng căng cứng cơ bắp chuẩn bị năng lượng cho tuần mới.",
        "exercises": [],
    },
]

# Per-user active weekly schedule storage
USER_SCHEDULES: dict[str, list[dict[str, Any]]] = {}


def get_user_schedule(email: str) -> list[dict[str, Any]]:
    if email not in USER_SCHEDULES:
        USER_SCHEDULES[email] = deepcopy(DEFAULT_WEEKLY_SCHEDULE)
    return USER_SCHEDULES[email]


def _catalog_exercise(exercise: dict, catalog: list[dict]) -> dict | None:
    identified = next((entry for entry in catalog if entry["id"] == exercise.get("id")), None)
    return identified or resolve_exercise(exercise.get("name", ""), catalog)


def _add_catalog_ids(day: dict, catalog: list[dict]) -> None:
    for exercise in day["exercises"]:
        entry = _catalog_exercise(exercise, catalog)
        exercise["id"] = entry["id"] if entry else None


@router.get("/week")
def get_week():
    email = CURRENT_SESSION.get("user_email") or "guest"
    schedule = deepcopy(get_user_schedule(email))
    
    today_weekday_idx = datetime.now().weekday()
    today_name = DEFAULT_DAYS[today_weekday_idx]
    
    # Calculate warnings
    warnings_by_day = {}
    catalog = get_catalog()
    for day in schedule:
        _add_catalog_ids(day, catalog)
    today_date = date.today()
    from backend.routers.progress import WORKOUT_HISTORY
    
    for day_data in schedule:
        day_name = day_data["day"]
        day_warns = recovery_warnings(day_data, today_date, WORKOUT_HISTORY, schedule)
        if day_warns:
            warnings_by_day[day_name] = day_warns

    return {
        "schedule": schedule,
        "today_name": today_name,
        "today_weekday_index": today_weekday_idx,
        "warnings": warnings_by_day,
    }


@router.post("/generate")
def generate_schedule(payload: PlanGenerationRequest):
    email = CURRENT_SESSION.get("user_email") or "guest"
    profile = (load_profile(email) if email != "guest" else None) or {
        "goal": "Sức bền",
        "fitness_level": "Beginner (Người mới bắt đầu)",
        "restrictions": ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
        "equipment": ["Không có dụng cụ (Chỉ tập Bodyweight)"],
    }
    
    if not payload.use_ai:
        raise HTTPException(status_code=400, detail="Chọn Tạo giáo án AI hoặc dùng nút đặt lại lịch mẫu.")
    goal_label = payload.goal or profile.get("goal", "Sức bền")
    goal_key = profile_goal_id(goal_label)
    if goal_key is None:
        raise HTTPException(status_code=422, detail="Hãy chọn mục tiêu Sức bền, Dẻo dai hoặc Đốt mỡ.")
    catalog = get_catalog()
    
    try:
        new_plan = generate_ai_schedule(
            profile=profile,
            goal=goal_key,
            library=catalog,
            complete=complete_with_school_ai,
        )
    except FitAIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except WorkoutPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    USER_SCHEDULES[email] = new_plan
    return {
        "success": True,
        "message": "AI đã tạo thành công giáo án tuần cá nhân hóa!",
        "schedule": new_plan,
    }


@router.post("/swap")
def swap_exercise(payload: ExerciseSwapRequest):
    email = CURRENT_SESSION.get("user_email") or "guest"
    schedule = get_user_schedule(email)
    catalog = get_catalog()
    
    target_day = next((d for d in schedule if d["day"].lower() == payload.day.lower()), None)
    if not target_day:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngày trong tuần.")
    
    new_ex = next((ex for ex in catalog if ex["id"] == payload.new_exercise_id), None)
    if not new_ex:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập mới trong thư viện.")
    
    exercises = target_day.get("exercises", [])
    index = payload.exercise_index
    candidates = range(len(exercises)) if index is None else [index]
    match = next((i for i in candidates if i < len(exercises) and
                  (_catalog_exercise(exercises[i], catalog) or {}).get("id") == payload.current_exercise_id), None)
    if match is None:
        raise HTTPException(status_code=400, detail="Không tìm thấy bài tập cần đổi trong ngày này.")

    profile = (load_profile(email) if email != "guest" else None) or {}
    try:
        equipment, injuries = planner_profile_filters(profile)
    except WorkoutPlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if (new_ex["id"] == payload.current_exercise_id or injuries.intersection(new_ex["avoid_if"])
            or not equipment.issuperset(new_ex["equipment"])):
        raise HTTPException(status_code=422, detail="Bài thay thế không phù hợp với giới hạn hoặc dụng cụ hiện có.")

    current = exercises[match]
    prescribed = current.get("ai_alternative")
    if isinstance(prescribed, dict) and (_catalog_exercise(prescribed, catalog) or {}).get("id") == new_ex["id"]:
        previous = {key: value for key, value in current.items() if key != "ai_alternative"}
        previous["id"] = payload.current_exercise_id
        exercises[match] = {**prescribed, "id": new_ex["id"], "ai_alternative": previous}
    else:
        exercises[match] = {
            "id": new_ex["id"],
            "name": f"{new_ex['name']} ({new_ex['name_en']})",
            "sets": current.get("sets", 3),
            "reps": current.get("reps", 12),
            "rest_sec": current.get("rest_sec", 60),
            "primary_muscle": ", ".join(new_ex["primary_muscles"]),
            "secondary_muscle": ", ".join(new_ex["secondary_muscles"]),
            "equipment": ", ".join(new_ex["equipment"]) or "Bodyweight",
            "difficulty": new_ex["difficulty"],
            "substitute": current.get("name"),
        }

    return {
        "success": True,
        "message": f"Đã đổi sang bài {new_ex['name']} thành công!",
        "day": target_day,
    }


@router.post("/reset")
def reset_schedule():
    email = CURRENT_SESSION.get("user_email") or "guest"
    USER_SCHEDULES[email] = deepcopy(DEFAULT_WEEKLY_SCHEDULE)
    return {
        "success": True,
        "message": "Đã đặt lại lịch tập tuần mặc định.",
        "schedule": USER_SCHEDULES[email],
    }


@router.get("/template")
def get_sample_template():
    """Returns sample weekly workout plan template for download."""
    sample = deepcopy(DEFAULT_WEEKLY_SCHEDULE)
    return {
        "filename": "fitsense_plan_template.json",
        "template": sample,
    }


@router.post("/upload")
def upload_custom_plan(payload: PlanUploadRequest):
    """Uploads and validates custom plan file (.json or .csv)."""
    email = CURRENT_SESSION.get("user_email") or "guest"
    try:
        parsed = parse_uploaded_plan(payload.content.encode("utf-8"), payload.filename)
        if not parsed:
            raise ValueError("Không tìm thấy dữ liệu giáo án trong file.")
        USER_SCHEDULES[email] = parsed
        return {
            "success": True,
            "message": f"Đã nạp giáo án từ file {payload.filename} thành công!",
            "schedule": parsed,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Lỗi đọc file giáo án: {str(exc)}")


@router.post("/update-day")
def update_single_day(payload: DayUpdateRequest):
    """Updates focus, rest status, and exercises for a specific day."""
    email = CURRENT_SESSION.get("user_email") or "guest"
    schedule = get_user_schedule(email)
    
    target_idx = None
    for idx, d in enumerate(schedule):
        if d["day"].lower() == payload.day.lower():
            target_idx = idx
            break
            
    if target_idx is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy ngày {payload.day}")

    # Ensure all exercises have a valid id, auto-matching catalog if needed
    catalog = get_catalog()
    cleaned_exercises = []
    for ex in payload.exercises:
        ex_id = ex.get("id")
        ex_name = (ex.get("name") or "").strip().lower()
        
        # If ID is missing or marked custom, try fuzzy/name matching against catalog
        if not ex_id or ex_id == "custom":
            matched = next(
                (c for c in catalog if 
                 c["name"].lower() == ex_name or 
                 c.get("name_en", "").lower() == ex_name or 
                 c["id"].lower() == ex_name or
                 c["name"].lower() in ex_name or
                 (len(ex_name) > 3 and ex_name in c["name"].lower())),
                None
            )
            if matched:
                ex["id"] = matched["id"]
                if not ex.get("primary_muscle"):
                    ex["primary_muscle"] = matched.get("primary_muscles", ["Toàn thân"])[0]
            else:
                ex["id"] = "custom"
        cleaned_exercises.append(ex)
        
    schedule[target_idx] = {
        "day": payload.day,
        "focus": payload.focus or ("Nghỉ ngơi phục hồi" if payload.is_rest else "Buổi tập tùy chỉnh"),
        "is_rest": payload.is_rest,
        "ai_reason": "Chỉnh sửa thủ công bởi người dùng.",
        "exercises": [] if payload.is_rest else cleaned_exercises,
    }
    
    return {
        "success": True,
        "message": f"Đã lưu chỉnh sửa cho {payload.day}!",
        "day_data": schedule[target_idx],
        "schedule": schedule,
    }


@router.get("/check-recovery/{day}")
def check_day_recovery(day: str):
    """Checks recovery warnings for a specific day."""
    email = CURRENT_SESSION.get("user_email") or "guest"
    schedule = get_user_schedule(email)
    from backend.routers.progress import WORKOUT_HISTORY
    
    day_data = next((d for d in schedule if d["day"].lower() == day.lower()), None)
    if not day_data:
        return {"has_warnings": False, "warnings": []}
        
    warns = recovery_warnings(day_data, date.today(), WORKOUT_HISTORY, schedule)
    return {
        "has_warnings": len(warns) > 0,
        "warnings": warns,
        "day": day_data["day"],
        "focus": day_data.get("focus", ""),
    }


def realign_schedule_with_profile(email: str, profile_data: dict) -> list[str]:
    """Realigns user's active weekly plan by replacing any exercises that conflict with new physical limitations."""
    restrictions = profile_data.get("restrictions", [])
    limits: set[str] = set()
    for r in restrictions:
        rl = r.lower()
        if "gối" in rl or "knee" in rl:
            limits.add("knee")
        if "cổ tay" in rl or "tay" in rl or "wrist" in rl:
            limits.add("wrist")
        if "lưng" in rl or "cột sống" in rl or "back" in rl:
            limits.add("lower_back")
        if "vai" in rl or "shoulder" in rl:
            limits.add("shoulder")
            
    if not limits:
        return []
        
    schedule = get_user_schedule(email)
    catalog = get_catalog()
    changes: list[str] = []
    
    for day in schedule:
        if day.get("is_rest") or not day.get("exercises"):
            continue
        new_exercises = []
        for ex in day.get("exercises", []):
            cat_ex = resolve_exercise(ex.get("id") or ex.get("name", ""), catalog)
            avoid_tags = set(cat_ex.get("avoid_if", [])) if cat_ex else set()
            conflicts = avoid_tags & limits
            if conflicts:
                reps = compatible_replacements(cat_ex or ex, catalog, limitations=limits)
                if reps:
                    rep = reps[0]
                    old_name = ex.get("name", ex.get("id"))
                    rep_name = rep.get("name") or rep.get("name_vi") or rep.get("id")
                    new_ex = deepcopy(ex)
                    new_ex["id"] = rep.get("id")
                    new_ex["name"] = rep_name
                    if rep.get("primary_muscles"):
                        pm = rep["primary_muscles"]
                        new_ex["primary_muscle"] = pm[0] if isinstance(pm, list) else pm
                    if rep.get("secondary_muscles"):
                        sm = rep["secondary_muscles"]
                        new_ex["secondary_muscle"] = ", ".join(sm) if isinstance(sm, list) else sm
                    if rep.get("equipment"):
                        eq = rep["equipment"]
                        new_ex["equipment"] = eq[0] if isinstance(eq, list) else eq
                    conflict_desc = "khớp gối" if "knee" in conflicts else ("cổ tay" if "wrist" in conflicts else ", ".join(conflicts))
                    new_ex["substitute"] = f"Thay thế cho {old_name} do hạn chế {conflict_desc}"
                    new_exercises.append(new_ex)
                    changes.append(f"{day['day']}: '{old_name}' ➔ '{rep_name}' (Bảo vệ {conflict_desc})")
                else:
                    new_exercises.append(ex)
            else:
                new_exercises.append(ex)
        day["exercises"] = new_exercises
        
    if changes:
        USER_SCHEDULES[email] = schedule
        if not CURRENT_SESSION.get("user_email") or CURRENT_SESSION.get("user_email") == "guest":
            USER_SCHEDULES["guest"] = schedule
    return changes


@router.post("/start-day-workout")
def start_day_workout(payload: StartDayWorkoutRequest):
    """Starts a workout day, copying it to today and AI-rescheduling remaining days if out-of-order."""
    email = CURRENT_SESSION.get("user_email") or "guest"
    schedule = get_user_schedule(email)
    today = date.today()
    today_name = DAYS[today.weekday()]
    
    source = next((d for d in schedule if d["day"].lower() == payload.source_day.lower()), None)
    if not source:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy buổi tập {payload.source_day}")
    if source.get("is_rest") or not source.get("exercises"):
        raise HTTPException(status_code=400, detail=f"Ngày {payload.source_day} là ngày nghỉ hoặc chưa có bài tập.")
        
    try:
        updated_schedule, active_workout, method = start_actual_workout(
            schedule, source["day"], today, use_ai=payload.use_ai
        )
        _add_catalog_ids(active_workout, get_catalog())
        USER_SCHEDULES[email] = updated_schedule
        is_rearranged = (source["day"] != today_name)
        message = (
            f"Đã bắt đầu tập giáo án {source['day']} thay cho hôm nay ({today_name})! AI đã tự động sắp xếp lại các ngày còn lại trong tuần ({method})."
            if is_rearranged
            else f"Đã kích hoạt buổi tập hôm nay ({today_name}) thành công!"
        )
        return {
            "success": True,
            "rearranged": is_rearranged,
            "replan_method": method,
            "message": message,
            "schedule": updated_schedule,
            "active_workout": active_workout,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Lỗi khởi động buổi tập: {str(exc)}")


