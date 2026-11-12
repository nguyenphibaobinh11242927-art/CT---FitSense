"""Deterministic workout set/rest transitions and real completion metrics.

Pure-Python state, independent of Streamlit. Timestamps are monotonic seconds.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkoutSession:
    total_sets: int = 3
    target_reps: int = 12
    rest_seconds: int = 60
    set_number: int = 1
    phase: str = "ready"  # ready, active, resting, paused, finished
    current_reps: int = 0
    completed_reps: list[int] = field(default_factory=list)
    rest_started: float | None = None
    paused_at: float | None = None
    paused_phase: str | None = None

    def __post_init__(self):
        if self.total_sets < 1 or self.target_reps < 1 or self.rest_seconds < 0:
            raise ValueError("Workout configuration must use positive sets/reps and nonnegative rest.")

    def start(self):
        if self.phase == "ready":
            self.phase = "active"

    def update_reps(self, reps: int):
        if self.phase == "active":
            self.current_reps = max(self.current_reps, max(0, int(reps)))

    def finish_set(self, now: float):
        if self.phase != "active":
            return False
        self.completed_reps.append(self.current_reps)
        self.current_reps = 0
        if self.set_number >= self.total_sets:
            self.phase = "finished"
        else:
            self.phase = "resting"
            self.rest_started = now
        return True

    def rest_remaining(self, now: float) -> float:
        if self.phase != "resting" or self.rest_started is None:
            return 0.0
        return max(0.0, self.rest_seconds - (now - self.rest_started))

    def resume_after_rest(self, now: float):
        if self.phase == "resting" and self.rest_remaining(now) <= 0:
            self.set_number += 1
            self.rest_started = None
            self.phase = "active"
            return True
        return False

    def pause(self, now: float):
        if self.phase not in {"active", "resting"}:
            return False
        self.paused_phase = self.phase
        self.paused_at = now
        self.phase = "paused"
        return True

    def resume(self, now: float):
        if self.phase != "paused":
            return False
        if self.paused_phase == "resting" and self.rest_started is not None and self.paused_at is not None:
            self.rest_started += max(0.0, now - self.paused_at)
        self.phase = self.paused_phase or "active"
        self.paused_at = None
        self.paused_phase = None
        return True

    def end_early(self):
        if self.phase == "finished":
            return
        if self.phase in {"active", "paused"} and (self.current_reps > 0):
            self.completed_reps.append(self.current_reps)
        self.current_reps = 0
        self.phase = "finished"

    @property
    def total_reps(self):
        return sum(self.completed_reps)

    @property
    def completion_percent(self):
        planned = self.total_sets * self.target_reps
        return min(100.0, round(100 * self.total_reps / planned, 1))

    def summary(self):
        return {
            "completed_reps": self.total_reps,
            "planned_reps": self.total_sets * self.target_reps,
            "completion_rate": self.completion_percent,
            "sets_completed": len(self.completed_reps),
            "sets_planned": self.total_sets,
        }
