import speech_recognition as sr

from stt.base import STTEngine


class SpeechRecognitionEngine(STTEngine):

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self._stop_fn = None

    def name(self) -> str:
        return "Google Speech Recognition"

    def listen_once(self, lang: str = "ro-RO", timeout: float = 5.0, phrase_time_limit: float = 10.0) -> str:
        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self.recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )
        return self.recognizer.recognize_google(audio, language=lang)

    
    def start_listening(self, on_result, on_error, lang: str = "ro-RO"):
      
        if self._stop_fn is not None:
            return  

        mic = sr.Microphone()

        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

        def _callback(recognizer, audio):
            try:
                text = recognizer.recognize_google(audio, language=lang)
                if text:
                    on_result(text)
            except sr.UnknownValueError:
                pass  
            except sr.RequestError as e:
                on_error(f"Ошибка сети: {e}")
            except Exception as e:
                on_error(str(e))

        self._stop_fn = self.recognizer.listen_in_background(
            mic, _callback, phrase_time_limit=10
        )

    def stop_listening(self):
        if self._stop_fn is not None:
            self._stop_fn(wait_for_stop=False)
            self._stop_fn = None
