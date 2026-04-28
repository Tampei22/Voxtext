import threading

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from ui.theme import RoundedButton
from ui.i18n import load_lang, t


class TTSScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'tts'
        self.app_core = app_core
        self.is_speaking = False
        self._stop_requested = False
        self._speak_pulse_event = None
        self._speak_pulse_bright = True

        from storage.settings import load_app_settings
        self.settings = load_app_settings().tts_settings()

        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(8))

        self.back_btn = RoundedButton(size_hint_y=None, height=50)
        self.back_btn.bind(on_release=self.go_back)
        layout.add_widget(self.back_btn)

        self.title_label = Label(
            font_size='16sp',
            size_hint_y=None,
            height=sp(34),
        )
        layout.add_widget(self.title_label)

        self.text_input = TextInput(
            text='',
            multiline=True,
        )
        layout.add_widget(self.text_input)

        self.status_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height=sp(28),
        )
        layout.add_widget(self.status_label)

        action_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(62),
            spacing=dp(8),
        )
        self.speak_btn = RoundedButton(font_size='19sp')
        self.speak_btn.bind(on_release=self.speak_text)
        action_row.add_widget(self.speak_btn)

        self.stop_btn = RoundedButton(
            font_size='19sp', disabled=True, size_hint_x=0.32
        )
        self.stop_btn.bind(on_release=self.stop_speech)
        action_row.add_widget(self.stop_btn)
        layout.add_widget(action_row)

        sec_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(44),
            spacing=dp(8),
        )
        self.clear_btn = RoundedButton(font_size='15sp')
        self.clear_btn.bind(on_release=self.clear_text)
        sec_row.add_widget(self.clear_btn)

        self.paste_btn = RoundedButton(font_size='15sp')
        self.paste_btn.bind(on_release=self.paste_from_clipboard)
        sec_row.add_widget(self.paste_btn)

        layout.add_widget(sec_row)

        self.settings_btn = RoundedButton(
            font_size='15sp',
            size_hint_y=None,
            height=50,
        )
        self.settings_btn.bind(on_release=lambda i: setattr(self.manager, 'current', 'settings'))
        layout.add_widget(self.settings_btn)

        self.add_widget(layout)
        self._update_texts()

    def _update_texts(self):
        self.back_btn.text = t('back')
        self.title_label.text = t('tts_title')
        self.text_input.hint_text = t('tts_hint')
        self.speak_btn.text = t('tts_speak')
        self.stop_btn.text = t('tts_stop')
        self.clear_btn.text = t('tts_clear')
        self.paste_btn.text = t('tts_paste')
        self.settings_btn.text = t('tts_voice_settings')

    def on_enter(self, *args):
        load_lang()
        self._update_texts()
        from storage.settings import load_app_settings
        self.settings = load_app_settings().tts_settings()

    def _start_speak_pulse(self):
        from ui.theme import get as _theme
        self.stop_btn.btn_color = list(_theme()['btn_accent'])
        self._speak_pulse_bright = True
        self._speak_pulse_event = Clock.schedule_interval(self._do_speak_pulse, 0.7)
        self.status_label.color = list(_theme()['btn_accent'])
        self.status_label.text = t('tts_speaking')

    def _do_speak_pulse(self, dt):
        from ui.theme import get as _theme
        a = list(_theme()['btn_accent'])
        if self._speak_pulse_bright:
            self.stop_btn.btn_color = [a[0] * 0.45, a[1] * 0.45, a[2] * 0.45, a[3]]
            self._speak_pulse_bright = False
        else:
            self.stop_btn.btn_color = a
            self._speak_pulse_bright = True

    def _stop_speak_pulse(self):
        if self._speak_pulse_event is not None:
            self._speak_pulse_event.cancel()
            self._speak_pulse_event = None
        from ui.theme import get as _theme
        self.stop_btn.btn_color = list(_theme()['btn_normal'])
        self.status_label.color = (0.93, 0.93, 0.96, 1)

    def speak_text(self, instance):
        text = self.text_input.text.strip()
        if not text:
            self.status_label.text = t('tts_empty')
            return
        if self.is_speaking:
            return
        self.is_speaking = True
        self._stop_requested = False
        self.speak_btn.disabled = True
        self.stop_btn.disabled = False
        self._start_speak_pulse()
        threading.Thread(target=self._do_speak, args=(text,), daemon=True).start()

    def _do_speak(self, text):
        try:
            self.app_core.speak_text(text, self.settings)
            if not self._stop_requested:
                Clock.schedule_once(lambda dt: self._on_speak_done(), 0)
        except Exception as e:
            if not self._stop_requested:
                msg = t('tts_error', e=e)
                Clock.schedule_once(lambda dt, m=msg: self._on_speak_error(m), 0)

    def _on_speak_done(self):
        self._stop_speak_pulse()
        self.is_speaking = False
        self.speak_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = t('tts_done')

    def _on_speak_error(self, error):
        self._stop_speak_pulse()
        self.is_speaking = False
        self.speak_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = error

    def stop_speech(self, instance):
        if self.is_speaking:
            self._stop_requested = True
            self.app_core.tts.stop()
            self._stop_speak_pulse()
            self.is_speaking = False
            self.speak_btn.disabled = False
            self.stop_btn.disabled = True
            self.status_label.text = t('tts_stopped')

    def clear_text(self, instance):
        self.text_input.text = ''
        self.status_label.text = ''

    def paste_from_clipboard(self, instance):
        try:
            from kivy.core.clipboard import Clipboard
            text = Clipboard.paste()
            if text and text.strip():
                cur = self.text_input.text
                self.text_input.text = (cur + ' ' + text).strip() if cur else text
                self.status_label.text = t('tts_pasted', n=len(text))
            else:
                self.status_label.text = t('tts_clipboard_empty')
        except Exception as e:
            self.status_label.text = t('tts_paste_error', e=e)

    def go_back(self, instance):
        self.manager.current = 'main'
