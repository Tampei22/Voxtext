from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.config import Config

Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

from ui.main_screen import MainScreen
from ui.stt_screen import STTScreen
from ui.tts_screen import TTSScreen
from ui.pdf_screen import PDFScreen
from ui.history_screen import HistoryScreen

from app_core.core import AppCore
from stt.speech_recognition_engine import SpeechRecognitionEngine
from tts.edge_tts_engine import EdgeTTSEngine

class VoxTextApp(App):
    def __init__(self):
        super().__init__()

        self.app_core = AppCore(
            tts_engine=EdgeTTSEngine(),
            stt_engine=SpeechRecognitionEngine()
        )
    
    def build(self):
        self.title = 'VoxText'

        sm = ScreenManager()

        sm.add_widget(MainScreen())
        sm.add_widget(STTScreen(self.app_core))
        sm.add_widget(TTSScreen(self.app_core))
        sm.add_widget(PDFScreen(self.app_core))
        sm.add_widget(HistoryScreen(self.app_core))
        
        return sm

if __name__ == '__main__':
    VoxTextApp().run()