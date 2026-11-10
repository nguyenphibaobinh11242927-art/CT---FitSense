import json
import unittest

from streamlit.proto.WidgetStates_pb2 import WidgetStates
from streamlit.testing.v1 import AppTest

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

    def test_voice_feedback_reaches_webcam_on_the_same_rerun(self):
        app = AppTest.from_string("""
import streamlit as st
from src.fsm_gestures import StopGestureFSM
from src.session_view import PoseSession, render_session_view
from src.workout_session import start_session

if "workout_session" not in st.session_state:
    st.session_state["workout_session"] = start_session()
    st.session_state["pose_session"] = PoseSession(started=True, stop=StopGestureFSM(required_frames=1))
render_session_view()
""").run()
        component_id = app.get("component_instance")[0].proto.id
        session = app.session_state["workout_session"]

        def send(frames, sequence=None):
            if sequence is None:
                sequence = session.last_event_id + len(frames)
            states = WidgetStates()
            states.widgets.add(id=component_id, json_value=json.dumps({
                "session_id": session.session_id, "stream_id": "test-camera",
                "sequence": sequence, "frames": frames,
            }))
            app._run(states)
            self.assertFalse(app.exception)
            component = app.get("component_instance")[0].proto
            self.assertEqual(component.id, component_id)
            return json.loads(component.json_args)["voice_feedback"]

        slight_bend = send([self.frame(angle) for angle in (145, 165)] * 2)
        self.assertIsNone(slight_bend["event"])
        attempt = [self.frame(angle) for angle in (145, 115, 165)]
        self.assertIsNone(send(attempt)["event"])
        self.assertTrue(send([self.frame(None)])["stopped"])
        self.assertEqual(session.status, "paused")
        self.assertIsNone(send([self.frame(165), *attempt])["event"])
        shallow = send([*attempt[:-1], self.frame(165) | {"captured_at": 123}])
        self.assertEqual(shallow["event"], {"kind": "shallow_squat", "captured_at": 123})
        self.assertIsNone(send(attempt * 4)["event"])
        rep = send([self.frame(angle) for angle in (145, 90, 120, 165)])
        self.assertEqual(rep["event"], {"kind": "rep", "count": 1})
        self.assertEqual(rep["session_id"], session.session_id)
        self.assertEqual(rep["stream_id"], "test-camera")
        self.assertEqual(session.ai_reps, 1)
        self.assertEqual(send([self.frame(165)], sequence=rep["sequence"]), rep)
        self.assertIsNone(send(attempt)["event"])
        self.assertEqual(send(attempt)["event"], {"kind": "shallow_squat"})
        stopped = send([self.frame(x_detected=True)])
        self.assertTrue(stopped["stopped"])
        self.assertIsNone(stopped["event"])
        self.assertIsNone(send([self.frame(angle) for angle in (145, 90, 120, 165)])["event"])
        self.assertEqual(session.ai_reps, 1)


if __name__ == "__main__":
    unittest.main()
