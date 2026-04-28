from abc import ABC, abstractmethod
from app_core.models import TTSSettings


class TTSEngine(ABC):
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def speak(self, text: str, settings: TTSSettings, output_path: str | None = None) -> str | None:
        raise NotImplementedError
