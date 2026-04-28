import subprocess
import sys

from app_core.constants import DEFAULT_TTS_RATE, DEFAULT_TTS_VOLUME
from app_core.logger import get_logger

_logger = get_logger(__name__)


class Pyttsx3Engine:

    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def name(self) -> str:
        return "pyttsx3 Local Engine"

    def speak(self, text: str, settings, output_path: str | None = None) -> str | None:
        rate = settings.rate if (settings and settings.rate) else DEFAULT_TTS_RATE
        volume = settings.volume if (settings and settings.volume is not None) else DEFAULT_TTS_VOLUME

        script = "\n".join([
            "import pyttsx3",
            "e = pyttsx3.init()",
            f"e.setProperty('rate', {int(rate)})",
            f"e.setProperty('volume', {float(volume)})",
            f"e.say({repr(text)})",
            "e.runAndWait()",
        ])

        try:
            self._proc = subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._proc.wait()
        except Exception as e:
            _logger.error("pyttsx3 speak failed: %s", e)
        finally:
            self._proc = None
        return None

    def stop(self) -> None:
        proc = self._proc
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
