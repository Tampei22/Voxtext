import re
from app_core.models import InterpretationResult


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def normalize_text(text: str) -> str:
    text = text.replace("\u00A0", " ")          
    text = re.sub(r"\s+", " ", text).strip()   
    return text

def detect_language(text: str) -> str:
    return "ro"

def split_to_segments(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]

def interpret(text: str) -> InterpretationResult:
    clean = normalize_text(text)
    lang = detect_language(clean)
    segments = split_to_segments(clean)

    words = clean.split() if clean else []
    stats = {
        "chars": len(clean),
        "words": len(words),
        "segments": len(segments),
    }

    return InterpretationResult(
        clean_text=clean,
        language=lang,
        segments=segments,
        stats=stats,
    )
