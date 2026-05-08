from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner

from storage.settings import load_app_settings, save_app_settings, default_stt_engine
from tts.edge_tts_engine import EdgeTTSEngine
from ui.theme import (
    RoundedButton, COLOR_SCHEMES,
    apply_color_scheme, apply_theme,
    get, current_scheme, restart_app,
    register_refresh_hook, unregister_refresh_hook,
)
from ui.i18n import load_lang, t

_LANG_OPTIONS   = [("RO", "ro"), ("RU", "ru"), ("EN", "en")]
_THEME_KEYS     = [("DARK", "dark"), ("LIGHT", "light")]
_WHISPER_MODELS = ("tiny", "base", "small", "medium")
_STT_ENGINES    = [("Whisper", "whisper"), ("Google", "google")]
_SCHEME_NAMES   = {
    "blue": "Albastru", "green": "Verde",
    "orange": "Portocaliu", "purple": "Violet", "red": "Rosu",
}


class _SectionHeader(Label):
    def __init__(self, text, **kwargs):
        th = get()
        super().__init__(
            text=text,
            font_size="12sp",
            size_hint_y=None,
            height=dp(28),
            color=th["btn_accent"],
            bold=True,
            halign="left",
            valign="middle",
        )
        self.bind(size=self.setter("text_size"))


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"
        self._s = load_app_settings()
        self._refreshing = False
        self._lang_btns:       dict[str, RoundedButton] = {}
        self._theme_btns:      dict[str, RoundedButton] = {}
        self._whisper_btns:    dict[str, RoundedButton] = {}
        self._stt_engine_btns: dict[str, RoundedButton] = {}
        self._scheme_btns:  dict[str, RoundedButton] = {}
        self._scheme_name_lbls: list[Label] = []
        self._section_headers: list[_SectionHeader]  = []
        self._reco_row_lbls:   list[Label] = []
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        top = BoxLayout(orientation="horizontal",
                        size_hint_y=None, height=dp(48), spacing=dp(8))
        self.back_btn = RoundedButton(
            size_hint=(None, None), size=(dp(90), dp(44)),
            font_size="14sp",
        )
        self.back_btn.bind(on_release=self.go_back)
        self.title_lbl = Label(
            font_size="22sp", bold=True,
            halign="left", valign="middle",
        )
        self.title_lbl.bind(size=self.title_lbl.setter("text_size"))
        top.add_widget(self.back_btn)
        top.add_widget(self.title_lbl)
        outer.add_widget(top)

        scroll = ScrollView(do_scroll_x=False)
        grid = GridLayout(cols=1, spacing=dp(10),
                          size_hint_y=None, padding=(0, dp(4)))
        grid.bind(minimum_height=grid.setter("height"))

        # ── 1. Language & Voice ───────────────────────────────────────────
        grid.add_widget(self._make_header("LIMBA SI VOCE"))

        lang_row = BoxLayout(orientation="horizontal",
                             size_hint_y=None, height=dp(44), spacing=dp(8))
        for display, code in _LANG_OPTIONS:
            btn = RoundedButton(text=display, font_size="16sp",
                                size_hint_y=None, height=dp(44))
            btn.bind(on_release=lambda _, c=code: self._set_lang(c))
            self._lang_btns[code] = btn
            lang_row.add_widget(btn)
        grid.add_widget(lang_row)

        self.voice_spinner = Spinner(
            text="", values=[],
            size_hint_y=None, height=dp(44), font_size="14sp",
        )
        self.voice_spinner.bind(text=self._on_voice_selected)
        grid.add_widget(self.voice_spinner)

        # ── 2. TTS ───────────────────────────────────────────────────────
        grid.add_widget(self._make_header("SINTEZA VOCALA (TTS)"))
        self.rate_lbl, self.rate_slider = self._slider_row(
            grid, 100, 300, self._s.tts_rate, 5, self._on_rate)
        self.vol_lbl, self.vol_slider = self._slider_row(
            grid, 0.1, 1.0, self._s.tts_volume, 0.1, self._on_volume)

        # ── 3. STT ───────────────────────────────────────────────────────
        grid.add_widget(self._make_header("RECUNOASTERE VOCALA (STT)"))
        self.pause_lbl, self.pause_slider = self._slider_row(
            grid, 0.3, 3.0, self._s.stt_pause_threshold, 0.1, self._on_pause)

        self.whisper_lbl = Label(
            font_size="13sp", size_hint_y=None, height=dp(22),
            halign="left", valign="middle", color=get()["text"],
        )
        self.whisper_lbl.bind(size=self.whisper_lbl.setter("text_size"))
        grid.add_widget(self.whisper_lbl)

        whisper_row = BoxLayout(orientation="horizontal",
                                size_hint_y=None, height=dp(44), spacing=dp(6))
        for m in _WHISPER_MODELS:
            btn = RoundedButton(text=m, font_size="13sp",
                                size_hint_y=None, height=dp(44))
            btn.bind(on_release=lambda _, model=m: self._set_whisper_model(model))
            self._whisper_btns[m] = btn
            whisper_row.add_widget(btn)
        grid.add_widget(whisper_row)

        self.stt_engine_lbl = Label(
            text="Motor STT activ",
            font_size="13sp", size_hint_y=None, height=dp(22),
            halign="left", valign="middle", color=get()["text"],
        )
        self.stt_engine_lbl.bind(size=self.stt_engine_lbl.setter("text_size"))
        grid.add_widget(self.stt_engine_lbl)

        engine_row = BoxLayout(orientation="horizontal",
                               size_hint_y=None, height=dp(44), spacing=dp(8))
        for label, eng in _STT_ENGINES:
            btn = RoundedButton(text=label, font_size="15sp",
                                size_hint_y=None, height=dp(44))
            btn.bind(on_release=lambda _, e=eng: self._set_stt_engine(e))
            self._stt_engine_btns[eng] = btn
            engine_row.add_widget(btn)
        grid.add_widget(engine_row)

        # ── 4. Benchmark recommendations ──────────────────────────────────
        self._reco_title_hdr = _SectionHeader(t("benchmark_reco_title"))
        self._section_headers.append(self._reco_title_hdr)
        grid.add_widget(self._reco_title_hdr)

        th = get()
        for row_text in [
            "Română:   Google STT  (WER 27% vs 58% Whisper)",
            "Русский:     Whisper medium  (WER 15% vs 13% Google)",
            "English:  Whisper medium  (WER 20% vs 37% Google)",
        ]:
            lbl = Label(
                text=row_text, font_size="13sp",
                size_hint_y=None, height=dp(24),
                halign="left", valign="middle", color=th["text"],
            )
            lbl.bind(size=lbl.setter("text_size"))
            grid.add_widget(lbl)
            self._reco_row_lbls.append(lbl)

        self._reco_note_lbl = Label(
            text=t("benchmark_reco_note"),
            font_size="11sp", size_hint_y=None, height=dp(52),
            halign="left", valign="top", color=th["text"],
        )
        self._reco_note_lbl.bind(size=self._reco_note_lbl.setter("text_size"))
        grid.add_widget(self._reco_note_lbl)

        self._reco_apply_btn = RoundedButton(
            size_hint_y=None, height=dp(44), font_size="14sp",
        )
        self._reco_apply_btn.bind(on_release=self._apply_recommendations)
        grid.add_widget(self._reco_apply_btn)

        # ── 5. History ────────────────────────────────────────────────────
        grid.add_widget(self._make_header("ISTORIC"))
        self.hist_lbl, self.hist_slider = self._slider_row(
            grid, 10, 200, self._s.max_history, 10, self._on_max_history)

        # ── 5. Appearance ─────────────────────────────────────────────────
        grid.add_widget(self._make_header("ASPECT"))

        theme_row = BoxLayout(orientation="horizontal",
                              size_hint_y=None, height=dp(44), spacing=dp(8))
        for label, tname in _THEME_KEYS:
            btn = RoundedButton(text=label, font_size="15sp",
                                size_hint_y=None, height=dp(44))
            btn.bind(on_release=lambda _, n=tname: self._set_theme(n))
            self._theme_btns[tname] = btn
            theme_row.add_widget(btn)
        grid.add_widget(theme_row)

        self.scheme_lbl = Label(
            text=t("settings_color_scheme"),
            font_size="13sp", color=get()["text"],
            size_hint_y=None, height=dp(24),
            halign="left", valign="middle",
        )
        self.scheme_lbl.bind(size=self.scheme_lbl.setter("text_size"))
        grid.add_widget(self.scheme_lbl)

        scheme_row = BoxLayout(orientation="horizontal",
                               size_hint_y=None, height=dp(52), spacing=dp(6))
        for key, color in COLOR_SCHEMES.items():
            col_box = BoxLayout(orientation="vertical", spacing=dp(2))
            dot_btn = RoundedButton(
                text="",
                size_hint_y=None, height=dp(34),
                btn_color=list(color),
                corner_radius=8,
            )
            dot_btn.bind(on_release=lambda _, k=key: self._set_scheme(k))
            self._scheme_btns[key] = dot_btn
            name_lbl = Label(
                text=_SCHEME_NAMES.get(key, key),
                font_size="9sp", color=get()["text"],
                size_hint_y=None, height=dp(14),
                halign="center",
            )
            name_lbl.bind(size=name_lbl.setter("text_size"))
            self._scheme_name_lbls.append(name_lbl)
            col_box.add_widget(dot_btn)
            col_box.add_widget(name_lbl)
            scheme_row.add_widget(col_box)
        grid.add_widget(scheme_row)

        grid.add_widget(self._make_header("SCALA TEXT"))
        pct = int(self._s.font_scale * 100)
        self.scale_lbl, self.scale_slider = self._slider_row(
            grid, 85, 150, pct, 5, self._on_font_scale)

        self.restart_btn = RoundedButton(
            size_hint_y=None, height=dp(48),
            font_size="13sp",
            btn_color=list(get()["btn_accent"]),
        )
        self.restart_btn.bind(on_release=lambda _: restart_app())
        grid.add_widget(self.restart_btn)

        grid.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))

        scroll.add_widget(grid)
        outer.add_widget(scroll)
        self.add_widget(outer)

        self._update_texts()
        self._refresh_lang_buttons()
        self._refresh_theme_buttons()
        self._refresh_whisper_buttons()
        self._refresh_stt_engine_buttons()
        self._refresh_scheme_buttons()
        self._refresh_voice_spinner()

    def _make_header(self, text: str) -> _SectionHeader:
        h = _SectionHeader(text)
        self._section_headers.append(h)
        return h

    # ── Slider helper ─────────────────────────────────────────────────────

    def _slider_row(self, parent, min_val, max_val, value, step, on_value):
        box = BoxLayout(orientation="vertical",
                        size_hint_y=None, height=dp(64), spacing=dp(0))
        lbl = Label(
            text="", font_size="13sp",
            size_hint_y=None, height=dp(22),
            halign="left", valign="middle", color=get()["text"],
        )
        lbl.bind(size=lbl.setter("text_size"))
        sldr = Slider(
            min=min_val, max=max_val, value=value, step=step,
            size_hint_y=None, height=dp(40),
            cursor_size=(dp(22), dp(22)),
        )
        sldr.bind(value=on_value)
        box.add_widget(lbl)
        box.add_widget(sldr)
        parent.add_widget(box)
        return lbl, sldr

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_rate(self, slider, value):
        if self._refreshing: return
        self._s.tts_rate = int(value)
        self.rate_lbl.text = t("settings_rate", n=int(value))
        save_app_settings(self._s)

    def _on_volume(self, slider, value):
        if self._refreshing: return
        self._s.tts_volume = round(float(value), 1)
        self.vol_lbl.text = t("settings_volume", n=f"{self._s.tts_volume:.1f}")
        save_app_settings(self._s)

    def _on_pause(self, slider, value):
        if self._refreshing: return
        self._s.stt_pause_threshold = round(float(value), 1)
        self.pause_lbl.text = t("settings_pause",
                                n=f"{self._s.stt_pause_threshold:.1f}")
        save_app_settings(self._s)

    def _on_max_history(self, slider, value):
        if self._refreshing: return
        self._s.max_history = int(value)
        self.hist_lbl.text = t("settings_max_history", n=self._s.max_history)
        save_app_settings(self._s)

    def _on_font_scale(self, slider, value):
        if self._refreshing: return
        self._s.font_scale = round(float(value) / 100.0, 2)
        self.scale_lbl.text = t("settings_scale", n=int(value))
        save_app_settings(self._s)

    def _set_lang(self, lang: str):
        self._s.lang = lang
        self._s.voice_id = None
        self._refresh_lang_buttons()
        self._refresh_voice_spinner()
        # Auto-select the recommended engine for this language.
        self._set_stt_engine(default_stt_engine(lang))

    def _set_stt_engine(self, name: str):
        if self._s.stt_engine == name:
            return
        # Swap primary ↔ fallback in the running AppCore so the change is
        # effective immediately — no restart needed.
        from kivy.app import App
        core = getattr(App.get_running_app(), "app_core", None)
        if core is not None:
            core.stt, core._fallback_stt = core._fallback_stt, core.stt
        self._s.stt_engine = name
        self._refresh_stt_engine_buttons()
        save_app_settings(self._s)

    def _on_voice_selected(self, spinner, name):
        if self._refreshing: return
        for vname, vid in EdgeTTSEngine.VOICES_BY_LANG.get(self._s.lang, []):
            if vname == name:
                self._s.voice_id = vid
                break
        save_app_settings(self._s)

    def _set_theme(self, theme_name: str):
        self._s.theme = theme_name
        save_app_settings(self._s)
        apply_theme(theme_name)         # live switch — no restart needed
        # apply_theme fires refresh hooks, but also call local refresh directly
        # so the settings screen updates without waiting for the hook dispatch
        self._refresh_theme_buttons()

    def _set_whisper_model(self, model: str):
        self._s.whisper_model = model
        self.whisper_lbl.text = t("settings_whisper_model", model=model)
        self._refresh_whisper_buttons()
        save_app_settings(self._s)

    def _apply_recommendations(self, *args):
        from kivy.clock import Clock
        self._s.whisper_model = "medium"
        self._set_stt_engine(default_stt_engine(self._s.lang))
        self._refresh_whisper_buttons()
        save_app_settings(self._s)
        self._reco_apply_btn.text = t("benchmark_reco_applied")
        Clock.schedule_once(
            lambda dt: setattr(self._reco_apply_btn, "text", t("benchmark_reco_apply")), 2
        )

    def _set_scheme(self, scheme: str):
        self._s.color_scheme = scheme
        save_app_settings(self._s)
        apply_color_scheme(scheme)
        self._refresh_scheme_buttons()
        th = get()
        self.restart_btn.btn_color = list(th["btn_accent"])

    # ── Refresh helpers ───────────────────────────────────────────────────

    def _refresh_lang_buttons(self):
        th = get()
        for code, btn in self._lang_btns.items():
            btn.btn_color = list(
                th["btn_accent"] if code == self._s.lang else th["btn_normal"]
            )

    def _refresh_theme_buttons(self):
        th = get()
        for tname, btn in self._theme_btns.items():
            btn.btn_color = list(
                th["btn_accent"] if tname == self._s.theme else th["btn_normal"]
            )

    def _refresh_whisper_buttons(self):
        th = get()
        for model, btn in self._whisper_btns.items():
            btn.btn_color = list(
                th["btn_accent"] if model == self._s.whisper_model
                else th["btn_normal"]
            )

    def _refresh_stt_engine_buttons(self):
        th = get()
        for eng, btn in self._stt_engine_btns.items():
            btn.btn_color = list(
                th["btn_accent"] if eng == self._s.stt_engine else th["btn_normal"]
            )

    def _refresh_scheme_buttons(self):
        cur = getattr(self._s, "color_scheme", "blue")
        for key, btn in self._scheme_btns.items():
            btn.btn_color = list(COLOR_SCHEMES.get(key, [0.2, 0.47, 0.9, 1]))
            btn.text = "●" if key == cur else ""

    def _refresh_voice_spinner(self):
        self._refreshing = True
        voices = EdgeTTSEngine.VOICES_BY_LANG.get(self._s.lang, [])
        names = [name for name, _ in voices]
        self.voice_spinner.values = names
        selected = ""
        if self._s.voice_id:
            for name, vid in voices:
                if vid == self._s.voice_id:
                    selected = name
                    break
        self.voice_spinner.text = selected or (names[0] if names else "")
        self._refreshing = False

    def _update_texts(self):
        self.back_btn.text    = t("back")
        self.title_lbl.text   = t("settings_title")
        self.rate_lbl.text    = t("settings_rate",       n=self._s.tts_rate)
        self.vol_lbl.text     = t("settings_volume",     n=f"{self._s.tts_volume:.1f}")
        self.pause_lbl.text   = t("settings_pause",      n=f"{self._s.stt_pause_threshold:.1f}")
        self.whisper_lbl.text = t("settings_whisper_model", model=self._s.whisper_model)
        self.hist_lbl.text    = t("settings_max_history", n=self._s.max_history)
        self.scale_lbl.text   = t("settings_scale",      n=int(self._s.font_scale * 100))
        self.restart_btn.text = t("settings_restart")
        self._reco_title_hdr.text = t("benchmark_reco_title")
        self._reco_note_lbl.text  = t("benchmark_reco_note")
        self._reco_apply_btn.text = t("benchmark_reco_apply")

    # ── Theme refresh hook ────────────────────────────────────────────────

    def _on_theme_refresh(self):
        th = get()
        text_c = list(th["text"])
        for hdr in self._section_headers:
            hdr.color = th["btn_accent"]
        self.back_btn.color = text_c
        self.title_lbl.color = text_c
        self.restart_btn.btn_color = list(th["btn_accent"])
        self.restart_btn.color = text_c
        for lbl in (self.rate_lbl, self.vol_lbl, self.pause_lbl,
                    self.hist_lbl, self.scale_lbl, self.whisper_lbl,
                    self.stt_engine_lbl):
            lbl.color = text_c
        for btn in self._lang_btns.values():
            btn.color = text_c
        for btn in self._theme_btns.values():
            btn.color = text_c
        for btn in self._whisper_btns.values():
            btn.color = text_c
        for btn in self._stt_engine_btns.values():
            btn.color = text_c
        self.scheme_lbl.color = text_c
        for lbl in self._scheme_name_lbls:
            lbl.color = text_c
        for lbl in self._reco_row_lbls:
            lbl.color = text_c
        self._reco_note_lbl.color = text_c
        self._reco_apply_btn.color = text_c
        self._refresh_lang_buttons()
        self._refresh_theme_buttons()
        self._refresh_whisper_buttons()
        self._refresh_stt_engine_buttons()
        self._refresh_scheme_buttons()

    # ── Screen lifecycle ──────────────────────────────────────────────────

    def on_enter(self, *args):
        register_refresh_hook(self._on_theme_refresh)
        load_lang()
        self._refreshing = True
        self._s = load_app_settings()
        self._update_texts()
        self._refresh_lang_buttons()
        self._refresh_theme_buttons()
        self._refresh_whisper_buttons()
        self._refresh_stt_engine_buttons()
        self._refresh_scheme_buttons()
        self._refresh_voice_spinner()
        self.rate_slider.value   = self._s.tts_rate
        self.vol_slider.value    = self._s.tts_volume
        self.pause_slider.value  = self._s.stt_pause_threshold
        self.hist_slider.value   = self._s.max_history
        self.scale_slider.value  = int(self._s.font_scale * 100)
        self._refreshing = False
        self._on_theme_refresh()

    def on_leave(self, *args):
        unregister_refresh_hook(self._on_theme_refresh)

    def go_back(self, instance):
        self.manager.current = "main"
