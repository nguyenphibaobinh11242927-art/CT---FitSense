import unittest

from streamlit.testing.v1 import AppTest


class SessionHandoffTests(unittest.TestCase):
    def test_closed_session_and_new_session(self):
        script = """
import streamlit as st
from src.session_view import render_session_view
from src.evaluation_view import render_evaluation_view
if st.session_state.get("pending_navigation"):
    render_evaluation_view()
else:
    render_session_view()
"""
        for click_pause in (False, True):
            with self.subTest(click_pause=click_pause):
                app = AppTest.from_string(script).run()
                session = app.session_state["workout_session"]
                session.ai_reps = 2
                if click_pause:
                    next(b for b in app.button if "Tạm ngưng" in b.label).click().run()
                    self.assertTrue(app.session_state["session_user_paused"])
                    self.assertEqual(app.session_state["paused_progress"]["reps"], 2)
                    next(b for b in app.button if "Tiếp tục" in b.label).click().run()
                    self.assertFalse(app.session_state["session_user_paused"])
                next(b for b in app.button if "Kết thúc" in b.label).click().run()
                self.assertFalse(app.exception)
                record = app.session_state["workout_results"][session.session_id]
                self.assertEqual((record["status"], record["reps"]), ("completed", 2))
                app.session_state["pending_navigation"] = None
                app.run()
                next(b for b in app.button if b.label == "Bắt đầu buổi mới").click().run()
                fresh = app.session_state["workout_session"]
                self.assertNotEqual(fresh.session_id, session.session_id)
                self.assertEqual(fresh.ai_reps, 0)
                self.assertEqual(record["reps"], 2)
