import json
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.capybara import router
from src import capybara_agent, school_ai
from src.school_ai import FitAIServiceError


@pytest.mark.parametrize(("message", "intent", "action", "params"), [
    ("Mẹo chống đẩy", "QA_FITNESS_APP", None, {}),
    ("Mở Live HUD ở đâu?", "QA_FITNESS_APP", None, {}),
    ("Squat có làm đau gối không?", "QA_FITNESS_APP", None, {}),
    ("Nếu bị đau cổ tay khi tập thì sao?", "QA_FITNESS_APP", None, {}),
    ("Đầu gối là gì?", "QA_FITNESS_APP", None, {}),
    ("Hôm nay, tôi không còn đau gối", "QA_FITNESS_APP", None, {}),
    ("Mình hết đau lưng dưới rồi", "QA_FITNESS_APP", None, {}),
    ("Bạn mình đau đầu gối", "QA_FITNESS_APP", None, {}),
    ("Đừng dời lịch thứ 4 sang thứ 5", "QA_FITNESS_APP", None, {}),
    ("Không cần giảm tải 30%", "QA_FITNESS_APP", None, {}),
    ("Chưa cần giảm tải 30%", "QA_FITNESS_APP", None, {}),
    ("Giảm tải nghĩa là gì?", "QA_FITNESS_APP", None, {}),
    ("Chỉ mình cách đổi lịch tập", "QA_FITNESS_APP", None, {}),
    ("Đau đầu gối", "INJURY_REPORT", "swap_exercise_for_injury", {"joint": "knee"}),
    ("Toi dau goi khi squat", "INJURY_REPORT", "swap_exercise_for_injury", {"joint": "knee"}),
    ("Cổ tay mình bị nhức sau khi tập", "INJURY_REPORT", "swap_exercise_for_injury", {"joint": "wrist"}),
    ("Vai mình đau", "INJURY_REPORT", None, {"joint": "shoulder"}),
    ("Đau vùng thắt lưng", "INJURY_REPORT", None, {"joint": "lower_back"}),
    ("Đau gối và nhức cổ tay", "INJURY_REPORT", None, {}),
    ("Đau gối và cổ tay", "INJURY_REPORT", None, {}),
    ("Mình bị đau quá", "INJURY_REPORT", None, {}),
    ("Đau gối, dời lịch sang thứ 5", "INJURY_REPORT", None, {"joint": "knee"}),
    ("Dời lịch hôm nay", "RESCHEDULE_DELOAD", None, {"from_day": "Thứ 4"}),
    ("Dời lịch sang thứ 6", "RESCHEDULE_DELOAD", None, {"to_day": "Thứ 6"}),
    ("Dời thứ tư qua thứ năm", "RESCHEDULE_DELOAD", "move_workout_day", {"from_day": "Thứ 4", "to_day": "Thứ 5"}),
    ("Doi lich hom nay sang ngay mai", "RESCHEDULE_DELOAD", "move_workout_day", {"from_day": "Thứ 4", "to_day": "Thứ 5"}),
    ("Chuyển buổi tập t4 sang CN", "RESCHEDULE_DELOAD", "move_workout_day", {"from_day": "Thứ 4", "to_day": "Chủ Nhật"}),
    ("Dời lịch thứ 4 sang thứ tư", "RESCHEDULE_DELOAD", None, {"from_day": "Thứ 4", "to_day": "Thứ 4"}),
    ("Dời sang thứ 5 buổi thứ 4", "RESCHEDULE_DELOAD", "move_workout_day", {"from_day": "Thứ 4", "to_day": "Thứ 5"}),
    ("Dời lịch thứ 4 hay thứ 5", "RESCHEDULE_DELOAD", None, {}),
    ("Hoán đổi thứ 4 và thứ 5", "RESCHEDULE_DELOAD", "move_workout_day", {"from_day": "Thứ 4", "to_day": "Thứ 5"}),
    ("Giảm tải 30%", "RESCHEDULE_DELOAD", "apply_instant_deload", {"percentage": 0.3}),
    ("Cho mình giảm tải", "RESCHEDULE_DELOAD", "apply_instant_deload", {"percentage": 0.3}),
    ("Giam khoi luong 12,5 phan tram", "RESCHEDULE_DELOAD", "apply_instant_deload", {"percentage": 0.125}),
    ("Giảm tải -10%", "RESCHEDULE_DELOAD", None, {}),
    ("Giảm tải 100%", "RESCHEDULE_DELOAD", None, {}),
    ("Giảm tải 30", "RESCHEDULE_DELOAD", None, {}),
    ("Giảm tải 20% hay 30%", "RESCHEDULE_DELOAD", None, {}),
    ("Dời lịch thứ 4 sang thứ 5 và giảm tải", "RESCHEDULE_DELOAD", None, {}),
])
def test_offline_intents(message, intent, action, params):
    result = capybara_agent.classify_intent(message, today=date(2026, 11, 18))
    assert result.intent == intent
    assert result.action == action
    assert result.params.model_dump(exclude_none=True) == params
    assert result.reply.endswith("🦫✨")


def test_move_does_not_treat_next_monday_as_part_of_this_week():
    result = capybara_agent.classify_intent("Dời lịch hôm nay sang ngày mai", today=date(2026, 11, 22))
    assert result.params.from_day == "Chủ Nhật"
    assert result.params.to_day is None
    assert result.action is None
    assert "trong tuần này" in result.reply


