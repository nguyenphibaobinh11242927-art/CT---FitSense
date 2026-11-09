"""Generate a validated Calisthenics/Bodyweight plan from a reviewed catalog."""

import json
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


GOALS = {"endurance": "Sức bền", "flexibility": "Dẻo dai", "fat_loss": "Giảm mỡ"}
EXPERIENCE_LEVELS = frozenset({"beginner", "intermediate", "advanced"})
INJURY_REGIONS = frozenset({"wrist", "knee"})


@dataclass(frozen=True)
class Exercise:
    """Catalog entry with explicit, reviewed wrist/knee exclusion tags.

    Use an empty collection only for an entry reviewed for both regions.
    Equipment uses the same IDs as the caller's profile.
    """

    name: str
    contraindications: Collection[str]
    equipment: Collection[str] = ()


class WorkoutPlanError(ValueError):
    """The profile, catalog or model response cannot produce a valid plan."""


_PRESCRIPTION_FIELDS = {
    "exercise_id": {"type": "string", "minLength": 1},
    "sets": {"type": "integer", "minimum": 1},
    "reps": {"type": "integer", "minimum": 1},
    "hold_seconds": {"type": "integer", "minimum": 0},
    "rest_seconds": {"type": "integer", "minimum": 0},
}

WEEKLY_PLAN_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["goal", "days"],
    "additionalProperties": False,
    "properties": {
        "goal": {"enum": list(GOALS)},
        "days": {
            "type": "array",
            "minItems": 7,
            "maxItems": 7,
            "items": {"$ref": "#/$defs/day"},
        },
    },
    "$defs": {
        "day": {
            "type": "object",
            "required": ["day", "exercises"],
            "additionalProperties": False,
            "properties": {
                "day": {"type": "integer", "minimum": 1, "maximum": 7},
                "exercises": {"type": "array", "items": {"$ref": "#/$defs/exercise"}},
            },
        },
        "prescription": {
            "type": "object",
            "required": list(_PRESCRIPTION_FIELDS),
            "additionalProperties": False,
            "properties": _PRESCRIPTION_FIELDS,
        },
        "exercise": {
            "type": "object",
            "required": [*_PRESCRIPTION_FIELDS, "alternative"],
            "additionalProperties": False,
            "properties": {
                **_PRESCRIPTION_FIELDS,
                "alternative": {
                    "anyOf": [{"type": "null"}, {"$ref": "#/$defs/prescription"}],
                },
            },
        },
    },
}
_PLAN_VALIDATOR = Draft202012Validator(WEEKLY_PLAN_SCHEMA)


