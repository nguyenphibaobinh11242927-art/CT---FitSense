import unittest

from src.exercise_catalog import exercise_id, merge_catalog, replacement_options, swap_scheduled_exercise
from src.fsm_gestures import StartGestureFSM, StopGestureFSM


class TimeBasedGestureTests(unittest.TestCase):
    def test_start_at_slow_fps_is_one_point_five_seconds(self):
        gesture = StartGestureFSM()
        results = [gesture.update(True, timestamp_ms=t) for t in (0, 500, 1000, 1499, 1500, 1550)]
        self.assertEqual([r["triggered"] for r in results], [False, False, False, False, True, False])
        self.assertEqual(results[-1]["progress"], 1)

    def test_stop_at_high_fps_does_not_trigger_early(self):
        gesture = StopGestureFSM()
        for t in range(0, 1500, 20):
            result = gesture.update(True, True, timestamp_ms=t)
            self.assertFalse(result["triggered"])
        result = gesture.update(True, True, timestamp_ms=1500)
        self.assertTrue(result["triggered"])
        self.assertTrue(result["is_rep_locked"])
        self.assertFalse(gesture.update(True, True, timestamp_ms=1600)["triggered"])

    def test_releasing_early_cancels_x(self):
        gesture = StopGestureFSM()
        gesture.update(True, True, timestamp_ms=0)
        gesture.update(True, True, timestamp_ms=1200)
        self.assertEqual(gesture.update(False, True, timestamp_ms=1300)["progress"], 0)
        self.assertFalse(gesture.update(True, True, timestamp_ms=2000)["triggered"])
        self.assertFalse(gesture.update(True, True, timestamp_ms=3000)["triggered"])
        self.assertTrue(gesture.update(True, True, timestamp_ms=3500)["triggered"])

    def test_missing_head_resets_x(self):
        gesture = StopGestureFSM()
        gesture.update(True, True, timestamp_ms=0)
        gesture.update(True, False, timestamp_ms=1000)
        self.assertFalse(gesture.update(True, True, timestamp_ms=1500)["triggered"])


class LibraryReplacementTests(unittest.TestCase):
    def test_merge_and_swap_changes_schedule(self):
        library = [{"name": "Squat", "primary_muscle": "Đùi", "steps": ["Hạ người"]}]
        schedule = [{"exercises": [{"name": "Squat", "primary_muscle": "Đùi", "sets": 4, "reps": 12, "rest_sec": 45},
                                   {"name": "Glute Bridge", "primary_muscle": "Mông", "sets": 3, "reps": 15}]}]
        catalog = merge_catalog(library, schedule)
        self.assertEqual(len(catalog), 2)
        self.assertEqual(len(replacement_options(schedule[0]["exercises"][0], catalog)), 1)
        new = swap_scheduled_exercise(schedule, 0, 0, catalog[1])
        self.assertEqual(new["name"], "Glute Bridge")
        self.assertEqual(new["exercise_id"], exercise_id("Glute Bridge"))
        self.assertEqual(new["sets"], 4)
        self.assertEqual(new["reps"], 12)
        self.assertEqual(schedule[0]["exercises"][0]["name"], "Glute Bridge")


if __name__ == "__main__":
    unittest.main()
