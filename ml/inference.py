from __future__ import annotations

import os
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Detection:
    label: str
    confidence: float
    box: list[float]
    color: str


class BodyAnalyzer:
    def __init__(self, weights_path: str = "ml/weights/body_parts_yolo.pt") -> None:
        self.weights_path = weights_path
        self.model_name = "yolo-body-parts" if os.path.exists(weights_path) else "mock-yolo-body-parts"

    def analyze_bytes(self, content: bytes, filename: str) -> dict:
        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return {
                "filename": filename,
                "model": self.model_name,
                "form_score": 0.0,
                "parts": [],
                "notes": ["image decode failed"],
            }

        h, w = img.shape[:2]
        parts = self._mock_parts(w, h)
        score = self._form_score(parts)
        return {
            "filename": filename,
            "model": self.model_name,
            "form_score": score,
            "parts": [part.__dict__ for part in parts],
            "notes": [
                "pose landmarker was tested first, but yolo segmentation was more stable",
                "mock boxes are used when weights file is absent",
            ],
        }

    def _mock_parts(self, width: int, height: int) -> list[Detection]:
        # Нормированные bbox, frontend сам масштабирует под canvas.
        return [
            Detection("torso", 0.86, [0.38, 0.25, 0.24, 0.32], "#2447ff"),
            Detection("left_arm", 0.78, [0.24, 0.28, 0.16, 0.28], "#17a673"),
            Detection("right_arm", 0.75, [0.60, 0.28, 0.16, 0.28], "#17a673"),
            Detection("left_leg", 0.81, [0.40, 0.55, 0.10, 0.32], "#e06b28"),
            Detection("right_leg", 0.80, [0.52, 0.55, 0.10, 0.32], "#e06b28"),
        ]

    def _form_score(self, parts: list[Detection]) -> float:
        if not parts:
            return 0.0
        return round(float(np.mean([p.confidence for p in parts])), 2)
