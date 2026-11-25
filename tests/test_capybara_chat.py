import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.routers.auth import CURRENT_SESSION
from src.school_ai import FitAIServiceError


class TestCapybaraChat(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.previous_session = CURRENT_SESSION.copy()
        CURRENT_SESSION.update({"user_email": "chat-test@example.invalid", "is_logged_in": True})

    def tearDown(self):
        CURRENT_SESSION.clear()
        CURRENT_SESSION.update(self.previous_session)

    def test_chat_returns_ai_reply_and_passes_conversation_to_provider(self):
        with patch(
            "backend.routers.capybara.complete_with_school_ai",
            return_value='{"reply":"Bắt đầu nhẹ nhàng với vài hiệp chống đẩy nhé!"}',
        ) as complete:
            response = self.client.post("/api/capybara/chat", json={
                "messages": [{"role": "user", "content": "Gợi ý bài tập thân trên"}],
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reply": "Bắt đầu nhẹ nhàng với vài hiệp chống đẩy nhé!"})
        self.assertIn("Gợi ý bài tập thân trên", complete.call_args.args[0])

    def test_chat_requires_login(self):
        CURRENT_SESSION.update({"user_email": None, "is_logged_in": False})
        with patch("backend.routers.capybara.complete_with_school_ai") as complete:
            response = self.client.post("/api/capybara/chat", json={
                "messages": [{"role": "user", "content": "Xin chào"}],
            })

        self.assertEqual(response.status_code, 401)
        complete.assert_not_called()

    def test_chat_surfaces_missing_ai_configuration(self):
        with patch(
            "backend.routers.capybara.complete_with_school_ai",
            side_effect=FitAIServiceError("Máy chủ FitSense chưa cấu hình FITAI_API_KEY."),
        ):
            response = self.client.post("/api/capybara/chat", json={
                "messages": [{"role": "user", "content": "Xin chào"}],
            })

        self.assertEqual(response.status_code, 503)
        self.assertIn("FITAI_API_KEY", response.json()["detail"])

    def test_chat_rejects_malformed_ai_response(self):
        with patch("backend.routers.capybara.complete_with_school_ai", return_value="not json"):
            response = self.client.post("/api/capybara/chat", json={
                "messages": [{"role": "user", "content": "Xin chào"}],
            })

        self.assertEqual(response.status_code, 502)

    def test_chat_rejects_non_user_final_message_and_oversized_history(self):
        invalid_last_message = self.client.post("/api/capybara/chat", json={
            "messages": [{"role": "assistant", "content": "Xin chào"}],
        })
        oversized_history = self.client.post("/api/capybara/chat", json={
            "messages": [
                {"role": "user", "content": "x" * 900}
                for _ in range(7)
            ],
        })

        self.assertEqual(invalid_last_message.status_code, 422)
        self.assertEqual(oversized_history.status_code, 422)
