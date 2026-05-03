from dataclasses import dataclass, field
from typing import Any, List


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


@dataclass
class STTPhrase:
    text: str
    start: float  # seconds from recording start
    end: float    # seconds from recording start


@dataclass
class STTSession:
    session_id: str
    lang: str
    engine: str
    created_at_iso: str
    phrases: List[STTPhrase]

    @property
    def full_text(self) -> str:
        return " ".join(p.text.strip() for p in self.phrases)

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())
