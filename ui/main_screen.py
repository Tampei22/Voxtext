from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'main'
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        title = Label(
            text='VoxText', 
            font_size='32sp',
            size_hint_y=None,
            height=80
        )
        layout.add_widget(title)
        
        buttons = [
            ('ГОВОРИТЬ', self.go_to_stt),
            ('ЧИТАТЬ ВСЛУХ', self.go_to_tts), 
            ('ЗАГРУЗИТЬ PDF', self.go_to_pdf),
            ('ИСТОРИЯ', self.go_to_history)
        ]
        
        for text, callback in buttons:
            btn = Button(
                text=text,
                font_size='20sp',
                size_hint_y=None,
                height=80
            )
            btn.bind(on_release=callback)
            layout.add_widget(btn)
        
        self.add_widget(layout)
    
    def go_to_stt(self, instance):
        self.manager.current = 'stt'
    
    def go_to_tts(self, instance):
        self.manager.current = 'tts'
        
    def go_to_pdf(self, instance):
        self.manager.current = 'pdf'
        
    def go_to_history(self, instance):
        self.manager.current = 'history'