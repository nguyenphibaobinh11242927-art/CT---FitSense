"""Chat action endpoint for the existing local FastAPI session architecture."""
from datetime import date
from threading import RLock
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from src.capybara_actions import (ActionError, parse_action, swap_exercise_for_injury,
                                  move_workout_day, apply_instant_deload)
from src.exercise_library import load_catalog
from src.planner_generation import planner_profile_filters
from src.workout_planner import WorkoutPlanError
from backend import weekly_action_storage as storage

router = APIRouter(prefix='/api/capybara', tags=['Capybara Actions'])
ACTION_LOCK = RLock()


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=1000)


def current_user():
    from backend.routers.auth import CURRENT_SESSION
    if not CURRENT_SESSION.get('is_logged_in') or not CURRENT_SESSION.get('user_email'):
        raise HTTPException(401, 'Cần đăng nhập để điều chỉnh lịch tập.')
    return CURRENT_SESSION['user_email']


def get_schedule(email):
    from backend.routers.planner import get_user_schedule
    return get_user_schedule(email)


def publish_schedule(email, schedule):
    from backend.routers.planner import USER_SCHEDULES
    USER_SCHEDULES[email] = schedule


def get_profile(email):
    from src.profile import load_profile
    return load_profile(email) or {}


@router.post('/chat')
def chat(payload: ChatRequest):
    email = current_user()
    action, params = parse_action(payload.message)
    if not action:
        return {'success': False, 'action': None, 'diff': [], 'message': 'Chưa nhận diện được yêu cầu điều chỉnh lịch rõ ràng. Nếu đang đau, hãy dừng động tác gây đau.'}
    today = date.today()
    with ACTION_LOCK:
        try:
            # Kiểm tra file đã tồn tại để không ghi đè dữ liệu JSON bị hỏng
            storage.read_plan(email, today)
            schedule = get_schedule(email)
            if not schedule:
                raise ActionError('Chưa có lịch tập tuần.')
            if action == 'injury':
                equipment, limits = planner_profile_filters(get_profile(email))
                plan, diff = swap_exercise_for_injury(schedule, params['injury'], load_catalog(), today.weekday(), equipment, limits)
            elif action == 'move':
                plan, diff = move_workout_day(schedule, **params)
            else:
                plan, diff = apply_instant_deload(schedule, today.weekday())
            if diff:
                storage.save_plan(email, plan, today)
                publish_schedule(email, plan)
        except (ActionError, WorkoutPlanError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except (OSError, ValueError, TypeError) as exc:
            raise HTTPException(500, 'Không thể đọc hoặc lưu dữ liệu lịch tập; chưa xác nhận thay đổi.') from exc
    paused = sum(item.get('status') == 'paused' for item in diff)
    message = 'Đã cập nhật lịch tập.' if diff else 'Không có thay đổi cần thực hiện.'
    if action == 'injury':
        message += ' Dừng động tác gây đau; bài thay thế không phải bảo đảm an toàn y khoa.'
    if paused:
        message += f' Có {paused} bài tạm ngừng, không thực hiện các bài này.'
    return {'success': True, 'action': action, 'diff': diff, 'schedule': plan, 'message': message, 'partial': bool(paused)}
