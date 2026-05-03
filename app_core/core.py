import uuid
from datetime import datetime, timezone

from app_core.logger import get_logger
from app_core.models import TTSJob, TTSSettings
from app_core.constants import MAX_TTS_TEXT_LENGTH
from stt.base import STTEngine
from storage.paths import make_output_path
from text_interpreter.interpreter import interpret
from tts.base import TTSEngine

_logger = get_logger(__name__)


class AppCore:
    def __init__(
        self,
        tts_engine: TTSEngine,
        stt_engine: STTEngine | None = None,
        fallback_tts: TTSEngine | None = None,
        fallback_stt: STTEngine | None = None,
    ) -> None:
        self.tts = tts_engine
        self.stt = stt_engine
        self._fallback_tts = fallback_tts
        self._fallback_stt = fallback_stt

    def interpret_text(self, text: str):
        return interpret(text)

    def listen_text(self, lang: str = "ro-RO") -> str:
        if not self.stt:
            raise RuntimeError("STT engine not set.")
        try:
            return self.stt.listen_once(lang=lang)
        except Exception as primary_err:
            if self._fallback_stt is None:
                raise
            _logger.warning(
                "Primary STT (%s) failed, switching to fallback (%s): %s",
                self.stt.name(), self._fallback_stt.name(), primary_err,
            )
            return self._fallback_stt.listen_once(lang=lang)

    def start_stt(self, on_result, on_error, lang: str = "ro-RO") -> None:
        engine = self.stt
        if not engine:
            on_error("No STT engine configured")
            return
        if hasattr(engine, "start_listening"):
            engine.start_listening(on_result, on_error, lang)
        else:
            on_error("Engine does not support continuous listening")

    def stop_stt(self) -> None:
        if self.stt and hasattr(self.stt, "stop_listening"):
            self.stt.stop_listening()

    def speak_text(self, text: str, settings: TTSSettings) -> TTSJob:
        interpretation = interpret(text)
        job_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()

        try:
            saved_path = self.tts.speak(
                interpretation.clean_text, settings, output_path=make_output_path(job_id)
            )
        except Exception as primary_err:
            if self._fallback_tts is None:
                raise
            _logger.warning(
                "Primary TTS (%s) failed, switching to fallback (%s): %s",
                self.tts.name(), self._fallback_tts.name(), primary_err,
            )
            saved_path = self._fallback_tts.speak(interpretation.clean_text, settings)

        job = TTSJob(
            job_id=job_id,
            text=text,
            interpretation=interpretation,
            settings=settings,
            output_path=saved_path,
            created_at_iso=created_at,
        )
        from storage.jobs import save_job
        save_job(job)
        return job
