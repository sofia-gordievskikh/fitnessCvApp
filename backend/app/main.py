from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .schemas import AnalysisResponse
from ml.inference import BodyAnalyzer


app = FastAPI(title="fitness cv backend")
analyzer = BodyAnalyzer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(image: UploadFile = File(...)) -> AnalysisResponse:
    content = await image.read()
    return analyzer.analyze_bytes(content, filename=image.filename or "frame.jpg")
