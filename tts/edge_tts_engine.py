import subprocess
import sys


class EdgeTTSEngine:
    
    VOICES = {
        "ro":    "ro-RO-AlinaNeural",
        "ro-RO": "ro-RO-AlinaNeural",
        "ru":    "ru-RU-SvetlanaNeural",
        "ru-RU": "ru-RU-SvetlanaNeural",
        "en":    "en-US-JennyNeural",
        "en-US": "en-US-JennyNeural",
    }

    def __init__(self, voice: str | None = None):
    
        self._override_voice = voice
        self._proc: subprocess.Popen | None = None

    def name(self) -> str:
        return "Edge TTS Neural"

    def speak(self, text: str, settings) -> None:
        lang = (settings.lang if settings and settings.lang else "ro")
        voice = self._override_voice or self.VOICES.get(lang, "ro-RO-AlinaNeural")

        rate_val = settings.rate if (settings and settings.rate) else 175
        rate_pct = int((rate_val - 175) / 175 * 100)
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

        script = f"""import asyncio, os, tempfile
import pygame
import edge_tts

async def main():
    communicate = edge_tts.Communicate({repr(text)}, {repr(voice)}, rate={repr(rate_str)})
    tmp = tempfile.mktemp(suffix='.mp3')
    await communicate.save(tmp)
    pygame.mixer.init()
    pygame.mixer.music.load(tmp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)
    pygame.mixer.quit()
    try:
        os.unlink(tmp)
    except Exception:
        pass

asyncio.run(main())
"""

        try:
            self._proc = subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            _, stderr_bytes = self._proc.communicate()
            if self._proc.returncode != 0:
                err = stderr_bytes.decode("utf-8", errors="replace").strip()
                last_line = err.splitlines()[-1] if err else "TTS subprocess failed"
                raise RuntimeError(last_line)
        finally:
            self._proc = None

    def stop(self) -> None:
        proc = self._proc
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
