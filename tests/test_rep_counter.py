import unittest
import pytest

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

    def test_tracking_loss_discards_partial_rep_and_preserves_total(self):
        squat = (170, 145, 90, 120, 165)
        for interruption in range(1, len(squat)):
            with self.subTest(interruption=interruption):
                counter = RepCounterFSM()
                for angle in squat * 2 + squat[:interruption]:
                    counter.update(angle)
                for angle in (None, None, 145, 90, 120, 165):
                    counter.update(angle)
                    self.assertEqual(counter.rep_count, 2)
                for angle in squat:
                    counter.update(angle)
                self.assertEqual(counter.rep_count, 3)

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





@pytest.mark.parametrize("depth, expected", [(89, 1), (90, 1), (91, 0)])
def test_scrum24_depth_boundary(depth, expected):
    counter = RepCounterFSM()
    for angle in (170, 145, depth, 120, 160):
        result = counter.update(angle)
    assert result["rep_count"] == expected


@pytest.mark.parametrize("angle", [-1, 181, float("nan")])
def test_scrum24_invalid_angle(angle):
    counter = RepCounterFSM()
    with pytest.raises(ValueError):
        counter.update(angle)
    assert counter.rep_count == 0


def test_scrum24_camera_absent_at_start():
    counter = RepCounterFSM()
    for angle in (None, None, 90, 120, 160):
        assert not counter.update(angle)["rep_incremented"]
    assert counter.rep_count == 0
    for angle in (145, 90, 120, 160):
        counter.update(angle)
    assert counter.rep_count == 1


if __name__ == "__main__":
    unittest.main()
