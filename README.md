# fitnessCvApp

Desktop-прототип фитнес приложения: Electron-обертка, простой frontend,
Python backend и ML-модуль для сегментации человека и детекции частей тела.

Сохранившийся старый код лежит в `notebooks/body_segmentation_parts.ipynb`.
Там был первый эксперимент через MediaPipe Pose Landmarker. Он работал быстро,
но на фото из зала часто путал руки/ноги при перекрытиях и давал слабую
стабильность на боковых позах. После этого перешли на YOLO-подход: отдельно
сегментация силуэта человека и классы частей тела.

## Структура

- `electron/` - desktop wrapper;
- `frontend/` - экран загрузки кадра и просмотра результата;
- `backend/` - FastAPI сервис для анализа изображения;
- `ml/` - инференс, train scripts и конфиги;
- `docs/` - сбор датасета, обучение, архитектура;
- `notebooks/` - восстановленный Colab.

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

Основная модель в коде ожидается как YOLO segmentation checkpoint:
`ml/weights/body_parts_yolo.pt`.

Команды:

```bash
python -m ml.train --config ml/configs/body_parts.yaml
python -m ml.predict --image samples/squat.jpg --weights ml/weights/body_parts_yolo.pt
```

Если весов нет, backend возвращает mock-результат с той же схемой ответа. Это
нужно для проверки frontend/backend без тяжелой модели.
