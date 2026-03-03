import threading

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput


class TTSScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'tts'
        self.app_core = app_core
        self.is_speaking = False

        from app_core.models import TTSSettings
        self.settings = TTSSettings(lang="ro", rate=175, volume=1.0)

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        back_btn = Button(text='← Назад', size_hint_y=None, height=50)
        back_btn.bind(on_release=self.go_back)
        layout.add_widget(back_btn)

        layout.add_widget(Label(
            text='Введите текст для озвучивания',
            font_size='18sp',
            size_hint_y=None,
            height=40,
        ))

        self.text_input = TextInput(
            text='',
            multiline=True,
            hint_text='Введите текст здесь...',
        )
        layout.add_widget(self.text_input)

        self.status_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height=30,
        )
        layout.add_widget(self.status_label)

        btn_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=70,
            spacing=10,
        )

        self.speak_btn = Button(text='ГОВОРИТЬ', font_size='20sp')
        self.speak_btn.bind(on_release=self.speak_text)
        btn_row.add_widget(self.speak_btn)

        self.stop_btn = Button(text='СТОП', font_size='20sp', disabled=True)
        self.stop_btn.bind(on_release=self.stop_speech)
        btn_row.add_widget(self.stop_btn)

        clear_btn = Button(text='ОЧИСТИТЬ', font_size='20sp')
        clear_btn.bind(on_release=self.clear_text)
        btn_row.add_widget(clear_btn)

        layout.add_widget(btn_row)

        settings_btn = Button(
            text='Настройки голоса',
            font_size='16sp',
            size_hint_y=None,
            height=50,
        )
        settings_btn.bind(on_release=self.open_settings)
        layout.add_widget(settings_btn)

        self.add_widget(layout)

    def speak_text(self, instance):
        text = self.text_input.text.strip()
        if not text or self.is_speaking:
            return
        self.is_speaking = True
        self.speak_btn.disabled = True
        self.stop_btn.disabled = False
        self.status_label.text = 'Озвучивание...'
        threading.Thread(target=self._do_speak, args=(text,), daemon=True).start()

    def _do_speak(self, text):
        try:
            self.app_core.speak_text(text, self.settings)
            Clock.schedule_once(lambda dt: self._on_speak_done(), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_speak_error(str(e)), 0)

    def _on_speak_done(self):
        self.is_speaking = False
        self.speak_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = 'Готово'

    def _on_speak_error(self, error):
        self.is_speaking = False
        self.speak_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = f'Ошибка: {error}'

    def stop_speech(self, instance):
        if self.is_speaking:
            self.app_core.tts.stop()
            self.is_speaking = False
            self.speak_btn.disabled = False
            self.stop_btn.disabled = True
            self.status_label.text = 'Остановлено'

    def clear_text(self, instance):
        self.text_input.text = ''
        self.status_label.text = ''

    def open_settings(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)

        rate_row = BoxLayout(orientation='vertical', size_hint_y=None, height=80)
        self.rate_val_label = Label(
            text=f'Скорость речи: {int(self.settings.rate)}',
            size_hint_y=None,
            height=30,
        )
        rate_row.add_widget(self.rate_val_label)
        rate_slider = Slider(min=100, max=300, value=self.settings.rate, step=5)
        rate_slider.bind(value=self.on_rate_change)
        rate_row.add_widget(rate_slider)
        content.add_widget(rate_row)

        vol_row = BoxLayout(orientation='vertical', size_hint_y=None, height=80)
        self.vol_val_label = Label(
            text=f'Громкость: {self.settings.volume:.1f}',
            size_hint_y=None,
            height=30,
        )
        vol_row.add_widget(self.vol_val_label)
        vol_slider = Slider(min=0.1, max=1.0, value=self.settings.volume, step=0.1)
        vol_slider.bind(value=self.on_volume_change)
        vol_row.add_widget(vol_slider)
        content.add_widget(vol_row)

        close_btn = Button(text='Закрыть', size_hint_y=None, height=50)
        content.add_widget(close_btn)

        popup = Popup(title='Настройки голоса', content=content, size_hint=(0.9, 0.6))
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

    def on_rate_change(self, slider, value):
        self.settings.rate = int(value)
        self.rate_val_label.text = f'Скорость речи: {int(value)}'

    def on_volume_change(self, slider, value):
        self.settings.volume = round(value, 1)
        self.vol_val_label.text = f'Громкость: {round(value, 1)}'

    def go_back(self, instance):
        self.manager.current = 'main'
