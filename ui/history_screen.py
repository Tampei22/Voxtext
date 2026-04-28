import threading

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from ui.theme import RoundedButton
from ui.i18n import load_lang, t


class HistoryScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'history'
        self.app_core = app_core

        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

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
            height=sp(40),
        )
        layout.add_widget(self.title_label)

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

    def on_enter(self, *args):
        load_lang()
        self._update_texts()
        self.load_jobs()

    def load_jobs(self):
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
            self._add_job_row(job)

    def _add_job_row(self, job):
        row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=sp(70),
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

        play_btn = RoundedButton(text='▶', size_hint_x=None, width=dp(55), font_size='18sp')
        play_btn.bind(on_release=lambda inst, tx=raw_text: self.play_job(tx))
        row.add_widget(play_btn)

        job_id = job.get('job_id', '')
        del_btn = RoundedButton(text='✕', size_hint_x=None, width=dp(55), font_size='18sp')
        del_btn.bind(on_release=lambda inst, jid=job_id: self.delete_job(jid))
        row.add_widget(del_btn)

        self.jobs_grid.add_widget(row)

    def play_job(self, text):
        if not text.strip():
            return
        from storage.settings import load_app_settings
        settings = load_app_settings().tts_settings()
        self.status_label.text = t('history_playing')
        threading.Thread(
            target=self._do_speak,
            args=(text, settings),
            daemon=True,
        ).start()

    def _do_speak(self, text, settings):
        try:
            self.app_core.speak_text(text, settings)
            Clock.schedule_once(
                lambda dt: setattr(self.status_label, 'text', t('history_done')), 0
            )
        except Exception as e:
            msg = t('history_error', e=e)
            Clock.schedule_once(
                lambda dt, m=msg: setattr(self.status_label, 'text', m), 0
            )

    def delete_job(self, job_id):
        from storage.jobs import delete_job
        delete_job(job_id)
        self.load_jobs()

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
            from storage.jobs import clear_jobs
            clear_jobs()
            self.load_jobs()
            popup.dismiss()

        confirm_btn.bind(on_release=on_confirm)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def go_back(self, instance):
        self.manager.current = 'main'
