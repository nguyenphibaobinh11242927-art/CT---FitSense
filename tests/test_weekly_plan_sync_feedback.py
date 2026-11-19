"""Regression tests: Planner 'Tập ngay buổi này' luôn đồng bộ trạng thái."""
import unittest
from src.weekly_plan_sync import start_planned_day, finish_planned_day


class TestWeeklyPlanSync(unittest.TestCase):
    def setUp(self):
        self.plan = [
            {"day": "Thứ 2", "focus": "Ngực", "is_rest": False,
             "exercises": [{"name": "Push-up", "sets": 3, "reps": 12}]},
            {"day": "Thứ 3", "focus": "Chân", "is_rest": False,
             "exercises": [{"name": "Squat", "sets": 4, "reps": 15}]},
            {"day": "Thứ 4", "focus": "Nghỉ", "is_rest": True, "exercises": []},
        ]

    def test_start_marks_selected_day_and_preserves_original(self):
        new_plan, active = start_planned_day(self.plan, "Thứ 2")
        self.assertEqual(new_plan[0]["workout_status"], "in_progress")
        self.assertEqual(active["day"], "Thứ 2")
        self.assertEqual(active["exercises"], self.plan[0]["exercises"])
        self.assertNotIn("workout_status", self.plan[0])

    def test_switch_day_resets_previous_in_progress(self):
        started, _ = start_planned_day(self.plan, "Thứ 2")
        switched, _ = start_planned_day(started, "Thứ 3")
        self.assertEqual(switched[0]["workout_status"], "planned")
        self.assertEqual(switched[1]["workout_status"], "in_progress")

    def test_complete_updates_weekly_schedule_without_changing_exercises(self):
        started, _ = start_planned_day(self.plan, "Thứ 2")
        done = finish_planned_day(started, "Thứ 2", completed=True,
                                  actual_reps=27, finished_at="15:00 12/11/2026")
        self.assertEqual(done[0]["workout_status"], "completed")
        self.assertEqual(done[0]["workout_actual_reps"], 27)
        self.assertEqual(done[0]["workout_completed_at"], "15:00 12/11/2026")
        self.assertEqual(done[0]["exercises"], self.plan[0]["exercises"])
        self.assertEqual(started[0]["workout_status"], "in_progress")

    def test_abandoned_and_duplicate_finish(self):
        started, _ = start_planned_day(self.plan, "Thứ 2")
        abandoned = finish_planned_day(started, "Thứ 2", completed=False,
                                       actual_reps=7, finished_at="15:00")
        self.assertEqual(abandoned[0]["workout_status"], "abandoned")
        again = finish_planned_day(abandoned, "Thứ 2", completed=True,
                                  actual_reps=100, finished_at="16:00")
        self.assertEqual(again, abandoned)

    def test_rest_or_unknown_day_disallowed(self):
        with self.assertRaises(ValueError):
            start_planned_day(self.plan, "Thứ 4")
        with self.assertRaises(ValueError):
            start_planned_day(self.plan, "Chủ Nhật")

    def test_restart_completed_day_clears_previous_result(self):
        started, _ = start_planned_day(self.plan, "Thứ 2")
        completed = finish_planned_day(started, "Thứ 2", completed=True,
                                       actual_reps=36, finished_at="14:00")
        restarted, _ = start_planned_day(completed, "Thứ 2")
        self.assertEqual(restarted[0]["workout_status"], "in_progress")
        self.assertNotIn("workout_completed_at", restarted[0])
        self.assertNotIn("workout_actual_reps", restarted[0])


if __name__ == "__main__":
    unittest.main()
