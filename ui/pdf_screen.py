import os
import re
import threading
import tkinter as tk
from tkinter import filedialog

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from app_core.models import TTSSettings


def _split_text(text: str) -> list:
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    segments = []
    for para in paragraphs:
        parts = re.split(r'(?<=[.!?])\s+', para)
        segments.extend(s.strip() for s in parts if len(s.strip()) > 3)
    return segments


class PDFScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'pdf'
        self.app_core = app_core
        self.pdf_path = None
        self.is_speaking = False
        self.segments = []
        self.current_segment = 0
        self._stop_requested = False

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        back_btn = Button(text='← Назад', size_hint_y=None, height=50)
        back_btn.bind(on_release=self.go_back)
        layout.add_widget(back_btn)

        layout.add_widget(Label(
            text='Загрузить и озвучить PDF',
            font_size='20sp',
            size_hint_y=None,
            height=40,
        ))

        select_btn = Button(
            text='ВЫБРАТЬ PDF ФАЙЛ',
            font_size='18sp',
            size_hint_y=None,
            height=70,
        )
        select_btn.bind(on_release=self.open_file_chooser)
        layout.add_widget(select_btn)

        self.file_label = Label(
            text='Файл не выбран',
            font_size='14sp',
            size_hint_y=None,
            height=35,
        )
        layout.add_widget(self.file_label)

        self.text_preview = TextInput(
            text='',
            multiline=True,
            readonly=True,
            hint_text='Текст PDF появится здесь...',
        )
        layout.add_widget(self.text_preview)

        self.progress_label = Label(
            text='',
            font_size='13sp',
            size_hint_y=None,
            height=28,
            color=(0.6, 0.9, 0.6, 1),
        )
        layout.add_widget(self.progress_label)

        self.status_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height=28,
        )
        layout.add_widget(self.status_label)

        btn_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=70,
            spacing=8,
        )

        self.read_btn = Button(text='ЧИТАТЬ ВСЛУХ', font_size='17sp', disabled=True)
        self.read_btn.bind(on_release=self.read_aloud)
        btn_row.add_widget(self.read_btn)

        self.stop_btn = Button(text='СТОП', font_size='17sp', disabled=True, size_hint_x=0.35)
        self.stop_btn.bind(on_release=self.stop_reading)
        btn_row.add_widget(self.stop_btn)

        self.restart_btn = Button(text='↩', font_size='22sp', size_hint_x=None, width=55, disabled=True)
        self.restart_btn.bind(on_release=self.restart_reading)
        btn_row.add_widget(self.restart_btn)

        layout.add_widget(btn_row)
        self.add_widget(layout)

    def open_file_chooser(self, instance):
        threading.Thread(target=self._native_pick, daemon=True).start()

    def _native_pick(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title='Выберите PDF файл',
            initialdir=os.path.expanduser('~'),
            filetypes=[('PDF файлы', '*.pdf'), ('Все файлы', '*.*')],
        )
        root.destroy()
        if path:
            Clock.schedule_once(lambda _: self.on_file_selected(path), 0)

    def on_file_selected(self, path):
        self.pdf_path = path
        self.file_label.text = f'Файл: {os.path.basename(path)}'
        self.status_label.text = 'Загрузка текста...'
        self.text_preview.text = ''
        self.read_btn.disabled = True
        self.restart_btn.disabled = True
        self.segments = []
        self.current_segment = 0
        self.progress_label.text = ''
        threading.Thread(target=self._load_pdf, args=(path,), daemon=True).start()

    def _load_pdf(self, path):
        try:
            from file_reader.pdf_reader import read_pdf
            text = read_pdf(path)
            Clock.schedule_once(lambda _: self._on_pdf_loaded(text), 0)
        except Exception as e:
            Clock.schedule_once(lambda _: self._on_pdf_error(str(e)), 0)

    def _on_pdf_loaded(self, text):
        if text:
            self.text_preview.text = text
            self.segments = _split_text(text)
            self.current_segment = 0
            self.status_label.text = f'Загружено: {len(self.segments)} фраз'
            self.read_btn.disabled = False
        else:
            self.status_label.text = 'PDF не содержит распознаваемый текст'

    def _on_pdf_error(self, error):
        self.status_label.text = f'Ошибка: {error}'

    def read_aloud(self, instance):
        if not self.segments or self.is_speaking:
            return
        self.is_speaking = True
        self._stop_requested = False
        self.read_btn.disabled = True
        self.stop_btn.disabled = False
        self.restart_btn.disabled = True
        self.status_label.text = 'Озвучивание...'
        threading.Thread(target=self._do_read_loop, daemon=True).start()

    def _do_read_loop(self):
        settings = TTSSettings(lang="ro")
        total = len(self.segments)

        for i in range(self.current_segment, total):
            if self._stop_requested:
                self.current_segment = i
                Clock.schedule_once(lambda _: self._on_read_paused(), 0)
                return

            idx = i  
            Clock.schedule_once(
                lambda dt, n=idx: setattr(
                    self.progress_label, 'text', f'Фраза {n + 1} из {total}'
                ), 0
            )

            try:
                self.app_core.tts.speak(self.segments[i], settings)
            except Exception:
                if self._stop_requested:
                    self.current_segment = i
                    Clock.schedule_once(lambda _: self._on_read_paused(), 0)
                else:
                    Clock.schedule_once(
                        lambda _: self._on_read_error('Ошибка TTS'), 0
                    )
                return

        self.current_segment = 0
        Clock.schedule_once(lambda _: self._on_read_done(), 0)

    def _on_read_paused(self):
        self.is_speaking = False
        self.stop_btn.disabled = True
        self.read_btn.disabled = False
        self.read_btn.text = 'ПРОДОЛЖИТЬ'
        self.restart_btn.disabled = False
        total = len(self.segments)
        self.status_label.text = f'Пауза — фраза {self.current_segment + 1} из {total}'

    def _on_read_done(self):
        self.is_speaking = False
        self.read_btn.disabled = False
        self.read_btn.text = 'ЧИТАТЬ ВСЛУХ'
        self.stop_btn.disabled = True
        self.restart_btn.disabled = True
        self.progress_label.text = ''
        self.status_label.text = 'Готово'

    def _on_read_error(self, error):
        self.is_speaking = False
        self.read_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = f'Ошибка: {error}'

    def stop_reading(self, instance):
        if self.is_speaking:
            self._stop_requested = True
            self.app_core.tts.stop()

    def restart_reading(self, _):
        if self.is_speaking:
            return
        self.current_segment = 0
        self.read_btn.text = 'ЧИТАТЬ ВСЛУХ'
        self.restart_btn.disabled = True
        self.progress_label.text = ''
        self.status_label.text = 'Готово к озвучиванию'

   
    def go_back(self, instance):
        if self.is_speaking:
            self._stop_requested = True
            self.app_core.tts.stop()
        self.manager.current = 'main'
