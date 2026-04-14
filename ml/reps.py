"""Подсчёт повторений по последовательности кадров.

Простая state machine на два состояния: "up" и "down". Повторение засчитывается
на переходе down -> up (человек опустился и вернулся). Ведущий сустав и пороги
берутся из профиля упражнения.

Такой подсчёт устойчивее, чем сравнение с одним порогом: между down_angle и
up_angle есть гистерезис, поэтому дрожание угла на границе не накручивает счёт.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .profiles import ExerciseProfile, get_profile


@dataclass
class RepEvent:
    kind: str          # "rep_start" | "rep_end"
    frame_index: int
    angle: float


@dataclass
class RepCounter:
    profile: ExerciseProfile
    count: int = 0
    phase: str = "up"          # текущая фаза
    frame_index: int = -1
    events: List[RepEvent] = field(default_factory=list)
    _reached_bottom: bool = False

    @classmethod
    def for_exercise(cls, exercise: Optional[str]) -> "RepCounter":
        return cls(profile=get_profile(exercise))

    def update(self, angle: Optional[float]) -> Optional[str]:
        """Прогоняет один кадр. Возвращает событие фазы, если оно произошло."""
        self.frame_index += 1
        if angle is None:
            return None

        p = self.profile
        event: Optional[str] = None

        if self.phase == "up" and angle < p.down_angle:
            self.phase = "down"
            self._reached_bottom = True
            event = "rep_start"
            self.events.append(RepEvent("rep_start", self.frame_index, angle))
        elif self.phase == "down" and angle > p.up_angle:
            self.phase = "up"
            if self._reached_bottom:
                self.count += 1
                self._reached_bottom = False
            event = "rep_end"
            self.events.append(RepEvent("rep_end", self.frame_index, angle))
        return event

    def as_dict(self) -> dict:
        return {
            "exercise": self.profile.name,
            "rep_count": self.count,
            "phase": self.phase,
            "events": [e.__dict__ for e in self.events],
        }
