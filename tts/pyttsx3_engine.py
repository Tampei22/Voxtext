import subprocess
import sys


class Pyttsx3Engine:

    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def name(self) -> str:
        return "pyttsx3 Local Engine"

    def speak(self, text: str, settings) -> None:
        rate = settings.rate if (settings and settings.rate) else 175
        volume = settings.volume if (settings and settings.volume is not None) else 1.0

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
            print(f"TTS Error: {e}")
        finally:
            self._proc = None

    def stop(self) -> None:
        proc = self._proc
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
