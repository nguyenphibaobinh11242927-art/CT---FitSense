"""Regression tests for camera model delivery and real workout state."""
import unittest
from pathlib import Path
from src.workout_session import WorkoutSession
from src.fsm_gestures import StopGestureFSM


class WorkoutSessionFeedbackTests(unittest.TestCase):
    def test_real_set_rest_next_set_and_metrics(self):
        session = WorkoutSession(total_sets=2, target_reps=10, rest_seconds=60)
        session.start()
        session.update_reps(7)
        self.assertTrue(session.finish_set(100))
        self.assertEqual(session.phase, "resting")
        self.assertEqual(session.rest_remaining(135), 25)
        self.assertFalse(session.resume_after_rest(150))
        self.assertTrue(session.resume_after_rest(160))
        self.assertEqual(session.set_number, 2)
        session.update_reps(10)
        session.finish_set(200)
        self.assertEqual(session.phase, "finished")
        self.assertEqual(session.total_reps, 17)
        self.assertEqual(session.completion_percent, 85)

    def test_pause_rest_excludes_paused_duration(self):
        session = WorkoutSession(total_sets=2, rest_seconds=60)
        session.start()
        session.finish_set(10)
        session.pause(20)
        session.resume(120)
        self.assertEqual(session.rest_remaining(120), 50)

    def test_finish_early_preserves_partial_progress(self):
        session = WorkoutSession(total_sets=3, target_reps=12)
        session.start()
        session.update_reps(5)
        session.end_early()
        self.assertEqual(session.total_reps, 5)
        self.assertEqual(session.phase, "finished")
        self.assertFalse(session.finish_set(123))

    def test_just_one_stop_trigger_per_set(self):
        gesture = StopGestureFSM(dropout_grace_ms=180)
        gesture.update(True, True, timestamp_ms=100)
        self.assertFalse(gesture.update(False, True, timestamp_ms=200)["triggered"])
        self.assertTrue(gesture.update(True, True, timestamp_ms=1600)["triggered"])
        self.assertFalse(gesture.update(True, True, timestamp_ms=1700)["triggered"])
        gesture.reset()
        self.assertFalse(gesture.is_rep_locked)

    def test_camera_model_not_in_json_arguments(self):
        base = Path(__file__).resolve().parents[1]
        session_py = (base / "src/session_view.py").read_text(encoding="utf-8")
        webcam_js = (base / "assets/webcam/webcam.mjs").read_text(encoding="utf-8")
        self.assertNotIn("webcam(model=", session_py)
        self.assertIn("modelAssetPath:", webcam_js)
        self.assertTrue((base / "assets/webcam/pose_landmarker_lite.task").is_file())


if __name__ == "__main__":
    unittest.main()
