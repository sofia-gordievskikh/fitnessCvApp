"""Тесты FastAPI: health, схема /analyze и цикл session."""
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.schemas import AnalysisResponse


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # изолированная база под каждый тест
    import backend.app.storage as storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sessions.db")
    import importlib
    import backend.app.main as main
    importlib.reload(main)
    return TestClient(main.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_schema(client, squat_image):
    r = client.post(
        "/analyze",
        files={"image": ("squat.jpg", squat_image, "image/jpeg")},
        data={"exercise": "squat"},
    )
    assert r.status_code == 200
    # ответ обязан валидироваться схемой
    parsed = AnalysisResponse(**r.json())
    assert parsed.exercise_type == "squat"
    assert parsed.parts


def test_session_flow_counts_reps(client, squat_frames):
    sid = client.post("/session/start", data={"exercise": "squat"}).json()["session_id"]

    last = None
    for i, frame in enumerate(squat_frames):
        r = client.post(
            "/session/frame",
            data={"session_id": sid},
            files={"image": (f"f{i}.jpg", frame, "image/jpeg")},
        )
        assert r.status_code == 200
        last = r.json()

    assert last["rep_count"] == 1

    summary = client.post(f"/session/{sid}/finish").json()
    assert summary["frames"] == len(squat_frames)
    assert summary["rep_count"] == 1

    # история и экспорт
    assert any(s["session_id"] == sid for s in client.get("/sessions").json())
    csv_data = client.get(f"/sessions/{sid}/export", params={"format": "csv"}).text
    assert "frame_index" in csv_data


def test_session_frame_unknown_session(client, squat_image):
    r = client.post(
        "/session/frame",
        data={"session_id": "does-not-exist"},
        files={"image": ("f.jpg", squat_image, "image/jpeg")},
    )
    assert r.status_code == 404
