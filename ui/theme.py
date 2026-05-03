from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty, BooleanProperty
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout

THEMES: dict[str, dict] = {
    "dark": {
        "window_bg":  (0.10, 0.10, 0.12, 1),
        "btn_normal": (0.22, 0.22, 0.27, 1),
        "btn_accent": (0.20, 0.47, 0.90, 1),   # overridden by color scheme
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
        "btn_accent": (0.20, 0.47, 0.90, 1),   # overridden by color scheme
        "btn_danger": (0.68, 0.18, 0.18, 1),
        "text":       (0.10, 0.10, 0.14, 1),
        "text_dim":   (0.40, 0.40, 0.44, 1),
        "input_bg":   (1.00, 1.00, 1.00, 1),
        "input_fg":   (0.10, 0.10, 0.14, 1),
        "cursor":     (0.20, 0.47, 0.90, 1),
        "hint":       (0.54, 0.54, 0.56, 1),
        "section":    (0.08, 0.38, 0.70, 1),
        "progress":   (0.20, 0.47, 0.90, 1),
    },
}

COLOR_SCHEMES: dict[str, list] = {
    "blue":   [0.20, 0.47, 0.90, 1],
    "green":  [0.15, 0.70, 0.40, 1],
    "orange": [0.90, 0.50, 0.10, 1],
    "purple": [0.55, 0.25, 0.85, 1],
    "red":    [0.85, 0.20, 0.25, 1],
}

_name: str = "dark"
_t: dict = dict(THEMES["dark"])
_scheme: str = "blue"

# Registry of weak-callable refresh hooks — screens register/deregister
_refresh_hooks: list = []


def register_refresh_hook(fn):
    if fn not in _refresh_hooks:
        _refresh_hooks.append(fn)


def unregister_refresh_hook(fn):
    if fn in _refresh_hooks:
        _refresh_hooks.remove(fn)


def _fire_refresh_hooks():
    dead = []
    for fn in list(_refresh_hooks):
        try:
            fn()
        except Exception:
            dead.append(fn)
    for fn in dead:
        _refresh_hooks.remove(fn)


def init(theme_name: str, scheme_name: str = "blue") -> None:
    global _name, _t, _scheme
    _name = theme_name
    _scheme = scheme_name
    _t = dict(THEMES.get(theme_name, THEMES["dark"]))
    _t["btn_accent"] = COLOR_SCHEMES.get(scheme_name, COLOR_SCHEMES["blue"])
    from kivy.core.window import Window
    Window.clearcolor = _t["window_bg"]
    _apply_kv()


def apply_theme(theme_name: str) -> None:
    """Switch dark/light theme live without restart."""
    global _name, _t
    _name = theme_name
    _t = dict(THEMES.get(theme_name, THEMES["dark"]))
    _t["btn_accent"] = COLOR_SCHEMES.get(_scheme, COLOR_SCHEMES["blue"])
    from kivy.core.window import Window
    Window.clearcolor = _t["window_bg"]
    _fire_refresh_hooks()


def apply_color_scheme(scheme_name: str) -> None:
    """Change accent colour live — updates in-memory theme dict immediately."""
    global _t, _scheme
    _scheme = scheme_name
    _t["btn_accent"] = COLOR_SCHEMES.get(scheme_name, COLOR_SCHEMES["blue"])
    Clock.schedule_once(lambda _: _fire_refresh_hooks(), 0)


def get() -> dict:
    return _t


def current_name() -> str:
    return _name


def current_scheme() -> str:
    return _scheme


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


# ── RoundedButton ──────────────────────────────────────────────────────────────

class RoundedButton(Button):
    btn_color = ListProperty(None)
    corner_radius = NumericProperty(12)
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
            _press=self._redraw,
        )
        self.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        self._redraw()

    def on_state(self, instance, value: str) -> None:
        Animation.cancel_all(self, "_press")
        if value == "down":
            Animation(_press=1.0, duration=0.09, t="out_cubic").start(self)
        else:
            Animation(_press=0.0, duration=0.22, t="out_expo").start(self)

    def _redraw(self, *args) -> None:
        self.canvas.before.clear()
        base = list(self.btn_color) if self.btn_color else list(_t["btn_normal"])
        p = self._press

        factor = 1.0 - p * 0.20
        c = [base[0] * factor, base[1] * factor, base[2] * factor, base[3]]

        x, y = self.x, self.y
        w, h = self.width, self.height
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


