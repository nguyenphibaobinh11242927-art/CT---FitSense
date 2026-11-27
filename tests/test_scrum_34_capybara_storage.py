"""Unit and integration tests for SCRUM-34: Per-Client Session Auth, History Persistence, Error Propagation & Race Protection."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient

from backend.main import app
import backend.routers.auth as auth_router
from backend.routers.auth import CURRENT_SESSION, SESSION_TOKENS
import backend.routers.capybara as capybara_router
from src.capybara_agent import CapybaraReply
from src.capybara_history import (
    MAX_MESSAGES_PER_USER,
    append_chat_exchange,
    clear_chat_history,
    load_chat_history,
    save_chat_history,
    user_history_key,
)


class TestCapybaraHistoryStorage(unittest.TestCase):
    """Kiểm thử lớp lưu trữ bền vững và phân lập dữ liệu theo tài khoản."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_user_key_normalizes_case_and_whitespace(self):
        self.assertEqual(
            user_history_key("  Binh.M01@FitSense.vn "),
            user_history_key("binh.m01@fitsense.vn"),
        )
        self.assertEqual(user_history_key(""), "")
        self.assertEqual(user_history_key(None), "")

    def test_save_and_load_persists_metadata_and_truncates(self):
        messages = [
            {"role": "user", "content": f"Tin nhắn {i}", "time": "10:00"}
            for i in range(MAX_MESSAGES_PER_USER + 15)
        ]
        messages.append({
            "role": "assistant",
            "content": "Đổi Squat sang Glute Bridge nhé! 🦫✨",
            "time": "10:01",
            "emotion": "worried",
            "intent": "INJURY_REPORT",
            "action": "swap_exercise_for_injury",
            "actionCard": {"old": "Squat", "new": "Glute Bridge"},
            "diff": {"old_exercise": "squat", "new_exercise": "glute_bridge", "target_day": "Thứ 4"},
        })

        saved = save_chat_history("binh@example.com", messages, storage_dir=self.storage_dir)
        self.assertEqual(len(saved), MAX_MESSAGES_PER_USER)

        loaded = load_chat_history("binh@example.com", storage_dir=self.storage_dir)
        self.assertEqual(len(loaded), MAX_MESSAGES_PER_USER)
        self.assertEqual(loaded[-1]["emotion"], "worried")
        self.assertEqual(loaded[-1]["actionCard"]["new"], "Glute Bridge")
        self.assertEqual(loaded[-1]["diff"]["target_day"], "Thứ 4")

    def test_corrupt_json_returns_empty_list_safely(self):
        key = user_history_key("broken@example.com")
        bad_file = self.storage_dir / f"{key}.json"
        bad_file.write_text("{invalid-json", encoding="utf-8")
        self.assertEqual(load_chat_history("broken@example.com", storage_dir=self.storage_dir), [])

    def test_append_and_clear_are_isolated_per_user(self):
        append_chat_exchange(
            "user_a@example.com",
            "Tôi bị đau đầu gối",
            {"reply": "Đổi sang cầu mông nhé!", "intent": "INJURY_REPORT", "action": "swap_exercise_for_injury"},
            storage_dir=self.storage_dir,
        )
        append_chat_exchange(
            "user_b@example.com",
            "Xin mẹo chống đẩy",
            {"reply": "Giữ thân thẳng nhé!", "intent": "QA_FITNESS_APP", "action": None},
            storage_dir=self.storage_dir,
        )

        hist_a = load_chat_history("user_a@example.com", storage_dir=self.storage_dir)
        hist_b = load_chat_history("user_b@example.com", storage_dir=self.storage_dir)
        self.assertEqual(len(hist_a), 2)
        self.assertEqual(len(hist_b), 2)
        self.assertIn("đau đầu gối", hist_a[0]["content"])
        self.assertNotIn("đau đầu gối", hist_b[0]["content"])

        self.assertTrue(clear_chat_history("user_a@example.com", storage_dir=self.storage_dir))
        self.assertEqual(load_chat_history("user_a@example.com", storage_dir=self.storage_dir), [])
        self.assertEqual(len(load_chat_history("user_b@example.com", storage_dir=self.storage_dir)), 2)


