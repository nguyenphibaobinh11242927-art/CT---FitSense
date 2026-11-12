"""FSM nhận diện giơ tay để bắt đầu và cử chỉ chữ X để dừng. """
from typing import TypedDict


class GestureResult(TypedDict):
    state: str
    active_frames: int
    progress: float
    triggered: bool


class StopGestureResult(GestureResult):
    session_state: str
    is_rep_locked: bool


class StartGestureFSM:
    def __init__(self, required_frames: int = 45, hold_seconds: float = 1.5) -> None:
        if required_frames <= 0:
            raise ValueError("Số khung hình yêu cầu phải lớn hơn 0.")
        self.required_frames = required_frames
        self.hold_seconds = hold_seconds
        self._hold_start_ms = None
        self._last_time_ms = None
        self.active_frames = 0
        self._hold_start_ms = None
        self.state = "STATE_STANDBY"
        self._triggered = False

    def check_hand_raised_condition(
        self, wrist_y: float, nose_y: float, body_height: float, shoulder_angle: float
    ) -> bool:
        """Kiểm tra cổ tay có cao hơn đầu và vai có được nâng lên hay không."""
        if body_height <= 0: return False
        is_above_head = wrist_y < (nose_y - 0.15 * body_height)
        return is_above_head and shoulder_angle >= 140.0

    def update(self, is_detected: bool, timestamp_ms: float | None = None) -> GestureResult:
        triggered = False
        if is_detected:
            self.active_frames = min(self.active_frames + 1, self.required_frames)
            if timestamp_ms is not None:
                if self._hold_start_ms is None:
                    self._hold_start_ms = timestamp_ms
                elapsed = max(0.0, (timestamp_ms - self._hold_start_ms) / 1000)
                completed = elapsed >= self.hold_seconds
            else:
                completed = self.active_frames == self.required_frames
            if completed:
                self.state = "COUNTDOWN_321"
                triggered = not self._triggered
                self._triggered = True
            else: self.state = "DETECTING_START"
        else:
            self.state = "STATE_STANDBY"
            self.active_frames = 0
            self._hold_start_ms = None
            self._triggered = False

        return {
            "state": self.state,
            "active_frames": self.active_frames,
            "progress": (min(1.0, max(0.0, (timestamp_ms - self._hold_start_ms) / (1000 * self.hold_seconds))) if timestamp_ms is not None and self._hold_start_ms is not None else self.active_frames / self.required_frames),
            "triggered": triggered,
        }

    def reset(self) -> None:
        self.active_frames = 0
        self._hold_start_ms = None
        self.state = "STATE_STANDBY"
        self._triggered = False


class StopGestureFSM:
    STATE_NORMAL = "STATE_NORMAL"
    STATE_DETECTING_X = "DETECTING_X"
    STATE_CONFIRMED_STOP = "CONFIRMED_STOP"

    def __init__(self, required_frames: int = 45, hold_seconds: float = 1.5,
                 dropout_grace_ms: float = 0.0) -> None:
        if required_frames <= 0 or hold_seconds <= 0 or dropout_grace_ms < 0:
            raise ValueError("Ngưỡng thời gian/khung hình không hợp lệ.")
        self.required_frames = required_frames
        self.hold_seconds = hold_seconds
        self.dropout_grace_ms = dropout_grace_ms
        self._hold_start_ms = None
        self._last_seen_ms = None
        self.active_frames = 0
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
        if body_width <= 0 or shoulder_y >= hip_y: return False
        in_vertical_range = (
            shoulder_y < wrist_l_y < hip_y and shoulder_y < wrist_r_y < hip_y
        )
        is_crossed = abs(wrist_l_x - wrist_r_x) < (0.35 * body_width)
        return in_vertical_range and is_crossed

    def update(self, is_detected: bool, head_visible: bool, timestamp_ms: float | None = None) -> StopGestureResult:
        """Chỉ đếm cử chỉ dừng khi nhìn thấy cả đầu và cử chỉ chữ X."""
        triggered = False
        if self.state == self.STATE_CONFIRMED_STOP: return self._result()

        is_detected = is_detected and head_visible
        if is_detected:
            if (timestamp_ms is not None and self._last_seen_ms is not None
                    and timestamp_ms < self._last_seen_ms):
                self.active_frames = 0
                self._hold_start_ms = None
            self.active_frames += 1
            if timestamp_ms is not None:
                self._last_seen_ms = timestamp_ms
                if self._hold_start_ms is None:
                    self._hold_start_ms = timestamp_ms
                completed = timestamp_ms - self._hold_start_ms >= 1000 * self.hold_seconds
            else:
                completed = self.active_frames >= self.required_frames
            if completed:
                self.active_frames = self.required_frames
                self.state = self.STATE_CONFIRMED_STOP
                self.is_rep_locked = True
                triggered = True
            else: self.state = self.STATE_DETECTING_X
        else:
            # During timestamped tracking, tolerate a brief detector dropout.
            grace = (timestamp_ms is not None and self._last_seen_ms is not None
                     and 0 <= timestamp_ms - self._last_seen_ms <= self.dropout_grace_ms)
            if not grace:
                self.state = self.STATE_NORMAL
                self.active_frames = 0
                self._hold_start_ms = None
                self._last_seen_ms = None

        return self._result(triggered, timestamp_ms)

    def reset(self) -> None:
        """Mở khóa số lần tập và xóa tiến trình cử chỉ để bắt đầu phiên mới."""
        self.active_frames = 0
        self._hold_start_ms = None
        self._last_seen_ms = None
        self.state = self.STATE_NORMAL
        self.is_rep_locked = False

    def _result(self, triggered: bool = False, timestamp_ms: float | None = None) -> StopGestureResult:
        return {
            "state": self.state,
            "session_state": self.state,
            "active_frames": self.active_frames,
            "progress": (min(1.0, max(0.0, (timestamp_ms - self._hold_start_ms) / (1000 * self.hold_seconds))) if timestamp_ms is not None and self._hold_start_ms is not None else self.active_frames / self.required_frames),
            "is_rep_locked": self.is_rep_locked,
            "triggered": triggered,
        }