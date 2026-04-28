from app_core.models import TTSSettings
from tts.base import TTSEngine


class StubTTSEngine(TTSEngine):
    def name(self) -> str:
        return "stub-tts"

    def speak(self, text: str, settings: TTSSettings, output_path: str | None = None) -> str | None:
        if output_path:
            with open(output_path, "wb") as f:
                f.write(b"")
        return output_path
