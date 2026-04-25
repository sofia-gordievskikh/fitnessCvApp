from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from ml.inference import BodyAnalyzer
from ml.reps import RepCounter

from .schemas import (
    AnalysisResponse,
    FrameResponse,
    SessionSummary,
    VideoResponse,
)
from .storage import SessionStore

app = FastAPI(title="fitness cv backend", version="0.2.0")
analyzer = BodyAnalyzer()
store = SessionStore()

# счётчики повторений живут в памяти, пока запущен сервер (по session_id)
_counters: dict[str, RepCounter] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": analyzer.model_name}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(image: UploadFile = File(...), exercise: str | None = Form(default=None)) -> dict:
    content = await image.read()
    return analyzer.analyze_bytes(content, filename=image.filename or "frame.jpg", exercise=exercise)


# --------------------------------------------------------------------- session
@app.post("/session/start", response_model=SessionSummary)
def session_start(exercise: str = Form(default="squat")) -> dict:
    sid = store.create(exercise)
    _counters[sid] = RepCounter.for_exercise(exercise)
    return store.summary(sid)


@app.post("/session/frame", response_model=FrameResponse)
async def session_frame(
    session_id: str = Form(...),
    image: UploadFile = File(...),
) -> dict:
    sess = store.get(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="unknown session")

    counter = _counters.setdefault(session_id, RepCounter.for_exercise(sess["exercise"]))
    content = await image.read()
    frame = analyzer.analyze_frame(content, image.filename or "frame.jpg", exercise=sess["exercise"])

    knee = frame.joint_angles.get("knee")
    event = counter.update(knee)

    store.add_frame(session_id, {
        "frame_index": counter.frame_index,
        "depth": frame.depth,
        "knee_angle": knee,
        "form_score": frame.form_score,
        "phase": counter.phase,
        "event": event,
        "warnings": [w["code"] for w in frame.warnings],
        "rep_count": counter.count,
    })

    payload = frame.to_dict()
    payload.update({
        "session_id": session_id,
        "rep_count": counter.count,
        "phase": counter.phase,
        "event": event,
    })
    return payload


@app.post("/session/{session_id}/finish", response_model=SessionSummary)
def session_finish(session_id: str) -> dict:
    counter = _counters.get(session_id)
    reps = counter.count if counter else store.get(session_id)["rep_count"]
    summary = store.finish(session_id, reps)
    if summary is None:
        raise HTTPException(status_code=404, detail="unknown session")
    return summary


@app.get("/sessions", response_model=list[SessionSummary])
def sessions() -> list[dict]:
    return store.list()


@app.get("/sessions/{session_id}", response_model=SessionSummary)
def session_detail(session_id: str) -> dict:
    summary = store.summary(session_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="unknown session")
    return summary


@app.get("/sessions/{session_id}/export")
def session_export(session_id: str, format: str = "json"):
    if format == "csv":
        data = store.export_csv(session_id)
        if data is None:
            raise HTTPException(status_code=404, detail="unknown session")
        return PlainTextResponse(data, media_type="text/csv")
    data = store.export_json(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="unknown session")
    return PlainTextResponse(data, media_type="application/json")


# ----------------------------------------------------------------------- video
@app.post("/analyze-video", response_model=VideoResponse)
async def analyze_video(
    video: UploadFile = File(...),
    exercise: str = Form(default="squat"),
    stride: int = Form(default=3),
) -> dict:
    """Разбирает видео покадрово: каждый `stride`-й кадр идёт в анализатор,
    повторения и timeline (rep_start/rep_end) считаются по последовательности."""
    suffix = Path(video.filename or "clip.mp4").suffix or ".mp4"
    content = await video.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="cannot open video")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        counter = RepCounter.for_exercise(exercise)
        timeline: list[dict] = []
        warn_counts: dict[str, int] = {}
        score_sum, analyzed = 0.0, 0
        raw_index = 0

        while True:
            ok, frame_img = cap.read()
            if not ok:
                break
            if raw_index % max(1, stride) == 0:
                ok2, buf = cv2.imencode(".jpg", frame_img)
                if ok2:
                    fa = analyzer.analyze_frame(buf.tobytes(), f"frame_{raw_index}", exercise=exercise)
                    event = counter.update(fa.joint_angles.get("knee"))
                    score_sum += fa.form_score
                    analyzed += 1
                    for w in fa.warnings:
                        warn_counts[w["code"]] = warn_counts.get(w["code"], 0) + 1
                    if event:
                        timeline.append({
                            "kind": event,
                            "frame_index": raw_index,
                            "time_sec": round(raw_index / fps, 2),
                            "angle": fa.joint_angles.get("knee", 0.0),
                        })
            raw_index += 1
        cap.release()

    return {
        "filename": video.filename or "clip.mp4",
        "exercise": exercise,
        "frames_analyzed": analyzed,
        "fps": round(fps, 2),
        "rep_count": counter.count,
        "avg_form_score": round(score_sum / analyzed, 3) if analyzed else 0.0,
        "timeline": timeline,
        "warnings_count": warn_counts,
    }
