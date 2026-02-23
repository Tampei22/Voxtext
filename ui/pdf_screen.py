from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

class PDFScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'pdf'
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        back_btn = Button(text='← Înapoi', size_hint_y=None, height=50)
        back_btn.bind(on_release=self.go_back)
        layout.add_widget(back_btn)
        
        layout.add_widget(Label(text='PDF Reader - în dezvoltare', font_size='24sp'))
        
        self.add_widget(layout)
    
    def go_back(self, instance):
        self.manager.current = 'main'