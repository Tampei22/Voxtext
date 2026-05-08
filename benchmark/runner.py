"""
BenchmarkRunner — Whisper vs Google live microphone benchmark.

For each phrase the flow is:
  1. on_show_phrase(idx, total, text) — caller displays the phrase to the user
  2. Sleep PRE_WAIT_S (user reads the phrase)
  3. Record from microphone until silence or manual stop
  4. Transcribe in parallel: faster-whisper + Google Speech Recognition
  5. on_phrase_result(idx, total, PhraseResult) — caller updates the UI

Audio is optionally saved to a session folder (phrase_01.wav … phrase_N.wav
+ results.json) so the same recordings can be re-run with different models
without re-reading the phrases.  Use run_from_files() for that path.
"""
import concurrent.futures
import os
import platform
import queue
import threading
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

import numpy as np

from benchmark.metrics import word_error_rate, char_error_rate

# ── Recording constants ────────────────────────────────────────────────────
SAMPLE_RATE = 16_000
CHUNK_SIZE = 1024                   # ~64 ms per chunk at 16 kHz
PRE_WAIT_S = 1.2                    # pause before mic opens (user reads phrase)
SILENCE_RMS_THRESHOLD = 0.012       # energy below this = silence
MIN_SPEECH_S = 0.4                  # minimum voiced segment before silence ends recording
SILENCE_AFTER_SPEECH_S = 1.5       # consecutive silence that ends recording
NO_SPEECH_TIMEOUT_S = 6.0          # give up if no speech heard at all
MAX_RECORD_S = 20.0                 # hard cap per phrase

_LANG_TO_STT = {"ro": "ro-RO", "ru": "ru-RU", "en": "en-US"}

# Initial prompts anchor Whisper to the correct language and diacritics on short clips.
_INITIAL_PROMPT = {
    "ro": (
        "Aceasta este o conversație în limba română cu cuvinte uzuale: "
        "bună ziua, mulțumesc, vă rog, astăzi, mâine. "
        "Diacriticele â, ă, î, ș, ț sunt importante."
    ),
    "ru": "Это разговор на русском языке.",
    "en": "This is an English conversation.",
}


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class PhraseResult:
    phrase_id: int
    reference: str
    audio_duration_s: float = 0.0
    whisper_text: str = ""
    whisper_wer: float = 1.0
    whisper_cer: float = 1.0
    whisper_time_s: float = 0.0
    whisper_rtf: float = 0.0
    whisper_error: str = ""
    google_text: str = ""
    google_wer: float = 1.0
    google_cer: float = 1.0
    google_time_s: float = 0.0
    google_rtf: float = 0.0
    google_error: str = ""


@dataclass
class BenchmarkReport:
    lang: str
    whisper_model: str
    phrases: list[PhraseResult] = field(default_factory=list)

    def _ok(self, engine: str) -> list[PhraseResult]:
        return [p for p in self.phrases if not getattr(p, f"{engine}_error")]

    @property
    def whisper_avg_wer(self) -> float:
        ok = self._ok("whisper")
        return sum(p.whisper_wer for p in ok) / len(ok) if ok else 1.0

    @property
    def whisper_avg_cer(self) -> float:
        ok = self._ok("whisper")
        return sum(p.whisper_cer for p in ok) / len(ok) if ok else 1.0

    @property
    def whisper_avg_rtf(self) -> float:
        ok = self._ok("whisper")
        return sum(p.whisper_rtf for p in ok) / len(ok) if ok else 0.0

    @property
    def google_avg_wer(self) -> float:
        ok = self._ok("google")
        return sum(p.google_wer for p in ok) / len(ok) if ok else 1.0

    @property
    def google_avg_cer(self) -> float:
        ok = self._ok("google")
        return sum(p.google_cer for p in ok) / len(ok) if ok else 1.0

    @property
    def google_avg_rtf(self) -> float:
        ok = self._ok("google")
        return sum(p.google_rtf for p in ok) / len(ok) if ok else 0.0

    def to_json_dict(self) -> dict:
        return {
            "metadata": {
                "language": self.lang,
                "whisper_model": self.whisper_model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_phrases": len(self.phrases),
                "hardware": platform.processor() or platform.machine() or "unknown",
            },
            "results": [
                {
                    "phrase_id": p.phrase_id,
                    "reference": p.reference,
                    "audio_duration_s": round(p.audio_duration_s, 3),
                    "whisper": {
                        "transcription": p.whisper_text,
                        "wer": round(p.whisper_wer, 4),
                        "cer": round(p.whisper_cer, 4),
                        "inference_time_s": round(p.whisper_time_s, 3),
                        "rtf": round(p.whisper_rtf, 3),
                        **({"error": p.whisper_error} if p.whisper_error else {}),
                    },
                    "google": {
                        "transcription": p.google_text,
                        "wer": round(p.google_wer, 4),
                        "cer": round(p.google_cer, 4),
                        "inference_time_s": round(p.google_time_s, 3),
                        "rtf": round(p.google_rtf, 3),
                        **({"error": p.google_error} if p.google_error else {}),
                    },
                }
                for p in self.phrases
            ],
            "summary": {
                "whisper_avg_wer": round(self.whisper_avg_wer, 4),
                "whisper_avg_cer": round(self.whisper_avg_cer, 4),
                "whisper_avg_rtf": round(self.whisper_avg_rtf, 3),
                "google_avg_wer": round(self.google_avg_wer, 4),
                "google_avg_cer": round(self.google_avg_cer, 4),
                "google_avg_rtf": round(self.google_avg_rtf, 3),
            },
        }


