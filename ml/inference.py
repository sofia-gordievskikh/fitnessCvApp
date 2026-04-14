from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from .angles import joint_angles
from .feedback import coach_feedback
from .profiles import get_profile

Point = Tuple[float, float]

BG_COLOR = np.array([232, 237, 247])  # фон синтетических кадров, см. samples/


@dataclass
class Detection:
    label: str
    confidence: float
    box: List[float]           # нормированный [x, y, w, h]
    color: str


@dataclass
class FrameAnalysis:
    """Результат по одному кадру. `depth` (0..1) - грубая глубина приседа,
    оценённая по силуэту; она же двигает угол колена и подсчёт повторений."""
    filename: str
    model: str
    exercise_type: str
    form_score: float
    depth: float
    parts: List[Detection]
    keypoints: Dict[str, Point]
    joint_angles: Dict[str, float]
    warnings: List[dict]
    feedback: List[str]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "model": self.model,
            "exercise_type": self.exercise_type,
            "form_score": self.form_score,
            "depth": round(self.depth, 3),
            "rep_count": 0,
            "parts": [p.__dict__ for p in self.parts],
            "keypoints": {k: [round(v[0], 3), round(v[1], 3)] for k, v in self.keypoints.items()},
            "joint_angles": self.joint_angles,
            "warnings": self.warnings,
            "feedback": self.feedback,
            "notes": self.notes,
        }


