"""Pydantic schemas for the FitSense REST API."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class BMICalculationRequest(BaseModel):
    weight_kg: float = Field(..., ge=20, le=300, description="Cân nặng theo kg")
    height_cm: float = Field(..., ge=80, le=250, description="Chiều cao theo cm")


class BMICalculationResponse(BaseModel):
    bmi: float
    category: str
    healthy_weight_min: float
    healthy_weight_max: float
    description: str


class ProfileSchema(BaseModel):
    name: str = Field(default="FitSense User")
    email: Optional[str] = Field(default="user@fitsense.local")
    age: int = Field(default=22, ge=12, le=90)
    gender: str = Field(default="Nam")
    height_cm: float = Field(default=170.0, ge=100, le=230)
    weight_kg: float = Field(default=65.0, ge=30, le=200)
    days_per_week: int = Field(default=4, ge=2, le=6)
    session_duration_minutes: int = Field(default=45, ge=15, le=90)
    goal: str = Field(default="Tăng cơ & Sức mạnh")
    fitness_level: str = Field(default="Beginner (Người mới bắt đầu)")
    environment: str = Field(default="Tại nhà (Home Workout)")
    restrictions: list[str] = Field(default_factory=lambda: ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"])
    equipment: list[str] = Field(default_factory=lambda: ["Không có dụng cụ (Chỉ tập Bodyweight)"])


class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: str
    password: str = Field(..., min_length=6)
    age: Optional[int] = Field(default=22, ge=12, le=90)
    gender: Optional[str] = Field(default="Nam")
    height_cm: Optional[float] = Field(default=170.0, ge=100, le=230)
    weight_kg: Optional[float] = Field(default=65.0, ge=30, le=200)
    days_per_week: Optional[int] = Field(default=4, ge=2, le=6)
    session_duration_minutes: Optional[int] = Field(default=45, ge=15, le=90)
    goal: Optional[str] = Field(default="Tăng cơ & Sức mạnh")
    fitness_level: Optional[str] = Field(default="Beginner (Người mới bắt đầu)")
    environment: Optional[str] = Field(default="Tại nhà (Home Workout)")
    restrictions: Optional[list[str]] = Field(default_factory=lambda: ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"])
    equipment: Optional[list[str]] = Field(default_factory=lambda: ["Không có dụng cụ (Chỉ tập Bodyweight)"])


class GoogleAuthRequest(BaseModel):
    email: str
    name: Optional[str] = "Google Athlete"
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None


class GoogleCompleteRegistrationRequest(BaseModel):
    email: str
    name: str
    avatar_url: Optional[str] = None
    age: int = Field(default=22, ge=12, le=90)
    gender: str = Field(default="Nam")
    height_cm: float = Field(default=170.0, ge=100, le=230)
    weight_kg: float = Field(default=65.0, ge=30, le=200)
    days_per_week: int = Field(default=4, ge=2, le=6)
    session_duration_minutes: int = Field(default=45, ge=15, le=90)
    goal: str = Field(default="Tăng cơ & Sức mạnh")
    fitness_level: str = Field(default="Beginner (Người mới bắt đầu)")
    environment: str = Field(default="Tại nhà (Home Workout)")
    restrictions: list[str] = Field(default_factory=lambda: ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"])
    equipment: list[str] = Field(default_factory=lambda: ["Không có dụng cụ (Chỉ tập Bodyweight)"])


class ExerciseFilterQuery(BaseModel):
    query: str = ""
    muscle: str = ""
    role: str = "all"
    equipment: str = ""
    difficulty: str = ""
    category: str = ""


class PlanGenerationRequest(BaseModel):
    goal: Optional[str] = None
    fitness_level: Optional[str] = None
    use_ai: bool = True


class ExerciseSwapRequest(BaseModel):
    day: str
    current_exercise_id: str
    new_exercise_id: str
    exercise_index: Optional[int] = Field(default=None, ge=0)


class SessionStartRequest(BaseModel):
    exercise_id: str
    target_reps: int = Field(default=10, ge=1)
    day: Optional[str] = None
    exercise_list: Optional[list[dict[str, Any]]] = None
    total_sets: Optional[int] = 3
    current_set: Optional[int] = 1
    exercise_index: int = Field(default=0, ge=0)
    mode: Literal["ai", "manual"] = "ai"


class SessionSwitchExerciseRequest(BaseModel):
    session_id: str
    exercise_id: str
    exercise_name: Optional[str] = None
    target_reps: int = Field(default=10, ge=1)
    current_set: int = Field(default=1, ge=1)
    total_sets: int = Field(default=3, ge=1)
    exercise_index: Optional[int] = Field(default=None, ge=0)


class FSMRepRequest(BaseModel):
    session_id: str
    angle: Optional[float] = None
    landmark_type: str = "knee"  # 'knee' for squat, 'elbow' for pushup
    tracking_interrupted: bool = False
    current_set: Optional[int] = Field(default=None, ge=1)
    exercise_index: Optional[int] = Field(default=None, ge=0)
    frame_id: Optional[int] = Field(default=None, ge=1)


class SessionPauseRequest(BaseModel):
    session_id: str
    paused: bool


class SessionFinishRequest(BaseModel):
    session_id: str
    exercise_id: str
    completed_reps: int = Field(default=0, ge=0)
    duration_seconds: int = Field(..., ge=0)
    rpe: int = Field(default=7, ge=1, le=10)
    feedback_notes: Optional[str] = None
    day: Optional[str] = None
    target_reps: Optional[int] = None
    outcome: Literal["completed", "abandoned"] = "completed"


class PlanUploadRequest(BaseModel):
    content: str
    filename: str


class DayUpdateRequest(BaseModel):
    day: str
    focus: str
    is_rest: bool
    exercises: list[dict[str, Any]] = Field(default_factory=list)


class StartDayWorkoutRequest(BaseModel):
    source_day: str
    use_ai: bool = True


class EvaluationSubmitRequest(BaseModel):
    session_id: Optional[str] = None
    session_label: Optional[str] = None
    exercise_id: Optional[str] = None
    exercise_name: Optional[str] = None
    scope: Literal["session", "exercise"] = "session"
    completion_rate: int = Field(default=80, ge=0, le=100)
    rpe: int = Field(default=5, ge=1, le=10)
    soreness: list[str] = Field(default_factory=list)
    doms_severity: Literal["normal", "moderate", "intense"] = "moderate"
    satisfaction: Literal["very_satisfied", "satisfied", "neutral", "unsatisfied"] = "satisfied"
    duration_sec: Optional[int] = Field(default=0, ge=0)
    note: str = ""
    auto_apply: bool = True


