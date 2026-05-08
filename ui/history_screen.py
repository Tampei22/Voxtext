import os
import threading

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ui.theme import RoundedButton, get as _get_theme, register_refresh_hook, unregister_refresh_hook
from ui.i18n import load_lang, t


class HistoryScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'history'
        self.app_core = app_core
        self._active_tab = 'tts'

        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

        # Top row: back + clear-all
        top_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(50),
            spacing=dp(8),
        )
        self.back_btn = RoundedButton(size_hint_x=0.5)
        self.back_btn.bind(on_release=self.go_back)
        top_row.add_widget(self.back_btn)

        self.clear_all_btn = RoundedButton(size_hint_x=0.5)
        self.clear_all_btn.bind(on_release=self.confirm_clear_all)
        top_row.add_widget(self.clear_all_btn)
        layout.add_widget(top_row)

        self.title_label = Label(
            font_size='20sp',
            size_hint_y=None,
            height=sp(36),
        )
        layout.add_widget(self.title_label)

        # Tab row: TTS | STT
        tab_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(48),
            spacing=dp(8),
        )
        self.tab_tts_btn = RoundedButton(font_size='16sp')
        self.tab_tts_btn.bind(on_release=lambda _: self._set_tab('tts'))
        tab_row.add_widget(self.tab_tts_btn)

        self.tab_stt_btn = RoundedButton(font_size='16sp')
        self.tab_stt_btn.bind(on_release=lambda _: self._set_tab('stt'))
        tab_row.add_widget(self.tab_stt_btn)
        layout.add_widget(tab_row)

        self.status_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height=sp(25),
        )
        layout.add_widget(self.status_label)

        scroll = ScrollView()
        self.jobs_grid = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        self.jobs_grid.bind(minimum_height=self.jobs_grid.setter('height'))
        scroll.add_widget(self.jobs_grid)
        layout.add_widget(scroll)

        self.add_widget(layout)
        self._update_texts()

    def _update_texts(self):
        self.back_btn.text = t('back')
        self.clear_all_btn.text = t('history_clear_all')
        self.title_label.text = t('history_title')
        self.tab_tts_btn.text = t('history_tab_tts')
        self.tab_stt_btn.text = t('history_tab_stt')

    def on_enter(self, *args):
        load_lang()
        self._update_texts()
        self._refresh_tab_buttons()
        self.load_current_tab()
        register_refresh_hook(self._on_theme_refresh)
        self._on_theme_refresh()

    def on_leave(self, *args):
        unregister_refresh_hook(self._on_theme_refresh)

    # ------------------------------------------------------------------ #
    # Tab switching
    # ------------------------------------------------------------------ #

    def _set_tab(self, tab: str):
        self._active_tab = tab
        self._refresh_tab_buttons()
        self.load_current_tab()

    def _refresh_tab_buttons(self):
        from ui.theme import get as _theme
        th = _theme()
        self.tab_tts_btn.btn_color = list(
            th['btn_accent'] if self._active_tab == 'tts' else th['btn_normal']
        )
        self.tab_stt_btn.btn_color = list(
            th['btn_accent'] if self._active_tab == 'stt' else th['btn_normal']
        )

    def load_current_tab(self):
        if self._active_tab == 'tts':
            self._load_tts_jobs()
        else:
            self._load_stt_sessions()

    # ------------------------------------------------------------------ #
    # TTS tab
    # ------------------------------------------------------------------ #

    def _load_tts_jobs(self):
        from storage.jobs import list_jobs
        self.jobs_grid.clear_widgets()
        jobs = list_jobs()
        if not jobs:
            self.jobs_grid.add_widget(Label(
                text=t('history_empty'),
                font_size='16sp',
                size_hint_y=None,
                height=sp(60),
            ))
            self.status_label.text = t('history_count', n=0)
            return
        self.status_label.text = t('history_count', n=len(jobs))
        for job in reversed(jobs):
            self._add_tts_row(job)

    def _add_tts_row(self, job: dict):
        row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(80),
            spacing=dp(5),
        )

        info_col = BoxLayout(orientation='vertical')
        raw_text = job.get('text', '')
        preview = raw_text[:50] + ('...' if len(raw_text) > 50 else '')
        date_str = job.get('created_at_iso', '')[:10]

        lbl_preview = Label(
            text=preview,
            font_size='13sp',
            halign='left',
            valign='middle',
            color=list(_get_theme()['text']),
        )
        lbl_preview.bind(size=lbl_preview.setter('text_size'))
        info_col.add_widget(lbl_preview)

        lbl_date = Label(
            text=date_str,
            font_size='11sp',
            color=(0.7, 0.7, 0.7, 1),
            halign='left',
            valign='middle',
        )
        lbl_date.bind(size=lbl_date.setter('text_size'))
        info_col.add_widget(lbl_date)
        row.add_widget(info_col)

        play_btn = RoundedButton(text='Play', size_hint_x=None, width=dp(50), font_size='14sp')
        play_btn.bind(on_release=lambda inst, j=job: self._play_tts_job(j))
        row.add_widget(play_btn)

        copy_btn = RoundedButton(text=t('history_copy'), size_hint_x=None, width=dp(70), font_size='12sp')
        copy_btn.bind(on_release=lambda inst, tx=raw_text: self._copy_job_text(tx))
        row.add_widget(copy_btn)

        job_id = job.get('job_id', '')
        del_btn = RoundedButton(text='Del', size_hint_x=None, width=dp(50), font_size='14sp')
        del_btn.bind(on_release=lambda inst, jid=job_id: self._delete_tts_job(jid))
        row.add_widget(del_btn)

        self.jobs_grid.add_widget(row)

    def _play_tts_job(self, job: dict):
        text = job.get('text', '')
        if not text.strip():
            return
        self.status_label.text = t('history_playing')
        output_path = job.get('output_path')
        if output_path and os.path.exists(output_path):
            threading.Thread(
                target=self._do_play_mp3,
                args=(output_path,),
                daemon=True,
            ).start()
        else:
            from storage.settings import load_app_settings
            settings = load_app_settings().tts_settings()
            threading.Thread(
                target=self._do_speak_direct,
                args=(text, settings),
                daemon=True,
            ).start()

    def _do_play_mp3(self, path: str):
        import sys, subprocess
        script = (
            "import pygame, sys\n"
            "pygame.mixer.init()\n"
            f"pygame.mixer.music.load({repr(path)})\n"
            "pygame.mixer.music.play()\n"
            "while pygame.mixer.music.get_busy():\n"
            "    pygame.time.wait(100)\n"
            "pygame.mixer.quit()\n"
        )
        try:
            proc = subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            _, stderr_bytes = proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(stderr_bytes.decode("utf-8", errors="replace").strip())
            Clock.schedule_once(
                lambda dt: setattr(self.status_label, 'text', t('history_done')), 0
            )
        except Exception as e:
            msg = t('history_error', e=e)
            Clock.schedule_once(lambda dt, m=msg: setattr(self.status_label, 'text', m), 0)

    def _do_speak_direct(self, text, settings):
        try:
            self.app_core.tts.speak(text, settings)
            Clock.schedule_once(
                lambda dt: setattr(self.status_label, 'text', t('history_done')), 0
            )
        except Exception as e:
            msg = t('history_error', e=e)
            Clock.schedule_once(
                lambda dt, m=msg: setattr(self.status_label, 'text', m), 0
            )

    def _delete_tts_job(self, job_id: str):
        from storage.jobs import delete_job
        delete_job(job_id)
        self.load_current_tab()

    # ------------------------------------------------------------------ #
    # STT tab
    # ------------------------------------------------------------------ #

    def _load_stt_sessions(self):
        from storage.stt_sessions import list_sessions
        self.jobs_grid.clear_widgets()
        sessions = list_sessions()
        if not sessions:
            self.jobs_grid.add_widget(Label(
                text=t('history_stt_empty'),
                font_size='16sp',
                size_hint_y=None,
                height=sp(60),
            ))
            self.status_label.text = t('history_stt_count', n=0)
            return
        self.status_label.text = t('history_stt_count', n=len(sessions))
        for s in reversed(sessions):
            self._add_stt_row(s)

    def _add_stt_row(self, s: dict):
        row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(80),
            spacing=dp(5),
        )

        info_col = BoxLayout(orientation='vertical')
        phrases = s.get('phrases', [])
        raw_text = " ".join(p.get('text', '') for p in phrases)
        preview = raw_text[:50] + ('...' if len(raw_text) > 50 else '')
        word_count = len(raw_text.split()) if raw_text.strip() else 0
        date_str = s.get('created_at_iso', '')[:10]

        lbl_preview = Label(
            text=preview,
            font_size='13sp',
            halign='left',
            valign='middle',
            color=list(_get_theme()['text']),
        )
        lbl_preview.bind(size=lbl_preview.setter('text_size'))
        info_col.add_widget(lbl_preview)

        meta = f"{date_str}  •  {t('history_words', n=word_count)}"
        lbl_meta = Label(
            text=meta,
            font_size='11sp',
            color=(0.7, 0.7, 0.7, 1),
            halign='left',
            valign='middle',
        )
        lbl_meta.bind(size=lbl_meta.setter('text_size'))
        info_col.add_widget(lbl_meta)
        row.add_widget(info_col)

        exp_btn = RoundedButton(text=t('stt_export'), size_hint_x=None, width=dp(75), font_size='11sp')
        exp_btn.bind(on_release=lambda inst, sd=s: self._export_session_from_row(sd))
        row.add_widget(exp_btn)

        session_id = s.get('session_id', '')
        del_btn = RoundedButton(text='✕', size_hint_x=None, width=dp(50), font_size='14sp')
        del_btn.bind(on_release=lambda inst, sid=session_id: self._delete_stt_session(sid))
        row.add_widget(del_btn)

        self.jobs_grid.add_widget(row)

    def _delete_stt_session(self, session_id: str):
        from storage.stt_sessions import delete_session
        delete_session(session_id)
        self.load_current_tab()

    def _export_session_from_row(self, session_dict: dict):
        from storage.stt_sessions import session_from_dict
        session = session_from_dict(session_dict)
        self._show_export_popup(session)

    # ------------------------------------------------------------------ #
    # Export popup (shared between direct and row-triggered export)
    # ------------------------------------------------------------------ #

    def _show_export_popup(self, session):
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

            def _handler(_, f=fmt, e=ext):
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
            Clock.schedule_once(lambda _, m=msg: setattr(self.status_label, 'text', m), 0)

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
            Clock.schedule_once(lambda _, m=msg: setattr(self.status_label, 'text', m), 0)
        except Exception as exc:
            msg = t('stt_export_error', e=exc)
            Clock.schedule_once(lambda _, m=msg: setattr(self.status_label, 'text', m), 0)

    # ------------------------------------------------------------------ #
    # Clear all (tab-aware)
    # ------------------------------------------------------------------ #

    def confirm_clear_all(self, instance):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=t('history_confirm_text'), font_size='18sp'))

        btn_row = BoxLayout(size_hint_y=None, height=sp(50), spacing=dp(10))
        confirm_btn = RoundedButton(text=t('history_confirm_yes'))
        cancel_btn = RoundedButton(text=t('history_confirm_no'))
        btn_row.add_widget(confirm_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        popup = Popup(
            title=t('history_confirm_title'),
            content=content,
            size_hint=(0.8, 0.4),
        )

        def on_confirm(inst):
            if self._active_tab == 'tts':
                from storage.jobs import clear_jobs
                clear_jobs()
            else:
                from storage.stt_sessions import clear_sessions
                clear_sessions()
            self.load_current_tab()
            popup.dismiss()

        confirm_btn.bind(on_release=on_confirm)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def go_back(self, instance):
        self.manager.current = 'main'

    def _copy_job_text(self, text: str):
        if not text.strip():
            return
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(text)
        self.status_label.text = t('stt_copied')

    def _on_theme_refresh(self):
        from ui.theme import get as _theme
        th = _theme()
        normal, text_c = list(th['btn_normal']), list(th['text'])
        for btn in (self.back_btn, self.clear_all_btn):
            btn.btn_color = normal
            btn.color = text_c
        self.title_label.color = text_c
        self.status_label.color = text_c
        self._refresh_tab_buttons()
