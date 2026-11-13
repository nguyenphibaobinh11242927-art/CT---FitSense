"""FSM nhận diện giơ tay để bắt đầu và cử chỉ chữ X để dừng."""

import math
from typing import TypedDict


class GestureResult(TypedDict):
    state: str
    active_frames: int
    progress: float
    triggered: bool


class StopGestureResult(GestureResult):
    session_state: str
    is_rep_locked: bool


class _TimedGesture:
    def __init__(self, hold_ms: int, grace_ms: int) -> None:
        if hold_ms <= 0 or grace_ms < 0:
            raise ValueError("Thời gian giữ phải dương và dung sai không được âm.")
        self.hold_ms = hold_ms
        self.grace_ms = grace_ms
        self.reset()

    def update(self, detected: bool, now_ms: float) -> tuple[float, bool, bool]:
        if not math.isfinite(now_ms):
            raise ValueError("Mốc thời gian phải là số hữu hạn.")
        if self.last_update_at is not None and now_ms < self.last_update_at:
            raise ValueError("Mốc thời gian không được đi lùi.")
        self.last_update_at = now_ms

        if detected:
            if self.started_at is None:
                self.started_at = now_ms
            elif self.lost_at is not None:
                assert self.last_detected_at is not None
                gap = now_ms - self.last_detected_at
                if gap > self.grace_ms:
                    self.reset()
                    self.last_update_at = now_ms
                    self.started_at = now_ms
                else:
                    self.started_at += gap
            self.last_detected_at = now_ms
            self.lost_at = None
            active_ms = now_ms - self.started_at
            triggered = active_ms >= self.hold_ms and not self.triggered
            self.triggered = self.triggered or triggered
            return active_ms, triggered, True

        if self.started_at is None:
            return 0.0, False, False
        assert self.last_detected_at is not None
        if self.lost_at is None:
            self.lost_at = now_ms
        if now_ms - self.last_detected_at > self.grace_ms:
            self.reset()
            return 0.0, False, False
        return self.last_detected_at - self.started_at, False, True

    def reset(self) -> None:
        self.started_at: float | None = None
        self.last_detected_at: float | None = None
        self.last_update_at: float | None = None
        self.lost_at: float | None = None
        self.triggered = False


class StartGestureFSM:
    def __init__(
        self,
        required_frames: int = 45,
        *,
        hold_ms: int = 1500,
        grace_ms: int = 250,
    ) -> None:
        if required_frames <= 0:
            raise ValueError("Số khung hình yêu cầu phải lớn hơn 0.")
        self.required_frames = required_frames
        self.hold_ms = hold_ms
        self.grace_ms = grace_ms
        self._timed = _TimedGesture(hold_ms, grace_ms)
        self.active_frames = 0
        self.active_ms = 0.0
        self.state = "STATE_STANDBY"
        self._triggered = False

    def check_hand_raised_condition(
        self, wrist_y: float, nose_y: float, body_height: float, shoulder_angle: float
    ) -> bool:
        """Kiểm tra cổ tay có cao hơn đầu và vai có được nâng lên hay không."""
        if body_height <= 0:
            return False
        is_above_head = wrist_y < (nose_y - 0.15 * body_height)
        return is_above_head and shoulder_angle >= 140.0

    def update(self, is_detected: bool, now_ms: float | None = None) -> GestureResult:
        if now_ms is None:
            self._timed.reset()
            triggered = False
            if is_detected:
                self.active_frames = min(self.active_frames + 1, self.required_frames)
                if self.active_frames == self.required_frames:
                    self.state = "COUNTDOWN_321"
                    triggered = not self._triggered
                    self._triggered = True
                else:
                    self.state = "DETECTING_START"
            else:
                self.state = "STATE_STANDBY"
                self.active_frames = 0
                self._triggered = False
            self.active_ms = self.active_frames * self.hold_ms / self.required_frames
            return self._result(triggered)

        self.active_ms, triggered, active = self._timed.update(is_detected, now_ms)
        self.active_frames = min(
            self.required_frames,
            round(self.active_ms * self.required_frames / self.hold_ms),
        )
        if triggered:
            self.state = "COUNTDOWN_321"
            self._triggered = True
        elif active and self._triggered:
            self.state = "COUNTDOWN_321"
        elif active:
            self.state = "DETECTING_START"
        else:
            self.state = "STATE_STANDBY"
            self._triggered = False
        return self._result(triggered)

    def reset(self) -> None:
        self._timed.reset()
        self.active_frames = 0
        self.active_ms = 0.0
        self.state = "STATE_STANDBY"
        self._triggered = False

    def _result(self, triggered: bool) -> GestureResult:
        return {
            "state": self.state,
            "active_frames": self.active_frames,
            "progress": min(1.0, self.active_ms / self.hold_ms),
            "triggered": triggered,
        }


