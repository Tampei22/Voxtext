import uuid
from datetime import datetime, timezone
from stt.base import STTEngine

from app_core.models import TTSJob, TTSSettings
from text_interpreter.interpreter import interpret
from tts.base import TTSEngine

class AppCore:
    def __init__(self, tts_engine: TTSEngine, stt_engine: STTEngine | None = None) -> None:
        self.tts = tts_engine
        self.stt = stt_engine

    def interpret_text(self, text: str):
        return interpret(text)
    
    def listen_text(self, lang: str = "ro-RO") -> str:
        if not self.stt:
            raise RuntimeError("STT engine not set.")
        return self.stt.listen_once(lang=lang)

    def speak_text(self, text: str, settings: TTSSettings) -> TTSJob:
        interpretation = interpret(text)

        job_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()

        self.tts.speak(interpretation.clean_text, settings)

        job = TTSJob(
            job_id=job_id,
            text=text,
            interpretation=interpretation,
            settings=settings,
            output_path=None,
            created_at_iso=created_at,
        )
        from storage.jobs import save_job
        save_job(job)

        return job