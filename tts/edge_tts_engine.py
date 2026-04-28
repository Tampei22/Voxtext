import subprocess
import sys


class EdgeTTSEngine:

    VOICES_BY_LANG: dict[str, list[tuple[str, str]]] = {
        "ro": [
            ("Alina (Ж)", "ro-RO-AlinaNeural"),
            ("Emil (М)",  "ro-RO-EmilNeural"),
        ],
        "ru": [
            ("Светлана (Ж)", "ru-RU-SvetlanaNeural"),
            ("Дмитрий (М)",  "ru-RU-DmitryNeural"),
        ],
        "en": [
            ("Jenny (Ж)", "en-US-JennyNeural"),
            ("Guy (М)",   "en-US-GuyNeural"),
            ("Aria (Ж)",  "en-US-AriaNeural"),
        ],
    }

    def __init__(self, voice: str | None = None):
    
        self._override_voice = voice
        self._proc: subprocess.Popen | None = None

    def name(self) -> str:
        return "Edge TTS Neural"

    def speak(self, text: str, settings, output_path: str | None = None) -> str | None:
        lang_key = ((settings.lang or "ro") if settings else "ro").split("-")[0]
        if self._override_voice:
            voice = self._override_voice
        elif settings and settings.voice_id:
            voice = settings.voice_id
        else:
            voices = self.VOICES_BY_LANG.get(lang_key, self.VOICES_BY_LANG["ro"])
            voice = voices[0][1]

        rate_val = settings.rate if (settings and settings.rate) else 175
        rate_pct = int((rate_val - 175) / 175 * 100)
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

        out_path_repr = repr(output_path)

        script = f"""import asyncio, os, tempfile
import pygame
import edge_tts

async def main():
    communicate = edge_tts.Communicate({repr(text)}, {repr(voice)}, rate={repr(rate_str)})
    out_path = {out_path_repr}
    use_temp = out_path is None
    if use_temp:
        out_path = tempfile.mktemp(suffix='.mp3')
    await communicate.save(out_path)
    pygame.mixer.init()
    pygame.mixer.music.load(out_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)
    pygame.mixer.quit()
    if use_temp:
        try:
            os.unlink(out_path)
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

        return output_path

    def stop(self) -> None:
        proc = self._proc
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