# ── WAV helpers (stdlib only, no extra deps) ───────────────────────────────

def _save_wav(path: str, audio_np: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Save float32 numpy array as 16-bit mono WAV."""
    audio_i16 = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_i16.tobytes())


def _load_wav(path: str) -> tuple[np.ndarray, float]:
    """Load a 16-bit mono WAV and return (float32 array, duration_s)."""
    with wave.open(path, "rb") as wf:
        n_frames = wf.getnframes()
        sr = wf.getframerate()
        raw = wf.readframes(n_frames)
    audio_i16 = np.frombuffer(raw, dtype=np.int16)
    audio_f32 = audio_i16.astype(np.float32) / 32768.0
    duration_s = len(audio_f32) / sr
    return audio_f32, duration_s


# ── Runner ─────────────────────────────────────────────────────────────────

class BenchmarkRunner:
    """
    Runs the live microphone Whisper vs Google benchmark.

    Parameters
    ----------
    lang : str
        ISO-639-1 code ("ro", "ru", "en").
    whisper_model : str
        faster-whisper model size ("tiny", "base", "small", "medium").
    on_show_phrase : callable, optional
        Called as on_show_phrase(idx, total, phrase_text) BEFORE recording.
    on_phrase_result : callable, optional
        Called as on_phrase_result(idx, total, PhraseResult) AFTER transcription.
    abort : threading.Event, optional
        Set this to cancel the benchmark between phrases.
    session_dir : str, optional
        If set, each recorded phrase is saved as phrase_01.wav … phrase_N.wav
        in this directory, and results.json is written at the end.
    """

    def __init__(
        self,
        lang: str = "ro",
        whisper_model: str = "small",
        on_show_phrase: Optional[Callable[[int, int, str], None]] = None,
        on_phrase_result: Optional[Callable[[int, int, "PhraseResult"], None]] = None,
        abort: Optional[threading.Event] = None,
        session_dir: Optional[str] = None,
    ) -> None:
        self.lang = lang
        self.whisper_model = whisper_model
        self.on_show_phrase = on_show_phrase
        self.on_phrase_result = on_phrase_result
        self._abort = abort or threading.Event()
        self._stop_rec = threading.Event()
        self._whisper_model_obj = None
        self.session_dir = session_dir
        if session_dir:
            os.makedirs(session_dir, exist_ok=True)

    def stop_current_recording(self) -> None:
        """Signal the in-progress recording to end immediately."""
        self._stop_rec.set()

    # ── Public API ─────────────────────────────────────────────────────────

    def run(self, phrases: list[str]) -> BenchmarkReport:
        """Record each phrase from the microphone, then transcribe both engines."""
        report = BenchmarkReport(lang=self.lang, whisper_model=self.whisper_model)
        total = len(phrases)

        self._ensure_whisper()

        for idx, phrase in enumerate(phrases):
            if self._abort.is_set():
                break

            if self.on_show_phrase:
                self.on_show_phrase(idx, total, phrase)

            time.sleep(PRE_WAIT_S)

            if self._abort.is_set():
                break

            self._stop_rec.clear()
            try:
                audio_np, audio_dur = self._record_phrase()
            except Exception as exc:
                result = PhraseResult(phrase_id=idx + 1, reference=phrase)
                result.whisper_error = f"Mic error: {exc}"
                result.google_error = f"Mic error: {exc}"
                report.phrases.append(result)
                if self.on_phrase_result:
                    self.on_phrase_result(idx, total, result)
                continue

            if self.session_dir:
                wav_path = os.path.join(
                    self.session_dir, f"phrase_{idx + 1:02d}.wav"
                )
                try:
                    _save_wav(wav_path, audio_np)
                except Exception:
                    pass

            result = self._transcribe_both(idx, phrase, audio_np, audio_dur)
            report.phrases.append(result)
            if self.on_phrase_result:
                self.on_phrase_result(idx, total, result)

        if self.session_dir and report.phrases:
            import json
            results_path = os.path.join(self.session_dir, "results.json")
            try:
                with open(results_path, "w", encoding="utf-8") as f:
                    json.dump(report.to_json_dict(), f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        return report

    def run_from_files(
        self, session_dir: str, phrases: list[str]
    ) -> BenchmarkReport:
        """
        Re-run transcription + metrics on previously saved .wav files.
        No microphone recording takes place.  Use this to test a different
        Whisper model on the same recordings.

        Expects files named phrase_01.wav, phrase_02.wav, … in session_dir.
        """
        report = BenchmarkReport(lang=self.lang, whisper_model=self.whisper_model)
        total = len(phrases)

        self._ensure_whisper()

        for idx, phrase in enumerate(phrases):
            if self._abort.is_set():
                break

            wav_path = os.path.join(session_dir, f"phrase_{idx + 1:02d}.wav")

            if self.on_show_phrase:
                self.on_show_phrase(idx, total, phrase)

            if not os.path.exists(wav_path):
                result = PhraseResult(phrase_id=idx + 1, reference=phrase)
                result.whisper_error = f"File missing: {os.path.basename(wav_path)}"
                result.google_error = result.whisper_error
                report.phrases.append(result)
                if self.on_phrase_result:
                    self.on_phrase_result(idx, total, result)
                continue

            try:
                audio_np, audio_dur = _load_wav(wav_path)
            except Exception as exc:
                result = PhraseResult(phrase_id=idx + 1, reference=phrase)
                result.whisper_error = f"Load error: {exc}"
                result.google_error = result.whisper_error
                report.phrases.append(result)
                if self.on_phrase_result:
                    self.on_phrase_result(idx, total, result)
                continue

            result = self._transcribe_both(idx, phrase, audio_np, audio_dur)
            report.phrases.append(result)
            if self.on_phrase_result:
                self.on_phrase_result(idx, total, result)

        return report

    # ── Core transcription step (shared between live and file-based runs) ──

    def _transcribe_both(
        self, idx: int, phrase: str, audio_np: np.ndarray, audio_dur: float
    ) -> "PhraseResult":
        result = PhraseResult(
            phrase_id=idx + 1,
            reference=phrase,
            audio_duration_s=round(audio_dur, 3),
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            w_fut = ex.submit(self._transcribe_whisper, audio_np, audio_dur, idx)
            g_fut = ex.submit(self._transcribe_google, audio_np, audio_dur, idx)

            try:
                w_text, w_time, w_rtf = w_fut.result()
                result.whisper_text = w_text
                result.whisper_time_s = round(w_time, 3)
                result.whisper_rtf = round(w_rtf, 3)
                result.whisper_wer = min(word_error_rate(phrase, w_text), 1.0)
                result.whisper_cer = min(char_error_rate(phrase, w_text), 1.0)
            except Exception as exc:
                result.whisper_error = str(exc)

            try:
                g_text, g_time, g_rtf = g_fut.result()
                result.google_text = g_text
                result.google_time_s = round(g_time, 3)
                result.google_rtf = round(g_rtf, 3)
                result.google_wer = min(word_error_rate(phrase, g_text), 1.0)
                result.google_cer = min(char_error_rate(phrase, g_text), 1.0)
            except Exception as exc:
                result.google_error = str(exc)

        return result

    # ── Recording ──────────────────────────────────────────────────────────

    def _record_phrase(self) -> tuple[np.ndarray, float]:
        """
        Stream from the microphone until silence or manual stop.
        Returns (float32 numpy array at 16 kHz, duration_s).
        """
        import sounddevice as sd

        audio_q: queue.Queue = queue.Queue()
        frames: list[np.ndarray] = []

        silence_chunk_limit = int(SILENCE_AFTER_SPEECH_S * SAMPLE_RATE / CHUNK_SIZE)
        min_speech_chunks = int(MIN_SPEECH_S * SAMPLE_RATE / CHUNK_SIZE)
        no_speech_limit = int(NO_SPEECH_TIMEOUT_S * SAMPLE_RATE / CHUNK_SIZE)
        max_chunks = int(MAX_RECORD_S * SAMPLE_RATE / CHUNK_SIZE)

        had_speech = False
        speech_chunks = 0
        silence_chunks = 0

        def _cb(indata, frame_count, time_info, status):
            audio_q.put(indata[:, 0].copy())

        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK_SIZE,
                callback=_cb,
            )
            stream.start()
        except Exception as exc:
            raise OSError(f"Cannot open microphone: {exc}") from exc

        try:
            while len(frames) < max_chunks:
                if self._stop_rec.is_set() or self._abort.is_set():
                    break
                try:
                    chunk = audio_q.get(timeout=0.3)
                except queue.Empty:
                    continue

                frames.append(chunk)
                rms = float(np.sqrt(np.mean(chunk ** 2)))

                if rms >= SILENCE_RMS_THRESHOLD:
                    had_speech = True
                    speech_chunks += 1
                    silence_chunks = 0
                else:
                    if had_speech:
                        silence_chunks += 1
                        if (silence_chunks >= silence_chunk_limit
                                and speech_chunks >= min_speech_chunks):
                            break
                    elif len(frames) >= no_speech_limit:
                        break
        finally:
            stream.stop()
            stream.close()

        if not frames:
            raise ValueError("No audio captured from microphone")

        audio_np = np.concatenate(frames)
        duration_s = len(audio_np) / SAMPLE_RATE
        return audio_np, duration_s

    # ── Transcription helpers ──────────────────────────────────────────────

    def _ensure_whisper(self):
        if self._whisper_model_obj is None:
            from faster_whisper import WhisperModel
            self._whisper_model_obj = WhisperModel(
                self.whisper_model, device="cpu", compute_type="int8"
            )
        return self._whisper_model_obj

    # DEBUG_IDX: set to an integer phrase index (0-based) to dump WAVs + logs
    # for that phrase only.  None = no debug output.  Remove after diagnosis.
    DEBUG_IDX: int | None = 1

    def _transcribe_whisper(
        self, audio_np: np.ndarray, audio_dur: float, idx: int = -1
    ) -> tuple[str, float, float]:
        model = self._ensure_whisper()

        # Prepend 1.0 s of silence so Whisper has context before very short first words
        # ("Vă", "Am", "Îmi").  Applied only to the in-memory copy — .wav files unchanged.
        pad_samples = int(1.0 * SAMPLE_RATE)
        audio_padded = np.concatenate(
            [np.zeros(pad_samples, dtype=audio_np.dtype), audio_np]
        )

        prompt = _INITIAL_PROMPT.get(self.lang, "")
        print(
            f"[Whisper] lang={self.lang},"
            f" audio_dur={audio_dur:.2f}s,"
            f" padded_dur={len(audio_padded) / SAMPLE_RATE:.2f}s,"
            f" prompt_chars={len(prompt)}"
        )

        t0 = time.perf_counter()
        segments, info = model.transcribe(
            audio_padded,
            language=self.lang,
            task="transcribe",
            beam_size=5,
            vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt=prompt,
            temperature=0.0,
            no_speech_threshold=0.6,
            # Tightened from -1.0 — rejects low-confidence segments (hallucinations).
            log_prob_threshold=-0.5,
            # Tightened from 2.4 — stops infinite-loop repeats like "deci, deci, deci".
            compression_ratio_threshold=1.8,
            # Cuts hallucinations that fall on silent regions within the audio.
            hallucination_silence_threshold=0.5,
        )
        # Materialise the lazy generator so elapsed time covers full inference.
        segment_list = list(segments)
        elapsed = time.perf_counter() - t0

        print(
            f"[Whisper] detected_lang={info.language},"
            f" prob={info.language_probability:.2f}"
        )

        text = " ".join(s.text.strip() for s in segment_list).strip()
        rtf = elapsed / audio_dur if audio_dur > 0 else 0.0
        return text, elapsed, rtf

    def _transcribe_google(
        self, audio_np: np.ndarray, audio_dur: float, idx: int = -1
    ) -> tuple[str, float, float]:
        import speech_recognition as sr

        if idx == self.DEBUG_IDX:
            print(
                f"[DEBUG-GOOGLE]  phrase {idx+1} | "
                f"dtype={audio_np.dtype} | "
                f"min={audio_np.min():.4f}  max={audio_np.max():.4f} | "
                f"samples={len(audio_np)} | "
                f"dur_via_SR={len(audio_np)/SAMPLE_RATE:.3f}s | "
                f"dur_reported={audio_dur:.3f}s"
            )
            _save_wav("debug_audio_FOR_GOOGLE.wav", audio_np)
            print("[DEBUG-GOOGLE]  saved  debug_audio_FOR_GOOGLE.wav")

        # Convert float32 [-1, 1] → int16 PCM bytes
        audio_i16 = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16)
        audio_data = sr.AudioData(audio_i16.tobytes(), SAMPLE_RATE, 2)

        recognizer = sr.Recognizer()
        stt_lang = _LANG_TO_STT.get(self.lang, "en-US")

        t0 = time.perf_counter()
        text = recognizer.recognize_google(audio_data, language=stt_lang)
        elapsed = time.perf_counter() - t0

        if idx == self.DEBUG_IDX:
            print(f"[DEBUG-GOOGLE]  transcription: {text!r}")

        rtf = elapsed / audio_dur if audio_dur > 0 else 0.0
        return text, elapsed, rtf
