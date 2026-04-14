"""Геометрия суставных углов.

Углы считаются по трём точкам (keypoints). В проде точки берутся из
сегментации / позы, здесь же они могут приходить и из эвристической оценки
силуэта (см. `inference.BodyAnalyzer`).
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

Point = Tuple[float, float]


def angle_3pt(a: Point, b: Point, c: Point) -> float:
    """Угол в точке b (в градусах) между отрезками b->a и b->c."""
    v1 = (a[0] - b[0], a[1] - b[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    cos = max(-1.0, min(1.0, cos))
    return round(math.degrees(math.acos(cos)), 1)


def joint_angles(keypoints: Dict[str, Point]) -> Dict[str, float]:
    """Собирает основные углы из словаря keypoints.

    Ожидаемые ключи (по возможности): shoulder, hip, knee, ankle, elbow, wrist.
    Отсутствующие суставы просто пропускаются - на реальных кадрах часть точек
    теряется при перекрытиях.
    """
    out: Dict[str, float] = {}
    kp = keypoints

    if all(k in kp for k in ("hip", "knee", "ankle")):
        out["knee"] = angle_3pt(kp["hip"], kp["knee"], kp["ankle"])
    if all(k in kp for k in ("shoulder", "hip", "knee")):
        out["hip"] = angle_3pt(kp["shoulder"], kp["hip"], kp["knee"])
    if all(k in kp for k in ("shoulder", "elbow", "wrist")):
        out["elbow"] = angle_3pt(kp["shoulder"], kp["elbow"], kp["wrist"])
    if all(k in kp for k in ("shoulder", "hip")):
        # наклон спины относительно вертикали, 90 = вертикально стоит
        dx = kp["shoulder"][0] - kp["hip"][0]
        dy = kp["shoulder"][1] - kp["hip"][1]
        out["back"] = round(abs(math.degrees(math.atan2(abs(dy), abs(dx) + 1e-6))), 1)
    return out
