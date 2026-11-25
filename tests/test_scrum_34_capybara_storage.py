"""Unit and integration tests for SCRUM-34: Capybara Chat Persistence, User Isolation & FPS-Safe Sync."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.routers.auth import CURRENT_SESSION
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
    """Kiểm thử API /api/capybara/history và phân lập tài khoản qua FastAPI TestClient."""

    def setUp(self):
        self.client = TestClient(app)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.tmp_dir.name)
        self.orig_session = dict(CURRENT_SESSION)
        CURRENT_SESSION["user_email"] = None
        CURRENT_SESSION["is_logged_in"] = False

        self.patchers = [
            patch.object(
                capybara_router,
                "respond_to_message",
                side_effect=lambda msg: CapybaraReply(
                    reply=f"Capy đã nhận: {msg} 🦫✨",
                    intent="INJURY_REPORT" if "đau" in msg.lower() else "QA_FITNESS_APP",
                    action="swap_exercise_for_injury" if "đau" in msg.lower() else None,
                    params={"joint": "knee"} if "đau" in msg.lower() else {},
                    source="rule_based",
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
        CURRENT_SESSION.clear()
        CURRENT_SESSION.update(self.orig_session)
        self.tmp_dir.cleanup()

    def test_unauthenticated_requests_cannot_read_or_write_history(self):
        res_get = self.client.get("/api/capybara/history")
        self.assertEqual(res_get.status_code, 200)
        self.assertFalse(res_get.json()["authenticated"])
        self.assertEqual(res_get.json()["messages"], [])

        res_post = self.client.post("/api/capybara/history", json={"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(res_post.status_code, 401)

    def test_chat_persists_across_reload_and_isolates_between_users(self):
        # User A logs in and chats
        CURRENT_SESSION["user_email"] = "user.a@fitsense.vn"
        CURRENT_SESSION["is_logged_in"] = True

        chat_res = self.client.post("/api/capybara/chat", json={"message": "Tôi bị đau đầu gối khi squat"})
        self.assertEqual(chat_res.status_code, 200)

        # Simulate F5 reload for User A
        hist_a = self.client.get("/api/capybara/history").json()
        self.assertTrue(hist_a["authenticated"])
        self.assertEqual(len(hist_a["messages"]), 2)
        self.assertIn("đau đầu gối", hist_a["messages"][0]["content"])

        # User A logs out -> User B logs in
        CURRENT_SESSION["user_email"] = "user.b@fitsense.vn"
        CURRENT_SESSION["is_logged_in"] = True

        hist_b = self.client.get("/api/capybara/history").json()
        self.assertTrue(hist_b["authenticated"])
        self.assertEqual(hist_b["messages"], [])

        # User B saves custom history
        save_b = self.client.post(
            "/api/capybara/history",
            json={"messages": [{"role": "user", "content": "Lịch tập của User B", "time": "17:00"}]},
        )
        self.assertEqual(save_b.status_code, 200)
        self.assertEqual(save_b.json()["count"], 1)

        # Switch back to User A: User A still sees only User A's messages
        CURRENT_SESSION["user_email"] = "user.a@fitsense.vn"
        hist_a_again = self.client.get("/api/capybara/history").json()
        self.assertEqual(len(hist_a_again["messages"]), 2)
        self.assertTrue(all("User B" not in m["content"] for m in hist_a_again["messages"]))

        # Delete User A history -> User B remains untouched
        del_a = self.client.delete("/api/capybara/history")
        self.assertEqual(del_a.status_code, 200)
        self.assertTrue(del_a.json()["cleared"])
        self.assertEqual(self.client.get("/api/capybara/history").json()["messages"], [])

        CURRENT_SESSION["user_email"] = "user.b@fitsense.vn"
        self.assertEqual(len(self.client.get("/api/capybara/history").json()["messages"]), 1)


class TestCapybaraFrontendStorageContract(unittest.TestCase):
    """Kiểm tra hợp đồng Frontend SCRUM-34: localStorage theo user, xóa khi logout, async không chặn FPS."""

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
        self.assertIn("scheduleAsyncSync", js)
        self.assertIn("requestIdleCallback", js)

    def test_chat_api_and_app_user_isolation_wiring(self):
        with open(os.path.join(self.base_dir, "frontend", "js", "api.js"), "r", encoding="utf-8") as f:
            api_js = f.read()
        with open(os.path.join(self.base_dir, "frontend", "js", "components", "capybara_chat.js"), "r", encoding="utf-8") as f:
            chat_js = f.read()
        with open(os.path.join(self.base_dir, "frontend", "js", "app.js"), "r", encoding="utf-8") as f:
            app_js = f.read()

        self.assertIn("/api/capybara/history", api_js)
        self.assertIn("getHistory", api_js)
        self.assertIn("saveHistory", api_js)
        self.assertIn("clearHistory", api_js)

        self.assertIn("setActiveUser", chat_js)
        self.assertIn('Store.subscribe("user"', chat_js)
        self.assertIn("CapybaraStorage.cleanupLegacyGlobalKey()", chat_js)

        self.assertIn('Store.set("user", null)', app_js)
        self.assertIn("CapybaraChat.setActiveUser(null)", app_js)
        self.assertIn('Store.set("user", user)', app_js)
        self.assertIn("CapybaraChat.setActiveUser(user)", app_js)


if __name__ == "__main__":
    unittest.main()