def generate_workout_plan(
    *,
    goal: str,
    experience_level: str,
    injury_regions: Collection[str],
    available_equipment: Collection[str],
    catalog: Mapping[str, Exercise],
    complete: Callable[[str], str],
) -> dict[str, Any]:
    """Pass a prompt to ``complete`` and return a JSON-serializable plan.

    Map the profile to the supported goal, level and injury IDs before calling.
    An empty injury collection represents an explicitly unrestricted profile.
    Catalog keys become ``exercise_id`` values for consumers to look up.
    """
    if goal not in GOALS or experience_level not in EXPERIENCE_LEVELS:
        raise WorkoutPlanError("Mục tiêu hoặc trình độ tập luyện chưa được hỗ trợ.")

    injuries = _read_tags(injury_regions, "vùng chấn thương")
    if not injuries <= INJURY_REGIONS:
        raise WorkoutPlanError("Có vùng chấn thương chưa được hỗ trợ.")
    equipment = _read_tags(available_equipment, "dụng cụ có sẵn")

    eligible = {}
    for exercise_id, exercise in catalog.items():
        if not isinstance(exercise_id, str) or not exercise_id.strip():
            raise WorkoutPlanError("Thư viện có mã bài tập không hợp lệ.")
        exclusions = _read_tags(exercise.contraindications, "chống chỉ định của bài tập")
        if not exclusions <= INJURY_REGIONS:
            raise WorkoutPlanError("Thư viện có mã chống chỉ định chưa được hỗ trợ.")
        required = _read_tags(exercise.equipment, "dụng cụ của bài tập")
        if exclusions.isdisjoint(injuries) and required <= equipment:
            eligible[exercise_id] = exercise.name
    if not eligible:
        raise WorkoutPlanError("Không có bài tập phù hợp với giới hạn và dụng cụ đã khai báo.")

    prompt_data = {
        "goal": goal,
        "goal_label": GOALS[goal],
        "experience_level": experience_level,
        "eligible_exercises": eligible,
        "response_schema": WEEKLY_PLAN_SCHEMA,
    }
    prompt = (
        "Lập giáo án Calisthenics/Bodyweight trong một tuần theo mục tiêu và trình độ đã cho. "
        "Chỉ trả về một object JSON theo response_schema, không dùng Markdown. "
        "Xếp ngày 1 đến 7 theo thứ tự, với ít nhất một ngày tập và dùng exercises=[] cho ngày nghỉ. "
        "Cả bài chính và bài thay thế chỉ dùng ID trong eligible_exercises. "
        "Chọn bài thay thế khác bài chính và cùng mục đích; dùng null nếu không có bài phù hợp. "
        "Dùng số nguyên cho mọi số liệu. hold_seconds là số giây giữ mỗi lần lặp (0 nếu không giữ). "
        "rest_seconds là số giây nghỉ giữa các hiệp.\n"
        + json.dumps(prompt_data, ensure_ascii=False)
    )
    return _parse_plan(complete(prompt), goal, eligible.keys())


def _read_tags(tags: Collection[str], label: str) -> set[str]:
    if (
        not isinstance(tags, Collection)
        or isinstance(tags, (str, bytes, Mapping))
        or any(not isinstance(tag, str) or not tag.strip() for tag in tags)
    ):
        raise WorkoutPlanError(f"Dữ liệu {label} phải là một danh sách mã hợp lệ.")
    return set(tags)


def _reject_non_integer(value: str) -> None:
    raise ValueError("Expected an integer JSON number")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate JSON field")
    return result


def _parse_plan(response: str, goal: str, eligible_ids: Collection[str]) -> dict[str, Any]:
    try:
        plan = json.loads(
            response,
            parse_float=_reject_non_integer,
            parse_constant=_reject_non_integer,
            object_pairs_hook=_unique_object,
        )
    except (TypeError, ValueError, RecursionError) as error:
        raise WorkoutPlanError("Phản hồi AI không phải JSON giáo án hợp lệ.") from error

    try:
        _PLAN_VALIDATOR.validate(plan)
    except ValidationError as error:
        raise WorkoutPlanError(f"Giáo án sai cấu trúc tại {error.json_path}.") from error

    if plan["goal"] != goal:
        raise WorkoutPlanError("Giáo án không khớp với mục tiêu đã chọn.")
    if [day["day"] for day in plan["days"]] != list(range(1, 8)):
        raise WorkoutPlanError("Giáo án phải có đủ ngày 1 đến 7 theo thứ tự.")
    if not any(day["exercises"] for day in plan["days"]):
        raise WorkoutPlanError("Giáo án phải có ít nhất một ngày tập.")

    for day in plan["days"]:
        for exercise in day["exercises"]:
            exercise_id = exercise["exercise_id"]
            if exercise_id not in eligible_ids:
                raise WorkoutPlanError("Bài tập chính nằm ngoài danh sách được phép.")
            alternative = exercise["alternative"]
            if alternative is not None:
                alternative_id = alternative["exercise_id"]
                if alternative_id == exercise_id or alternative_id not in eligible_ids:
                    raise WorkoutPlanError("Bài tập thay thế không hợp lệ.")
    return plan