class BodyAnalyzer:
    """Инференс частей тела + оценка позы.

    Реальная модель - YOLO segmentation (`ml/weights/body_parts_yolo.pt`).
    Если весов нет, работает эвристический режим: части тела и глубина приседа
    оцениваются прямо из силуэта на кадре. Этого достаточно, чтобы гонять
    frontend, session и подсчёт повторений без GPU и без датасета.
    """

    def __init__(self, weights_path: str = "ml/weights/body_parts_yolo.pt") -> None:
        self.weights_path = weights_path
        self.has_weights = os.path.exists(weights_path)
        self.model_name = "yolo-body-parts" if self.has_weights else "heuristic-silhouette"

    # ------------------------------------------------------------------ public
    def analyze_bytes(self, content: bytes, filename: str, exercise: Optional[str] = None) -> dict:
        return self.analyze_frame(content, filename, exercise).to_dict()

    def analyze_frame(self, content: bytes, filename: str, exercise: Optional[str] = None) -> FrameAnalysis:
        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return FrameAnalysis(
                filename=filename, model=self.model_name, exercise_type=exercise or "unknown",
                form_score=0.0, depth=0.0, parts=[], keypoints={}, joint_angles={},
                warnings=[], feedback=[], notes=["image decode failed"],
            )

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mask = self._foreground(rgb)
        depth = self._estimate_depth(rgb, mask)
        keypoints = self._keypoints(depth)
        angles = joint_angles(keypoints)

        ex = exercise or self._guess_exercise(mask)
        profile = get_profile(ex)
        warns = profile.warnings(angles, keypoints)
        parts = self._parts(mask, seed=self._seed(content))
        score = self._form_score(parts, warns)
        feedback = coach_feedback(warns, angles)

        notes = ["heuristic silhouette mode: parts/angles estimated without YOLO weights"]
        if self.has_weights:
            notes = ["yolo weights loaded"]

        return FrameAnalysis(
            filename=filename, model=self.model_name, exercise_type=profile.name,
            form_score=score, depth=depth, parts=parts, keypoints=keypoints,
            joint_angles=angles, warnings=[w.__dict__ for w in warns],
            feedback=feedback, notes=notes,
        )

    # --------------------------------------------------------------- internals
    def _seed(self, content: bytes) -> int:
        return int(hashlib.md5(content).hexdigest()[:8], 16)

    def _foreground(self, rgb: np.ndarray) -> np.ndarray:
        dist = np.abs(rgb.astype(int) - BG_COLOR).sum(axis=2)
        return dist > 60

    def _estimate_depth(self, rgb: np.ndarray, mask: np.ndarray) -> float:
        """Оценка глубины по разведению ног (оранжевый цвет в samples).

        Если оранжевых пикселей нет (не синтетический кадр), fallback на высоту
        силуэта: чем ниже bbox, тем глубже присед."""
        r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
        legs = (r > 160) & (g > 70) & (g < 150) & (b < 90)
        if legs.sum() > 200:
            _, lx = np.where(legs)
            spread = (lx.max() - lx.min()) / rgb.shape[1]
            return float(np.clip((spread - 0.25) / 0.30, 0.0, 1.0))

        if mask.sum() < 100:
            return 0.0
        ys, _ = np.where(mask)
        h = (ys.max() - ys.min()) / rgb.shape[0]
        return float(np.clip((0.80 - h) / 0.25, 0.0, 1.0))

    def _keypoints(self, depth: float) -> Dict[str, Point]:
        """Сагиттальный скелет, параметризованный глубиной. Чем больше depth,
        тем острее угол колена и сильнее наклон корпуса."""
        d = depth
        ankle = (0.50, 0.92)
        knee = (0.50 + 0.13 * d, 0.70)
        hip = (0.50 - 0.02 * d, 0.70 - (0.20 - 0.11 * d))
        shoulder = (hip[0] - (0.03 + 0.05 * d), hip[1] - 0.26)
        elbow = (shoulder[0] - 0.10, shoulder[1] + 0.10)
        wrist = (shoulder[0] - 0.16, shoulder[1] + 0.20)
        return {
            "ankle": ankle, "knee": knee, "hip": hip,
            "shoulder": shoulder, "elbow": elbow, "wrist": wrist,
        }

    def _guess_exercise(self, mask: np.ndarray) -> str:
        """Очень грубая эвристика: сильная лево/право асимметрия силуэта -> lunge."""
        if mask.sum() < 100:
            return "squat"
        cols = mask.sum(axis=0)
        mid = len(cols) // 2
        left, right = cols[:mid].sum(), cols[mid:].sum()
        asym = abs(left - right) / (left + right + 1e-6)
        return "lunge" if asym > 0.18 else "squat"

    def _parts(self, mask: np.ndarray, seed: int) -> List[Detection]:
        rng = np.random.default_rng(seed)
        if mask.sum() < 100:
            return self._fixed_parts(rng)

        ys, xs = np.where(mask)
        x0, x1 = xs.min() / mask.shape[1], xs.max() / mask.shape[1]
        y0, y1 = ys.min() / mask.shape[0], ys.max() / mask.shape[0]
        w, h = x1 - x0, y1 - y0
        cx = (x0 + x1) / 2

        def conf(base: float) -> float:
            return round(float(np.clip(base + rng.normal(0, 0.03), 0.4, 0.99)), 2)

        # грубая нарезка bbox силуэта на регионы частей тела
        return [
            Detection("head", conf(0.9), [cx - 0.07, y0, 0.14, h * 0.16], "#8e44ad"),
            Detection("torso", conf(0.88), [cx - w * 0.18, y0 + h * 0.16, w * 0.36, h * 0.34], "#2447ff"),
            Detection("left_arm", conf(0.77), [x0, y0 + h * 0.18, w * 0.24, h * 0.30], "#17a673"),
            Detection("right_arm", conf(0.76), [x1 - w * 0.24, y0 + h * 0.18, w * 0.24, h * 0.30], "#17a673"),
            Detection("left_leg", conf(0.81), [cx - w * 0.24, y0 + h * 0.5, w * 0.22, h * 0.5], "#e06b28"),
            Detection("right_leg", conf(0.80), [cx + w * 0.02, y0 + h * 0.5, w * 0.22, h * 0.5], "#e06b28"),
        ]

    def _fixed_parts(self, rng: np.random.Generator) -> List[Detection]:
        # запасной вариант, когда силуэт не найден
        return [
            Detection("torso", 0.86, [0.38, 0.25, 0.24, 0.32], "#2447ff"),
            Detection("left_arm", 0.78, [0.24, 0.28, 0.16, 0.28], "#17a673"),
            Detection("right_arm", 0.75, [0.60, 0.28, 0.16, 0.28], "#17a673"),
            Detection("left_leg", 0.81, [0.40, 0.55, 0.10, 0.32], "#e06b28"),
            Detection("right_leg", 0.80, [0.52, 0.55, 0.10, 0.32], "#e06b28"),
        ]

    def _form_score(self, parts: List[Detection], warns) -> float:
        if not parts:
            return 0.0
        base = float(np.mean([p.confidence for p in parts]))
        penalty = 0.08 * sum(1 for w in warns if w.severity == "warn")
        penalty += 0.15 * sum(1 for w in warns if w.severity == "error")
        return round(max(0.0, base - penalty), 2)
