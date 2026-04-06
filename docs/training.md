# Обучение и модели

## MediaPipe Pose Landmarker

Первый прототип был через MediaPipe Pose Landmarker. Код сохранился в
`notebooks/body_segmentation_parts.ipynb`.

Что не подошло:

- на боковых позах landmarks часто прыгали;
- при перекрытии рук и корпуса точки путались;
- для задачи частей тела нужны были области, а не только точки;
- метрики на ручной проверке были хуже, чем у YOLO segmentation.

Итог: Pose Landmarker оставили как baseline и быстрый sanity check.

## YOLO

Основной вариант: YOLO segmentation для частей тела.

Конфиг: `ml/configs/body_parts.yaml`.

Команда:

```bash
python -m ml.train --config ml/configs/body_parts.yaml
```

Скрипт печатает команду для `yolo segment train`. Веса в репозиторий не кладутся:
`ml/weights/*.pt` игнорируются git.

## Метрики

Смотрели:

- mask mAP;
- box mAP;
- стабильность классов на соседних кадрах;
- процент кадров, где перепутаны левая/правая конечность.

Для приложения важнее была стабильность на видео, чем один красивый кадр.
