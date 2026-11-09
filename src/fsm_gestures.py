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
    def __init__(self, required_frames: int = 45) -> None:
        if required_frames <= 0:
            raise ValueError("Số khung hình yêu cầu phải lớn hơn 0.")
        self.required_frames = required_frames
        self.active_frames = 0
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

    def update(self, is_detected: bool) -> GestureResult:
        triggered = False
        if is_detected:
            self.active_frames = min(self.active_frames + 1, self.required_frames)
            if self.active_frames == self.required_frames:
                self.state = "COUNTDOWN_321"
                triggered = self.active_frames == self.required_frames and not self._triggered
                self._triggered = True
            else:
                self.state = "DETECTING_START"
        else:
            self.state = "STATE_STANDBY"
            self.active_frames = 0
            self._triggered = False

        return {
            "state": self.state,
            "active_frames": self.active_frames,
            "progress": self.active_frames / self.required_frames,
            "triggered": triggered,
        }

    def reset(self) -> None:
        self.active_frames = 0
        self.state = "STATE_STANDBY"
        self._triggered = False


class StopGestureFSM:
    STATE_NORMAL = "STATE_NORMAL"
    STATE_DETECTING_X = "DETECTING_X"
    STATE_CONFIRMED_STOP = "CONFIRMED_STOP"

    def __init__(self, required_frames: int = 45) -> None:
        if required_frames <= 0:
            raise ValueError("Số khung hình yêu cầu phải lớn hơn 0.")
        self.required_frames = required_frames
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
        if body_width <= 0 or shoulder_y >= hip_y:
            return False
        in_vertical_range = (
            shoulder_y < wrist_l_y < hip_y and shoulder_y < wrist_r_y < hip_y
        )
        is_crossed = abs(wrist_l_x - wrist_r_x) < (0.08 * body_width)
        return in_vertical_range and is_crossed

    def update(self, is_detected: bool) -> StopGestureResult:
        triggered = False
        if self.state == self.STATE_CONFIRMED_STOP:
            return self._result()

        if is_detected:
            self.active_frames += 1
            if self.active_frames >= self.required_frames:
                self.active_frames = self.required_frames
                self.state = self.STATE_CONFIRMED_STOP
                self.is_rep_locked = True
                triggered = True
            else:
                self.state = self.STATE_DETECTING_X
        else:
            self.state = self.STATE_NORMAL
            self.active_frames = 0

        return self._result(triggered)

    def reset(self) -> None:
        """Mở khóa số lần tập và xóa tiến trình cử chỉ để bắt đầu phiên mới."""
        self.active_frames = 0
        self.state = self.STATE_NORMAL
        self.is_rep_locked = False

    def _result(self, triggered: bool = False) -> StopGestureResult:
        return {
            "state": self.state,
            "session_state": self.state,
            "active_frames": self.active_frames,
            "progress": self.active_frames / self.required_frames,
            "is_rep_locked": self.is_rep_locked,
            "triggered": triggered,
        }
