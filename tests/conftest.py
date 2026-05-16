from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture(scope="session")
def squat_frames() -> list[bytes]:
    frames = sorted((SAMPLES / "frames").glob("squat_*.jpg"))
    assert frames, "нет демо-кадров, запусти samples/generate_samples.py"
    return [f.read_bytes() for f in frames]


@pytest.fixture(scope="session")
def squat_image() -> bytes:
    return (SAMPLES / "squat.jpg").read_bytes()
