from abc import ABC, abstractmethod
from app_core.models import TTSSettings


class TTSEngine(ABC):
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def speak(self, text: str, settings: TTSSettings) -> None:
        raise NotImplementedError
