import json
import unittest
from unittest.mock import patch

import streamlit as st

from streamlit.proto.WidgetStates_pb2 import WidgetStates
from streamlit.testing.v1 import AppTest

from src.fsm_gestures import StartGestureFSM, StopGestureFSM
from src.fsm_rep_counter import RepCounterFSM
from src.session_view import _handle_webcam_value, process_pose_frames


class SessionFsmIntegrationTests(unittest.TestCase):
    def setUp(self):
        st.session_state.clear()
        self.rep_fsm = RepCounterFSM()
        self.start_fsm = StartGestureFSM()
        self.stop_fsm = StopGestureFSM()

    @staticmethod
    def frame(
        now_ms, knee_angle=None, start_detected=False, x_detected=False,
        head_detected=True,
    ):
        return {
            "now_ms": now_ms,
            "knee_angle": knee_angle,
            "start_detected": start_detected,
            "x_detected": x_detected,
            "head_detected": head_detected,
        }

    def process(self, frames, session_started=False):
        return process_pose_frames(
            frames,
            self.rep_fsm,
            self.start_fsm,
            self.stop_fsm,
            session_started,
        )

    def test_start_requires_elapsed_time_then_counts_reps(self):
        start_frames = [
            self.frame(now, start_detected=True)
            for now in (0, 1000, 1500)
        ]
        session_started = self.process(start_frames)
        self.assertTrue(session_started)

        squat_angles = (170, 145, 90, 120, 165)
        squat_frames = [
            self.frame(1600 + index * 100, knee_angle=angle)
            for index, angle in enumerate(squat_angles * 3)
        ]
        self.process(squat_frames, session_started)
        self.assertEqual(self.rep_fsm.rep_count, 3)

    def test_x_ends_set_and_locks_rep_counter(self):
        frames = [
            self.frame(now, x_detected=True)
            for now in (0, 1000, 1500)
        ]
        self.process(frames, session_started=True)
        self.assertTrue(self.stop_fsm.is_rep_locked)
        self.assertEqual(self.stop_fsm.state, StopGestureFSM.END_SET)

        more_squats = [
            self.frame(1600 + index * 100, knee_angle=angle)
            for index, angle in enumerate((170, 145, 90, 120, 165))
        ]
        self.process(more_squats, session_started=True)
        self.assertEqual(self.rep_fsm.rep_count, 0)

    def test_rejects_invalid_frame_data(self):
        with self.assertRaises(ValueError):
            self.process([{
                "now_ms": 0,
                "knee_angle": 90,
                "start_detected": 1,
                "x_detected": False,
                "head_detected": True,
            }])

    def test_head_must_be_visible_for_end_set(self):
        frames = [
            self.frame(now, x_detected=True, head_detected=False)
            for now in (0, 1000, 2000)
        ]
        self.process(frames, session_started=True)
        self.assertFalse(self.stop_fsm.is_rep_locked)
        self.assertEqual(self.stop_fsm.active_ms, 0)

    def test_timestamp_is_required(self):
        with self.assertRaises(ValueError):
            self.process([{
                "start_detected": False,
                "x_detected": False,
                "head_detected": True,
            }])

    def test_end_set_event_is_exposed_once_for_rest_timer_integration(self):
        st.session_state["scrum16_session_id"] = "test-session"
        value = {
            "session_id": "test-session",
            "sequence": 1,
            "events": [{
                "type": "END_SET",
                "exercise_index": 0,
                "exercise_name": "Squat",
                "set_number": 1,
                "reps": 8,
                "rest_seconds": 45,
            }],
            "snapshot": {
                "phase": "RESTING",
                "exercise_index": 0,
                "set_number": 1,
                "sets_total": 3,
                "reps": 8,
                "tracking": True,
            },
        }

        with patch("src.session_view.time.time", return_value=1000):
            _handle_webcam_value(value)
        event = st.session_state["workout_control_event"]
        self.assertEqual(event["type"], "END_SET")
        self.assertEqual(event["reps"], 8)
        self.assertEqual(event["rest_seconds"], 45)
        self.assertEqual(len(st.session_state["scrum16_completed_sets"]), 1)
        self.assertEqual(st.session_state["scrum16_rest_timer"]["deadline"], 1045)

        _handle_webcam_value(value)
        self.assertEqual(len(st.session_state["scrum16_completed_sets"]), 1)

    def test_rest_complete_event_finishes_hud_countdown(self):
        st.session_state["scrum16_session_id"] = "test-session"
        st.session_state["scrum16_event_sequence"] = 1
        st.session_state["scrum16_rest_timer"] = {
            "status": "running",
            "duration_seconds": 45,
            "deadline": 1045,
            "set_number": 1,
            "reps": 8,
        }
        _handle_webcam_value({
            "session_id": "test-session",
            "sequence": 2,
            "events": [{"type": "REST_COMPLETE", "set_number": 2}],
            "snapshot": {
                "phase": "ACTIVE",
                "exercise_index": 0,
                "set_number": 2,
                "sets_total": 3,
                "reps": 0,
                "tracking": True,
            },
        })
        self.assertEqual(st.session_state["scrum16_rest_timer"]["status"], "complete")
        self.assertEqual(st.session_state["workout_control_event"]["type"], "REST_COMPLETE")

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
        self.assertEqual(slight_bend["events"], [])
        attempt = [self.frame(angle) for angle in (145, 115, 165)]
        self.assertEqual(send(attempt[:-1])["events"], [])
        self.assertTrue(send([self.frame(None)])["stopped"])
        self.assertEqual(session.status, "paused")
        self.assertEqual(send([self.frame(165)])["events"], [])
        with self.assertLogs("src.session_view", level="DEBUG") as logged:
            shallow = send([*attempt[:-1], self.frame(165) | {"captured_at": 123}, *attempt])
        self.assertEqual(shallow["events"], [
            {"kind": "shallow_squat", "captured_at": 123, "frame_sequence": shallow["sequence"] - 3},
            {"kind": "shallow_squat", "frame_sequence": shallow["sequence"]},
        ])
        self.assertEqual(len(logged.records), 2)
        rep = send([self.frame(angle) for angle in (145, 90, 120, 165)])
        self.assertEqual(rep["events"], [{"kind": "rep", "count": 1}])
        self.assertEqual(rep["session_id"], session.session_id)
        self.assertEqual(rep["stream_id"], "test-camera")
        self.assertEqual(session.ai_reps, 1)
        self.assertEqual(send([self.frame(165)], sequence=rep["sequence"]), rep)
        self.assertEqual(len(send(attempt)["events"]), 1)
        stopped = send([self.frame(x_detected=True)])
        self.assertTrue(stopped["stopped"])
        self.assertEqual(stopped["events"], [])
        self.assertEqual(send([self.frame(angle) for angle in (145, 90, 120, 165)])["events"], [])
        self.assertEqual(session.ai_reps, 1)


if __name__ == "__main__":
    unittest.main()