class TestCapybaraHistoryAPI(unittest.TestCase):
    """Kiểm thử API /api/capybara/history với 2 client độc lập đồng thời, OSError & race condition xóa."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.tmp_dir.name)
        self.auth_dir = self.storage_dir / "auth"
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.auth_dir / "users.json"

        self.orig_session = dict(CURRENT_SESSION)
        self.orig_tokens = dict(SESSION_TOKENS)
        CURRENT_SESSION["user_email"] = None
        CURRENT_SESSION["is_logged_in"] = False
        SESSION_TOKENS.clear()

        self.profiles: dict[str, dict] = {}

        def _load_profile(email):
            return self.profiles.get(email.strip().lower())

        def _save_profile(email, data):
            self.profiles[email.strip().lower()] = dict(data)

        self.patchers = [
            patch.object(auth_router, "USERS_FILE", self.users_file),
            patch.object(auth_router, "load_profile", side_effect=_load_profile),
            patch.object(auth_router, "save_profile", side_effect=_save_profile),
            patch.object(
                capybara_router,
                "respond_to_message",
                side_effect=lambda msg: CapybaraReply(
                    reply=f"Capy đã nhận: {msg} 🦫✨",
                    intent="INJURY_REPORT" if "đau" in msg.lower() else "QA_FITNESS_APP",
                    action="swap_exercise_for_injury" if "đau" in msg.lower() else None,
                    params={"joint": "knee"} if "đau" in msg.lower() else {},
                ),
            ),
            patch.object(
                capybara_router,
                "load_chat_history",
                side_effect=lambda email: load_chat_history(email, storage_dir=self.storage_dir),
            ),
            patch.object(
                capybara_router,
                "save_chat_history",
                side_effect=lambda email, msgs: save_chat_history(email, msgs, storage_dir=self.storage_dir),
            ),
            patch.object(
                capybara_router,
                "append_chat_exchange",
                side_effect=lambda email, msg, reply: append_chat_exchange(email, msg, reply, storage_dir=self.storage_dir),
            ),
            patch.object(
                capybara_router,
                "clear_chat_history",
                side_effect=lambda email: clear_chat_history(email, storage_dir=self.storage_dir),
            ),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        SESSION_TOKENS.clear()
        SESSION_TOKENS.update(self.orig_tokens)
        CURRENT_SESSION.clear()
        CURRENT_SESSION.update(self.orig_session)
        self.tmp_dir.cleanup()

    def test_unauthenticated_requests_cannot_read_write_or_delete_history(self):
        client = TestClient(app)
        res_get = client.get("/api/capybara/history")
        self.assertEqual(res_get.status_code, 200)
        self.assertFalse(res_get.json()["authenticated"])
        self.assertEqual(res_get.json()["messages"], [])

        res_post = client.post("/api/capybara/history", json={"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(res_post.status_code, 401)

        res_del = client.delete("/api/capybara/history")
        self.assertEqual(res_del.status_code, 401)

    def test_concurrent_clients_do_not_overwrite_each_other_or_delete_wrong_user(self):
        client_a = TestClient(app)
        client_b = TestClient(app)
        client_guest = TestClient(app)

        email_a = f"user_a_{uuid.uuid4().hex[:6]}@fitsense.vn"
        email_b = f"user_b_{uuid.uuid4().hex[:6]}@fitsense.vn"

        login_a = client_a.post("/api/auth/login", json={"email": email_a, "password": "Password123"})
        self.assertEqual(login_a.status_code, 200)
        token_a = login_a.json()["session_token"]

        # Client B logs in AFTER Client A in the same backend process
        login_b = client_b.post("/api/auth/login", json={"email": email_b, "password": "Password123"})
        self.assertEqual(login_b.status_code, 200)
        token_b = login_b.json()["session_token"]
        self.assertNotEqual(token_a, token_b)

        # Unauthenticated Client C must NOT inherit B's CURRENT_SESSION
        self.assertFalse(client_guest.get("/api/auth/me").json()["is_logged_in"])
        self.assertFalse(client_guest.get("/api/capybara/history").json()["authenticated"])
        self.assertEqual(client_guest.delete("/api/capybara/history").status_code, 401)

        # Client A sends a message AFTER Client B logged in -> must save strictly to User A
        chat_a = client_a.post("/api/capybara/chat", json={"message": "Tôi bị đau đầu gối khi squat"})
        self.assertEqual(chat_a.status_code, 200)
        self.assertTrue(chat_a.json()["persisted"])

        # Client B sends a different message -> must save strictly to User B
        chat_b = client_b.post("/api/capybara/chat", json={"message": "Xin mẹo chống đẩy cho User B"})
        self.assertEqual(chat_b.status_code, 200)
        self.assertTrue(chat_b.json()["persisted"])

        # Reload simulation for both clients concurrently
        hist_a = client_a.get("/api/capybara/history").json()
        hist_b = client_b.get("/api/capybara/history").json()
        self.assertEqual(len(hist_a["messages"]), 2)
        self.assertEqual(len(hist_b["messages"]), 2)
        self.assertIn("đau đầu gối", hist_a["messages"][0]["content"])
        self.assertIn("User B", hist_b["messages"][0]["content"])
        self.assertNotEqual(hist_a["user_key"], hist_b["user_key"])

        # Expected-user mismatch guard: if a stale delete for A arrives with B's session -> 409 Conflict!
        stale_delete = client_b.delete("/api/capybara/history", headers={"X-FitSense-User": email_a})
        self.assertEqual(stale_delete.status_code, 409)
        self.assertEqual(len(client_b.get("/api/capybara/history").json()["messages"]), 2)

        # Client A deletes its own history (with explicit session header) -> B remains untouched!
        del_a = client_a.delete(
            "/api/capybara/history",
            headers={"X-FitSense-Session": token_a, "X-FitSense-User": email_a},
        )
        self.assertEqual(del_a.status_code, 200)
        self.assertTrue(del_a.json()["cleared"])
        self.assertEqual(client_a.get("/api/capybara/history").json()["messages"], [])
        self.assertEqual(len(client_b.get("/api/capybara/history").json()["messages"]), 2)

        # Client A logs out -> Client B stays authenticated and keeps its history
        client_a.post("/api/auth/logout")
        self.assertFalse(client_a.get("/api/capybara/history").json()["authenticated"])
        self.assertTrue(client_b.get("/api/auth/me").json()["is_logged_in"])
        self.assertEqual(len(client_b.get("/api/capybara/history").json()["messages"]), 2)

    def test_os_errors_are_logged_and_surfaced_instead_of_silently_ignored(self):
        client = TestClient(app)
        email = f"io_err_{uuid.uuid4().hex[:6]}@fitsense.vn"
        client.post("/api/auth/login", json={"email": email, "password": "Password123"})

        with (
            patch.object(capybara_router, "append_chat_exchange", side_effect=OSError("disk full")),
            self.assertLogs("fitsense.capybara", level="ERROR") as logs,
        ):
            res_chat = client.post("/api/capybara/chat", json={"message": "Xin mẹo hít đất"})
        self.assertEqual(res_chat.status_code, 200)
        self.assertFalse(res_chat.json()["persisted"])
        self.assertIsNotNone(res_chat.json()["persistence_error"])
        self.assertTrue(any("Failed to persist Capybara chat exchange" in line for line in logs.output))

        with (
            patch.object(capybara_router, "save_chat_history", side_effect=OSError("read-only fs")),
            self.assertLogs("fitsense.capybara", level="ERROR") as logs,
        ):
            res_save = client.post("/api/capybara/history", json={"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(res_save.status_code, 500)
        self.assertIn("cục bộ", res_save.json()["detail"])
        self.assertTrue(any("Failed to save Capybara chat history" in line for line in logs.output))

        with (
            patch.object(capybara_router, "load_chat_history", side_effect=OSError("permission denied")),
            self.assertLogs("fitsense.capybara", level="ERROR") as logs,
        ):
            res_load = client.get("/api/capybara/history")
        self.assertEqual(res_load.status_code, 500)
        self.assertTrue(any("Failed to load Capybara chat history" in line for line in logs.output))

        with (
            patch.object(capybara_router, "clear_chat_history", side_effect=OSError("locked file")),
            self.assertLogs("fitsense.capybara", level="ERROR") as logs,
        ):
            res_del = client.delete("/api/capybara/history")
        self.assertEqual(res_del.status_code, 500)
        self.assertTrue(any("Failed to delete Capybara chat history" in line for line in logs.output))


class TestCapybaraFrontendStorageContract(unittest.TestCase):
    """Kiểm tra hợp đồng Frontend SCRUM-34: token per-client, hủy timer/abort khi đổi user, cảnh báo lỗi sync."""

    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_storage_module_and_async_fps_protection(self):
        storage_path = os.path.join(self.base_dir, "frontend", "js", "components", "capybara_storage.js")
        self.assertTrue(os.path.exists(storage_path))
        with open(storage_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("STORAGE_KEY_PREFIX", js)
        self.assertIn("fitsense_capy_chat_history", js)
        self.assertIn("normalizeUserKey", js)
        self.assertIn("cleanupLegacyGlobalKey", js)
        self.assertIn("cancelPendingSync", js)
        self.assertIn("AbortController", js)
        self.assertIn("onError", js)
        self.assertIn("scheduleAsyncSync", js)
        self.assertIn("requestIdleCallback", js)

    def test_chat_api_and_app_user_isolation_wiring(self):
        with open(os.path.join(self.base_dir, "frontend", "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        with open(os.path.join(self.base_dir, "frontend", "js", "api.js"), "r", encoding="utf-8") as f:
            api_js = f.read()
        with open(os.path.join(self.base_dir, "frontend", "js", "components", "capybara_chat.js"), "r", encoding="utf-8") as f:
            chat_js = f.read()
        with open(os.path.join(self.base_dir, "frontend", "js", "components", "toast.js"), "r", encoding="utf-8") as f:
            toast_js = f.read()
        with open(os.path.join(self.base_dir, "frontend", "js", "app.js"), "r", encoding="utf-8") as f:
            app_js = f.read()

        self.assertIn('id="capy-sync-status"', html)
        self.assertIn("X-FitSense-Session", api_js)
        self.assertIn("X-FitSense-User", api_js)
        self.assertIn("getSessionToken", api_js)
        self.assertIn("/api/capybara/history", api_js)

        self.assertIn("setSyncWarning", chat_js)
        self.assertIn("_isSessionStillBound", chat_js)
        self.assertIn("CapybaraStorage.cancelPendingSync()", chat_js)
        self.assertIn("Toast.warning", chat_js)
        self.assertIn("res.persisted === false", chat_js)
        self.assertIn("warning(msg)", toast_js)

        self.assertIn('Store.set("user", null)', app_js)
        self.assertIn("CapybaraChat.setActiveUser(null)", app_js)
        self.assertIn('Store.set("user", user)', app_js)
        self.assertIn("CapybaraChat.setActiveUser(user)", app_js)


if __name__ == "__main__":
    unittest.main()
