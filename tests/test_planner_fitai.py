import json
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from src.exercise_library import load_catalog
from src.planner_generation import generate_ai_schedule
from src.workout_planner import WorkoutPlanError


class PlannerFitAITests(unittest.TestCase):
    def test_button_uses_fitai_and_keeps_the_schedule_on_api_error(self):
        days = [{"day": day, "exercises": []} for day in range(1, 8)]
        days[0]["exercises"].append({
            "exercise_id": "glute_bridge", "sets": 2, "reps": 10, "hold_seconds": 0, "rest_seconds": 30,
            "alternative": {"exercise_id": "dead_bug", "sets": 3, "reps": 6, "hold_seconds": 5, "rest_seconds": 45},
        })
        content = json.dumps({"goal": "endurance", "days": days})
        success = Mock(status_code=200, **{"json.return_value": {"choices": [{"message": {"content": content}}]}})
        failure = Mock(status_code=429)
        app = AppTest.from_string('''
import streamlit as st
from src.exercise_library import load_catalog
from src.planner_view import render_planner_view

if "weekly_schedule" not in st.session_state:
    st.session_state["weekly_schedule"] = []
    st.session_state["exercise_library"] = load_catalog()
    st.session_state["user_profile"] = {
        "name": "Họ tên riêng tư", "email": "private@example.com",
        "goal": "Sức bền & Tăng cơ Calisthenics", "fitness_level": "Beginner",
        "restrictions": ["Khớp gối yếu"], "equipment": ["Thảm yoga/thể dục"],
    }
render_planner_view()
''').run()

        def generate():
            next(button for button in app.button if "Tái lập Kế hoạch AI" in button.label).click().run()
            self.assertFalse(app.exception)

        with patch.dict("os.environ", {"FITAI_API_KEY": "test-key"}), patch(
            "src.school_ai.requests.post", side_effect=[success, failure],
        ) as post:
            generate()
            self.assertFalse(app.error)
            request = post.call_args
            self.assertEqual(request.args[0], "https://api-fit.hcmus.edu.vn/v1/chat/completions")
            self.assertEqual(request.kwargs["headers"], {"Authorization": "Bearer test-key", "User-Agent": "FitSense/1.0"})
            self.assertEqual(request.kwargs["json"]["model"], "Qwen-27B")
            prompt = request.kwargs["json"]["messages"][0]["content"]
            self.assertNotIn("private@example.com", prompt)
            self.assertNotIn("Họ tên riêng tư", prompt)
            eligible = json.loads(prompt.split("\n", 1)[1])["eligible_exercises"]
            self.assertNotIn("squat", eligible)
            self.assertNotIn("incline_push_up", eligible)
            self.assertIn("dead_bug", eligible)

            next(button for button in app.button if button.key == "apply_swap_0_0").click().run()
            schedule = app.session_state["weekly_schedule"]
            exercise = schedule[0]["exercises"][0]
            self.assertEqual(len(schedule), 7)
            self.assertEqual((exercise["sets"], exercise["reps"], exercise["hold_seconds"], exercise["rest_sec"]), (3, 6, 5, 45))

            generate()
            self.assertIn("giới hạn lượt gọi", app.error[0].value)
            self.assertEqual(app.session_state["weekly_schedule"], schedule)

    def test_unsupported_restriction_stops_before_api_call(self):
        complete = Mock()
        profile = {"fitness_level": "Beginner", "restrictions": ["Đau lưng dưới"]}
        with self.assertRaisesRegex(WorkoutPlanError, "hạn chế vận động"):
            generate_ai_schedule(profile, "endurance", load_catalog(), complete)
        complete.assert_not_called()
