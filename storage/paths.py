from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

OUT_DIR = BASE_DIR / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def make_output_path(job_id: str, ext: str = "mp3") -> str:
    return str(OUT_DIR / f"{job_id}.{ext}")
