# fitnessCvApp

Desktop-прототип фитнес приложения: Electron-обертка, простой frontend,
Python backend и ML-модуль для сегментации человека и детекции частей тела.

Рабочий CV notebook лежит в `notebooks/body_segmentation_parts.ipynb`.
В проекте есть baseline через MediaPipe Pose Landmarker и основной YOLO-подход:
отдельно сегментация силуэта человека и классы частей тела. Pose Landmarker
используется как быстрый sanity check, но на фото из зала чаще путает руки/ноги
при перекрытиях и хуже держит боковые позы.

## Структура

- `electron/` - desktop wrapper;
- `frontend/` - экран загрузки кадра и просмотра результата;
- `backend/` - FastAPI сервис для анализа изображения;
- `ml/` - инференс, train scripts и конфиги;
- `docs/` - сбор датасета, обучение, архитектура;
- `notebooks/` - рабочие ML notebooks.

## Локальный запуск

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

Electron:

```bash
npm install
npm start
```

## ML

Основная модель в проекте - YOLO segmentation checkpoint:
`ml/weights/body_parts_yolo.pt`. Файл весов не хранится в git, потому что он
тяжелый, но backend и ML-скрипты работают с этой моделью.

Команды:

```bash
python -m ml.train --config ml/configs/body_parts.yaml
python -m ml.predict --image samples/squat.jpg --weights ml/weights/body_parts_yolo.pt
```

Для dev-режима без локального файла весов backend возвращает mock-результат с
той же схемой ответа. Это нужно для проверки frontend/backend на машине без GPU.
