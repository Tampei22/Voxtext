"""WhisperSTTEngine — faster-whisper primary STT with silero-vad phrase streaming."""
import logging
import queue
import threading
from collections import deque

import numpy as np

from stt.base import STTEngine

_logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
VAD_CHUNK = 512          # silero-vad requires exactly 512 samples at 16 kHz
PRE_ROLL_CHUNKS = 6      # ~192 ms prepended before VAD fires, avoids clipping phrase start
CHUNK_SEC = VAD_CHUNK / SAMPLE_RATE   # 0.032 s per chunk

_LANG_MAP: dict[str, str] = {
    "ro-RO": "ro", "ru-RU": "ru",
    "en-US": "en", "en-GB": "en",
}
VALID_MODELS = ("tiny", "base", "small", "medium")


class WhisperSTTEngine(STTEngine):
    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        if model_size not in VALID_MODELS:
            model_size = "small"
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None
        self._vad_model = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._session_phrases: list = []

    # ------------------------------------------------------------------ #
    # Lazy loaders
    # ------------------------------------------------------------------ #

    def _ensure_whisper(self) -> None:
        if self._model is None:
            from faster_whisper import WhisperModel
            _logger.info("Loading Whisper model '%s'...", self._model_size)
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )

    def _ensure_vad(self):
        if self._vad_model is None:
            from silero_vad import load_silero_vad
            _logger.info("Loading Silero VAD...")
            self._vad_model = load_silero_vad()
        return self._vad_model

    # ------------------------------------------------------------------ #
    # STTEngine interface
    # ------------------------------------------------------------------ #

    def name(self) -> str:
        return f"Whisper ({self._model_size})"

    def listen_once(
        self,
        lang: str = "ro-RO",
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0,
    ) -> str:
        import sounddevice as sd

        self._ensure_whisper()
        self._session_phrases = []
        whisper_lang = _LANG_MAP.get(lang, lang.split("-")[0])

        try:
            audio = sd.rec(
                int(phrase_time_limit * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
            )
            sd.wait()
        except Exception as exc:
            raise OSError(f"Microphone error: {exc}") from exc

        from app_core.models import STTPhrase
        segments, _ = self._model.transcribe(
            audio.flatten(),
            language=whisper_lang,
            beam_size=5,
            vad_filter=True,
        )
        text_parts = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                text_parts.append(text)
                self._session_phrases.append(
                    STTPhrase(text=text, start=seg.start, end=seg.end)
                )
        full_text = " ".join(text_parts).strip()
        if not full_text:
            raise ValueError("No speech detected")
        return full_text

    def start_listening(
        self,
        on_result,
        on_error,
        lang: str = "ro-RO",
    ) -> None:
        self._session_phrases = []
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._vad_loop,
            args=(on_result, on_error, lang),
            daemon=True,
        )
        self._thread.start()

    def stop_listening(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def get_session_phrases(self) -> list:
        """Return a snapshot of STTPhrase objects from the last recording session."""
        return list(self._session_phrases)

    # ------------------------------------------------------------------ #
    # Continuous VAD + Whisper loop
    # ------------------------------------------------------------------ #

    def _vad_loop(self, on_result, on_error, lang: str) -> None:
        try:
            self._ensure_whisper()
            vad_model = self._ensure_vad()
        except Exception as exc:
            on_error(str(exc))
            return

        import sounddevice as sd
        import torch
        from silero_vad import VADIterator

        whisper_lang = _LANG_MAP.get(lang, lang.split("-")[0])
        vad_iter = VADIterator(
            vad_model,
            sampling_rate=SAMPLE_RATE,
            threshold=0.5,
            min_silence_duration_ms=600,
        )

        audio_q: queue.Queue = queue.Queue()
        speech_chunks: list[np.ndarray] = []
        in_speech = False
        pre_roll: deque[np.ndarray] = deque(maxlen=PRE_ROLL_CHUNKS)
        chunk_count = 0
        speech_offset_sec = 0.0

        def _sd_callback(indata, frames, time_info, status):
            audio_q.put(indata[:, 0].copy())

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=VAD_CHUNK,
                callback=_sd_callback,
            ):
                while not self._stop_event.is_set():
                    try:
                        chunk = audio_q.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    chunk_count += 1
                    vad_out = vad_iter(torch.from_numpy(chunk), return_seconds=False)

                    # Accumulate pre-roll while silent (chunk already added to pre_roll)
                    if not in_speech:
                        pre_roll.append(chunk)

                    if vad_out:
                        if "start" in vad_out:
                            in_speech = True
                            # pre_roll already contains the current chunk (appended above),
                            # so list(pre_roll) is the complete audio buffer without duplication.
                            speech_offset_sec = max(
                                0.0, (chunk_count - len(pre_roll)) * CHUNK_SEC
                            )
                            speech_chunks = list(pre_roll)
                            pre_roll.clear()
                        if "end" in vad_out and in_speech:
                            in_speech = False
                            audio_np = np.concatenate(speech_chunks)
                            speech_chunks = []
                            self._transcribe_emit(
                                audio_np, whisper_lang,
                                on_result, on_error,
                                speech_offset_sec,
                            )
                    elif in_speech:
                        speech_chunks.append(chunk)
        except Exception as exc:
            if not self._stop_event.is_set():
                on_error(str(exc))
        finally:
            vad_iter.reset_states()

    def _transcribe_emit(
        self,
        audio: np.ndarray,
        lang: str,
        on_result,
        on_error,
        time_offset: float = 0.0,
    ) -> None:
        try:
            from app_core.models import STTPhrase
            segments, _ = self._model.transcribe(
                audio, language=lang, beam_size=5, vad_filter=False
            )
            phrases = []
            text_parts = []
            for seg in segments:
                text = seg.text.strip()
                if text:
                    text_parts.append(text)
                    phrases.append(
                        STTPhrase(
                            text=text,
                            start=time_offset + seg.start,
                            end=time_offset + seg.end,
                        )
                    )
            self._session_phrases.extend(phrases)
            full_text = " ".join(text_parts).strip()
            if full_text:
                on_result(full_text)
        except Exception as exc:
            on_error(str(exc))
