import pyttsx3

class Pyttsx3Engine:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
        except:
            self.engine = None
        
    def name(self) -> str:
        return "pyttsx3 Local Engine"
        
    def speak(self, text: str, settings) -> None:
        if not self.engine:
            print(f"TTS: {text}")
            return
            
        try:
            self.engine.setProperty('rate', 175)
            self.engine.setProperty('volume', 1.0)
            
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"TTS Error: {e}")
            print(f"Text: {text}")