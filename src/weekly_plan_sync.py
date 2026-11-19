"""Đồng bộ trạng thái buổi tập với kế hoạch tuần (không phụ thuộc Streamlit)."""

from copy import deepcopy


def start_planned_day(schedule: list[dict], day_name: str) -> tuple[list[dict], dict]:
    """Đánh dấu buổi được chọn đang tập, giữ nguyên bài và cấu hình của giáo án."""
    if not isinstance(schedule, list):
        raise ValueError("Kế hoạch tuần không hợp lệ.")
    updated = deepcopy(schedule)
    selected = None
    for day in updated:
        if not isinstance(day, dict):
            continue
        if day.get("day") == day_name:
            if day.get("is_rest") or not day.get("exercises"):
                raise ValueError("Ngày nghỉ không có bài tập để bắt đầu.")
            day["workout_status"] = "in_progress"
            # Khởi động một lượt tập mới, không mang kết quả buổi trước sang.
            day.pop("workout_completed_at", None)
            day.pop("workout_actual_reps", None)
            selected = day
        elif day.get("workout_status") == "in_progress":
            day["workout_status"] = "planned"
    if selected is None:
        raise ValueError(f"Không tìm thấy buổi tập '{day_name}' trong kế hoạch tuần.")
    return updated, selected


def finish_planned_day(
    schedule: list[dict], day_name: str | None, *,
    completed: bool, actual_reps: int, finished_at: str,
) -> list[dict]:
    """Ghi kết quả về đúng ngày trong kế hoạch, không sửa bài tập đã lên lịch."""
    updated = deepcopy(schedule)
    if not day_name:
        return updated
    for day in updated:
        if isinstance(day, dict) and day.get("day") == day_name:
            if day.get("workout_status") != "in_progress":
                break
            day["workout_status"] = "completed" if completed else "abandoned"
            day["workout_actual_reps"] = max(0, int(actual_reps))
            day["workout_completed_at"] = finished_at
            break
    return updated
