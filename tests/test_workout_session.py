import unittest

from src.workout_session import apply_event, finish_session, start_session


class WorkoutSessionTests(unittest.TestCase):
    def setUp(self):
        self.session = start_session()

    def send(self, number, kind):
        apply_event(
            self.session,
            session_id=self.session.session_id,
            event_id=number,
            event_type=kind,
        )

    def test_duplicate_rep_is_counted_once(self):
        self.send(1, "rep_completed")
        self.send(1, "rep_completed")
        self.assertEqual(self.session.ai_reps, 1)

    def test_tracking_loss_pauses_counting(self):
        self.send(1, "tracking_lost")
        self.send(2, "rep_completed")
        self.assertEqual(self.session.status, "paused")
        self.assertEqual(self.session.ai_reps, 0)

    def test_tracking_restored_allows_next_rep(self):
        self.send(1, "tracking_lost")
        self.send(2, "tracking_restored")
        self.assertEqual(self.session.status, "active")
        self.assertEqual(self.session.ai_reps, 0)

        self.send(3, "rep_completed")
        self.assertEqual(self.session.ai_reps, 1)

    def test_finished_session_keeps_its_result(self):
        for outcome in ("completed", "abandoned"):
            with self.subTest(outcome=outcome):
                self.session = start_session()
                self.send(1, "rep_completed")
                finish_session(self.session, outcome)
                self.send(2, "rep_completed")
                self.assertEqual(self.session.ai_reps, 1)
                self.assertEqual(self.session.status, outcome)

    def test_event_from_previous_session_is_ignored(self):
        old_session = start_session()
        apply_event(
            self.session,
            session_id=old_session.session_id,
            event_id=1,
            event_type="rep_completed",
        )
        self.assertEqual(self.session.ai_reps, 0)