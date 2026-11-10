import unittest

from src.session_view import PoseSession
from src.workout_session import finish_session, start_session


class PoseHandoffTests(unittest.TestCase):
    def test_batch_replay_tracking_loss_and_handoff(self):
        session = start_session()
        pose = PoseSession()
        squat = [170, 145, 90, 120, 165]
        angles = [170] * 45 + squat * 2 + [145, 90, None, 120, 165]
        frames = [
            dict(knee_angle=a, start_detected=i < 45, head_detected=a is not None, x_detected=False)
            for i, a in enumerate(angles)
        ]
        def deliver(samples, end):
            pose.consume(session, dict(session_id=session.session_id, sequence=end, frames=samples))

        deliver(frames[:-2], len(frames)-2)
        self.assertEqual((session.status, session.ai_reps), ("paused", 2))
        deliver(frames, len(frames))
        deliver(frames, len(frames))
        self.assertEqual((session.status, session.ai_reps), ("active", 2))
        cycle = [dict(frames[-1], knee_angle=a) for a in squat]
        deliver(cycle, len(frames)+5)
        self.assertEqual(session.ai_reps, 3)
        finish_session(session, "abandoned")
        deliver(cycle, len(frames)+10)
        self.assertEqual((session.status, session.ai_reps), ("abandoned", 3))
