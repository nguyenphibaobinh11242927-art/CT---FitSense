"""Detect a shallow squat once per completed attempt."""

from dataclasses import dataclass

from src.fsm_rep_counter import RepCounterFSM


SHALLOW_ATTEMPT_ANGLE = 135
SHALLOW_TRACKING_GRACE_FRAMES = 2


@dataclass
class SquatCorrection:
    deepest_angle: float | None = None
    missing_frames: int = 0

    @property
    def tracking_lost(self) -> bool:
        return self.missing_frames > SHALLOW_TRACKING_GRACE_FRAMES

    def interrupt_tracking(self) -> None:
        self.deepest_angle = None
        self.missing_frames = SHALLOW_TRACKING_GRACE_FRAMES + 1

    def update(self, angle: float | None, rep_fsm: RepCounterFSM) -> bool:
        if angle is None:
            if not self.tracking_lost:
                self.missing_frames += 1
                if self.tracking_lost:
                    self.interrupt_tracking()
            return False

        self.missing_frames = 0
        if angle >= rep_fsm.up_thresh:
            deepest_angle = self.deepest_angle
            self.deepest_angle = None
            return deepest_angle is not None and rep_fsm.down_thresh < deepest_angle <= SHALLOW_ATTEMPT_ANGLE

        # Keep the attempt through brief gaps while the rep FSM waits for an upright frame.
        if self.deepest_angle is not None:
            self.deepest_angle = min(self.deepest_angle, angle)
        elif rep_fsm.state == RepCounterFSM.STATE_GOING_DOWN:
            self.deepest_angle = angle
        return False
