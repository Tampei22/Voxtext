from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

class TTSScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'tts'
        self.app_core = app_core
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        back_btn = Button(text='← Înapoi', size_hint_y=None, height=50)
        back_btn.bind(on_release=self.go_back)
        layout.add_widget(back_btn)
        
        layout.add_widget(Label(text='Introdu text pentru citire', font_size='18sp'))
        
        self.text_input = TextInput(
            text='',
            multiline=True,
            hint_text='Introdu textul român aici...'
        )
        layout.add_widget(self.text_input)
        
        speak_btn = Button(
            text='VORBEȘTE',
            font_size='24sp',
            size_hint_y=None,
            height=80
        )
        speak_btn.bind(on_release=self.speak_text)
        layout.add_widget(speak_btn)
        
        self.add_widget(layout)
    
    def speak_text(self, instance):
        text = self.text_input.text.strip()
        if text:
            from app_core.models import TTSSettings
            settings = TTSSettings(lang="ro")
            self.app_core.speak_text(text, settings)
    
    def go_back(self, instance):
        self.manager.current = 'main'