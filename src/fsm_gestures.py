"""FSM nhận diện cử chỉ bắt đầu và kết thúc hiệp bằng thời gian thực."""
import math
from typing import TypedDict


class GestureResult(TypedDict):
    state: str
    active_ms: float
    progress: float
    triggered: bool


class StopGestureResult(GestureResult):
    session_state: str
    is_rep_locked: bool
    event: str | None


class _TimedGesture:
    def __init__(self, hold_ms: int, grace_ms: int) -> None:
        if hold_ms <= 0 or grace_ms < 0:
            raise ValueError("Thời gian giữ phải dương và dung sai không được âm.")
        self.hold_ms = hold_ms
        self.grace_ms = grace_ms
        self.started_at: float | None = None
        self.last_detected_at: float | None = None
        self.lost_at: float | None = None
        self.triggered = False

    def update(self, detected: bool, now_ms: float) -> tuple[float, bool]:
        if not math.isfinite(now_ms):
            raise ValueError("Mốc thời gian phải là số hữu hạn.")

        just_triggered = False
        if detected:
            if self.started_at is None:
                self.started_at = now_ms
            elif self.lost_at is not None:
                gap = now_ms - self.lost_at
                if gap > self.grace_ms:
                    self.reset()
                    self.started_at = now_ms
                else:
                    self.started_at += gap
            self.last_detected_at = now_ms
            self.lost_at = None
            active_ms = now_ms - self.started_at
            if active_ms >= self.hold_ms and not self.triggered:
                self.triggered = True
                just_triggered = True
            return active_ms, just_triggered

        if self.started_at is None:
            return 0.0, False
        if self.lost_at is None:
            self.lost_at = now_ms
        if now_ms - self.lost_at > self.grace_ms:
            self.reset()
            return 0.0, False

        last_detected_at = (
            self.last_detected_at if self.last_detected_at is not None else now_ms
        )
        active_ms = last_detected_at - self.started_at
        return active_ms, False

    def reset(self) -> None:
        self.started_at = None
        self.last_detected_at = None
        self.lost_at = None
        self.triggered = False


class StartGestureFSM:
    STATE_STANDBY = "STATE_STANDBY"
    DETECTING_START = "DETECTING_START"
    START_EXERCISE = "START_EXERCISE"

    def __init__(self, hold_ms: int = 1500, grace_ms: int = 250) -> None:
        self.hold_ms = hold_ms
        self.grace_ms = grace_ms
        self._gesture = _TimedGesture(hold_ms, grace_ms)
        self.state = self.STATE_STANDBY
        self.active_ms = 0.0

    def check_hand_raised_condition(
        self, wrist_y: float, nose_y: float, body_height: float, shoulder_angle: float
    ) -> bool:
        """Kiểm tra tay giơ cao hơn đầu và vai mở đủ góc."""
        if body_height <= 0:
            return False
        return (
            wrist_y < nose_y - 0.15 * body_height
            and shoulder_angle >= 140.0
        )

    def update(self, is_detected: bool, now_ms: float) -> GestureResult:
        self.active_ms, triggered = self._gesture.update(is_detected, now_ms)
        if triggered:
            self.state = self.START_EXERCISE
        elif self._gesture.started_at is None:
            self.state = self.STATE_STANDBY
        else:
            self.state = self.DETECTING_START
        return {
            "state": self.state,
            "active_ms": self.active_ms,
            "progress": min(1.0, self.active_ms / self.hold_ms),
            "triggered": triggered,
        }

    def reset(self) -> None:
        self._gesture.reset()
        self.active_ms = 0.0
        self.state = self.STATE_STANDBY


class StopGestureFSM:
    STATE_NORMAL = "STATE_NORMAL"
    STATE_DETECTING_X = "DETECTING_X"
    END_SET = "END_SET"
    STATE_CONFIRMED_STOP = END_SET

    def __init__(
        self,
        hold_ms: int = 1500,
        grace_ms: int = 250,
        crossed_threshold: float = 0.15,
    ) -> None:
        if not 0 < crossed_threshold <= 1:
            raise ValueError("Ngưỡng cử chỉ chữ X phải nằm trong khoảng (0, 1].")
        self.hold_ms = hold_ms
        self.grace_ms = grace_ms
        self.crossed_threshold = crossed_threshold
        self._gesture = _TimedGesture(hold_ms, grace_ms)
        self.active_ms = 0.0
        self.state = self.STATE_NORMAL
        self.is_rep_locked = False

    def check_x_gesture_condition(
        self,
        wrist_l_x: float,
        wrist_r_x: float,
        wrist_l_y: float,
        wrist_r_y: float,
        shoulder_y: float,
        hip_y: float,
        body_width: float,
    ) -> bool:
        """Kiểm tra hai cổ tay ở vùng thân và đủ gần nhau để tạo chữ X."""
        if body_width <= 0 or shoulder_y >= hip_y:
            return False
        in_vertical_range = (
            shoulder_y < wrist_l_y < hip_y
            and shoulder_y < wrist_r_y < hip_y
        )
        wrists_are_crossed = (
            abs(wrist_l_x - wrist_r_x) < self.crossed_threshold * body_width
        )
        return in_vertical_range and wrists_are_crossed

    def update(
        self, is_detected: bool, head_visible: bool, now_ms: float
    ) -> StopGestureResult:
        if self.is_rep_locked:
            return self._result(False)

        self.active_ms, triggered = self._gesture.update(
            is_detected and head_visible, now_ms
        )
        if triggered:
            self.state = self.END_SET
            self.is_rep_locked = True
        elif self._gesture.started_at is None:
            self.state = self.STATE_NORMAL
        else:
            self.state = self.STATE_DETECTING_X
        return self._result(triggered)

    def reset(self) -> None:
        """Mở khóa và chuẩn bị FSM cho hiệp mới."""
        self._gesture.reset()
        self.active_ms = 0.0
        self.state = self.STATE_NORMAL
        self.is_rep_locked = False

    def _result(self, triggered: bool) -> StopGestureResult:
        return {
            "state": self.state,
            "session_state": self.state,
            "active_ms": self.active_ms,
            "progress": min(1.0, self.active_ms / self.hold_ms),
            "is_rep_locked": self.is_rep_locked,
            "triggered": triggered,
            "event": self.END_SET if triggered else None,
        }
