import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app_core.models import TTSJob, TTSSettings, InterpretationResult
from storage.paths import BASE_DIR

JOBS_FILE: Path = BASE_DIR / "jobs.json"


def _safe_read_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _safe_write_json(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def save_job(job: TTSJob) -> None:
    from storage.settings import load_app_settings
    keep_last = load_app_settings().max_history
    jobs = _safe_read_json(JOBS_FILE)

    record = {
        "job_id": job.job_id,
        "text": job.text,
        "interpretation": asdict(job.interpretation) if job.interpretation else None,
        "settings": asdict(job.settings),
        "output_path": job.output_path,
        "created_at_iso": job.created_at_iso,
    }

    jobs.append(record)

    if keep_last > 0 and len(jobs) > keep_last:
        jobs = jobs[-keep_last:]

    _safe_write_json(JOBS_FILE, jobs)


def list_jobs() -> list[dict[str, Any]]:
    return _safe_read_json(JOBS_FILE)


def delete_job(job_id: str) -> bool:

    jobs = _safe_read_json(JOBS_FILE)
    before = len(jobs)
    jobs = [j for j in jobs if j.get("job_id") != job_id]
    if len(jobs) == before:
        return False
    _safe_write_json(JOBS_FILE, jobs)
    return True


def clear_jobs() -> None:
    _safe_write_json(JOBS_FILE, [])


def job_from_dict(d: dict[str, Any]) -> TTSJob:
    interp = d.get("interpretation")
    interpretation = InterpretationResult(**interp) if isinstance(interp, dict) else None

    settings_raw = d.get("settings") or {}
    settings = TTSSettings(**settings_raw)

    return TTSJob(
        job_id=d.get("job_id", ""),
        text=d.get("text", ""),
        interpretation=interpretation,
        settings=settings,
        output_path=d.get("output_path"),
        created_at_iso=d.get("created_at_iso", ""),
    )
