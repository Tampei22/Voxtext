from kivy.animation import Animation
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.button import Button

THEMES: dict[str, dict] = {
    "dark": {
        "window_bg":  (0.10, 0.10, 0.12, 1),
        "btn_normal": (0.22, 0.22, 0.27, 1),
        "btn_accent": (0.16, 0.58, 0.28, 1),
        "btn_danger": (0.52, 0.14, 0.14, 1),
        "text":       (0.93, 0.93, 0.96, 1),
        "text_dim":   (0.55, 0.55, 0.60, 1),
        "input_bg":   (0.15, 0.15, 0.18, 1),
        "input_fg":   (0.93, 0.93, 0.96, 1),
        "cursor":     (0.20, 0.68, 0.32, 1),
        "hint":       (0.44, 0.44, 0.48, 1),
        "section":    (0.48, 0.72, 1.00, 1),
        "progress":   (0.55, 0.88, 0.60, 1),
    },
    "light": {
        "window_bg":  (0.93, 0.93, 0.95, 1),
        "btn_normal": (0.76, 0.76, 0.80, 1),
        "btn_accent": (0.12, 0.52, 0.24, 1),
        "btn_danger": (0.68, 0.18, 0.18, 1),
        "text":       (0.10, 0.10, 0.14, 1),
        "text_dim":   (0.40, 0.40, 0.44, 1),
        "input_bg":   (1.00, 1.00, 1.00, 1),
        "input_fg":   (0.10, 0.10, 0.14, 1),
        "cursor":     (0.12, 0.52, 0.24, 1),
        "hint":       (0.54, 0.54, 0.56, 1),
        "section":    (0.08, 0.38, 0.70, 1),
        "progress":   (0.12, 0.52, 0.24, 1),
    },
}

_name: str = "dark"
_t: dict = THEMES["dark"]


def init(theme_name: str) -> None:
    global _name, _t
    _name = theme_name
    _t = THEMES.get(theme_name, THEMES["dark"])
    from kivy.core.window import Window
    Window.clearcolor = _t["window_bg"]
    _apply_kv()


def get() -> dict:
    return _t


def current_name() -> str:
    return _name


_kv_done = False


def _apply_kv() -> None:
    global _kv_done
    if _kv_done:
        return
    _kv_done = True

    def f(key: str) -> str:
        r, g, b, a = _t[key]
        return f"{r}, {g}, {b}, {a}"

    Builder.load_string(f"""
#:import dp kivy.metrics.dp

<Label>:
    color: {f('text')}
    text_size: self.width, None

<TextInput>:
    background_color: {f('input_bg')}
    foreground_color: {f('input_fg')}
    cursor_color: {f('cursor')}
    hint_text_color: {f('hint')}
    padding: dp(8), dp(8)

<Spinner>:
    background_normal: ''
    background_down: ''
    background_color: {f('btn_normal')}
    color: {f('text')}
    option_cls: 'SpinnerOption'

<SpinnerOption>:
    background_color: {f('btn_normal')}
    color: {f('text')}
    height: dp(44)
    font_size: '15sp'
""")


def restart_app() -> None:
    import os
    import subprocess
    import sys
    subprocess.Popen([sys.executable] + sys.argv)
    os._exit(0)


class RoundedButton(Button):
    btn_color = ListProperty(None)
    corner_radius = NumericProperty(12)
    _scale = NumericProperty(1.0)
    _press = NumericProperty(0.0)

    def __init__(self, **kwargs):
        if "height" in kwargs and isinstance(kwargs["height"], (int, float)):
            kwargs["height"] = sp(kwargs["height"])
        if "btn_color" not in kwargs:
            kwargs["btn_color"] = list(_t["btn_normal"])
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = list(_t["text"])
        self.halign = "center"
        self.valign = "middle"
        self.shorten = True
        self.shorten_from = "right"
        self.bind(
            pos=self._redraw,
            size=self._redraw,
            btn_color=self._redraw,
            _scale=self._redraw,
            _press=self._redraw,
        )
        self.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        self._redraw()

    def on_state(self, instance, value: str) -> None:
        Animation.cancel_all(self, "_scale", "_press")
        if value == "down":
            Animation(_scale=0.95, _press=1.0, duration=0.09, t="out_cubic").start(self)
        else:
            Animation(_scale=1.0, _press=0.0, duration=0.22, t="out_expo").start(self)

    def _redraw(self, *args) -> None:
        self.canvas.before.clear()
        base = list(self.btn_color) if self.btn_color else list(_t["btn_normal"])
        s = self._scale
        p = self._press

        factor = 1.0 - p * 0.20
        c = [base[0] * factor, base[1] * factor, base[2] * factor, base[3]]

        w = self.width * s
        h = self.height * s
        x = self.center_x - w / 2
        y = self.center_y - h / 2
        r = dp(self.corner_radius)

        with self.canvas.before:
            Color(*c)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[r])
            Color(
                min(1.0, base[0] + 0.22),
                min(1.0, base[1] + 0.22),
                min(1.0, base[2] + 0.22),
                0.38 * (1.0 - p * 0.6),
            )
            Line(rounded_rectangle=(x, y, w, h, r), width=dp(0.9))
