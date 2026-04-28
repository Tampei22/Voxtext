from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from ui.theme import RoundedButton
from ui.i18n import load_lang, t


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'main'

        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))

        layout.add_widget(Label(
            text='VoxText',
            font_size='32sp',
            size_hint_y=None,
            height=sp(60),
        ))

        self.btn_stt = RoundedButton(font_size='20sp')
        self.btn_stt.bind(on_release=lambda i: setattr(self.manager, 'current', 'stt'))

        self.btn_tts = RoundedButton(font_size='20sp')
        self.btn_tts.bind(on_release=lambda i: setattr(self.manager, 'current', 'tts'))

        self.btn_file = RoundedButton(font_size='20sp')
        self.btn_file.bind(on_release=lambda i: setattr(self.manager, 'current', 'pdf'))

        self.btn_history = RoundedButton(font_size='20sp')
        self.btn_history.bind(on_release=lambda i: setattr(self.manager, 'current', 'history'))

        self.btn_settings = RoundedButton(font_size='20sp')
        self.btn_settings.bind(on_release=lambda i: setattr(self.manager, 'current', 'settings'))

        for btn in (self.btn_stt, self.btn_tts, self.btn_file, self.btn_history, self.btn_settings):
            layout.add_widget(btn)

        self.add_widget(layout)
        self._update_texts()

    def _update_texts(self):
        self.btn_stt.text = t('main_stt')
        self.btn_tts.text = t('main_tts')
        self.btn_file.text = t('main_file')
        self.btn_history.text = t('main_history')
        self.btn_settings.text = t('main_settings')

    def on_enter(self, *args):
        load_lang()
        self._update_texts()
