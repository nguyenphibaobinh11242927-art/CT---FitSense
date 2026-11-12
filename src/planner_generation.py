"""Connect SCRUM-12 plan validation to FitSense profiles and weekly schedules."""

from collections.abc import Callable

from src.exercise_library import EQUIPMENT, MUSCLES
from src.profile import NO_RESTRICTIONS
from src.workout_planner import GOALS, Exercise, WorkoutPlanError, generate_workout_plan


DEFAULT_DAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
_PROFILE_GOALS = {
    "Sức bền": "endurance",
    "Dẻo dai": "flexibility",
    "Đốt mỡ": "fat_loss",
    "Giảm mỡ": "fat_loss",
}
_PROFILE_RESTRICTIONS = {"Khớp gối yếu": "knee", "Cổ tay đau": "wrist"}
_PROFILE_EQUIPMENT = {
    "Thảm yoga/thể dục": "mat",
    "Dây kháng lực (Resistance Band)": "band",
    "Ghế tựa / Điểm tựa cao": "chair",
}


def profile_goal_id(label: str) -> str | None:
    return _PROFILE_GOALS.get(label.split(" & ", 1)[0], label if label in GOALS else None)


def generate_ai_schedule(
    profile: dict, goal: str, library: list[dict], complete: Callable[[str], str],
) -> list[dict]:
    injuries = set()
    for restriction in profile.get("restrictions", []):
        if restriction == NO_RESTRICTIONS:
            continue
        injury = _PROFILE_RESTRICTIONS.get(restriction.split(" (", 1)[0])
        if injury is None:
            raise WorkoutPlanError("Thư viện AI chưa lọc được mọi hạn chế vận động trong hồ sơ của bạn.")
        injuries.add(injury)

    equipment = [_PROFILE_EQUIPMENT[item] for item in profile.get("equipment", []) if item in _PROFILE_EQUIPMENT]
    by_id = {item["id"]: item for item in library}
    plan = generate_workout_plan(
        goal=goal,
        experience_level=profile.get("fitness_level", "").partition(" ")[0].lower(),
        injury_regions=injuries,
        available_equipment=equipment,
        catalog={
            exercise_id: Exercise(item["name"], item["avoid_if"], item["equipment"])
            for exercise_id, item in by_id.items()
        },
        complete=complete,
    )

    schedule = []
    for day in plan["days"]:
        exercises = []
        for prescription in day["exercises"]:
            exercise = _schedule_exercise(prescription, by_id)
            alternative = prescription["alternative"]
            exercise["ai_alternative"] = _schedule_exercise(alternative, by_id) if alternative else None
            exercises.append(exercise)
        schedule.append({
            "day": DEFAULT_DAYS[day["day"] - 1],
            "focus": GOALS[goal] if exercises else "Nghỉ ngơi phục hồi",
            "is_rest": not exercises,
            "ai_reason": "Giáo án AI dựa trên mục tiêu và các giới hạn tập luyện trong hồ sơ.",
            "exercises": exercises,
        })
    return schedule


def _schedule_exercise(prescription: dict, library: dict[str, dict]) -> dict:
    item = library[prescription["exercise_id"]]
    return {
        "name": item["name"],
        "sets": prescription["sets"],
        "reps": prescription["reps"],
        "hold_seconds": prescription["hold_seconds"],
        "rest_sec": prescription["rest_seconds"],
        "primary_muscle": ", ".join(MUSCLES[muscle] for muscle in item["primary_muscles"]),
        "secondary_muscle": ", ".join(MUSCLES[muscle] for muscle in item["secondary_muscles"]) or "Không",
        "equipment": ", ".join(EQUIPMENT[equipment] for equipment in item["equipment"]) or "Bodyweight",
        "difficulty": item["difficulty"],
        "form_tip": item["steps"][0],
    }
