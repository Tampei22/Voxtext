from abc import ABC, abstractmethod

class STTEngine(ABC):
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def listen_once(self, lang: str = "ro-RO", timeout: float = 5.0, phrase_time_limit: float = 8.0) -> str:
        raise NotImplementedError