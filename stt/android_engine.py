from stt.base import STTEngine
import time

class AndroidSTTEngine(STTEngine):
    def __init__(self):
        self.result = None
        self.is_listening = False
        
    def name(self) -> str:
        return "Android Speech Recognition"
    
    def listen_once(self, lang: str = "ro-RO", timeout: float = 5.0, phrase_time_limit: float = 8.0) -> str:
        try:
            return "Salut, acesta este un test pentru aplicația VoxText!"
            
        except Exception as e:
            print(f"Ошибка STT: {e}")
            return "Eroare STT"