# ── GlowSlider ─────────────────────────────────────────────────────────────────

class GlowSlider(FloatLayout):
    """
    Slider wrapped in a FloatLayout that draws a glowing coloured track,
    shows a value bubble on touch, and pulses the thumb on press.

    Public interface matches Slider: .value, .min, .max, .step
    Bind to on_value via: slider.bind(value=callback)
    """

    value = NumericProperty(0)
    min = NumericProperty(0)
    max = NumericProperty(100)
    step = NumericProperty(1)

    def __init__(self, min_val=0, max_val=100, value=50, step=1, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(48))
        super().__init__(**kwargs)

        self.min = min_val
        self.max = max_val
        self.step = step
        self.value = value

        # Underlying Kivy Slider (invisible track — we draw our own)
        self._slider = Slider(
            min=min_val, max=max_val, value=value, step=step,
            size_hint=(1, None), height=dp(48),
            pos_hint={"center_y": 0.5},
            cursor_size=(dp(20), dp(20)),
        )
        self._slider.bind(value=self._on_slider_value)
        self._slider.bind(on_touch_down=self._on_touch_down_slider)
        self._slider.bind(on_touch_up=self._on_touch_up_slider)
        self.add_widget(self._slider)

        # Value bubble label
        self._bubble = Label(
            font_size="11sp",
            size_hint=(None, None),
            size=(dp(44), dp(22)),
            opacity=0,
            halign="center",
            valign="middle",
        )
        self._bubble.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.add_widget(self._bubble)

        self._hide_event = None
        self.bind(pos=self._redraw_canvas, size=self._redraw_canvas)
        self._slider.bind(value=lambda *_: self._redraw_canvas())
        Clock.schedule_once(lambda _: self._redraw_canvas(), 0)

    def bind(self, **kwargs):
        # Forward value binding to the internal slider
        if "value" in kwargs:
            self._slider.bind(value=kwargs.pop("value"))
        super().bind(**kwargs)

    # ── canvas ────────────────────────────────────────────────────────────

    def _redraw_canvas(self, *_):
        self.canvas.before.clear()
        accent = _t.get("btn_accent", [0.20, 0.47, 0.90, 1])
        track_h = dp(4)
        pad = dp(12)
        track_y = self.y + self.height / 2 - track_h / 2
        track_w = self.width - pad * 2
        track_x = self.x + pad

        ratio = 0.0
        span = self._slider.max - self._slider.min
        if span > 0:
            ratio = (self._slider.value - self._slider.min) / span

        filled_w = track_w * ratio

        with self.canvas.before:
            # Dim full track
            Color(accent[0], accent[1], accent[2], 0.22)
            RoundedRectangle(
                pos=(track_x, track_y),
                size=(track_w, track_h),
                radius=[dp(2)],
            )
            # Bright filled portion
            if filled_w > dp(2):
                Color(accent[0], accent[1], accent[2], 0.85)
                RoundedRectangle(
                    pos=(track_x, track_y),
                    size=(filled_w, track_h),
                    radius=[dp(2)],
                )

        # Reposition bubble above thumb
        thumb_x = track_x + filled_w - dp(22)
        self._bubble.x = max(self.x, min(thumb_x, self.right - self._bubble.width))
        self._bubble.y = self.y + self.height / 2 + dp(8)
        self._bubble.text = self._format_value(self._slider.value)

    def _format_value(self, v) -> str:
        return str(int(v)) if self._slider.step >= 1 else f"{v:.1f}"

    # ── touch/pulse ───────────────────────────────────────────────────────

    def _on_touch_down_slider(self, inst, touch):
        if inst.collide_point(*touch.pos):
            self._show_bubble()

    def _on_touch_up_slider(self, inst, touch):
        if self._hide_event:
            self._hide_event.cancel()
        self._hide_event = Clock.schedule_once(self._hide_bubble, 1.5)

    def _show_bubble(self):
        Animation.cancel_all(self._bubble, "opacity")
        Animation(opacity=1, duration=0.15).start(self._bubble)
        if self._hide_event:
            self._hide_event.cancel()

    def _hide_bubble(self, *_):
        Animation(opacity=0, duration=0.3).start(self._bubble)

    def _on_slider_value(self, inst, val):
        self.value = val
        self._redraw_canvas()
