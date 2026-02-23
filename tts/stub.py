from app_core.models import TTSSettings
from tts.base import TTSEngine


class StubTTSEngine(TTSEngine):
    def name(self) -> str:
        return "stub-tts"

    def synthesize_to_file(self, text: str, settings: TTSSettings, out_path: str) -> str:
        with open(out_path, "wb") as f:
            f.write(b"")
        return out_path
