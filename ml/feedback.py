"""Короткие подсказки по технике (coach mode).

Берём warnings и углы и складываем 1-3 человекочитаемые фразы. Ничего умного,
просто маппинг код -> совет, но в UI это выглядит как обратная связь тренера.
"""
from __future__ import annotations

from typing import Dict, List

from .profiles import Warning

TIPS = {
    "knee_over_toe": "держи колени над стопами, не выводи их сильно вперёд",
    "back_angle_low": "выше грудь, не заваливай корпус вперёд",
    "shallow_depth": "старайся сесть глубже, бедро до параллели",
    "elbow_flare": "прижми локти ближе к корпусу",
}


def coach_feedback(warnings: List[Warning], angles: Dict[str, float]) -> List[str]:
    tips: List[str] = []
    for w in warnings:
        tip = TIPS.get(w.code)
        if tip and tip not in tips:
            tips.append(tip)

    if not tips:
        knee = angles.get("knee")
        if knee is not None and knee < 120:
            tips.append("хорошая глубина, держи темп")
        else:
            tips.append("техника выглядит ровно")
    return tips[:3]
