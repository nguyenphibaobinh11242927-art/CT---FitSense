import unittest

from src.fsm_rep_counter import RepCounterFSM


class RepCounterFSMTests(unittest.TestCase):
    """Kiểm tra bộ đếm squat."""
    def test_10_complete_reps(self):
        """Chỉ tăng số lần sau khi hoàn thành đủ một chu kỳ squat."""
        counter = RepCounterFSM()
        squat_angles = (170, 145, 90, 120, 165)

        for _ in range(10):
            for angle in squat_angles:
                result = counter.update(angle)

        self.assertEqual(result["rep_count"], 10)
        self.assertEqual(result["state"], RepCounterFSM.STATE_UP)

    def test_incomplete_reps(self):
        """Squat chưa đạt độ sâu yêu cầu thì không được tính."""
        counter = RepCounterFSM()
        counter.update(170)
        counter.update(120)

        result = counter.update(165)
        self.assertEqual(result["rep_count"], 0)
        self.assertFalse(result["rep_incremented"])

    def test_preserve_missing_data(self):
        """Không có góc gối thì bộ đếm không đổi trạng thái."""
        counter = RepCounterFSM()
        counter.update(140)

        result = counter.update(None)
        self.assertEqual(result["state"], RepCounterFSM.STATE_GOING_DOWN)
        self.assertEqual(result["rep_count"], 0)

    def test_reset_counter(self):
        """Reset đưa số lần và trạng thái về ban đầu."""
        counter = RepCounterFSM()
        for angle in (170, 145, 90, 120, 165): counter.update(angle)

        counter.reset()
        self.assertEqual(counter.rep_count, 0)
        self.assertEqual(counter.state, RepCounterFSM.STATE_UP)

    def test_rejects_invalid_threshold_order(self):
        """Thứ tự ngưỡng sai phải báo lỗi."""
        with self.assertRaises(ValueError):
            RepCounterFSM(down_thresh = 110, going_up_thresh = 100)


if __name__ == "__main__":
    unittest.main()