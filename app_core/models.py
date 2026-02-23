from dataclasses import dataclass, field
from typing import Any


@dataclass
class InterpretationResult:
    clean_text: str
    language: str
    segments: list[str]
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSSettings:
    voice_id: str | None = None
    rate: int = 175
    volume: float = 1.0
    lang: str | None = None


@dataclass
class TTSJob:
    job_id: str
    text: str
    interpretation: InterpretationResult | None
    settings: TTSSettings
    output_path: str | None
    created_at_iso: str
