.PHONY: backend ui samples test lint smoke docker-up docker-down

PY ?= python

backend:  ## запустить FastAPI backend
	uvicorn backend.app.main:app --reload --port 8000

ui:  ## запустить Electron UI
	npm start

samples:  ## перегенерировать демо-кадры
	$(PY) samples/generate_samples.py

test:  ## прогнать pytest
	$(PY) -m pytest -q

lint:  ## быстрые проверки: компиляция python + формат json
	$(PY) -m compileall -q backend ml samples tests
	$(PY) -c "import json,glob; [json.load(open(f)) for f in glob.glob('ml/configs/*.json')]" 2>/dev/null || true

smoke:  ## поднять backend и дёрнуть /health и /analyze на демо-кадре
	$(PY) -m uvicorn backend.app.main:app --port 8000 & echo $$! > .smoke.pid; \
	sleep 3; \
	curl -sf http://127.0.0.1:8000/health && echo " health ok"; \
	curl -sf -F "image=@samples/squat.jpg" -F "exercise=squat" \
	    http://127.0.0.1:8000/analyze | $(PY) -m json.tool | head -20; \
	kill `cat .smoke.pid`; rm -f .smoke.pid

docker-up:  ## backend в docker
	docker compose up --build

docker-down:
	docker compose down
