import threading

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput


class STTScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stt'
        self.app_core = app_core
        self.is_recording = False

        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        back_btn = Button(text='← Назад', size_hint_y=None, height=50)
        back_btn.bind(on_release=self.go_back)
        layout.add_widget(back_btn)

        self.status_label = Label(
            text='Нажмите кнопку для начала записи',
            font_size='17sp',
            size_hint_y=None,
            height=40,
        )
        layout.add_widget(self.status_label)

        self.record_btn = Button(
            text='ГОВОРИТЬ',
            font_size='24sp',
            size_hint_y=None,
            height=100,
        )
        self.record_btn.bind(on_release=self.toggle_recording)
        layout.add_widget(self.record_btn)

        self.result_input = TextInput(
            text='',
            multiline=True,
            readonly=True,
            hint_text='Распознанный текст появится здесь...',
        )
        layout.add_widget(self.result_input)

        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)

        clear_btn = Button(text='ОЧИСТИТЬ', font_size='17sp')
        clear_btn.bind(on_release=self.clear_result)
        btn_row.add_widget(clear_btn)

        speak_btn = Button(text='ОЗВУЧИТЬ', font_size='17sp')
        speak_btn.bind(on_release=self.speak_result)
        btn_row.add_widget(speak_btn)

        layout.add_widget(btn_row)
        self.add_widget(layout)

    def toggle_recording(self, instance):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.is_recording = True
        self.record_btn.text = 'ОСТАНОВИТЬ'
        self.status_label.text = 'Калибровка микрофона...'

        stt = self.app_core.stt

        if hasattr(stt, 'start_listening'):
            threading.Thread(target=self._start_continuous, daemon=True).start()
        else:
            threading.Thread(target=self._do_listen_once, daemon=True).start()

    def _start_continuous(self):
        try:
            self.app_core.stt.start_listening(
                on_result=self._on_phrase_recognized,
                on_error=self._on_stt_error,
                lang="ro-RO",
            )
            Clock.schedule_once(
                lambda dt: setattr(self.status_label, 'text', 'Слушаю... Говорите по-румынски'), 0
            )
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_stt_error(str(e)), 0)

    def stop_recording(self):
        self.is_recording = False
        self.record_btn.text = 'ГОВОРИТЬ'

        stt = self.app_core.stt
        if hasattr(stt, 'stop_listening'):
            stt.stop_listening()

        word_count = len(self.result_input.text.split()) if self.result_input.text.strip() else 0
        self.status_label.text = f'Запись остановлена — {word_count} слов'

    def _on_phrase_recognized(self, text):
        def update(dt):
            if not self.is_recording:
                return
            current = self.result_input.text
            self.result_input.text = (current + ' ' + text).strip() if current else text
            word_count = len(self.result_input.text.split())
            self.status_label.text = f'Слушаю... ({word_count} слов)'
        Clock.schedule_once(update, 0)

    def _on_stt_error(self, error):
        def update(dt):
            self.status_label.text = f'Ошибка: {error}'
        Clock.schedule_once(update, 0)

    def _do_listen_once(self):
        try:
            text = self.app_core.listen_text(lang="ro-RO")
            Clock.schedule_once(lambda dt: self._on_listen_once_done(text), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_listen_once_error(str(e)), 0)

    def _on_listen_once_done(self, text):
        self.is_recording = False
        self.record_btn.text = 'ГОВОРИТЬ'
        if text:
            self.result_input.text = text
            self.status_label.text = f'Распознано: {len(text)} символов'
        else:
            self.status_label.text = 'Ничего не распознано'

    def _on_listen_once_error(self, error):
        self.is_recording = False
        self.record_btn.text = 'ГОВОРИТЬ'
        self.status_label.text = f'Ошибка: {error}'

    def clear_result(self, instance):
        self.result_input.text = ''
        self.status_label.text = 'Нажмите кнопку для начала записи'

    def speak_result(self, instance):
        text = self.result_input.text.strip()
        if text:
            from app_core.models import TTSSettings
            settings = TTSSettings(lang="ro")
            threading.Thread(
                target=self.app_core.speak_text,
                args=(text, settings),
                daemon=True,
            ).start()

    def go_back(self, instance):
        if self.is_recording:
            self.stop_recording()
        self.manager.current = 'main'
