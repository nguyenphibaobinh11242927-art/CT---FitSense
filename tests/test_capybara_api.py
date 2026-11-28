"""Kiểm thử Action Engine và HTTP router, không gọi LLM hay dữ liệu thật."""
from copy import deepcopy
from datetime import date
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from backend.routers import capybara_actions as api
from backend import weekly_action_storage as storage
from src.capybara_actions import (parse_action, swap_exercise_for_injury, move_workout_day,
                                 apply_instant_deload, ActionError)
from src.exercise_library import load_catalog
from src.planner_generation import DEFAULT_DAYS


class Wednesday(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 25)


@pytest.fixture
def plan():
    return [{'day': d, 'is_rest': i == 6, 'is_completed': False, 'focus': str(i),
             'exercises': [] if i == 6 else [{'id': 'squat', 'name': 'Squat', 'sets': 3, 'reps': '20', 'rest_sec': 60}]}
            for i, d in enumerate(DEFAULT_DAYS)]


@pytest.fixture
def env(monkeypatch, tmp_path, plan):
    state = {'alice@example.test': deepcopy(plan), 'bob@example.test': deepcopy(plan)}
    monkeypatch.setattr(storage, 'STORE', tmp_path)
    monkeypatch.setattr(api, 'date', Wednesday)
    monkeypatch.setattr(api, 'current_user', lambda: 'alice@example.test')
    monkeypatch.setattr(api, 'get_schedule', lambda email: state.get(email))
    monkeypatch.setattr(api, 'publish_schedule', lambda email, value: state.__setitem__(email, value))
    monkeypatch.setattr(api, 'get_profile', lambda email: {'equipment': ['Thảm yoga/thể dục']})
    app = FastAPI(); app.include_router(api.router)
    with TestClient(app) as client:
        yield client, state


def post(env, text):
    return env[0].post('/api/capybara/chat', json={'message': text})


@pytest.mark.parametrize('text,action', [('đau đầu gối','injury'), ('Tôi bị đau cổ tay','injury'),
    ('dời lịch thứ 4 sang thứ 5','move'), ('đổi lịch thứ 4 sang chủ nhật','move'),
    ('Hôm nay tôi cảm thấy khá mệt, hãy giảm cường độ tập luyện cho tôi.','deload'),
    ('tôi không đau đầu gối',None), ('nếu đau đầu gối thì sao',None), ('đau vai',None)])
def test_intents(text, action):
    assert parse_action(text)[0] == action


def test_knee_api_persist(env, plan):
    response = post(env, 'đau đầu gối'); assert response.status_code == 200
    data = response.json(); assert data['success'] and len(data['diff']) == 4
    assert all(x['new_exercise']['id'] == 'glute_bridge' for x in data['diff'])
    assert data['schedule'][:2] == plan[:2]
    assert storage.read_plan('alice@example.test', Wednesday.today()) == data['schedule']
    assert env[1]['alice@example.test'] == data['schedule']
    assert env[1]['bob@example.test'] == plan


def test_no_equipment_pauses(env, monkeypatch):
    monkeypatch.setattr(api, 'get_profile', lambda email: {})
    catalog = [e for e in load_catalog() if e['id'] in {'squat', 'glute_bridge'}]
    monkeypatch.setattr(api, 'load_catalog', lambda: catalog)
    data = post(env, 'đau đầu gối').json()
    assert data['partial'] and data['schedule'][2]['exercises'][0]['paused']
    assert data['diff'][0]['new_exercise'] is None


def test_completed_untouched(env):
    env[1]['alice@example.test'][2]['is_completed'] = True
    data = post(env, 'đau đầu gối').json(); assert len(data['diff']) == 3
    assert data['schedule'][2]['exercises'][0]['id'] == 'squat'


def test_unsafe_candidate_filtered(plan):
    catalog = load_catalog()
    for item in catalog:
        if item['id'] == 'glute_bridge': item['avoid_if'] = ['knee']
    result, diff = swap_exercise_for_injury(plan, 'knee', catalog, 2, {'mat'})
    assert all(not d['new_exercise'] or d['new_exercise']['id'] != 'glute_bridge' for d in diff)
    assert plan[2]['exercises'][0]['id'] == 'squat'


def test_unknown_exercise_paused(plan):
    plan[2]['exercises'][0]['id'] = 'unknown'
    result, diff = swap_exercise_for_injury(plan, 'knee', load_catalog(), 2, {'mat'})
    assert result[2]['exercises'][0]['paused']


def test_move_api(env, plan):
    data = post(env, 'dời lịch thứ 4 sang thứ 5').json()
    assert data['schedule'][2] == {**plan[3], 'day': 'Thứ 4'}
    assert data['schedule'][3] == {**plan[2], 'day': 'Thứ 5'}
    assert len(data['diff']) == 2
    assert storage.read_plan('alice@example.test', Wednesday.today()) == data['schedule']


def test_move_rest(env):
    data = post(env, 'dời lịch thứ 4 sang chủ nhật').json()
    assert data['schedule'][2]['is_rest'] and not data['schedule'][6]['is_rest']


def test_move_same(env):
    assert post(env, 'dời lịch thứ 4 sang thứ 4').json()['diff'] == []


def test_move_completed(env, plan):
    env[1]['alice@example.test'][3]['is_completed'] = True
    assert post(env, 'dời lịch thứ 4 sang thứ 5').status_code == 422
    assert not storage.plan_path('alice@example.test', Wednesday.today()).exists()


def test_move_invalid(plan):
    with pytest.raises(ActionError): move_workout_day(plan, 'Thứ 9', 'Thứ 4')


def test_deload_api(env, plan):
    data = post(env, 'giảm tải').json()
    assert data['schedule'][2]['exercises'][0]['reps'] == '14'
    assert data['schedule'][2]['exercises'][0]['sets'] == 3
    assert data['schedule'][:2] == plan[:2] and data['schedule'][3:] == plan[3:]
    assert post(env, 'giảm tải').json()['diff'] == []


@pytest.mark.parametrize('old,new', [(15,10),(1,1),('45s','45s'),(0,0),(True,True)])
def test_deload_boundary(plan, old, new):
    plan[2]['exercises'][0]['reps'] = old
    result, _ = apply_instant_deload(plan, 2)
    assert result[2]['exercises'][0]['reps'] == new


def test_deload_rest(plan):
    assert apply_instant_deload(plan, 6)[1] == []


def test_corrupt_json(env, plan):
    path = storage.plan_path('alice@example.test', Wednesday.today()); path.write_text('{bad', encoding='utf-8')
    assert post(env, 'giảm tải').status_code == 500
    assert path.read_text() == '{bad' and env[1]['alice@example.test'] == plan


def test_failed_write(env, plan, monkeypatch):
    def fail(*args): raise OSError('disk full')
    monkeypatch.setattr(storage.os, 'replace', fail)
    assert post(env, 'giảm tải').status_code == 500
    assert env[1]['alice@example.test'] == plan
    assert not list(storage.STORE.iterdir())


def test_missing_plan(env):
    env[1].clear(); assert post(env, 'giảm tải').status_code == 422


def test_reject_user_override(env):
    assert env[0].post('/api/capybara/chat', json={'message':'giảm tải','email':'bob@example.test'}).status_code == 422


def test_auth_required(env, monkeypatch):
    def denied(): raise HTTPException(401, 'Cần đăng nhập')
    monkeypatch.setattr(api, 'current_user', denied)
    assert post(env, 'giảm tải').status_code == 401
