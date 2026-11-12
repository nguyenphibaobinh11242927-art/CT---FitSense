"""Regressions: actual workout day, historical isolation, future AI, fallback and storage."""
from copy import deepcopy
from datetime import date
import json
from unittest.mock import patch

from src.adaptive_weekly_plan import (
    DAYS, add_workout_event, muscle_tags, recovery_warnings, start_actual_workout,
)
from src.weekly_plan_storage import save_week_state, load_week_state


def plan():
    muscles = ["Ngực", "Chân", None, "Lưng", "Vai", "Đùi trước", None]
    result = []
    for i, label in enumerate(DAYS):
        rest = muscles[i] is None
        result.append({"day": label, "focus": muscles[i] or "Nghỉ", "is_rest": rest,
                       "exercises": [] if rest else [{"name": f"Bài {i}", "primary_muscle": muscles[i],
                                                         "sets": 3, "reps": 12}],
                       "workout_status": "completed" if i == 0 else "planned",
                       **({"workout_actual_reps": 45} if i == 0 else {})})
    return result


def test_copy_past_day_into_today_not_touch_past():
    original = plan()
    before = deepcopy(original)
    updated, today, method = start_actual_workout(original, "Thứ 2", date(2026, 11, 12), use_ai=False)
    assert original == before
    assert updated[0] == before[0]
    assert updated[1:3] == before[1:3]
    assert today["day"] == "Thứ 5"
    assert today["focus"] == "Ngực"
    assert today["copied_from_day"] == "Thứ 2"
    assert today["actual_date"] == "2026-11-12"
    assert today["workout_status"] == "in_progress"
    assert "workout_actual_reps" not in today
    assert method == "Thuật toán dự phòng"
    assert [x["day"] for x in updated] == DAYS


def test_copy_future_day_and_preserve_history():
    original = plan()
    updated, today, _ = start_actual_workout(original, "Thứ 6", date(2026, 11, 12), use_ai=False)
    assert today["focus"] == "Vai"
    assert original[4]["focus"] == "Vai"
    assert updated[0]["workout_actual_reps"] == 45
    assert updated[3]["day"] == "Thứ 5"


def test_today_no_copy_and_week_sunday_no_future():
    updated, day, _ = start_actual_workout(plan(), "Thứ 5", date(2026, 11, 12), use_ai=False)
    assert day["focus"] == "Lưng"
    assert updated[4:] == plan()[4:]
    sunday_plan = plan()
    sunday_plan[-1] = {"day": "Chủ Nhật", "focus": "Core", "is_rest": False,
                       "exercises": [{"name": "Plank", "primary_muscle": "Core"}]}
    sunday, day, _ = start_actual_workout(sunday_plan, "Thứ 2", date(2026, 11, 15), use_ai=False)
    assert len(sunday) == 7
    assert day["day"] == "Chủ Nhật"
    assert sunday[:6] == sunday_plan[:6]


def test_history_append_is_idempotent():
    old = [{"session_id": "1", "actual_date": "2026-11-09", "reps": 60}]
    new = add_workout_event(old, session_id="2", actual_date=date(2026, 11, 12),
                            workout={"day": "Thứ 5", "copied_from_day": "Thứ 2", "focus": "Ngực",
                                     "exercises": [{"primary_muscle": "Ngực"}]},
                            reps=80, status="completed", finished_at="17:30")
    assert len(new) == 2
    assert new[0] == old[0]
    assert new[1]["actual_date"] == "2026-11-12"
    assert new[1]["source_day"] == "Thứ 2"
    assert add_workout_event(new, session_id="2", actual_date=date(2026, 11, 12),
                             workout={}, reps=10, status="completed", finished_at="18:00") == new


def test_recovery_warning_uses_real_history():
    target = {"exercises": [{"primary_muscle": "Ngực (Chest)", "secondary_muscle": "Tay sau"}]}
    history = [{"actual_date": "2026-11-11", "status": "completed", "muscle_tags": ["chest"]}]
    assert recovery_warnings(target, date(2026, 11, 12), history, plan())
    assert recovery_warnings(target, date(2026, 11, 14), history, plan()) == []


def test_completed_future_cannot_be_changed():
    original = plan()
    original[5]["workout_status"] = "completed"
    updated, *_ = start_actual_workout(original, "Thứ 2", date(2026, 11, 12), use_ai=False)
    assert updated[5] == original[5]


def test_ai_invalid_response_falls_back():
    with patch.dict("os.environ", {"FITAI_API_KEY": "dummy"}):
        with patch("src.adaptive_weekly_plan.urlopen", side_effect=OSError("offline")):
            updated, _, mode = start_actual_workout(plan(), "Thứ 2", date(2026, 11, 12))
    assert len(updated) == 7
    assert mode == "Thuật toán dự phòng"


def test_ai_only_reorders_existing_candidates():
    class MockResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, n):
            return json.dumps({"choices": [{"message": {"content": '{"indices":[0,1,2]}'}}]}).encode()
    with patch.dict("os.environ", {"FITAI_API_KEY": "dummy"}):
        with patch("src.adaptive_weekly_plan.urlopen", return_value=MockResponse()):
            updated, _, _ = start_actual_workout(plan(), "Thứ 2", date(2026, 11, 12))
    assert updated[0] == plan()[0]
    assert set(x["focus"] for x in updated[4:]) <= {"Vai", "Đùi trước", "Nghỉ", "Lưng"}


def test_local_storage_per_user(tmp_path):
    state = {"is_logged_in": True, "user_profile": {"email": "first@example.org"},
             "weekly_schedule": plan(), "workout_event_history": [{"session_id": "x"}]}
    assert save_week_state(state, directory=tmp_path)
    loaded = {"is_logged_in": True, "user_profile": {"email": "first@example.org"},
              "weekly_schedule": [], "workout_event_history": []}
    assert load_week_state(loaded, directory=tmp_path)
    assert loaded["weekly_schedule"] == state["weekly_schedule"]
    assert loaded["workout_event_history"] == [{"session_id": "x"}]
    another = {"is_logged_in": True, "user_profile": {"email": "second@example.org"},
               "weekly_schedule": plan()}
    assert load_week_state(another, directory=tmp_path) is False


def test_rest_cannot_start():
    import pytest
    with pytest.raises(ValueError):
        start_actual_workout(plan(), "Thứ 4", date(2026, 11, 12), use_ai=False)


def test_preserve_number_of_rest_days_after_replan():
    original = plan()
    updated, *_ = start_actual_workout(original, "Thứ 2", date(2026, 11, 12), use_ai=False)
    assert sum(bool(x["is_rest"]) for x in updated[4:]) == sum(bool(x["is_rest"]) for x in original[4:])