class StopGestureFSM:
    STATE_NORMAL = "STATE_NORMAL"
    STATE_DETECTING_X = "DETECTING_X"
    STATE_CONFIRMED_STOP = "CONFIRMED_STOP"

    def __init__(
        self,
        required_frames: int = 45,
        *,
        hold_ms: int = 1500,
        grace_ms: int = 250,
        crossed_threshold: float = 0.15,
    ) -> None:
        if required_frames <= 0:
            raise ValueError("Số khung hình yêu cầu phải lớn hơn 0.")
        if hold_ms <= 0 or grace_ms < 0:
            raise ValueError("Thời gian giữ phải dương và dung sai không được âm.")
        if not 0 < crossed_threshold <= 1:
            raise ValueError("Ngưỡng cử chỉ chữ X phải nằm trong khoảng (0, 1].")
        self.required_frames = required_frames
        self.hold_ms = hold_ms
        self.grace_ms = grace_ms
        self.crossed_threshold = crossed_threshold
        self._timed = _TimedGesture(hold_ms, grace_ms)
        self.active_frames = 0
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
        """Kiểm tra hai cổ tay có bắt chéo trước thân người hay không."""
        if body_width <= 0 or shoulder_y >= hip_y:
            return False
        in_vertical_range = (
            shoulder_y < wrist_l_y < hip_y and shoulder_y < wrist_r_y < hip_y
        )
        is_crossed = abs(wrist_l_x - wrist_r_x) < self.crossed_threshold * body_width
        return in_vertical_range and is_crossed

    def update(
        self,
        is_detected: bool,
        head_visible: bool,
        now_ms: float | None = None,
    ) -> StopGestureResult:
        """Chỉ đếm cử chỉ dừng khi nhìn thấy cả đầu và cử chỉ chữ X."""
        if self.state == self.STATE_CONFIRMED_STOP:
            return self._result()

        is_detected = is_detected and head_visible
        if now_ms is None:
            self._timed.reset()
            triggered = False
            if is_detected:
                self.active_frames = min(self.active_frames + 1, self.required_frames)
                if self.active_frames == self.required_frames:
                    self.state = self.STATE_CONFIRMED_STOP
                    self.is_rep_locked = True
                    triggered = True
                else:
                    self.state = self.STATE_DETECTING_X
            else:
                self.state = self.STATE_NORMAL
                self.active_frames = 0
                self.is_rep_locked = False
            self.active_ms = self.active_frames * self.hold_ms / self.required_frames
            return self._result(triggered)

        self.active_ms, triggered, active = self._timed.update(is_detected, now_ms)
        self.active_frames = min(
            self.required_frames,
            round(self.active_ms * self.required_frames / self.hold_ms),
        )
        if triggered:
            self.state = self.STATE_CONFIRMED_STOP
            self.is_rep_locked = True
        elif active:
            self.state = self.STATE_DETECTING_X
        else:
            self.state = self.STATE_NORMAL
            self.is_rep_locked = False
        return self._result(triggered)

    def reset(self) -> None:
        """Mở khóa số lần tập và xóa tiến trình cử chỉ để bắt đầu phiên mới."""
        self._timed.reset()
        self.active_frames = 0
        self.active_ms = 0.0
        self.state = self.STATE_NORMAL
        self.is_rep_locked = False

    def _result(self, triggered: bool = False) -> StopGestureResult:
        return {
            "state": self.state,
            "session_state": self.state,
            "active_frames": self.active_frames,
            "progress": min(1.0, self.active_ms / self.hold_ms),
            "is_rep_locked": self.is_rep_locked,
            "triggered": triggered,
        }
