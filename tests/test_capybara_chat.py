import unittest
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.routers.auth import CURRENT_SESSION, SESSION_COOKIE_NAME, create_session_token
from src.school_ai import FitAIServiceError


class TestCapybaraChat(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.previous_session = CURRENT_SESSION.copy()
        self.client.cookies.set(
            SESSION_COOKIE_NAME,
            create_session_token("chat-test@example.invalid"),
        )

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
        self.client.cookies.delete(SESSION_COOKIE_NAME)
        CURRENT_SESSION.update({"user_email": "someone-else@example.invalid", "is_logged_in": True})
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

    def test_chat_authentication_isolated_between_clients(self):
        other_client = TestClient(app)
        other_client.cookies.set(
            SESSION_COOKIE_NAME,
            create_session_token("other-user@example.invalid"),
        )
        with patch(
            "backend.routers.capybara.complete_with_school_ai",
            return_value='{"reply":"Được nhé."}',
        ) as complete:
            response = other_client.post("/api/capybara/chat", json={
                "messages": [{"role": "user", "content": "Xin chào"}],
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reply": "Được nhé."})
        self.assertIn("Xin chào", complete.call_args.args[0])

    def test_auth_me_uses_the_request_cookie_instead_of_global_session(self):
        CURRENT_SESSION.update({"user_email": "global-user@example.invalid", "is_logged_in": True})
        self.client.cookies.delete(SESSION_COOKIE_NAME)
        anonymous = self.client.get("/api/auth/me")
        self.assertFalse(anonymous.json()["is_logged_in"])

        other_client = TestClient(app)
        other_client.cookies.set(
            SESSION_COOKIE_NAME,
            create_session_token("cookie-user@example.invalid"),
        )
        with patch("backend.routers.auth.load_profile", return_value={"email": "cookie-user@example.invalid"}) as load:
            authenticated = other_client.get("/api/auth/me")

        self.assertTrue(authenticated.json()["is_logged_in"])
        self.assertEqual(authenticated.json()["user"]["email"], "cookie-user@example.invalid")
        load.assert_called_once_with("cookie-user@example.invalid")

    def test_chat_rejects_tampered_and_expired_session_cookies(self):
        valid = create_session_token("chat-test@example.invalid")
        for token in (valid + "tampered", create_session_token("expired@example.invalid", now=1)):
            self.client.cookies.set(SESSION_COOKIE_NAME, token)
            response = self.client.post("/api/capybara/chat", json={
                "messages": [{"role": "user", "content": "Xin chào"}],
            })
            self.assertEqual(response.status_code, 401)

    def test_chat_uses_configured_session_secret_and_rejects_weak_secret(self):
        with patch.dict(os.environ, {"FITNESS_SESSION_SECRET": "a" * 32}):
            token = create_session_token("configured@example.invalid")
            self.client.cookies.set(SESSION_COOKIE_NAME, token)
            with patch(
                "backend.routers.capybara.complete_with_school_ai",
                return_value='{"reply":"Đã xác thực."}',
            ):
                response = self.client.post("/api/capybara/chat", json={
                    "messages": [{"role": "user", "content": "Xin chào"}],
                })
        self.assertEqual(response.status_code, 200)

        with patch.dict(os.environ, {"FITNESS_SESSION_SECRET": "short"}):
            with self.assertRaises(RuntimeError):
                create_session_token("weak-secret@example.invalid")

    def test_login_issues_http_only_session_cookie_used_by_chat(self):
        with (
            patch("backend.routers.auth.load_users", return_value={}),
            patch("backend.routers.auth.save_users"),
            patch("backend.routers.auth.load_profile", return_value=None),
            patch("backend.routers.auth.save_profile"),
        ):
            login_response = self.client.post("/api/auth/login", json={
                "email": "new-login@example.invalid",
                "password": "Password123",
            })

        self.assertEqual(login_response.status_code, 200)
        cookie_header = login_response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie_header)
        self.assertIn("samesite=lax", cookie_header)
        with patch(
            "backend.routers.capybara.complete_with_school_ai",
            return_value='{"reply":"Xin chào!"}',
        ):
            chat_response = self.client.post("/api/capybara/chat", json={
                "messages": [{"role": "user", "content": "Xin chào"}],
            })
        self.assertEqual(chat_response.status_code, 200)

    def test_google_sign_in_verifies_provider_credential_before_issuing_cookie(self):
        from fastapi import HTTPException

        self.client.cookies.delete(SESSION_COOKIE_NAME)
        with patch(
            "backend.routers.auth.verify_google_credential",
            side_effect=HTTPException(status_code=401, detail="invalid credential"),
        ):
            response = self.client.post("/api/auth/google", json={"credential": "invalid"})

        self.assertEqual(response.status_code, 401)
        self.assertNotIn(SESSION_COOKIE_NAME, self.client.cookies)

    def test_google_identity_is_verified_against_configured_client_id(self):
        from backend.routers.auth import verify_google_credential

        identity = {
            "email": "verified@example.com",
            "email_verified": True,
            "name": "Verified User",
            "picture": "https://example.com/avatar.png",
            "sub": "google-subject",
        }
        with (
            patch("backend.routers.auth._google_client_id", return_value="fitsense-client-id"),
            patch("backend.routers.auth.id_token.verify_oauth2_token", return_value=identity) as verify,
        ):
            result = verify_google_credential("signed-google-credential")

        self.assertEqual(result["email"], "verified@example.com")
        verify.assert_called_once()
        self.assertEqual(verify.call_args.kwargs["audience"], "fitsense-client-id")

    def test_google_identity_without_verified_email_is_rejected(self):
        from fastapi import HTTPException
        from backend.routers.auth import verify_google_credential

        with (
            patch("backend.routers.auth._google_client_id", return_value="fitsense-client-id"),
            patch("backend.routers.auth.id_token.verify_oauth2_token", return_value={
                "email": "unverified@example.com",
                "email_verified": False,
                "sub": "google-subject",
            }),
            self.assertRaises(HTTPException) as raised,
        ):
            verify_google_credential("signed-google-credential")

        self.assertEqual(raised.exception.status_code, 401)

    def test_login_rejects_legacy_profiles_without_password_hash(self):
        with (
            patch("backend.routers.auth.load_users", return_value={
                "legacy@example.com": {"email": "legacy@example.com"},
            }),
            patch("backend.routers.auth.load_profile", return_value={"email": "legacy@example.com"}),
        ):
            response = self.client.post("/api/auth/login", json={
                "email": "legacy@example.com",
                "password": "any-password",
            })

        self.assertEqual(response.status_code, 401)
