"""Локальное хранение сессий тренировок в SQLite.

Одна база `sessions.db` рядом с backend. Храним заголовок сессии и агрегаты по
кадрам - этого хватает для экрана истории и экспорта в JSON/CSV. Кадры-картинки
не сохраняем, только числа.
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "sessions.db"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SessionStore:
    def __init__(self, path: Path | str = DB_PATH) -> None:
        self.path = str(path)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with closing(self._conn()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    exercise TEXT NOT NULL,
                    rep_count INTEGER DEFAULT 0,
                    frames INTEGER DEFAULT 0,
                    score_sum REAL DEFAULT 0,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS frames (
                    session_id TEXT NOT NULL,
                    frame_index INTEGER NOT NULL,
                    depth REAL,
                    knee_angle REAL,
                    form_score REAL,
                    phase TEXT,
                    event TEXT,
                    warnings TEXT
                );
                """
            )
            conn.commit()

    # ------------------------------------------------------------ sessions
    def create(self, exercise: str) -> str:
        sid = uuid.uuid4().hex[:12]
        with closing(self._conn()) as conn:
            conn.execute(
                "INSERT INTO sessions (id, exercise, started_at) VALUES (?, ?, ?)",
                (sid, exercise, _now()),
            )
            conn.commit()
        return sid

    def get(self, sid: str) -> Optional[dict]:
        with closing(self._conn()) as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
        return dict(row) if row else None

    def list(self) -> list[dict]:
        with closing(self._conn()) as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC"
            ).fetchall()
        return [self._summary(dict(r)) for r in rows]

    def add_frame(self, sid: str, frame: dict) -> None:
        with closing(self._conn()) as conn:
            conn.execute(
                """INSERT INTO frames
                   (session_id, frame_index, depth, knee_angle, form_score, phase, event, warnings)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sid, frame.get("frame_index", 0), frame.get("depth"),
                    frame.get("knee_angle"), frame.get("form_score"),
                    frame.get("phase"), frame.get("event"),
                    json.dumps(frame.get("warnings", []), ensure_ascii=False),
                ),
            )
            conn.execute(
                """UPDATE sessions
                   SET frames = frames + 1,
                       score_sum = score_sum + ?,
                       rep_count = ?
                   WHERE id = ?""",
                (frame.get("form_score", 0.0), frame.get("rep_count", 0), sid),
            )
            conn.commit()

    def finish(self, sid: str, rep_count: int) -> Optional[dict]:
        with closing(self._conn()) as conn:
            conn.execute(
                "UPDATE sessions SET finished_at = ?, rep_count = ? WHERE id = ?",
                (_now(), rep_count, sid),
            )
            conn.commit()
        s = self.get(sid)
        return self._summary(s) if s else None

    def frames(self, sid: str) -> list[dict]:
        with closing(self._conn()) as conn:
            rows = conn.execute(
                "SELECT * FROM frames WHERE session_id = ? ORDER BY frame_index", (sid,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------- export
    @staticmethod
    def _summary(s: dict) -> dict:
        frames = s.get("frames") or 0
        avg = round((s.get("score_sum") or 0.0) / frames, 3) if frames else 0.0
        return {
            "session_id": s["id"],
            "exercise": s["exercise"],
            "rep_count": s.get("rep_count", 0),
            "frames": frames,
            "avg_form_score": avg,
            "started_at": s["started_at"],
            "finished_at": s.get("finished_at"),
        }

    def summary(self, sid: str) -> Optional[dict]:
        s = self.get(sid)
        return self._summary(s) if s else None

    def export_json(self, sid: str) -> Optional[str]:
        s = self.summary(sid)
        if s is None:
            return None
        s["frames_detail"] = self.frames(sid)
        return json.dumps(s, ensure_ascii=False, indent=2)

    def export_csv(self, sid: str) -> Optional[str]:
        if self.get(sid) is None:
            return None
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["frame_index", "depth", "knee_angle", "form_score", "phase", "event", "warnings"])
        for f in self.frames(sid):
            writer.writerow([
                f["frame_index"], f["depth"], f["knee_angle"],
                f["form_score"], f["phase"], f["event"], f["warnings"],
            ])
        return buf.getvalue()
