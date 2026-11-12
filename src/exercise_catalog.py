"""Shared exercise identity, library merge and real schedule replacement.

The schedule and the library use the same canonical name-based exercise ID.
Only exercises from supplied local data may be selected.
"""
from __future__ import annotations

import re
import unicodedata
from copy import deepcopy


def exercise_id(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name.casefold())
    ascii_name = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")


def muscle_group(exercise: dict) -> str:
    primary = unicodedata.normalize("NFD", str(exercise.get("primary_muscle", "")).casefold())
    primary = "".join(x for x in primary if unicodedata.category(x) != "Mn").replace("đ", "d")
    if any(k in primary for k in ("dui", "mong", "chan", "calf", "glute", "quad")):
        return "legs"
    if any(k in primary for k in ("nguc", "chest")):
        return "chest"
    if any(k in primary for k in ("tay sau", "triceps")):
        return "triceps"
    if any(k in primary for k in ("lung", "lat", "back")):
        return "back"
    if any(k in primary for k in ("bung", "core", "abs")):
        return "core"
    return exercise_id(primary)


def merge_catalog(library: list[dict], schedule: list[dict]) -> list[dict]:
    """Include ALL available exercises, deduplicated by stable IDs."""
    result = {}
    for exercise in library:
        item = deepcopy(exercise)
        item["exercise_id"] = exercise_id(item["name"])
        result[item["exercise_id"]] = item
    for day in schedule:
        for exercise in day.get("exercises", []):
            identifier = exercise_id(exercise["name"])
            if identifier in result:
                continue
            item = deepcopy(exercise)
            item["exercise_id"] = identifier
            item.setdefault("description", "Bài tập có trong kế hoạch tuần hiện tại.")
            item.setdefault("steps", [])
            item.setdefault("common_mistake", "")
            result[identifier] = item
    return list(result.values())


def replacement_options(current: dict, catalog: list[dict]) -> list[dict]:
    group = muscle_group(current)
    current_id = exercise_id(current["name"])
    return [item for item in catalog if exercise_id(item["name"]) != current_id
            and muscle_group(item) == group]


def swap_scheduled_exercise(
    schedule: list[dict], day_index: int, exercise_index: int, replacement: dict
) -> dict:
    """Replace the actual prescription in-place, keeping original sets/reps/rest."""
    original = schedule[day_index]["exercises"][exercise_index]
    replacement_item = deepcopy(replacement)
    replacement_item.update({
        "exercise_id": exercise_id(replacement["name"]),
        "sets": original.get("sets", 3),
        "reps": original.get("reps", 10),
        "rest_sec": original.get("rest_sec", 60),
    })
    schedule[day_index]["exercises"][exercise_index] = replacement_item
    return replacement_item
