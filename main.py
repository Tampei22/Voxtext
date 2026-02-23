from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.config import Config

Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

from ui.main_screen import MainScreen
from ui.stt_screen import STTScreen
from ui.tts_screen import TTSScreen
from ui.pdf_screen import PDFScreen

from app_core.core import AppCore
from stt.android_engine import AndroidSTTEngine  
from tts.pyttsx3_engine import Pyttsx3Engine

class VoxTextApp(App):
    def __init__(self):
        super().__init__()

        self.app_core = AppCore(
            tts_engine=Pyttsx3Engine(),
            stt_engine=AndroidSTTEngine()
        )
    
    def build(self):
        self.title = 'VoxText'

        sm = ScreenManager()

        sm.add_widget(MainScreen())
        sm.add_widget(STTScreen(self.app_core))
        # sm.add_widget(TTSScreen(self.app_core)) 
        # sm.add_widget(PDFScreen(self.app_core)) 
        
        return sm

if __name__ == '__main__':
    VoxTextApp().run()