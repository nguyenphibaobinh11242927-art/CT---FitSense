import json
import unittest
from unittest.mock import Mock

from jsonschema import Draft202012Validator

from src.workout_planner import (
    GOALS,
    WEEKLY_PLAN_SCHEMA,
    Exercise,
    WorkoutPlanError,
    generate_workout_plan,
)


class WorkoutPlannerTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {
            "first": Exercise("Bài A", ()),
            "second": Exercise("Bài B", (), ("mat",)),
            "wrist_only": Exercise("Bài C", ("wrist",)),
            "knee_only": Exercise("Bài D", ("knee",)),
            "needs_bar": Exercise("Bài E", (), ("bar",)),
        }

    def generate(self, complete, **overrides):
        profile = {
            "goal": "endurance",
            "experience_level": "beginner",
            "injury_regions": ("wrist", "knee"),
            "available_equipment": ("mat",),
            "catalog": self.catalog,
        }
        return generate_workout_plan(complete=complete, **(profile | overrides))

    def plan(self, goal="endurance"):
        days = [{"day": day, "exercises": []} for day in range(1, 8)]
        dosage = {"sets": 2, "reps": 4, "hold_seconds": 0, "rest_seconds": 30}
        days[0]["exercises"] = [{
            "exercise_id": "first",
            **dosage,
            "alternative": {"exercise_id": "second", **dosage, "hold_seconds": 10},
        }]
        return {"goal": goal, "days": days}

    def test_supported_goals_and_filtered_prompt(self):
        Draft202012Validator.check_schema(WEEKLY_PLAN_SCHEMA)
        for goal, label in GOALS.items():
            with self.subTest(goal=goal):
                plan = self.plan(goal)
                complete = Mock(return_value=json.dumps(plan))
                self.assertEqual(self.generate(complete, goal=goal), plan)
                complete.assert_called_once()
                prompt_data = json.loads(complete.call_args.args[0].split("\n", 1)[1])
                self.assertEqual(prompt_data["goal"], goal)
                self.assertEqual(prompt_data["goal_label"], label)
                self.assertEqual(prompt_data["experience_level"], "beginner")
                self.assertEqual(prompt_data["eligible_exercises"], {"first": "Bài A", "second": "Bài B"})
                self.assertEqual(prompt_data["response_schema"], WEEKLY_PLAN_SCHEMA)

    def test_checks_both_exercise_ids_against_the_filtered_catalog(self):
        for forbidden in ("wrist_only", "knee_only", "needs_bar", "invented"):
            for role in ("primary", "alternative"):
                with self.subTest(forbidden=forbidden, role=role):
                    plan = self.plan()
                    exercise = plan["days"][0]["exercises"][0]
                    target = exercise if role == "primary" else exercise["alternative"]
                    target["exercise_id"] = forbidden
                    with self.assertRaises(WorkoutPlanError):
                        self.generate(lambda _: json.dumps(plan))

    def test_validates_alternative_shape(self):
        plan = self.plan()
        exercise = plan["days"][0]["exercises"][0]
        exercise["alternative"]["exercise_id"] = "first"
        with self.assertRaisesRegex(WorkoutPlanError, "thay thế"):
            self.generate(lambda _: json.dumps(plan))
        exercise["alternative"] = None
        self.assertEqual(self.generate(lambda _: json.dumps(plan)), plan)
        del exercise["alternative"]
        with self.assertRaisesRegex(WorkoutPlanError, "sai cấu trúc"):
            self.generate(lambda _: json.dumps(plan))

    def test_rejects_invalid_json_and_dosage(self):
        for response in ("```json\n{}\n```", '{"goal":"endurance","goal":"fat_loss"}'):
            with self.subTest(response=response), self.assertRaisesRegex(WorkoutPlanError, "không phải JSON"):
                self.generate(lambda _: response)
        for field, value in (("sets", True), ("reps", 0), ("rest_seconds", -1), ("hold_seconds", 1.5)):
            with self.subTest(field=field), self.assertRaises(WorkoutPlanError):
                plan = self.plan()
                plan["days"][0]["exercises"][0][field] = value
                self.generate(lambda _: json.dumps(plan))

    def test_rejects_wrong_goal_incomplete_week_duplicate_day_and_all_rest(self):
        with self.assertRaisesRegex(WorkoutPlanError, "không khớp"):
            self.generate(lambda _: json.dumps(self.plan("fat_loss")))
        for change in ("missing day", "duplicate day", "all rest"):
            with self.subTest(change=change), self.assertRaises(WorkoutPlanError):
                plan = self.plan()
                if change == "missing day":
                    plan["days"].pop()
                elif change == "duplicate day":
                    plan["days"][1]["day"] = 1
                else:
                    plan["days"][0]["exercises"].clear()
                self.generate(lambda _: json.dumps(plan))

    def test_stops_before_calling_ai_for_unknown_restrictions_or_no_candidates(self):
        complete = Mock()
        for overrides in (
            {"injury_regions": ("shoulder",)},
            {"injury_regions": "wrist"},
            {"catalog": {"invalid": Exercise("Mã sai", ("wrst",))}},
            {"catalog": {"blocked": self.catalog["wrist_only"]}},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(WorkoutPlanError):
                self.generate(complete, **overrides)
        complete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
