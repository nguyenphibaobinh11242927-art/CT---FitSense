import unittest

from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.fsm_rep_counter import RepCounterFSM
from src.session_view import process_pose_frames

class SessionFsmIntegrationTests(unittest.TestCase):
    """Kiểm tra luồng FSM nhận dữ liệu theo lô từ camera."""
    def setUp(self):
        self.rep_fsm = RepCounterFSM()
        self.start_fsm = StartGestureFSM()
        self.stop_fsm = StopGestureFSM()

    @staticmethod
    def frame(
        knee_angle=None, start_detected=False, x_detected=False, head_detected=True
    ):
        """Tạo một mẫu dữ liệu khung hình."""
        return {
            "knee_angle": knee_angle,
            "start_detected": start_detected,
            "x_detected": x_detected,
            "head_detected": head_detected,
        }

    def process(self, frames, session_started = False):
        """Chuyển các khung hình qua FSM và trả về trạng thái buổi tập."""
        return process_pose_frames(
            frames,
            self.rep_fsm,
            self.start_fsm,
            self.stop_fsm,
            session_started,
        )

    def test_start_gesture_cnt_reps(self):
        """Đủ cử chỉ bắt đầu rồi tập 10 squat thì bộ đếm ghi nhận đủ."""
        start_frames = [
            self.frame(start_detected = True)
            for _ in range(self.start_fsm.required_frames)
        ]
        session_started = self.process(start_frames)
        self.assertTrue(session_started)

        squat_angles = (170, 145, 90, 120, 165)
        squat_frames = [
            self.frame(knee_angle = angle)
            for _ in range(10)
            for angle in squat_angles
        ]
        self.process(squat_frames, session_started)
        self.assertEqual(self.rep_fsm.rep_count, 10)

    def test_locks_X(self):
        """Giữ chữ X đủ lâu thì không nhận thêm squat."""
        frames = [
            self.frame(x_detected = True)
            for _ in range(self.stop_fsm.required_frames)
        ]
        self.process(frames, session_started = True)
        self.assertTrue(self.stop_fsm.is_rep_locked)
        self.assertEqual(self.stop_fsm.state, StopGestureFSM.STATE_CONFIRMED_STOP)

        more_squats = [
            self.frame(knee_angle = angle)
            for angle in (170, 145, 90, 120, 165)
        ]
        self.process(more_squats, session_started = True)
        self.assertEqual(self.rep_fsm.rep_count, 0)

    def test_rejects_invalid_frame_data(self):
        """Dữ liệu cử chỉ không phải đúng/sai thì báo lỗi."""
        with self.assertRaises(ValueError):
            self.process([{
                "knee_angle": 90,
                "start_detected": 1,
                "x_detected": False,
                "head_detected": True,
            }])

    def test_no_head_detected(self):
        """Không thấy đầu thì cử chỉ chữ X không dừng buổi tập."""
        frames = [
            self.frame(x_detected = True, head_detected = False)
            for _ in range(self.stop_fsm.required_frames)
        ]
        self.process(frames, session_started = True)
        self.assertFalse(self.stop_fsm.is_rep_locked)
        self.assertEqual(self.stop_fsm.active_frames, 0)


if __name__ == "__main__":
    unittest.main()