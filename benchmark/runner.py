"""
BenchmarkRunner — compares WhisperSTTEngine vs Google Speech Recognition.

Audio ground-truth is synthesised with pyttsx3 so the exact wording is known
and WER can be computed.  A single subprocess call generates all WAV files
before timing begins, keeping inference measurements clean.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

from benchmark.metrics import word_error_rate

_LANG_TO_STT = {"ro": "ro-RO", "ru": "ru-RU", "en": "en-US"}


@dataclass
class PhraseResult:
    reference: str
    whisper_text: str = ""
    whisper_wer: float = 1.0
    whisper_time_s: float = 0.0
    whisper_error: str = ""
    google_text: str = ""
    google_wer: float = 1.0
    google_time_s: float = 0.0
    google_error: str = ""


@dataclass
class BenchmarkReport:
    lang: str
    whisper_model: str
    phrases: list[PhraseResult] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Aggregate stats (skip errored phrases)
    # ------------------------------------------------------------------ #

    def _ok(self, engine: str) -> list[PhraseResult]:
        return [p for p in self.phrases if not getattr(p, f"{engine}_error")]

    @property
    def whisper_avg_wer(self) -> float:
        ok = self._ok("whisper")
        return sum(p.whisper_wer for p in ok) / len(ok) if ok else 1.0

    @property
    def google_avg_wer(self) -> float:
        ok = self._ok("google")
        return sum(p.google_wer for p in ok) / len(ok) if ok else 1.0

    @property
    def whisper_avg_time(self) -> float:
        ok = self._ok("whisper")
        return sum(p.whisper_time_s for p in ok) / len(ok) if ok else 0.0

    @property
    def google_avg_time(self) -> float:
        ok = self._ok("google")
        return sum(p.google_time_s for p in ok) / len(ok) if ok else 0.0

    def to_json_dict(self) -> dict:
        from datetime import datetime, timezone
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lang": self.lang,
            "whisper_model": self.whisper_model,
            "summary": {
                "phrases_tested": len(self.phrases),
                "whisper_ok": len(self._ok("whisper")),
                "google_ok": len(self._ok("google")),
                "whisper_avg_wer": round(self.whisper_avg_wer, 4),
                "whisper_avg_time_s": round(self.whisper_avg_time, 3),
                "google_avg_wer": round(self.google_avg_wer, 4),
                "google_avg_time_s": round(self.google_avg_time, 3),
            },
            "phrases": [asdict(p) for p in self.phrases],
        }


class BenchmarkRunner:
    """
    Runs the Whisper vs Google benchmark on a list of reference phrases.

    Parameters
    ----------
    lang : str
        ISO-639-1 code ("ro", "ru", "en").
    whisper_model : str
        faster-whisper model name ("tiny", "base", "small", "medium").
    on_progress : callable, optional
        Called as ``on_progress(current_idx, total, phrase)`` after each phrase.
    """

    def __init__(
        self,
        lang: str = "ro",
        whisper_model: str = "small",
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        self.lang = lang
        self.whisper_model = whisper_model
        self.on_progress = on_progress
        self._model = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(self, phrases: list[str]) -> BenchmarkReport:
        report = BenchmarkReport(lang=self.lang, whisper_model=self.whisper_model)

        # Pre-warm Whisper (model loading excluded from per-phrase timing)
        self._ensure_whisper()

        # Generate all WAV files in one subprocess call
        wav_paths = self._generate_all_wav(phrases)

        for i, (phrase, wav) in enumerate(zip(phrases, wav_paths)):
            if self.on_progress:
                self.on_progress(i, len(phrases), phrase)

            result = PhraseResult(reference=phrase)

            if wav is None:
                msg = "Audio generation failed"
                result.whisper_error = msg
                result.google_error = msg
                report.phrases.append(result)
                continue

            # Whisper
            try:
                text, elapsed = self._transcribe_whisper(wav)
                result.whisper_text = text
                result.whisper_time_s = elapsed
                result.whisper_wer = min(word_error_rate(phrase, text), 1.0)
            except Exception as exc:
                result.whisper_error = str(exc)

            # Google (may fail if offline — not fatal)
            try:
                text, elapsed = self._transcribe_google(wav)
                result.google_text = text
                result.google_time_s = elapsed
                result.google_wer = min(word_error_rate(phrase, text), 1.0)
            except Exception as exc:
                result.google_error = str(exc)

            # Clean up temp file
            try:
                os.unlink(wav)
            except OSError:
                pass

            report.phrases.append(result)

        if self.on_progress:
            self.on_progress(len(phrases), len(phrases), "")

        return report

    # ------------------------------------------------------------------ #
    # Audio generation
    # ------------------------------------------------------------------ #

    def _generate_all_wav(self, phrases: list[str]) -> list[Optional[str]]:
        """
        Generate one WAV per phrase via a single pyttsx3 subprocess.
        Returns a parallel list of file paths (None on failure).
        """
        tmpdir = tempfile.mkdtemp(prefix="voxbench_")
        paths = [os.path.join(tmpdir, f"p{i:03d}.wav") for i in range(len(phrases))]
        payload = json.dumps(list(zip(phrases, paths)))

        script = (
            "import pyttsx3, json\n"
            f"data = json.loads({payload!r})\n"
            "e = pyttsx3.init()\n"
            "e.setProperty('rate', 150)\n"
            "for text, path in data:\n"
            "    e.save_to_file(text, path)\n"
            "e.runAndWait()\n"
        )
        try:
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.decode(errors="replace"))
        except Exception:
            return [None] * len(phrases)

        return [p if os.path.exists(p) else None for p in paths]

    # ------------------------------------------------------------------ #
    # Transcription helpers
    # ------------------------------------------------------------------ #

    def _ensure_whisper(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.whisper_model, device="cpu", compute_type="int8"
            )
        return self._model

    def _transcribe_whisper(self, wav_path: str) -> tuple[str, float]:
        model = self._ensure_whisper()
        t0 = time.perf_counter()
        # Pass file path — faster-whisper resamples to 16 kHz internally
        segments, _ = model.transcribe(wav_path, language=self.lang, beam_size=5)
        text = " ".join(s.text.strip() for s in segments).strip()
        return text, time.perf_counter() - t0

    def _transcribe_google(self, wav_path: str) -> tuple[str, float]:
        import speech_recognition as sr
        stt_lang = _LANG_TO_STT.get(self.lang, "en-US")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        t0 = time.perf_counter()
        text = recognizer.recognize_google(audio, language=stt_lang)
        return text, time.perf_counter() - t0
