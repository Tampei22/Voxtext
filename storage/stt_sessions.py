import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app_core.models import STTPhrase, STTSession
from storage.paths import BASE_DIR

SESSIONS_FILE: Path = BASE_DIR / "stt_sessions.json"


def _safe_read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _safe_write(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def save_session(session: STTSession) -> None:
    from storage.settings import load_app_settings
    keep = load_app_settings().max_history
    sessions = _safe_read(SESSIONS_FILE)
    record = {
        "session_id": session.session_id,
        "lang": session.lang,
        "engine": session.engine,
        "created_at_iso": session.created_at_iso,
        "phrases": [asdict(p) for p in session.phrases],
    }
    sessions.append(record)
    if keep > 0 and len(sessions) > keep:
        sessions = sessions[-keep:]
    _safe_write(SESSIONS_FILE, sessions)


def list_sessions() -> list[dict[str, Any]]:
    return _safe_read(SESSIONS_FILE)


def delete_session(session_id: str) -> bool:
    sessions = _safe_read(SESSIONS_FILE)
    before = len(sessions)
    sessions = [s for s in sessions if s.get("session_id") != session_id]
    if len(sessions) == before:
        return False
    _safe_write(SESSIONS_FILE, sessions)
    return True


def clear_sessions() -> None:
    _safe_write(SESSIONS_FILE, [])


def session_from_dict(d: dict[str, Any]) -> STTSession:
    phrases = [STTPhrase(**p) for p in d.get("phrases", [])]
    return STTSession(
        session_id=d.get("session_id", ""),
        lang=d.get("lang", ""),
        engine=d.get("engine", ""),
        created_at_iso=d.get("created_at_iso", ""),
        phrases=phrases,
    )
