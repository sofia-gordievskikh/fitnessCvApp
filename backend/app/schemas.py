from __future__ import annotations

from pydantic import BaseModel, Field


class BodyPart(BaseModel):
    label: str
    confidence: float
    box: list[float]
    color: str


class Warning(BaseModel):
    code: str
    message: str
    severity: str = "warn"


class AnalysisResponse(BaseModel):
    filename: str
    model: str
    exercise_type: str
    form_score: float
    depth: float = 0.0
    rep_count: int = 0
    parts: list[BodyPart]
    keypoints: dict[str, list[float]] = Field(default_factory=dict)
    joint_angles: dict[str, float] = Field(default_factory=dict)
    warnings: list[Warning] = Field(default_factory=list)
    feedback: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SessionSummary(BaseModel):
    session_id: str
    exercise: str
    rep_count: int
    frames: int
    avg_form_score: float
    started_at: str
    finished_at: str | None = None


class FrameResponse(AnalysisResponse):
    session_id: str
    phase: str
    event: str | None = None


class TimelineMark(BaseModel):
    kind: str          # rep_start | rep_end
    frame_index: int
    time_sec: float
    angle: float


class VideoResponse(BaseModel):
    filename: str
    exercise: str
    frames_analyzed: int
    fps: float
    rep_count: int
    avg_form_score: float
    timeline: list[TimelineMark] = Field(default_factory=list)
    warnings_count: dict[str, int] = Field(default_factory=dict)
