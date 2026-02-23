from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import threading

class STTScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stt'
        self.app_core = app_core
        self.is_recording = False
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        back_btn = Button(
            text='← Назад',
            size_hint_y=None,
            height=50
        )
        back_btn.bind(on_release=self.go_back)
        layout.add_widget(back_btn)
        
        self.status_label = Label(
            text='Нажмите кнопку для записи',
            font_size='18sp'
        )
        layout.add_widget(self.status_label)
        
        self.record_btn = Button(
            text='НАЧАТЬ ЗАПИСЬ',
            font_size='24sp',
            size_hint_y=None,
            height=100
        )
        self.record_btn.bind(on_release=self.toggle_recording)
        layout.add_widget(self.record_btn)

        self.result_input = TextInput(
            text='',
            multiline=True,
            readonly=True
        )
        layout.add_widget(self.result_input)
        
        speak_btn = Button(
            text='ОЗВУЧИТЬ РЕЗУЛЬТАТ',
            size_hint_y=None,
            height=60
        )
        speak_btn.bind(on_release=self.speak_result)
        layout.add_widget(speak_btn)
        
        self.add_widget(layout)
    
    def toggle_recording(self, instance):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.is_recording = True
        self.record_btn.text = 'ОСТАНОВИТЬ'
        self.status_label.text = 'Говорите сейчас...'
        
        thread = threading.Thread(target=self.do_recording)
        thread.daemon = True
        thread.start()
    
    def do_recording(self):
        try:
            text = self.app_core.listen_text(lang="ro-RO")
            Clock.schedule_once(lambda dt: self.on_recording_complete(text), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_recording_error(str(e)), 0)
    
    def on_recording_complete(self, text):
        self.is_recording = False
        self.record_btn.text = 'НАЧАТЬ ЗАПИСЬ'
        
        if text:
            self.result_input.text = text
            self.status_label.text = f'Распознано: {len(text)} символов'
        else:
            self.status_label.text = 'Ничего не распознано'
    
    def on_recording_error(self, error):
        self.is_recording = False
        self.record_btn.text = 'НАЧАТЬ ЗАПИСЬ'
        self.status_label.text = f'Ошибка: {error}'
    
    def speak_result(self, instance):
        if self.result_input.text.strip():
            from app_core.models import TTSSettings
            settings = TTSSettings(lang="ro")
            self.app_core.speak_text(self.result_input.text, settings)
    
    def stop_recording(self):

        pass
    
    def go_back(self, instance):
        self.manager.current = 'main'