"""Bộ máy trạng thái hữu hạn (FSM) đếm số lần squat hoàn chỉnh."""
from typing import TypedDict


class RepCounterResult(TypedDict):
    rep_count: int
    state: str
    rep_incremented: bool


class RepCounterFSM:
    STATE_UP = "STATE_UP"
    STATE_GOING_DOWN = "STATE_GOING_DOWN"
    STATE_DOWN = "STATE_DOWN"
    STATE_GOING_UP = "STATE_GOING_UP"

    def __init__(
        self,
        up_thresh: float = 160.0,
        down_thresh: float = 90.0,
        going_down_thresh: float = 150.0,
        going_up_thresh: float = 105.0,
    ) -> None:
        if not 0 <= down_thresh < going_up_thresh < going_down_thresh < up_thresh <= 180:
            raise ValueError(
                "Ngưỡng góc phải thỏa mãn: 0 <= xuống < bắt đầu đứng lên "
                "< bắt đầu hạ xuống < đứng thẳng <= 180."
            )

        self.up_thresh = up_thresh
        self.down_thresh = down_thresh
        self.going_down_thresh = going_down_thresh
        self.going_up_thresh = going_up_thresh
        self.state = self.STATE_UP
        self.rep_count = 0

    def update(self, angle: float | None) -> RepCounterResult:
        """Nhận góc gối của một khung hình và đếm squat hoàn chỉnh."""
        rep_incremented = False
        if angle is None: return self._result(rep_incremented)
        if not 0 <= angle <= 180: raise ValueError("Góc phải nằm trong khoảng từ 0 đến 180 độ.")

        if self.state == self.STATE_UP:
            if angle < self.going_down_thresh: self.state = self.STATE_GOING_DOWN
        elif self.state == self.STATE_GOING_DOWN:
            if angle <= self.down_thresh: self.state = self.STATE_DOWN
            elif angle >= self.up_thresh: self.state = self.STATE_UP
        elif self.state == self.STATE_DOWN:
            if angle > self.going_up_thresh: self.state = self.STATE_GOING_UP
        elif self.state == self.STATE_GOING_UP:
            if angle >= self.up_thresh:
                self.state = self.STATE_UP
                self.rep_count += 1
                rep_incremented = True
            elif angle <= self.down_thresh: self.state = self.STATE_DOWN

        return self._result(rep_incremented)

    def reset(self) -> None:
        """Đặt lại bộ đếm để bắt đầu phiên mới."""
        self.state = self.STATE_UP
        self.rep_count = 0

    def _result(self, rep_incremented: bool) -> RepCounterResult:
        return {
            "rep_count": self.rep_count,
            "state": self.state,
            "rep_incremented": rep_incremented,
        }