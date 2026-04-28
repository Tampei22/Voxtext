import os
import re
import threading

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from ui.theme import RoundedButton
from ui.i18n import load_lang, t


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
        self._read_pulse_event = None
        self._read_pulse_bright = True

        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(8))

        self.back_btn = RoundedButton(size_hint_y=None, height=50)
        self.back_btn.bind(on_release=self.go_back)
        layout.add_widget(self.back_btn)

        self.title_label = Label(
            font_size='20sp',
            size_hint_y=None,
            height=sp(40),
        )
        layout.add_widget(self.title_label)

        self.select_btn = RoundedButton(
            font_size='18sp',
            size_hint_y=None,
            height=70,
        )
        self.select_btn.bind(on_release=self.open_file_chooser)
        layout.add_widget(self.select_btn)

        self.file_label = Label(
            font_size='14sp',
            size_hint_y=None,
            height=sp(35),
        )
        layout.add_widget(self.file_label)

        self.text_preview = TextInput(
            text='',
            multiline=True,
            readonly=True,
        )
        layout.add_widget(self.text_preview)

        self.progress_label = Label(
            text='',
            font_size='13sp',
            size_hint_y=None,
            height=sp(28),
            color=(0.6, 0.9, 0.6, 1),
        )
        layout.add_widget(self.progress_label)

        self.status_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height=sp(28),
        )
        layout.add_widget(self.status_label)

        btn_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(70),
            spacing=dp(8),
        )

        self.read_btn = RoundedButton(font_size='17sp', disabled=True)
        self.read_btn.bind(on_release=self.read_aloud)
        btn_row.add_widget(self.read_btn)

        self.stop_btn = RoundedButton(font_size='17sp', disabled=True, size_hint_x=0.35)
        self.stop_btn.bind(on_release=self.stop_reading)
        btn_row.add_widget(self.stop_btn)

        self.restart_btn = RoundedButton(
            font_size='22sp', size_hint_x=None, width=dp(55), disabled=True
        )
        self.restart_btn.bind(on_release=self.restart_reading)
        btn_row.add_widget(self.restart_btn)

        layout.add_widget(btn_row)
        self.add_widget(layout)
        self._update_texts()

    def _update_texts(self):
        self.back_btn.text = t('back')
        self.title_label.text = t('file_title')
        self.select_btn.text = t('file_select')
        self.file_label.text = t('file_none') if not self.pdf_path else f'{os.path.basename(self.pdf_path)}'
        self.text_preview.hint_text = t('file_hint')
        self.read_btn.text = t('file_continue') if self.current_segment > 0 else t('file_read')
        self.stop_btn.text = t('file_stop')
        self.restart_btn.text = t('file_restart')

    def on_enter(self, *args):
        load_lang()
        self._update_texts()

    def _start_read_pulse(self):
        from ui.theme import get as _theme
        self.stop_btn.btn_color = list(_theme()['btn_accent'])
        self._read_pulse_bright = True
        self._read_pulse_event = Clock.schedule_interval(self._do_read_pulse, 0.7)
        self.status_label.color = list(_theme()['btn_accent'])
        self.status_label.text = t('file_speaking')

    def _do_read_pulse(self, dt):
        from ui.theme import get as _theme
        a = list(_theme()['btn_accent'])
        if self._read_pulse_bright:
            self.stop_btn.btn_color = [a[0] * 0.45, a[1] * 0.45, a[2] * 0.45, a[3]]
            self._read_pulse_bright = False
        else:
            self.stop_btn.btn_color = a
            self._read_pulse_bright = True

    def _stop_read_pulse(self):
        if self._read_pulse_event is not None:
            self._read_pulse_event.cancel()
            self._read_pulse_event = None
        from ui.theme import get as _theme
        self.stop_btn.btn_color = list(_theme()['btn_normal'])
        self.status_label.color = (0.93, 0.93, 0.96, 1)

    def open_file_chooser(self, instance):
        threading.Thread(target=self._native_pick, daemon=True).start()

    def _native_pick(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askopenfilename(
                title=t('file_dialog_title'),
                initialdir=os.path.expanduser('~'),
                filetypes=[
                    ('Текст, DOCX, PDF', '*.txt *.docx *.pdf'),
                    ('TXT', '*.txt'),
                    ('DOCX', '*.docx'),
                    ('PDF', '*.pdf'),
                    ('*', '*.*'),
                ],
            )
            root.destroy()
            if path:
                Clock.schedule_once(lambda _: self.on_file_selected(path), 0)
        except Exception as e:
            msg = t('file_dialog_error', e=e)
            Clock.schedule_once(lambda dt, m=msg: setattr(self.status_label, 'text', m), 0)

    def on_file_selected(self, path):
        self.pdf_path = path
        self.file_label.text = os.path.basename(path)
        self.status_label.text = t('file_loading')
        self.text_preview.text = ''
        self.read_btn.disabled = True
        self.restart_btn.disabled = True
        self.segments = []
        self.current_segment = 0
        self.progress_label.text = ''
        threading.Thread(target=self._load_file, args=(path,), daemon=True).start()

    def _load_file(self, path):
        try:
            from file_reader.file_reader import read_file
            text = read_file(path)
            Clock.schedule_once(lambda _: self._on_file_loaded(text), 0)
        except Exception as e:
            msg = str(e)
            Clock.schedule_once(lambda _, m=msg: self._on_file_error(m), 0)

    def _on_file_loaded(self, text):
        self.text_preview.text = text
        self.segments = _split_text(text)
        self.current_segment = 0
        self.status_label.text = t('file_loaded', n=len(self.segments))
        self.read_btn.text = t('file_read')
        self.read_btn.disabled = False

    def _on_file_error(self, error):
        self.status_label.text = t('file_error', e=error)

    def read_aloud(self, instance):
        if not self.segments or self.is_speaking:
            return
        self.is_speaking = True
        self._stop_requested = False
        self.read_btn.disabled = True
        self.stop_btn.disabled = False
        self.restart_btn.disabled = True
        self._start_read_pulse()
        threading.Thread(target=self._do_read_loop, daemon=True).start()

    def _do_read_loop(self):
        from storage.settings import load_app_settings
        settings = load_app_settings().tts_settings()
        total = len(self.segments)

        for i in range(self.current_segment, total):
            if self._stop_requested:
                self.current_segment = i
                Clock.schedule_once(lambda _: self._on_read_paused(), 0)
                return

            Clock.schedule_once(
                lambda dt, n=i: setattr(
                    self.progress_label, 'text', t('file_phrase', n=n + 1, total=total)
                ), 0
            )

            try:
                self.app_core.tts.speak(self.segments[i], settings)
            except Exception:
                if self._stop_requested:
                    self.current_segment = i
                    Clock.schedule_once(lambda _: self._on_read_paused(), 0)
                else:
                    Clock.schedule_once(lambda _: self._on_read_error(t('file_tts_error')), 0)
                return

        self.current_segment = 0
        Clock.schedule_once(lambda _: self._on_read_done(), 0)

    def _on_read_paused(self):
        self._stop_read_pulse()
        self.is_speaking = False
        self.stop_btn.disabled = True
        self.read_btn.disabled = False
        self.read_btn.text = t('file_continue')
        self.restart_btn.disabled = False
        total = len(self.segments)
        self.status_label.text = t('file_paused', n=self.current_segment + 1, total=total)

    def _on_read_done(self):
        self._stop_read_pulse()
        self.is_speaking = False
        self.read_btn.disabled = False
        self.read_btn.text = t('file_read')
        self.stop_btn.disabled = True
        self.restart_btn.disabled = True
        self.progress_label.text = ''
        self.status_label.text = t('file_done')

    def _on_read_error(self, error):
        self._stop_read_pulse()
        self.is_speaking = False
        self.read_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = t('file_error', e=error)

    def stop_reading(self, instance):
        if self.is_speaking:
            self._stop_requested = True
            self.app_core.tts.stop()

    def restart_reading(self, _):
        if self.is_speaking:
            return
        self.current_segment = 0
        self.read_btn.text = t('file_read')
        self.restart_btn.disabled = True
        self.progress_label.text = ''
        self.status_label.text = t('file_ready')

    def go_back(self, instance):
        if self.is_speaking:
            self._stop_requested = True
            self.app_core.tts.stop()
        self.manager.current = 'main'