def test_offline_without_key_never_calls_fit_ai(monkeypatch):
    monkeypatch.delenv("FITAI_API_KEY", raising=False)
    monkeypatch.setattr(capybara_agent, "complete_with_school_ai", lambda *_a, **_kw: pytest.fail("Called online"))
    assert "thân người" in capybara_agent.respond_to_message("Mẹo chống đẩy").reply


def test_offline_library_question_has_a_fitsense_answer(monkeypatch):
    monkeypatch.delenv("FITAI_API_KEY", raising=False)
    result = capybara_agent.respond_to_message("Xem thư viện ở đâu?")
    assert "Mở mục Thư viện" in result.reply


def test_school_ai_sends_system_and_user_messages_for_chat(monkeypatch):
    monkeypatch.setenv("FITAI_API_KEY", "test")
    sent = {}

    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}

    def post(url, **kwargs):
        sent.update(kwargs)
        return Response()

    monkeypatch.setattr(school_ai.requests, "post", post)
    response = school_ai.complete_with_school_ai(
        "Mẹo chống đẩy", system_prompt="Capybara", max_tokens=320, timeout=(2.0, 5.0),
    )
    assert response == "{}"
    assert sent["json"]["model"] == "Qwen-27B"
    assert sent["json"]["messages"] == [
        {"role": "system", "content": "Capybara"}, {"role": "user", "content": "Mẹo chống đẩy"},
    ]
    assert sent["json"]["response_format"] == {"type": "json_object"}
    assert sent["json"]["max_tokens"] == 320
    assert sent["timeout"] == (2.0, 5.0)


def test_qwen_answers_with_capybara_system_prompt(monkeypatch):
    monkeypatch.setenv("FITAI_API_KEY", "test")
    calls = []

    def complete(message, **kwargs):
        calls.append((message, kwargs))
        return json.dumps({"intent": "QA_FITNESS_APP", "reply": "Mở mục Thư viện để xem bài tập. 🦫✨ "})

    monkeypatch.setattr(capybara_agent, "complete_with_school_ai", complete)
    reply = capybara_agent.respond_to_message("Xem thư viện ở đâu?")
    assert reply.reply == "Mở mục Thư viện để xem bài tập. 🦫✨"
    assert calls[0][0] == "Xem thư viện ở đâu?"
    assert "Capybara" in calls[0][1]["system_prompt"]
    assert calls[0][1]["timeout"] == (2.0, 5.0)


@pytest.mark.parametrize("bad_payload", [
    "not json",
    '{"intent": "UNKNOWN", "reply": "Xin chào"}',
    '{"intent": "QA_FITNESS_APP", "reply": 29}',
    '{"intent": "QA_FITNESS_APP", "reply": "🦫✨ "}',
    '{"intent": "QA_FITNESS_APP", "reply": "Đã dời", "action": "move_workout_day"}',
])
def test_invalid_qwen_output_uses_local_reply(monkeypatch, bad_payload):
    monkeypatch.setenv("FITAI_API_KEY", "test")
    monkeypatch.setattr(capybara_agent, "complete_with_school_ai", lambda *_a, **_kw: bad_payload)
    message = "Mẹo chống đẩy"
    assert capybara_agent.respond_to_message(message) == capybara_agent.classify_intent(message)


def test_qwen_timeout_uses_local_reply(monkeypatch):
    monkeypatch.setenv("FITAI_API_KEY", "test")

    def timeout(*_args, **_kwargs):
        raise FitAIServiceError("timeout")

    monkeypatch.setattr(capybara_agent, "complete_with_school_ai", timeout)
    assert "thân người" in capybara_agent.respond_to_message("Mẹo chống đẩy").reply


def test_qwen_can_request_clarification_but_cannot_supply_a_schedule_action(monkeypatch):
    monkeypatch.setenv("FITAI_API_KEY", "test")
    monkeypatch.setattr(
        capybara_agent, "complete_with_school_ai",
        lambda *_a, **_kw: '{"intent": "RESCHEDULE_DELOAD", "reply": "Đã sửa lịch"}',
    )
    result = capybara_agent.respond_to_message("Sắp lại giáo án giúp mình")
    assert result.intent == "RESCHEDULE_DELOAD"
    assert result.action is None
    assert result.params.model_dump(exclude_none=True) == {}
    assert "Bạn muốn" in result.reply


def test_complete_local_requests_do_not_send_injury_or_schedule_to_qwen(monkeypatch):
    monkeypatch.setenv("FITAI_API_KEY", "test")
    monkeypatch.setattr(capybara_agent, "complete_with_school_ai", lambda *_a, **_kw: pytest.fail("Called online"))
    assert capybara_agent.respond_to_message("Đau đầu gối").params.joint == "knee"
    assert capybara_agent.respond_to_message("Giảm tải 30%").params.percentage == 0.3
    assert capybara_agent.respond_to_message("Đừng giảm tải 30%").action is None


def test_chat_endpoint_preserves_dispatcher_contract_offline(monkeypatch):
    monkeypatch.delenv("FITAI_API_KEY", raising=False)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post("/api/capybara/chat", json={"message": "Dời thứ 4 sang thứ 5"})
    assert response.status_code == 200
    assert response.json() == {
        "intent": "RESCHEDULE_DELOAD", "action": "move_workout_day",
        "params": {"joint": None, "from_day": "Thứ 4", "to_day": "Thứ 5", "percentage": None},
        "reply": "Capy hiểu rồi, bạn muốn dời buổi Thứ 4 sang Thứ 5. 🦫✨",
    }
    assert client.post("/api/capybara/chat", json={"message": "  "}).status_code == 422
    assert client.post("/api/capybara/chat", json={"message": "a" * 1001}).status_code == 422
