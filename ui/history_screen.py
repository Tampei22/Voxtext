import threading

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView


class HistoryScreen(Screen):
    def __init__(self, app_core, **kwargs):
        super().__init__(**kwargs)
        self.name = 'history'
        self.app_core = app_core

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        top_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=50,
            spacing=10,
        )
        back_btn = Button(text='← Назад', size_hint_x=0.5)
        back_btn.bind(on_release=self.go_back)
        top_row.add_widget(back_btn)

        clear_btn = Button(text='ОЧИСТИТЬ ВСЁ', size_hint_x=0.5)
        clear_btn.bind(on_release=self.confirm_clear_all)
        top_row.add_widget(clear_btn)
        layout.add_widget(top_row)

        layout.add_widget(Label(
            text='История заданий',
            font_size='20sp',
            size_hint_y=None,
            height=40,
        ))

        self.status_label = Label(
            text='',
            font_size='14sp',
            size_hint_y=None,
            height=25,
        )
        layout.add_widget(self.status_label)

        scroll = ScrollView()
        self.jobs_grid = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.jobs_grid.bind(minimum_height=self.jobs_grid.setter('height'))
        scroll.add_widget(self.jobs_grid)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_jobs()

    def load_jobs(self):
        from storage.jobs import list_jobs
        self.jobs_grid.clear_widgets()

        jobs = list_jobs()
        if not jobs:
            self.jobs_grid.add_widget(Label(
                text='История пуста',
                font_size='16sp',
                size_hint_y=None,
                height=60,
            ))
            self.status_label.text = '0 заданий'
            return

        self.status_label.text = f'{len(jobs)} заданий'
        for job in reversed(jobs):
            self._add_job_row(job)

    def _add_job_row(self, job):
        row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=70,
            spacing=5,
        )

        info_col = BoxLayout(orientation='vertical')
        raw_text = job.get('text', '')
        preview = raw_text[:50] + ('...' if len(raw_text) > 50 else '')
        date_str = job.get('created_at_iso', '')[:10]

        info_col.add_widget(Label(
            text=preview,
            font_size='13sp',
            halign='left',
            valign='middle',
        ))
        info_col.add_widget(Label(
            text=date_str,
            font_size='11sp',
            color=(0.7, 0.7, 0.7, 1),
            halign='left',
            valign='middle',
        ))
        row.add_widget(info_col)

        play_btn = Button(text='▶', size_hint_x=None, width=55, font_size='18sp')
        play_btn.bind(on_release=lambda inst, t=raw_text: self.play_job(t))
        row.add_widget(play_btn)

        job_id = job.get('job_id', '')
        del_btn = Button(text='✕', size_hint_x=None, width=55, font_size='18sp')
        del_btn.bind(on_release=lambda inst, jid=job_id: self.delete_job(jid))
        row.add_widget(del_btn)

        self.jobs_grid.add_widget(row)

    def play_job(self, text):
        if not text.strip():
            return
        from app_core.models import TTSSettings
        settings = TTSSettings(lang="ro")
        self.status_label.text = 'Озвучивание...'
        threading.Thread(
            target=self._do_speak,
            args=(text, settings),
            daemon=True,
        ).start()

    def _do_speak(self, text, settings):
        try:
            self.app_core.speak_text(text, settings)
            Clock.schedule_once(
                lambda dt: setattr(self.status_label, 'text', 'Готово'), 0
            )
        except Exception as e:
            Clock.schedule_once(
                lambda dt: setattr(self.status_label, 'text', f'Ошибка: {e}'), 0
            )

    def delete_job(self, job_id):
        from storage.jobs import delete_job
        delete_job(job_id)
        self.load_jobs()

    def confirm_clear_all(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text='Удалить всю историю?', font_size='18sp'))

        btn_row = BoxLayout(size_hint_y=None, height=50, spacing=10)
        confirm_btn = Button(text='Да, удалить')
        cancel_btn = Button(text='Отмена')
        btn_row.add_widget(confirm_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        popup = Popup(
            title='Подтверждение',
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
