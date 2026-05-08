from kivy.config import Config

Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '700')
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'minimum_width', '340')
Config.set('graphics', 'minimum_height', '540')
Config.set('input', 'mouse', 'mouse,disable_multitouch')

from storage.settings import load_app_settings as _load_settings
_startup_settings = _load_settings()

from ui.i18n import set_lang as _set_i18n_lang
_set_i18n_lang(_startup_settings.lang)

Config.set('kivy', 'font_scale', str(int(_startup_settings.font_scale * 100)))

from kivy.metrics import Metrics
Metrics.fontscale = _startup_settings.font_scale

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

from ui.main_screen import MainScreen
from ui.stt_screen import STTScreen
from ui.tts_screen import TTSScreen
from ui.pdf_screen import PDFScreen
from ui.history_screen import HistoryScreen
from ui.settings_screen import SettingsScreen
from ui.benchmark_screen import BenchmarkScreen

from app_core.core import AppCore
from stt.whisper_engine import WhisperSTTEngine
from stt.speech_recognition_engine import SpeechRecognitionEngine
from tts.edge_tts_engine import EdgeTTSEngine
from tts.pyttsx3_engine import Pyttsx3Engine


class VoxTextApp(App):
    def __init__(self):
        super().__init__()
        _whisper = WhisperSTTEngine(model_size=_startup_settings.whisper_model)
        _google  = SpeechRecognitionEngine()
        # Language-based engine preference: Google is primary for Romanian,
        # Whisper is primary for English and Russian.
        if _startup_settings.stt_engine == "google":
            _primary_stt, _fallback_stt = _google, _whisper
        else:
            _primary_stt, _fallback_stt = _whisper, _google
        self.app_core = AppCore(
            tts_engine=EdgeTTSEngine(),
            stt_engine=_primary_stt,
            fallback_tts=Pyttsx3Engine(),
            fallback_stt=_fallback_stt,
        )

    def build(self):
        from ui.theme import init as _init_theme
        _init_theme(_startup_settings.theme, _startup_settings.color_scheme)

        self.title = 'VoxText'
        sm = ScreenManager()
        sm.add_widget(MainScreen())
        sm.add_widget(STTScreen(self.app_core))
        sm.add_widget(TTSScreen(self.app_core))
        sm.add_widget(PDFScreen(self.app_core))
        sm.add_widget(HistoryScreen(self.app_core))
        sm.add_widget(SettingsScreen())
        sm.add_widget(BenchmarkScreen())
        return sm


if __name__ == '__main__':
    VoxTextApp().run()
