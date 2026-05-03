import os
import threading

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from ui.theme import RoundedButton, register_refresh_hook, unregister_refresh_hook
from ui.i18n import load_lang, t


class STTScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'stt'
        self.app_core = app_core
        self.is_recording = False
        self._stt_lang = "ro-RO"
        self._pulse_event = None
        self._pulse_bright = True
        self._last_session = None

        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

        self.back_btn = RoundedButton(size_hint_y=None, height=50)
        self.back_btn.bind(on_release=self.go_back)
        layout.add_widget(self.back_btn)

        self.status_label = Label(
            font_size='17sp',
            size_hint_y=None,
            height=sp(40),
        )
        layout.add_widget(self.status_label)

        self.record_btn = RoundedButton(
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
        )
        layout.add_widget(self.result_input)

        btn_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(60),
            spacing=dp(8),
        )

        self.clear_btn = RoundedButton(font_size='17sp')
        self.clear_btn.bind(on_release=self.clear_result)
        btn_row.add_widget(self.clear_btn)

        self.speak_result_btn = RoundedButton(font_size='17sp')
        self.speak_result_btn.bind(on_release=self.speak_result)
        btn_row.add_widget(self.speak_result_btn)

        self.copy_btn = RoundedButton(font_size='17sp')
        self.copy_btn.bind(on_release=self._copy_result)
        btn_row.add_widget(self.copy_btn)

        self.export_btn = RoundedButton(font_size='17sp', disabled=True)
        self.export_btn.bind(on_release=lambda inst: self._show_export_popup())
        btn_row.add_widget(self.export_btn)

        layout.add_widget(btn_row)
        self.add_widget(layout)
        self._update_texts()

    def _update_texts(self):
        self.back_btn.text = t('back')
        self.status_label.text = t('stt_hint')
        self.record_btn.text = t('stt_stop_rec') if self.is_recording else t('stt_speak')
        self.result_input.hint_text = t('stt_result_hint')
        self.clear_btn.text = t('stt_clear')
        self.speak_result_btn.text = t('stt_speak_result')
        self.copy_btn.text = t('stt_copy')
        self.export_btn.text = t('stt_export')

    def on_enter(self, *args):
        load_lang()
        self._update_texts()
        register_refresh_hook(self._on_theme_refresh)
        self._on_theme_refresh()

    def on_leave(self, *args):
        unregister_refresh_hook(self._on_theme_refresh)

    # ------------------------------------------------------------------ #
    # Pulse animation
    # ------------------------------------------------------------------ #

    def _start_pulse(self):
        from ui.theme import get as _theme
        self.record_btn.btn_color = list(_theme()['btn_danger'])
        self._pulse_bright = True
        self._pulse_event = Clock.schedule_interval(self._do_pulse, 0.55)

    def _do_pulse(self, dt):
        from ui.theme import get as _theme
        d = list(_theme()['btn_danger'])
        if self._pulse_bright:
            self.record_btn.btn_color = [d[0] * 0.45, d[1] * 0.45, d[2] * 0.45, d[3]]
            self._pulse_bright = False
        else:
            self.record_btn.btn_color = d
            self._pulse_bright = True

    def _stop_pulse(self):
        if self._pulse_event is not None:
            self._pulse_event.cancel()
            self._pulse_event = None
        from ui.theme import get as _theme
        self.record_btn.btn_color = list(_theme()['btn_normal'])

    # ------------------------------------------------------------------ #
    # Recording control
    # ------------------------------------------------------------------ #

    def toggle_recording(self, instance):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        from storage.settings import load_app_settings
        s = load_app_settings()
        self._stt_lang = s.stt_lang()
        stt = self.app_core.stt
        if hasattr(stt, 'recognizer'):
            stt.recognizer.pause_threshold = s.stt_pause_threshold

        # Reset previous session state
        self._last_session = None
        self.export_btn.disabled = True
        from ui.theme import get as _theme
        self.export_btn.btn_color = list(_theme()['btn_normal'])

        self.is_recording = True
        self.record_btn.text = t('stt_stop_rec')
        self.status_label.text = t('stt_calibrating')
        self.status_label.color = (0.93, 0.93, 0.96, 1)
        self._start_pulse()

        if hasattr(stt, 'start_listening'):
            threading.Thread(target=self._start_continuous, daemon=True).start()
        else:
            threading.Thread(target=self._do_listen_once, daemon=True).start()

    def _start_continuous(self):
        try:
            self.app_core.start_stt(
                on_result=self._on_phrase_recognized,
                on_error=self._on_stt_error,
                lang=self._stt_lang,
            )
            Clock.schedule_once(
                lambda dt: setattr(self.status_label, 'text', t('stt_recording')), 0
            )
        except OSError:
            Clock.schedule_once(lambda dt: self._on_mic_error(), 0)
        except Exception as e:
            msg = str(e)
            Clock.schedule_once(lambda dt, m=msg: self._on_stt_error(m), 0)

    def _on_mic_error(self):
        self._stop_pulse()
        self.is_recording = False
        self.record_btn.text = t('stt_speak')
        from ui.theme import get as _theme
        self.status_label.color = list(_theme()['btn_danger'])
        self.status_label.text = t('stt_no_mic')

    def stop_recording(self):
        self._stop_pulse()
        self.is_recording = False
        self.record_btn.text = t('stt_speak')
        self.status_label.color = (0.93, 0.93, 0.96, 1)
        word_count = len(self.result_input.text.split()) if self.result_input.text.strip() else 0
        self.status_label.text = t('stt_stopped', n=word_count)
        # Stop engine and save session without blocking the UI thread
        threading.Thread(target=self._stop_and_save, daemon=True).start()

    def _stop_and_save(self):
        self.app_core.stop_stt()
        self._save_current_session()
        Clock.schedule_once(lambda dt: self._on_session_ready(), 0)

    def _save_current_session(self):
        stt = self.app_core.stt
        if not hasattr(stt, 'get_session_phrases'):
            return
        phrases = stt.get_session_phrases()
        if not phrases:
            return
        import uuid
        from datetime import datetime, timezone
        from app_core.models import STTSession
        from storage.stt_sessions import save_session
        session = STTSession(
            session_id=uuid.uuid4().hex,
            lang=self._stt_lang,
            engine=stt.name(),
            created_at_iso=datetime.now(timezone.utc).isoformat(),
            phrases=phrases,
        )
        save_session(session)
        self._last_session = session

    def _on_session_ready(self):
        if self._last_session and self._last_session.phrases:
            from ui.theme import get as _theme
            self.export_btn.disabled = False
            self.export_btn.btn_color = list(_theme()['btn_accent'])

    # ------------------------------------------------------------------ #
    # Callbacks from engine
    # ------------------------------------------------------------------ #

    def _on_phrase_recognized(self, text):
        def update(dt):
            if not self.is_recording:
                return
            current = self.result_input.text
            self.result_input.text = (current + ' ' + text).strip() if current else text
            word_count = len(self.result_input.text.split())
            self.status_label.text = t('stt_recording_n', n=word_count)
        Clock.schedule_once(update, 0)

    def _on_stt_error(self, error):
        Clock.schedule_once(
            lambda dt, e=error: setattr(self.status_label, 'text', t('stt_error', e=e)), 0
        )

    def _do_listen_once(self):
        try:
            text = self.app_core.listen_text(lang=self._stt_lang)
            Clock.schedule_once(lambda dt: self._on_listen_once_done(text), 0)
        except OSError:
            Clock.schedule_once(lambda dt: self._on_mic_error(), 0)
        except Exception as e:
            msg = str(e)
            Clock.schedule_once(lambda dt, m=msg: self._on_listen_once_error(m), 0)

    def _on_listen_once_done(self, text):
        self._stop_pulse()
        self.is_recording = False
        self.record_btn.text = t('stt_speak')
        self.status_label.color = (0.93, 0.93, 0.96, 1)
        if text:
            self.result_input.text = text
            self.status_label.text = t('stt_recognized', n=len(text))
        else:
            self.status_label.text = t('stt_nothing')
        # Attempt to surface session phrases from listen_once too
        Clock.schedule_once(lambda dt: self._on_session_ready(), 0)

    def _on_listen_once_error(self, error):
        self._stop_pulse()
        self.is_recording = False
        self.record_btn.text = t('stt_speak')
        self.status_label.text = t('stt_error', e=error)

    # ------------------------------------------------------------------ #
    # Result actions
    # ------------------------------------------------------------------ #

    def clear_result(self, instance):
        self.result_input.text = ''
        self.status_label.color = (0.93, 0.93, 0.96, 1)
        self.status_label.text = t('stt_hint')

    def speak_result(self, instance):
        text = self.result_input.text.strip()
        if not text or self.is_recording:
            return
        from storage.settings import load_app_settings
        settings = load_app_settings().tts_settings()
        self.status_label.text = t('stt_playing')
        threading.Thread(
            target=self._do_speak_result,
            args=(text, settings),
            daemon=True,
        ).start()

    def _do_speak_result(self, text, settings):
        try:
            self.app_core.speak_text(text, settings)
            Clock.schedule_once(
                lambda dt: setattr(self.status_label, 'text', t('stt_done')), 0
            )
        except Exception as e:
            msg = t('stt_error', e=e)
            Clock.schedule_once(
                lambda dt, m=msg: setattr(self.status_label, 'text', m), 0
            )

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    def _show_export_popup(self):
        if not self._last_session:
            self.status_label.text = t('stt_no_session')
            return
        session = self._last_session
        _popup_ref = [None]

        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=t('stt_export_title'),
            font_size='15sp',
            size_hint_y=None,
            height=sp(36),
        ))

        btn_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=sp(110))
        for fmt, ext in [("TXT", ".txt"), ("DOCX", ".docx"), ("SRT", ".srt"), ("PDF", ".pdf")]:
            btn = RoundedButton(text=fmt, font_size='17sp')

            def _handler(inst, f=fmt, e=ext):
                if _popup_ref[0]:
                    _popup_ref[0].dismiss()
                threading.Thread(
                    target=self._native_save_and_export,
                    args=(session, f, e),
                    daemon=True,
                ).start()

            btn.bind(on_release=_handler)
            btn_grid.add_widget(btn)
        content.add_widget(btn_grid)

        cancel = RoundedButton(text=t('history_confirm_no'), size_hint_y=None, height=sp(46))
        content.add_widget(cancel)

        popup = Popup(
            title=t('stt_export_title'),
            content=content,
            size_hint=(0.82, 0.52),
        )
        _popup_ref[0] = popup
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _native_save_and_export(self, session, fmt: str, ext: str):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.asksaveasfilename(
                title=t('stt_export_title'),
                initialdir=os.path.expanduser('~'),
                defaultextension=ext,
                filetypes=[(fmt, f"*{ext}"), ('All files', '*.*')],
                initialfile=f"session_{session.created_at_iso[:10]}",
            )
            root.destroy()
            if path:
                self._run_export(session, fmt, path)
        except Exception as exc:
            msg = t('stt_export_error', e=exc)
            Clock.schedule_once(lambda dt, m=msg: setattr(self.status_label, 'text', m), 0)

    def _run_export(self, session, fmt: str, path: str):
        try:
            from stt.export import export_txt, export_docx, export_srt, export_pdf
            _EXPORTERS = {
                'TXT': export_txt, 'DOCX': export_docx,
                'SRT': export_srt, 'PDF': export_pdf,
            }
            _EXPORTERS[fmt](session, path)
            name = os.path.basename(path)
            msg = t('stt_export_done', name=name)
            Clock.schedule_once(lambda dt, m=msg: setattr(self.status_label, 'text', m), 0)
        except Exception as exc:
            msg = t('stt_export_error', e=exc)
            Clock.schedule_once(lambda dt, m=msg: setattr(self.status_label, 'text', m), 0)

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def go_back(self, instance):
        if self.is_recording:
            self.stop_recording()
        self.manager.current = 'main'

    def _copy_result(self, instance):
        text = self.result_input.text.strip()
        if not text:
            return
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(text)
        self.status_label.text = t('stt_copied')

    def _on_theme_refresh(self):
        from ui.theme import get as _theme
        th = _theme()
        normal, text_c = list(th['btn_normal']), list(th['text'])
        for btn in (self.back_btn, self.clear_btn, self.speak_result_btn, self.copy_btn):
            btn.btn_color = normal
            btn.color = text_c
        self.record_btn.color = text_c
        if not self.is_recording:
            self.record_btn.btn_color = normal
        self.export_btn.color = text_c
        if self._last_session and self._last_session.phrases:
            self.export_btn.btn_color = list(th['btn_accent'])
        else:
            self.export_btn.btn_color = normal
        self.status_label.color = text_c
