"""SCRUM-13: Profile validation and local JSON persistence for the Streamlit prototype.

This is *local demo storage*, not an authentication database. Do not put passwords,
API keys or third-party credentials in a profile. Files are ignored by Git.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

PROFILE_DIR = Path(__file__).resolve().parents[1] / "data" / "private" / "profiles"
NO_RESTRICTIONS = "Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"
NO_EQUIPMENT = "Không có dụng cụ (Chỉ tập Bodyweight)"


def validate_profile(profile: dict[str, Any]) -> list[str]:
    """Return human-readable validation errors without changing the given profile."""
    errors: list[str] = []
    if not isinstance(profile, dict):
        return ["Hồ sơ không đúng định dạng."]

    for field, label in (("name", "Họ tên"), ("goal", "Mục tiêu"),
                         ("fitness_level", "Trình độ"), ("environment", "Môi trường")):
        if not isinstance(profile.get(field), str) or not profile[field].strip():
            errors.append(f"Vui lòng nhập/chọn {label}.")

    if isinstance(profile.get("fitness_level"), str) and profile["fitness_level"].strip():
        if profile["fitness_level"].split()[0] not in {"Beginner", "Intermediate", "Advanced"}:
            errors.append("Trình độ không hợp lệ.")

    for field in ("restrictions", "equipment"):
        values = profile.get(field)
        if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
            errors.append(f"Trường {field} phải là danh sách.")

    restrictions = profile.get("restrictions", [])
    equipment = profile.get("equipment", [])
    if isinstance(restrictions, list) and NO_RESTRICTIONS in restrictions and len(restrictions) > 1:
        errors.append("Không thể chọn 'Không có hạn chế' cùng chấn thương khác.")
    if isinstance(equipment, list) and NO_EQUIPMENT in equipment and len(equipment) > 1:
        errors.append("Không thể chọn 'Không có dụng cụ' cùng với dụng cụ khác.")

    for field, low, high, label in (
        ("weight_kg", 30, 200, "Cân nặng"),
        ("height_cm", 100, 230, "Chiều cao"),
        ("age", 12, 90, "Tuổi"),
        ("days_per_week", 2, 6, "Số ngày tập/tuần"),
        ("session_duration_minutes", 15, 90, "Thời lượng buổi tập"),
    ):
        value = profile.get(field)
        # Weight/height/age are optional per the FitSense architecture.
        if value is None and field in {"weight_kg", "height_cm", "age"}:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            errors.append(f"{label} phải nằm trong khoảng {low}–{high}.")
    return errors


def profile_path(identifier: str, directory: Path = PROFILE_DIR) -> Path:
    """Use a pseudonymous filename instead of exposing an email/name in the path."""
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("Cần mã định danh người dùng để lưu hồ sơ.")
    digest = hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()
    return Path(directory) / f"{digest}.json"


def load_profile(identifier: str, directory: Path = PROFILE_DIR) -> dict[str, Any] | None:
    """Read a previously saved profile; raise a descriptive error for corrupt JSON."""
    path = profile_path(identifier, directory)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Không thể đọc hồ sơ JSON đã lưu.") from exc
    if not isinstance(data, dict) or validate_profile(data):
        raise ValueError("Hồ sơ JSON chứa dữ liệu không hợp lệ.")
    return data


def save_profile(identifier: str, profile: dict[str, Any], directory: Path = PROFILE_DIR) -> Path:
    """Validate and atomically write one user's local profile JSON."""
    errors = validate_profile(profile)
    if errors:
        raise ValueError(" ".join(errors))
    destination = profile_path(identifier, directory)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=destination.parent, suffix=".tmp", delete=False
        ) as stream:
            temp_name = stream.name
            json.dump(profile, stream, ensure_ascii=False, indent=2)
        os.replace(temp_name, destination)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return destination
