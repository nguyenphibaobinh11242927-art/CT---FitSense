import unittest

from src.fsm_gestures import StartGestureFSM, StopGestureFSM


class StartGestureFSMTests(unittest.TestCase):
    """Kiểm tra cử chỉ bắt đầu buổi tập."""
    def test_start_gesture(self):
        """Chưa đủ 45 khung hình thì chưa xác nhận bắt đầu."""
        gesture = StartGestureFSM()

        for _ in range(44): result = gesture.update(True)
        self.assertFalse(result["triggered"])
        self.assertEqual(result["state"], "DETECTING_START")

        result = gesture.update(True)
        self.assertTrue(result["triggered"])
        self.assertEqual(result["state"], "COUNTDOWN_321")

    def test_triggers_once(self):
        """Giữ tay liên tục không kích hoạt lại nhiều lần."""
        gesture = StartGestureFSM(required_frames = 2)

        self.assertFalse(gesture.update(True)["triggered"])
        self.assertTrue(gesture.update(True)["triggered"])
        self.assertFalse(gesture.update(True)["triggered"])

    def test_reset_hand_lowered(self):
        """Hạ tay trước ngưỡng thì bộ đếm khung hình trở về 0."""
        gesture = StartGestureFSM(required_frames = 3)
        gesture.update(True)

        result = gesture.update(False)
        self.assertEqual(result["active_frames"], 0)
        self.assertEqual(result["state"], "STATE_STANDBY")

    def test_hand_height_validation(self):
        """Chỉ chấp nhận tư thế hợp lệ và chiều cao cơ thể dương."""
        gesture = StartGestureFSM()

        self.assertTrue(gesture.check_hand_raised_condition(20, 40, 100, 140))
        self.assertFalse(gesture.check_hand_raised_condition(20, 40, 0, 140))

    def test_timed_hold_uses_milliseconds_and_grace(self):
        gesture = StartGestureFSM()
        gesture.update(True, 0)
        gesture.update(True, 500)
        gesture.update(False, 550)
        resumed = gesture.update(True, 700)
        self.assertEqual(resumed["progress"], 500 / 1500)
        self.assertFalse(resumed["triggered"])
        self.assertTrue(gesture.update(True, 1700)["triggered"])

    def test_timed_hold_resets_after_grace_and_validates_timestamp_order(self):
        gesture = StartGestureFSM()
        gesture.update(True, 0)
        gesture.update(True, 500)
        gesture.update(False, 550)
        lost = gesture.update(False, 751)
        self.assertEqual(lost["active_frames"], 0)
        self.assertEqual(gesture.update(True, 800)["progress"], 0)
        with self.assertRaises(ValueError):
            gesture.update(True, 799)


class StopGestureFSMTests(unittest.TestCase):
    """Kiểm tra cử chỉ chữ X để dừng buổi tập."""
    def test_stop_gesture(self):
        """Đủ 45 khung hình liên tiếp thì xác nhận dừng."""
        gesture = StopGestureFSM()

        for _ in range(44): result = gesture.update(True, head_visible = True)
        self.assertFalse(result["is_rep_locked"])
        self.assertEqual(result["session_state"], "DETECTING_X")

        result = gesture.update(True, head_visible = True)
        self.assertTrue(result["triggered"])
        self.assertTrue(result["is_rep_locked"])
        self.assertEqual(result["session_state"], "CONFIRMED_STOP")
        self.assertEqual(result["progress"], 1.0)

    def test_restart_X_gone(self):
        """Mất cử chỉ trước ngưỡng thì bắt đầu đếm lại."""
        gesture = StopGestureFSM(required_frames = 3)
        gesture.update(True, head_visible = True)
        gesture.update(True, head_visible = True)

        result = gesture.update(False, head_visible = True)
        self.assertEqual(result["active_frames"], 0)
        self.assertFalse(result["is_rep_locked"])

    def test_reset_after_stop(self):
        """Sau khi dừng, chỉ reset phiên mới mở khóa số lần tập."""
        gesture = StopGestureFSM(required_frames = 1)
        gesture.update(True, head_visible = True)

        result = gesture.update(False, head_visible = True)
        self.assertTrue(result["is_rep_locked"])
        self.assertEqual(result["session_state"], "CONFIRMED_STOP")
        gesture.reset()
        self.assertFalse(gesture.is_rep_locked)

    def test_no_head_detected(self):
        """Không thấy phần đầu thì không đếm tiến trình cử chỉ dừng."""
        gesture = StopGestureFSM(required_frames = 2)

        result = gesture.update(True, head_visible = False)
        self.assertEqual(result["active_frames"], 0)
        self.assertFalse(result["is_rep_locked"])

    def test_x_gesture_validation(self):
        """Chỉ chấp nhận hai cổ tay gần nhau trong vùng thân người."""
        gesture = StopGestureFSM()

        self.assertTrue(gesture.check_x_gesture_condition(
            49, 51, 40, 42, 20, 80, 100
        ))
        self.assertTrue(gesture.check_x_gesture_condition(
            45, 55, 40, 42, 20, 80, 100
        ))
        self.assertFalse(gesture.check_x_gesture_condition(
            40, 60, 40, 42, 20, 80, 100
        ))

    def test_timed_x_hold_triggers_at_1500_ms(self):
        gesture = StopGestureFSM()
        self.assertFalse(gesture.update(True, True, 0)["triggered"])
        self.assertFalse(gesture.update(True, True, 1499)["triggered"])
        result = gesture.update(True, True, 1500)
        self.assertTrue(result["triggered"])
        self.assertEqual(result["progress"], 1.0)

    def test_timed_x_hold_preserves_short_gap_and_resets_long_gap(self):
        gesture = StopGestureFSM()
        gesture.update(True, True, 0)
        gesture.update(True, True, 500)
        gesture.update(False, True, 550)
        resumed = gesture.update(True, True, 700)
        self.assertEqual(resumed["progress"], 500 / 1500)
        self.assertFalse(resumed["triggered"])
        self.assertEqual(gesture.update(False, True, 951)["active_frames"], 0)


if __name__ == "__main__":
    unittest.main()