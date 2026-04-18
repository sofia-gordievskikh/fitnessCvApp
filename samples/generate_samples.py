"""Генерация маленьких синтетических кадров для демо.

Настоящих фото из зала в git нет (приватность + вес), поэтому для быстрого
запуска `ml.predict` и тестов рисуем простые силуэты человека в разных фазах
приседа/выпада. Кадры намеренно примитивные - это заглушки, а не реальные данные.

    python samples/generate_samples.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 320, 480
SAMPLES = Path(__file__).resolve().parent


def _limb(draw: ImageDraw.ImageDraw, a, b, width, color):
    draw.line([a, b], fill=color, width=width)
    draw.ellipse([a[0] - width // 2, a[1] - width // 2, a[0] + width // 2, a[1] + width // 2], fill=color)
    draw.ellipse([b[0] - width // 2, b[1] - width // 2, b[0] + width // 2, b[1] + width // 2], fill=color)


def draw_pose(knee_bend: float, side: bool = False, split: float = 0.0) -> Image.Image:
    """knee_bend 0 = стоя, 1 = глубокий присед. split - разведение ног для выпада."""
    img = Image.new("RGB", (W, H), (232, 237, 247))
    d = ImageDraw.Draw(img)

    cx = W // 2
    hip_y = 210 + int(70 * knee_bend)
    shoulder_y = hip_y - 120
    head_y = shoulder_y - 40

    # torso
    d.line([(cx, shoulder_y), (cx, hip_y)], fill=(36, 71, 255), width=22)
    # head
    d.ellipse([cx - 22, head_y - 22, cx + 22, head_y + 22], fill=(240, 200, 120))

    knee_y = hip_y + int(90 * (1 - 0.4 * knee_bend))
    ankle_y = min(H - 30, knee_y + int(100 * (1 - 0.2 * knee_bend)))
    dx = 34 + int(40 * knee_bend)

    lx = int(split * 60)
    # left leg
    _limb(d, (cx - 26, hip_y), (cx - dx - lx, knee_y), 16, (224, 107, 40))
    _limb(d, (cx - dx - lx, knee_y), (cx - 20 - lx, ankle_y), 16, (224, 107, 40))
    # right leg
    _limb(d, (cx + 26, hip_y), (cx + dx + lx, knee_y), 16, (224, 107, 40))
    _limb(d, (cx + dx + lx, knee_y), (cx + 20 + lx, ankle_y), 16, (224, 107, 40))

    arm_drop = int(30 * knee_bend)
    if side:
        _limb(d, (cx, shoulder_y + 6), (cx + 70, shoulder_y + 40 + arm_drop), 12, (23, 166, 115))
    else:
        _limb(d, (cx, shoulder_y + 6), (cx - 60, shoulder_y + 50 + arm_drop), 12, (23, 166, 115))
        _limb(d, (cx, shoulder_y + 6), (cx + 60, shoulder_y + 50 + arm_drop), 12, (23, 166, 115))
    return img


def main() -> None:
    frames = SAMPLES / "frames"
    frames.mkdir(exist_ok=True)

    draw_pose(0.15).save(SAMPLES / "squat.jpg", quality=85)
    draw_pose(0.6, split=1.0).save(SAMPLES / "lunge.jpg", quality=85)

    # последовательность одного приседа: вниз и вверх - для session/video demo
    seq = [0.0, 0.25, 0.55, 0.85, 0.95, 0.7, 0.35, 0.05]
    for i, bend in enumerate(seq):
        draw_pose(bend).save(frames / f"squat_{i:02d}.jpg", quality=85)

    print(f"saved samples to {SAMPLES}")


if __name__ == "__main__":
    main()
