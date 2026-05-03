import json
import os
import threading

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from storage.settings import load_app_settings
from ui.i18n import load_lang, t
from ui.theme import RoundedButton, get

_LANG_OPTIONS = [("RO", "ro"), ("RU", "ru"), ("EN", "en")]


class BenchmarkScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "benchmark"
        self._selected_lang = "ro"
        self._report = None
        self._running = False

        outer = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        self.back_btn = RoundedButton(size_hint_y=None, height=sp(50))
        self.back_btn.bind(on_release=lambda _: setattr(self.manager, "current", "main"))
        outer.add_widget(self.back_btn)

        self.title_label = Label(font_size="22sp", size_hint_y=None, height=sp(44))
        outer.add_widget(self.title_label)

        # ── Language selector ──
        self.sec_lang = Label(
            font_size="13sp",
            color=get()["section"],
            size_hint_y=None,
            height=sp(28),
        )
        outer.add_widget(self.sec_lang)

        lang_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=sp(52), spacing=dp(8)
        )
        self._lang_btns: dict[str, RoundedButton] = {}
        for display, code in _LANG_OPTIONS:
            btn = RoundedButton(text=display, font_size="17sp")
            btn.bind(on_release=lambda _, c=code: self._set_lang(c))
            self._lang_btns[code] = btn
            lang_row.add_widget(btn)
        outer.add_widget(lang_row)

        # ── Model info ──
        self.model_label = Label(
            font_size="13sp",
            size_hint_y=None,
            height=sp(26),
            halign="left",
            text_size=(None, None),
        )
        outer.add_widget(self.model_label)

        # ── Run button ──
        self.run_btn = RoundedButton(
            font_size="17sp",
            size_hint_y=None,
            height=sp(54),
            btn_color=list(get()["btn_accent"]),
        )
        self.run_btn.bind(on_release=lambda _: self._start_benchmark())
        outer.add_widget(self.run_btn)

        # ── Progress / status ──
        self.progress_label = Label(
            font_size="13sp",
            size_hint_y=None,
            height=sp(26),
            halign="left",
            text_size=(None, None),
        )
        outer.add_widget(self.progress_label)

        # ── Log (scrollable read-only) ──
        scroll = ScrollView(size_hint=(1, 1))
        self.log_input = TextInput(
            readonly=True,
            multiline=True,
            font_size="12sp",
            size_hint=(1, None),
            height=sp(220),
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(0.9, 0.9, 0.9, 1),
        )
        scroll.add_widget(self.log_input)
        outer.add_widget(scroll)

        # ── Summary ──
        self.summary_label = Label(
            font_size="13sp",
            size_hint_y=None,
            height=sp(52),
            halign="left",
            valign="top",
            text_size=(None, None),
        )
        outer.add_widget(self.summary_label)

        # ── Save JSON button ──
        self.save_btn = RoundedButton(
            font_size="14sp",
            size_hint_y=None,
            height=sp(48),
            disabled=True,
        )
        self.save_btn.bind(on_release=lambda _: self._save_json())
        outer.add_widget(self.save_btn)

        self.add_widget(outer)
        self._update_texts()
        self._refresh_lang_buttons()

    # ------------------------------------------------------------------ #
    # Text / lang helpers
    # ------------------------------------------------------------------ #

    def _update_texts(self):
        s = load_app_settings()
        self.back_btn.text = t("back")
        self.title_label.text = t("benchmark_title")
        self.sec_lang.text = f'— {t("benchmark_lang")} —'
        self.model_label.text = t("benchmark_model", model=s.whisper_model)
        self.run_btn.text = t("benchmark_run")
        self.save_btn.text = t("benchmark_save")
        if not self.progress_label.text:
            self.progress_label.text = ""

    def _set_lang(self, code: str):
        self._selected_lang = code
        self._refresh_lang_buttons()

    def _refresh_lang_buttons(self):
        th = get()
        for code, btn in self._lang_btns.items():
            btn.btn_color = list(
                th["btn_accent"] if code == self._selected_lang else th["btn_normal"]
            )

    # ------------------------------------------------------------------ #
    # Benchmark execution
    # ------------------------------------------------------------------ #

    def _start_benchmark(self):
        if self._running:
            return
        self._running = True
        self._report = None
        self.log_input.text = ""
        self.summary_label.text = ""
        self.save_btn.disabled = True
        self.run_btn.disabled = True
        self.progress_label.text = t("benchmark_running")

        threading.Thread(target=self._run_benchmark_thread, daemon=True).start()

    def _run_benchmark_thread(self):
        try:
            from benchmark.phrases import TEST_PHRASES
            from benchmark.runner import BenchmarkRunner
            from storage.settings import load_app_settings as _ls

            s = _ls()
            lang = self._selected_lang
            phrases = TEST_PHRASES.get(lang, [])
            total = len(phrases)

            def on_progress(idx, n, phrase):
                if idx < n:
                    msg = t("benchmark_progress", n=idx + 1, total=n, phrase=phrase[:40])
                else:
                    msg = t("benchmark_running")
                Clock.schedule_once(
                    lambda _, m=msg: setattr(self.progress_label, "text", m), 0
                )

            runner = BenchmarkRunner(
                lang=lang,
                whisper_model=s.whisper_model,
                on_progress=on_progress,
            )
            report = runner.run(phrases)

            # Stream per-phrase results into log
            lines = []
            for i, p in enumerate(report.phrases, 1):
                whisper_line = (
                    f"  W: {p.whisper_text!r}  WER={p.whisper_wer:.2f}  t={p.whisper_time_s:.2f}s"
                    if not p.whisper_error
                    else f"  W: ERROR — {p.whisper_error}"
                )
                google_line = (
                    f"  G: {p.google_text!r}  WER={p.google_wer:.2f}  t={p.google_time_s:.2f}s"
                    if not p.google_error
                    else f"  G: ERROR — {p.google_error}"
                )
                lines.append(f"[{i}] {p.reference}")
                lines.append(whisper_line)
                lines.append(google_line)

            log_text = "\n".join(lines)
            summary = t(
                "benchmark_done",
                w_wer=f"{report.whisper_avg_wer:.3f}",
                w_t=f"{report.whisper_avg_time:.2f}",
                g_wer=f"{report.google_avg_wer:.3f}",
                g_t=f"{report.google_avg_time:.2f}",
            )

            self._report = report

            Clock.schedule_once(lambda _: self._on_done(log_text, summary), 0)

        except Exception as exc:
            msg = t("benchmark_error", e=str(exc))
            Clock.schedule_once(lambda _, m=msg: self._on_error(m), 0)

    def _on_done(self, log_text: str, summary: str):
        self.log_input.text = log_text
        self.summary_label.text = summary
        self.progress_label.text = ""
        self.run_btn.disabled = False
        self.save_btn.disabled = False
        self._running = False

    def _on_error(self, msg: str):
        self.progress_label.text = msg
        self.run_btn.disabled = False
        self._running = False

    # ------------------------------------------------------------------ #
    # Save JSON
    # ------------------------------------------------------------------ #

    def _save_json(self):
        if self._report is None:
            return
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            path = filedialog.asksaveasfilename(
                title=t("benchmark_save_title"),
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("All files", "*.*")],
                initialfile=f"benchmark_{self._report.lang}_{self._report.whisper_model}.json",
            )
            root.destroy()

            if not path:
                return

            data = self._report.to_json_dict()
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)

            name = os.path.basename(path)
            self.progress_label.text = t("benchmark_saved", name=name)
        except Exception as exc:
            self.progress_label.text = t("benchmark_error", e=str(exc))

    # ------------------------------------------------------------------ #
    # Screen lifecycle
    # ------------------------------------------------------------------ #

    def on_enter(self, *args):
        load_lang()
        self._update_texts()
        self._refresh_lang_buttons()
