import unittest

from src.fsm_gestures import StartGestureFSM, StopGestureFSM


class StartGestureFSMTests(unittest.TestCase):
    def test_start_requires_1500_ms_and_triggers_once(self):
        gesture = StartGestureFSM()
        self.assertFalse(gesture.update(True, 0)["triggered"])
        self.assertFalse(gesture.update(True, 1499)["triggered"])
        result = gesture.update(True, 1500)
        self.assertTrue(result["triggered"])
        self.assertEqual(result["state"], "START_EXERCISE")
        self.assertEqual(result["progress"], 1.0)
        self.assertFalse(gesture.update(True, 1600)["triggered"])

    def test_tracking_gap_within_grace_does_not_reset_progress(self):
        gesture = StartGestureFSM()
        gesture.update(True, 0)
        gesture.update(True, 600)
        gesture.update(False, 650)
        result = gesture.update(True, 850)
        self.assertEqual(result["active_ms"], 650)
        self.assertFalse(result["triggered"])
        self.assertTrue(gesture.update(True, 1700)["triggered"])

    def test_tracking_gap_over_grace_resets_progress(self):
        gesture = StartGestureFSM()
        gesture.update(True, 0)
        gesture.update(True, 600)
        gesture.update(False, 650)
        self.assertEqual(gesture.update(False, 901)["active_ms"], 0)
        result = gesture.update(True, 1000)
        self.assertEqual(result["active_ms"], 0)
        self.assertFalse(result["triggered"])

    def test_hand_height_validation(self):
        gesture = StartGestureFSM()
        self.assertTrue(gesture.check_hand_raised_condition(20, 40, 100, 140))
        self.assertFalse(gesture.check_hand_raised_condition(20, 40, 0, 140))
        self.assertFalse(gesture.check_hand_raised_condition(30, 40, 100, 140))


class StopGestureFSMTests(unittest.TestCase):
    def test_x_emits_end_set_after_1500_ms_and_locks_until_reset(self):
        gesture = StopGestureFSM()
        self.assertFalse(gesture.update(True, True, 0)["triggered"])
        self.assertFalse(gesture.update(True, True, 1499)["triggered"])
        result = gesture.update(True, True, 1500)
        self.assertTrue(result["triggered"])
        self.assertEqual(result["event"], "END_SET")
        self.assertEqual(result["session_state"], "END_SET")
        self.assertTrue(result["is_rep_locked"])
        self.assertFalse(gesture.update(True, True, 1600)["triggered"])

    def test_x_tracking_gap_within_grace_preserves_elapsed_hold(self):
        gesture = StopGestureFSM()
        gesture.update(True, True, 0)
        gesture.update(True, True, 600)
        gesture.update(False, True, 650)
        self.assertEqual(gesture.update(True, True, 850)["active_ms"], 650)
        self.assertTrue(gesture.update(True, True, 1700)["triggered"])

    def test_head_must_be_visible_and_reset_unlocks_next_set(self):
        gesture = StopGestureFSM(hold_ms=100)
        self.assertFalse(gesture.update(True, False, 0)["is_rep_locked"])
        self.assertFalse(gesture.update(True, True, 0)["triggered"])
        self.assertTrue(gesture.update(True, True, 100)["triggered"])
        gesture.reset()
        self.assertFalse(gesture.is_rep_locked)
        self.assertFalse(gesture.update(True, True, 200)["triggered"])

    def test_x_gesture_validation(self):
        gesture = StopGestureFSM()
        self.assertTrue(gesture.check_x_gesture_condition(49, 51, 40, 42, 20, 80, 100))
        self.assertFalse(gesture.check_x_gesture_condition(49, 51, 40, 42, 20, 80, 0))
        self.assertFalse(gesture.check_x_gesture_condition(40, 60, 40, 42, 20, 80, 100))


if __name__ == "__main__":
    unittest.main()
