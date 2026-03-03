from pydantic import BaseModel


class BodyPart(BaseModel):
    label: str
    confidence: float
    box: list[float]
    color: str


class AnalysisResponse(BaseModel):
    filename: str
    model: str
    form_score: float
    parts: list[BodyPart]
    notes: list[str]
