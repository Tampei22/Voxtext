from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from ui.theme import RoundedButton, get
from ui.i18n import load_lang, t


class _FeatureCard(ButtonBehavior, BoxLayout):
    """Tappable feature card: colored abbreviation + full name label."""

    btn_color = ListProperty([0.22, 0.22, 0.27, 1])
    _press = NumericProperty(0.0)

    def __init__(self, abbr: str, i18n_key: str, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", dp(10))
        kwargs.setdefault("spacing", dp(4))
        super().__init__(**kwargs)

        self._i18n_key = i18n_key
        th = get()

        self._abbr_lbl = Label(
            text=abbr,
            font_size="32sp",
            bold=True,
            color=list(th["btn_accent"]),
            size_hint_y=0.55,
            halign="center",
            valign="middle",
        )
        self._abbr_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self._name_lbl = Label(
            text=t(i18n_key),
            font_size="13sp",
            color=list(th["text"]),
            size_hint_y=0.45,
            halign="center",
            valign="top",
        )
        self._name_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self.add_widget(self._abbr_lbl)
        self.add_widget(self._name_lbl)

        self.bind(pos=self._redraw, size=self._redraw,
                  btn_color=self._redraw, _press=self._redraw)

    def refresh_text(self):
        self._name_lbl.text = t(self._i18n_key)

    def refresh_colors(self):
        th = get()
        self._abbr_lbl.color = list(th["btn_accent"])
        self._name_lbl.color = list(th["text"])

    def on_state(self, instance, value):
        Animation.cancel_all(self, "_press")
        if value == "down":
            Animation(_press=1.0, duration=0.08, t="out_cubic").start(self)
        else:
            Animation(_press=0.0, duration=0.20, t="out_expo").start(self)

    def _redraw(self, *_):
        self.canvas.before.clear()
        base = list(self.btn_color)
        f = 1.0 - self._press * 0.18
        c = [base[0] * f, base[1] * f, base[2] * f, base[3]]
        r = dp(16)
        with self.canvas.before:
            Color(*c)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r])
            Color(
                min(1.0, base[0] + 0.18),
                min(1.0, base[1] + 0.18),
                min(1.0, base[2] + 0.18),
                0.28,
            )
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r),
                 width=dp(0.8))


_CARDS = [
    ("STT", "main_stt",  "stt"),
    ("TTS", "main_tts",  "tts"),
    ("DOC", "main_file", "pdf"),
    ("LOG", "main_history", "history"),
]


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "main"

        root = BoxLayout(
            orientation="vertical",
            padding=(dp(12), dp(14), dp(12), dp(12)),
            spacing=dp(10),
        )

        # ── Top bar ──────────────────────────────────────────────────────
        top = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(8),
        )

        title_lbl = Label(
            text="VoxText",
            font_size="28sp",
            bold=True,
            size_hint_x=1,
            halign="left",
            valign="middle",
        )
        title_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self.gear_btn = RoundedButton(
            text="=",
            font_size="20sp",
            size_hint=(None, None),
            size=(dp(48), dp(40)),
            corner_radius=10,
        )
        self.gear_btn.bind(
            on_release=lambda _: setattr(self.manager, "current", "settings")
        )

        top.add_widget(title_lbl)
        top.add_widget(self.gear_btn)
        root.add_widget(top)

        # ── 2×2 feature card grid ─────────────────────────────────────────
        grid = GridLayout(
            cols=2,
            spacing=dp(10),
            size_hint_y=1,
        )

        self._cards: list[_FeatureCard] = []
        th = get()
        for abbr, i18n_key, screen_name in _CARDS:
            card = _FeatureCard(
                abbr=abbr,
                i18n_key=i18n_key,
                btn_color=list(th["btn_normal"]),
            )
            card.bind(
                on_release=lambda _, s=screen_name: setattr(self.manager, "current", s)
            )
            self._cards.append(card)
            grid.add_widget(card)

        root.add_widget(grid)
        self.add_widget(root)

    def on_enter(self, *args):
        load_lang()
        th = get()
        for card in self._cards:
            card.refresh_text()
            card.refresh_colors()
            card.btn_color = list(th["btn_normal"])
