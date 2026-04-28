from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner

from storage.settings import load_app_settings, save_app_settings
from tts.edge_tts_engine import EdgeTTSEngine
from ui.theme import RoundedButton, get, current_name, restart_app
from ui.i18n import load_lang, t

_LANG_OPTIONS = [("RO", "ro"), ("RU", "ru"), ("EN", "en")]
_THEME_KEYS = [("settings_theme_dark", "dark"), ("settings_theme_light", "light")]


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'settings'
        self._s = load_app_settings()
        self._refreshing = False
        self._lang_btns: dict[str, RoundedButton] = {}
        self._theme_btns: dict[str, RoundedButton] = {}

        outer = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

        self.back_btn = RoundedButton(size_hint_y=None, height=50)
        self.back_btn.bind(on_release=self.go_back)
        outer.add_widget(self.back_btn)

        self.title_label = Label(
            font_size='22sp',
            size_hint_y=None,
            height=sp(44),
        )
        outer.add_widget(self.title_label)

        scroll = ScrollView()
        content = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        content.bind(minimum_height=content.setter('height'))

        self.sec_lang = self._section_label()
        content.add_widget(self.sec_lang)

        lang_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=sp(52), spacing=dp(8))
        for display, code in _LANG_OPTIONS:
            btn = RoundedButton(text=display, font_size='17sp')
            btn.bind(on_release=lambda inst, c=code: self._set_lang(c))
            self._lang_btns[code] = btn
            lang_row.add_widget(btn)
        content.add_widget(lang_row)

        voice_col = BoxLayout(orientation='vertical', size_hint_y=None, height=sp(84), spacing=dp(4))
        self.voice_label = Label(
            font_size='14sp',
            size_hint_y=None,
            height=sp(26),
            halign='left',
        )
        self.voice_spinner = Spinner(
            text='', values=[],
            size_hint_y=None, height=sp(46), font_size='14sp',
        )
        self.voice_spinner.bind(text=self._on_voice_selected)
        voice_col.add_widget(self.voice_label)
        voice_col.add_widget(self.voice_spinner)
        content.add_widget(voice_col)

        self.sec_tts = self._section_label()
        content.add_widget(self.sec_tts)

        self.rate_label, self.rate_slider = self._slider_row(
            content, min_val=100, max_val=300,
            value=self._s.tts_rate, step=5, on_value=self._on_rate,
        )
        self.vol_label, self.vol_slider = self._slider_row(
            content, min_val=0.1, max_val=1.0,
            value=self._s.tts_volume, step=0.1, on_value=self._on_volume,
        )

        self.sec_stt = self._section_label()
        content.add_widget(self.sec_stt)

        self.pause_label, self.pause_slider = self._slider_row(
            content, min_val=0.3, max_val=3.0,
            value=self._s.stt_pause_threshold, step=0.1, on_value=self._on_pause,
        )

        self.sec_history = self._section_label()
        content.add_widget(self.sec_history)

        self.hist_label, self.hist_slider = self._slider_row(
            content, min_val=10, max_val=200,
            value=self._s.max_history, step=10, on_value=self._on_max_history,
        )

        self.sec_appearance = self._section_label()
        content.add_widget(self.sec_appearance)

        theme_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=sp(52), spacing=dp(8))
        for key, tname in _THEME_KEYS:
            btn = RoundedButton(font_size='16sp')
            btn.bind(on_release=lambda inst, n=tname: self._set_theme(n))
            self._theme_btns[tname] = btn
            theme_row.add_widget(btn)
        content.add_widget(theme_row)

        pct = int(self._s.font_scale * 100)
        self.scale_label, self.scale_slider = self._slider_row(
            content, min_val=85, max_val=150,
            value=pct, step=5, on_value=self._on_font_scale,
        )

        self.restart_btn = RoundedButton(
            font_size='14sp',
            size_hint_y=None, height=sp(54),
            btn_color=list(get()['btn_accent']),
        )
        self.restart_btn.bind(on_release=lambda inst: restart_app())
        content.add_widget(self.restart_btn)

        scroll.add_widget(content)
        outer.add_widget(scroll)
        self.add_widget(outer)

        self._update_texts()
        self._refresh_lang_buttons()
        self._refresh_theme_buttons()
        self._refresh_voice_spinner()

    def _section_label(self) -> Label:
        lbl = Label(
            font_size='13sp',
            color=get()['section'],
            size_hint_y=None,
            height=sp(32),
        )
        return lbl

    def _slider_row(self, parent, min_val, max_val, value, step, on_value):
        col = BoxLayout(orientation='vertical', size_hint_y=None, height=sp(76), spacing=dp(2))
        lbl = Label(text='', font_size='14sp', size_hint_y=None, height=sp(28))
        sldr = Slider(min=min_val, max=max_val, value=value, step=step)
        sldr.bind(value=on_value)
        col.add_widget(lbl)
        col.add_widget(sldr)
        parent.add_widget(col)
        return lbl, sldr

    def _update_texts(self):
        self.back_btn.text = t('back')
        self.title_label.text = t('settings_title')
        self.sec_lang.text = f'— {t("settings_lang_voice")} —'
        self.voice_label.text = t('settings_voice')
        self.sec_tts.text = f'— {t("settings_tts_section")} —'
        self.rate_label.text = t('settings_rate', n=self._s.tts_rate)
        self.vol_label.text = t('settings_volume', n=f'{self._s.tts_volume:.1f}')
        self.sec_stt.text = f'— {t("settings_stt_section")} —'
        self.pause_label.text = t('settings_pause', n=f'{self._s.stt_pause_threshold:.1f}')
        self.sec_history.text = f'— {t("settings_history_section")} —'
        self.hist_label.text = t('settings_max_history', n=self._s.max_history)
        self.sec_appearance.text = f'— {t("settings_appearance")} —'
        pct = int(self._s.font_scale * 100)
        self.scale_label.text = t('settings_scale', n=pct)
        self.restart_btn.text = t('settings_restart')
        for key, tname in _THEME_KEYS:
            self._theme_btns[tname].text = t(key)

    def _refresh_lang_buttons(self):
        th = get()
        for code, btn in self._lang_btns.items():
            btn.btn_color = list(th['btn_accent'] if code == self._s.lang else th['btn_normal'])

    def _refresh_theme_buttons(self):
        th = get()
        for tname, btn in self._theme_btns.items():
            btn.btn_color = list(th['btn_accent'] if tname == self._s.theme else th['btn_normal'])

    def _refresh_voice_spinner(self):
        self._refreshing = True
        voices = EdgeTTSEngine.VOICES_BY_LANG.get(self._s.lang, [])
        names = [name for name, _ in voices]
        self.voice_spinner.values = names

        selected = ''
        if self._s.voice_id:
            for name, vid in voices:
                if vid == self._s.voice_id:
                    selected = name
                    break
        self.voice_spinner.text = selected or (names[0] if names else '')
        self._refreshing = False

    def _set_lang(self, lang: str):
        self._s.lang = lang
        self._s.voice_id = None
        self._refresh_lang_buttons()
        self._refresh_voice_spinner()
        save_app_settings(self._s)

    def _on_voice_selected(self, spinner, name):
        if self._refreshing:
            return
        for vname, vid in EdgeTTSEngine.VOICES_BY_LANG.get(self._s.lang, []):
            if vname == name:
                self._s.voice_id = vid
                break
        save_app_settings(self._s)

    def _on_rate(self, slider, value):
        if self._refreshing:
            return
        self._s.tts_rate = int(value)
        self.rate_label.text = t('settings_rate', n=int(value))
        save_app_settings(self._s)

    def _on_volume(self, slider, value):
        if self._refreshing:
            return
        self._s.tts_volume = round(value, 1)
        self.vol_label.text = t('settings_volume', n=f'{round(value, 1):.1f}')
        save_app_settings(self._s)

    def _on_pause(self, slider, value):
        if self._refreshing:
            return
        self._s.stt_pause_threshold = round(value, 1)
        self.pause_label.text = t('settings_pause', n=f'{round(value, 1):.1f}')
        save_app_settings(self._s)

    def _on_max_history(self, slider, value):
        if self._refreshing:
            return
        self._s.max_history = int(value)
        self.hist_label.text = t('settings_max_history', n=int(value))
        save_app_settings(self._s)

    def _set_theme(self, theme_name: str):
        self._s.theme = theme_name
        save_app_settings(self._s)
        self._refresh_theme_buttons()

    def _on_font_scale(self, slider, value):
        if self._refreshing:
            return
        self._s.font_scale = round(value / 100, 2)
        self.scale_label.text = t('settings_scale', n=int(value))
        save_app_settings(self._s)

    def on_enter(self, *args):
        load_lang()
        self._refreshing = True
        self._s = load_app_settings()
        self._update_texts()
        self._refresh_lang_buttons()
        self._refresh_theme_buttons()
        self._refresh_voice_spinner()
        self.rate_slider.value = self._s.tts_rate
        self.vol_slider.value = self._s.tts_volume
        self.pause_slider.value = self._s.stt_pause_threshold
        self.hist_slider.value = self._s.max_history
        pct = int(self._s.font_scale * 100)
        self.scale_slider.value = pct
        self._refreshing = False

    def go_back(self, instance):
        self.manager.current = 'main'
