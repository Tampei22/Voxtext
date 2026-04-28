import json
from dataclasses import dataclass, asdict
from pathlib import Path

from app_core.constants import (
    DEFAULT_TTS_RATE,
    DEFAULT_TTS_VOLUME,
    DEFAULT_STT_PAUSE_THRESHOLD,
    DEFAULT_MAX_HISTORY,
)
from app_core.models import TTSSettings
from storage.paths import BASE_DIR

SETTINGS_FILE: Path = BASE_DIR / "settings.json"

_LANG_TO_STT = {"ro": "ro-RO", "ru": "ru-RU", "en": "en-US"}


@dataclass
class AppSettings:
    lang: str = "ro"
    voice_id: str | None = None
    tts_rate: int = DEFAULT_TTS_RATE
    tts_volume: float = DEFAULT_TTS_VOLUME
    stt_pause_threshold: float = DEFAULT_STT_PAUSE_THRESHOLD
    max_history: int = DEFAULT_MAX_HISTORY
    theme: str = "dark"
    font_scale: float = 1.0

    def tts_settings(self) -> TTSSettings:
        return TTSSettings(
            lang=self.lang,
            voice_id=self.voice_id,
            rate=self.tts_rate,
            volume=self.tts_volume,
        )

    def stt_lang(self) -> str:
        return _LANG_TO_STT.get(self.lang, "ro-RO")


_DEFAULTS = AppSettings()


def load_app_settings() -> AppSettings:
    if not SETTINGS_FILE.exists():
        return AppSettings()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "tts" in data and isinstance(data["tts"], dict):
            tts = data["tts"]
            data = {
                "lang": tts.get("lang", _DEFAULTS.lang),
                "voice_id": tts.get("voice_id", _DEFAULTS.voice_id),
                "tts_rate": tts.get("rate", _DEFAULTS.tts_rate),
                "tts_volume": tts.get("volume", _DEFAULTS.tts_volume),
                "stt_pause_threshold": _DEFAULTS.stt_pause_threshold,
                "max_history": _DEFAULTS.max_history,
            }
        return AppSettings(
            lang=data.get("lang", _DEFAULTS.lang),
            voice_id=data.get("voice_id", _DEFAULTS.voice_id),
            tts_rate=int(data.get("tts_rate", _DEFAULTS.tts_rate)),
            tts_volume=float(data.get("tts_volume", _DEFAULTS.tts_volume)),
            stt_pause_threshold=float(data.get("stt_pause_threshold", _DEFAULTS.stt_pause_threshold)),
            max_history=int(data.get("max_history", _DEFAULTS.max_history)),
            theme=data.get("theme", _DEFAULTS.theme),
            font_scale=float(data.get("font_scale", _DEFAULTS.font_scale)),
        )
    except Exception:
        return AppSettings()


def save_app_settings(settings: AppSettings) -> None:
    data = asdict(settings)
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(SETTINGS_FILE)
