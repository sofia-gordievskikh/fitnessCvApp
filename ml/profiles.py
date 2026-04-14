"""Профили упражнений: пороги углов и правила предупреждений.

Каждый профиль описывает:
- какой сустав считается ведущим для подсчёта повторений (`rep_joint`);
- пороги "вниз"/"вверх" по этому суставу для state machine (см. `reps.py`);
- набор правил, которые превращают углы/точки в warnings.

Значения подобраны грубо и вручную под учебный датасет, это не медицинская норма.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

Point = Tuple[float, float]


@dataclass
class Warning:
    code: str
    message: str
    severity: str = "warn"  # info | warn | error


@dataclass
class ExerciseProfile:
    name: str
    rep_joint: str
    down_angle: float  # ниже этого угла - фаза "внизу"
    up_angle: float    # выше этого угла - фаза "вверху"
    rules: List[Callable[[Dict[str, float], Dict[str, Point]], Warning | None]] = field(default_factory=list)

    def warnings(self, angles: Dict[str, float], keypoints: Dict[str, Point]) -> List[Warning]:
        found: List[Warning] = []
        for rule in self.rules:
            w = rule(angles, keypoints)
            if w is not None:
                found.append(w)
        return found


def _knee_over_toe(angles, kp):
    knee = kp.get("knee")
    ankle = kp.get("ankle")
    if knee is None or ankle is None:
        return None
    # колено сильно ушло вперёд за носок по горизонтали
    if abs(knee[0] - ankle[0]) > 0.12:
        return Warning("knee_over_toe", "колено выходит за носок", "warn")
    return None


def _back_angle_low(angles, kp):
    back = angles.get("back")
    if back is None:
        return None
    if back < 55:
        return Warning("back_angle_low", "сильный наклон корпуса вперёд", "warn")
    return None


def _shallow_depth(angles, kp):
    knee = angles.get("knee")
    if knee is None:
        return None
    if knee > 140:
        return Warning("shallow_depth", "недостаточная глубина приседа", "info")
    return None


def _elbow_flare(angles, kp):
    elbow = angles.get("elbow")
    if elbow is None:
        return None
    if elbow < 70:
        return Warning("elbow_flare", "локти слишком разведены", "info")
    return None


PROFILES: Dict[str, ExerciseProfile] = {
    "squat": ExerciseProfile(
        name="squat",
        rep_joint="knee",
        down_angle=110,
        up_angle=160,
        rules=[_knee_over_toe, _back_angle_low, _shallow_depth],
    ),
    "lunge": ExerciseProfile(
        name="lunge",
        rep_joint="knee",
        down_angle=115,
        up_angle=160,
        rules=[_knee_over_toe, _back_angle_low],
    ),
    "push_up": ExerciseProfile(
        name="push_up",
        rep_joint="elbow",
        down_angle=100,
        up_angle=155,
        rules=[_elbow_flare, _back_angle_low],
    ),
}

DEFAULT_PROFILE = "squat"


def get_profile(name: str | None) -> ExerciseProfile:
    return PROFILES.get(name or DEFAULT_PROFILE, PROFILES[DEFAULT_PROFILE])
