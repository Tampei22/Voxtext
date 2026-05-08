import json
import os
import threading
from datetime import datetime

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen

from storage.settings import load_app_settings
from ui.i18n import load_lang, t
from ui.theme import (
    RoundedButton, get,
    register_refresh_hook, unregister_refresh_hook,
)

_LANG_OPTIONS = [("RO", "ro"), ("RU", "ru"), ("EN", "en")]
_MODEL_OPTIONS = ["tiny", "base", "small", "medium"]

_COL_GOOD = (0.30, 0.85, 0.40, 1)
_COL_WARN = (0.95, 0.75, 0.10, 1)
_COL_BAD  = (0.85, 0.25, 0.25, 1)

# Base folder for benchmark audio sessions (relative to app directory)
_BENCH_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmark_runs")


def _wer_color(wer: float):
    if wer <= 0.10:
        return _COL_GOOD
    if wer <= 0.35:
        return _COL_WARN
    return _COL_BAD


class BenchmarkScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "benchmark"
        self._selected_lang = "ro"
        self._whisper_model = "small"
        self._report = None
        self._running = False
        self._runner = None
        self._abort = threading.Event()
        self._phrase_widgets: list[dict] = []
        self._last_session_dir: str | None = None

        outer = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6))

        # ── Back ──────────────────────────────────────────────────────────
        self.back_btn = RoundedButton(size_hint_y=None, height=sp(46))
        self.back_btn.bind(on_release=lambda _: setattr(self.manager, "current", "main"))
        outer.add_widget(self.back_btn)

        # ── Title ─────────────────────────────────────────────────────────
        self.title_label = Label(
            font_size="20sp", bold=True,
            size_hint_y=None, height=sp(38),
            halign="center", valign="middle",
        )
        self.title_label.bind(size=lambda i, v: setattr(i, "text_size", v))
        outer.add_widget(self.title_label)

        # ── Language selector ─────────────────────────────────────────────
        self._lang_hdr = Label(
            font_size="11sp", size_hint_y=None, height=sp(20),
            halign="left", valign="middle",
            color=list(get()["btn_accent"]),
        )
        self._lang_hdr.bind(size=lambda i, v: setattr(i, "text_size", v))
        outer.add_widget(self._lang_hdr)

        lang_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=sp(44), spacing=dp(6)
        )
        self._lang_btns: dict[str, RoundedButton] = {}
        for display, code in _LANG_OPTIONS:
            btn = RoundedButton(text=display, font_size="16sp")
            btn.bind(on_release=lambda _, c=code: self._set_lang(c))
            self._lang_btns[code] = btn
            lang_row.add_widget(btn)
        outer.add_widget(lang_row)

        # ── Whisper model selector ────────────────────────────────────────
        self._model_hdr = Label(
            font_size="11sp", size_hint_y=None, height=sp(20),
            halign="left", valign="middle",
            color=list(get()["btn_accent"]),
        )
        self._model_hdr.text = "Whisper model"
        self._model_hdr.bind(size=lambda i, v: setattr(i, "text_size", v))
        outer.add_widget(self._model_hdr)

        model_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=sp(42), spacing=dp(6)
        )
        self._model_btns: dict[str, RoundedButton] = {}
        for m in _MODEL_OPTIONS:
            btn = RoundedButton(text=m, font_size="14sp")
            btn.bind(on_release=lambda _, mo=m: self._set_model(mo))
            self._model_btns[m] = btn
            model_row.add_widget(btn)
        outer.add_widget(model_row)

        # ── Config label ──────────────────────────────────────────────────
        self.config_label = Label(
            font_size="12sp", size_hint_y=None, height=sp(22),
            halign="left", valign="middle",
        )
        self.config_label.bind(size=lambda i, v: setattr(i, "text_size", v))
        outer.add_widget(self.config_label)

        # ── Primary action row: Run + Done ────────────────────────────────
        action_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=sp(52), spacing=dp(8)
        )
        self.run_btn = RoundedButton(
            font_size="16sp",
            btn_color=list(get()["btn_accent"]),
        )
        self.run_btn.bind(on_release=lambda _: self._start_benchmark())
        action_row.add_widget(self.run_btn)

        self.done_btn = RoundedButton(
            font_size="14sp", size_hint_x=0.32, disabled=True
        )
        self.done_btn.bind(on_release=lambda _: self._manual_stop_recording())
        action_row.add_widget(self.done_btn)
        outer.add_widget(action_row)

        # ── Secondary action row: Re-run from folder ──────────────────────
        rerun_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=sp(40), spacing=dp(8)
        )
        self.rerun_btn = RoundedButton(font_size="13sp", size_hint_x=0.55)
        self.rerun_btn.bind(on_release=lambda _: self._pick_and_rerun())
        rerun_row.add_widget(self.rerun_btn)

        self.session_label = Label(
            font_size="10sp", size_hint_x=0.45,
            halign="left", valign="middle",
            color=(0.6, 0.6, 0.6, 1),
        )
        self.session_label.bind(size=lambda i, v: setattr(i, "text_size", v))
        rerun_row.add_widget(self.session_label)
        outer.add_widget(rerun_row)

        # ── Progress label ────────────────────────────────────────────────
        self.progress_label = Label(
            font_size="13sp", size_hint_y=None, height=sp(24),
            halign="left", valign="middle",
        )
        self.progress_label.bind(size=lambda i, v: setattr(i, "text_size", v))
        outer.add_widget(self.progress_label)

        # ── Scrollable results (2-column per phrase) ──────────────────────
        scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        self.results_grid = GridLayout(
            cols=1, spacing=dp(4), size_hint_y=None, padding=(0, dp(2))
        )
        self.results_grid.bind(minimum_height=self.results_grid.setter("height"))
        scroll.add_widget(self.results_grid)
        outer.add_widget(scroll)

        # ── Summary ───────────────────────────────────────────────────────
        self.summary_label = Label(
            font_size="12sp", size_hint_y=None, height=sp(48),
            halign="left", valign="top",
        )
        self.summary_label.bind(size=lambda i, v: setattr(i, "text_size", v))
        outer.add_widget(self.summary_label)

        # ── Save JSON ─────────────────────────────────────────────────────
        self.save_btn = RoundedButton(
            font_size="14sp", size_hint_y=None, height=sp(44), disabled=True
        )
        self.save_btn.bind(on_release=lambda _: self._save_json())
        outer.add_widget(self.save_btn)

        self.add_widget(outer)
        self._update_texts()
        self._refresh_lang_buttons()
        self._refresh_model_buttons()

    # ── Text / selectors ───────────────────────────────────────────────────

    def _update_texts(self):
        self.back_btn.text = t("back")
        self.title_label.text = t("benchmark_title")
        self._lang_hdr.text = f"— {t('benchmark_lang')} —"
        self.run_btn.text = t("benchmark_run")
        self.done_btn.text = "ГОТОВО"
        self.rerun_btn.text = "Re-run din folder"
        self.save_btn.text = t("benchmark_save")
        self._update_config_label()

    def _update_config_label(self):
        self.config_label.text = (
            f"Тест: Whisper [{self._whisper_model}] vs Google STT"
            f",  язык: {self._selected_lang.upper()}"
        )

    def _set_lang(self, code: str):
        self._selected_lang = code
        self._refresh_lang_buttons()
        self._update_config_label()

    def _set_model(self, model: str):
        self._whisper_model = model
        self._refresh_model_buttons()
        self._update_config_label()

    def _refresh_lang_buttons(self):
        th = get()
        for code, btn in self._lang_btns.items():
            btn.btn_color = list(
                th["btn_accent"] if code == self._selected_lang else th["btn_normal"]
            )

    def _refresh_model_buttons(self):
        th = get()
        for m, btn in self._model_btns.items():
            btn.btn_color = list(
                th["btn_accent"] if m == self._whisper_model else th["btn_normal"]
            )

    # ── Per-phrase card helpers ────────────────────────────────────────────

    def _add_phrase_card(self, idx: int, total: int, phrase: str) -> dict:
        th = get()
        accent = list(th["btn_accent"])
        dim_c  = list(th["text_dim"])

        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None, height=dp(98),
            spacing=dp(2), padding=(dp(4), dp(2)),
        )

        ref_lbl = Label(
            text=f"[{idx + 1}/{total}]  {phrase}",
            font_size="11sp",
            size_hint_y=None, height=dp(26),
            halign="left", valign="middle",
            color=accent,
        )
        ref_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        card.add_widget(ref_lbl)

        col_row = BoxLayout(size_hint_y=None, height=dp(66), spacing=dp(6))

        w_lbl = Label(
            text="Whisper\n[запись...]\n—",
            font_size="10sp", size_hint_x=0.5,
            halign="left", valign="top",
            color=dim_c,
        )
        w_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        g_lbl = Label(
            text="Google STT\n[запись...]\n—",
            font_size="10sp", size_hint_x=0.5,
            halign="left", valign="top",
            color=dim_c,
        )
        g_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        col_row.add_widget(w_lbl)
        col_row.add_widget(g_lbl)
        card.add_widget(col_row)

        self.results_grid.add_widget(card)
        return {"w_lbl": w_lbl, "g_lbl": g_lbl}

    def _fill_phrase_card(self, idx: int, result) -> None:
        if idx >= len(self._phrase_widgets):
            return
        refs = self._phrase_widgets[idx]
        dim_c = list(get()["text_dim"])

        if result.whisper_error:
            refs["w_lbl"].text = f"Whisper\nERR: {result.whisper_error[:36]}\n—"
            refs["w_lbl"].color = _COL_BAD
        else:
            trans = (result.whisper_text or "(тишина)")[:48]
            refs["w_lbl"].text = (
                f"Whisper\n{trans}\n"
                f"WER {result.whisper_wer:.2f}  CER {result.whisper_cer:.2f}"
                f"  RTF {result.whisper_rtf:.2f}"
            )
            refs["w_lbl"].color = _wer_color(result.whisper_wer)

        if result.google_error:
            refs["g_lbl"].text = f"Google\nERR: {result.google_error[:36]}\n—"
            refs["g_lbl"].color = _COL_BAD
        else:
            trans = (result.google_text or "(тишина)")[:48]
            refs["g_lbl"].text = (
                f"Google STT\n{trans}\n"
                f"WER {result.google_wer:.2f}  CER {result.google_cer:.2f}"
                f"  RTF {result.google_rtf:.2f}"
            )
            refs["g_lbl"].color = _wer_color(result.google_wer)

    # ── Benchmark execution (live recording) ──────────────────────────────

    def _start_benchmark(self):
        if self._running:
            return
        self._running = True
        self._report = None
        self._abort.clear()
        self._phrase_widgets.clear()
        self.results_grid.clear_widgets()
        self.summary_label.text = ""
        self.save_btn.disabled = True
        self.run_btn.disabled = True
        self.rerun_btn.disabled = True
        self.done_btn.disabled = True
        self.progress_label.text = t("benchmark_running")
        self.session_label.text = ""
        threading.Thread(target=self._run_thread, daemon=True).start()

    def _manual_stop_recording(self):
        if self._runner is not None:
            self._runner.stop_current_recording()

    def _run_thread(self):
        try:
            from benchmark.phrases import TEST_PHRASES
            from benchmark.runner import BenchmarkRunner

            phrases = TEST_PHRASES.get(self._selected_lang, [])
            total = len(phrases)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir = os.path.join(
                _BENCH_BASE,
                f"{self._selected_lang}_{self._whisper_model}_{ts}",
            )
            self._last_session_dir = session_dir

            def on_show_phrase(idx, tot, phrase):
                def do(dt):
                    self.progress_label.text = (
                        f"Фраза {idx + 1} / {tot}  •  Прочитайте вслух..."
                    )
                    self.done_btn.disabled = False
                    refs = self._add_phrase_card(idx, tot, phrase)
                    self._phrase_widgets.append(refs)
                Clock.schedule_once(do, 0)

            def on_phrase_result(idx, tot, result):
                def do(dt):
                    self.done_btn.disabled = True
                    self._fill_phrase_card(idx, result)
                Clock.schedule_once(do, 0)

            self._runner = BenchmarkRunner(
                lang=self._selected_lang,
                whisper_model=self._whisper_model,
                on_show_phrase=on_show_phrase,
                on_phrase_result=on_phrase_result,
                abort=self._abort,
                session_dir=session_dir,
            )
            report = self._runner.run(phrases)
            self._report = report

            short_dir = os.path.basename(session_dir)
            n_w = len([p for p in report.phrases if not p.whisper_error])
            n_g = len([p for p in report.phrases if not p.google_error])
            summary = (
                f"Whisper ({n_w}/{total} OK):"
                f"  WER {report.whisper_avg_wer:.3f}"
                f"  CER {report.whisper_avg_cer:.3f}"
                f"  RTF {report.whisper_avg_rtf:.2f}\n"
                f"Google  ({n_g}/{total} OK):"
                f"  WER {report.google_avg_wer:.3f}"
                f"  CER {report.google_avg_cer:.3f}"
                f"  RTF {report.google_avg_rtf:.2f}"
            )
            Clock.schedule_once(
                lambda _, s=summary, d=short_dir: self._on_done(s, d), 0
            )

        except Exception as exc:
            msg = t("benchmark_error", e=str(exc))
            Clock.schedule_once(lambda _, m=msg: self._on_error(m), 0)

    def _on_done(self, summary: str, session_name: str = ""):
        self.summary_label.text = summary
        self.progress_label.text = ""
        self.run_btn.disabled = False
        self.rerun_btn.disabled = False
        self.done_btn.disabled = True
        self.save_btn.disabled = False
        self.session_label.text = session_name
        self._running = False

    def _on_error(self, msg: str):
        self.progress_label.text = msg
        self.run_btn.disabled = False
        self.rerun_btn.disabled = False
        self.done_btn.disabled = True
        self._running = False

    # ── Re-run from saved folder ───────────────────────────────────────────

    def _pick_and_rerun(self):
        if self._running:
            return
        threading.Thread(target=self._pick_folder_and_start, daemon=True).start()

    def _pick_folder_and_start(self):
        try:
            import tkinter as tk
            from tkinter import filedialog

            initial = _BENCH_BASE if os.path.isdir(_BENCH_BASE) else os.path.expanduser("~")
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(
                title="Selectați folderul sesiunii (cu phrase_01.wav …)",
                initialdir=initial,
            )
            root.destroy()
        except Exception as exc:
            Clock.schedule_once(
                lambda _, m=str(exc): setattr(self.progress_label, "text", m), 0
            )
            return

        if not folder:
            return

        Clock.schedule_once(lambda _: self._start_rerun(folder), 0)

    def _start_rerun(self, session_dir: str):
        if self._running:
            return
        self._running = True
        self._report = None
        self._abort.clear()
        self._phrase_widgets.clear()
        self.results_grid.clear_widgets()
        self.summary_label.text = ""
        self.save_btn.disabled = True
        self.run_btn.disabled = True
        self.rerun_btn.disabled = True
        self.done_btn.disabled = True
        short = os.path.basename(session_dir)
        self.progress_label.text = f"Re-run: {short} …"
        self.session_label.text = short
        threading.Thread(
            target=self._rerun_thread, args=(session_dir,), daemon=True
        ).start()

    def _rerun_thread(self, session_dir: str):
        try:
            from benchmark.phrases import TEST_PHRASES
            from benchmark.runner import BenchmarkRunner

            phrases = TEST_PHRASES.get(self._selected_lang, [])
            total = len(phrases)

            def on_show_phrase(idx, tot, phrase):
                def do(_):
                    self.progress_label.text = (
                        f"Re-run фраза {idx + 1} / {tot} …"
                    )
                    refs = self._add_phrase_card(idx, tot, phrase)
                    self._phrase_widgets.append(refs)
                Clock.schedule_once(do, 0)

            def on_phrase_result(idx, _tot, result):
                Clock.schedule_once(
                    lambda _, r=result, i=idx: self._fill_phrase_card(i, r), 0
                )

            self._runner = BenchmarkRunner(
                lang=self._selected_lang,
                whisper_model=self._whisper_model,
                on_show_phrase=on_show_phrase,
                on_phrase_result=on_phrase_result,
                abort=self._abort,
            )
            report = self._runner.run_from_files(session_dir, phrases)
            self._report = report

            n_w = len([p for p in report.phrases if not p.whisper_error])
            n_g = len([p for p in report.phrases if not p.google_error])
            summary = (
                f"Whisper [{self._whisper_model}] ({n_w}/{total} OK):"
                f"  WER {report.whisper_avg_wer:.3f}"
                f"  CER {report.whisper_avg_cer:.3f}"
                f"  RTF {report.whisper_avg_rtf:.2f}\n"
                f"Google  ({n_g}/{total} OK):"
                f"  WER {report.google_avg_wer:.3f}"
                f"  CER {report.google_avg_cer:.3f}"
                f"  RTF {report.google_avg_rtf:.2f}"
            )
            Clock.schedule_once(lambda _, s=summary: self._on_done(s), 0)

        except Exception as exc:
            msg = t("benchmark_error", e=str(exc))
            Clock.schedule_once(lambda _, m=msg: self._on_error(m), 0)

    # ── Save JSON ──────────────────────────────────────────────────────────

    def _save_json(self):
        if self._report is None:
            return
        try:
            import tkinter as tk
            from tkinter import filedialog

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = (
                f"benchmark_{self._report.lang}"
                f"_{self._report.whisper_model}_{ts}.json"
            )
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.asksaveasfilename(
                title=t("benchmark_save_title"),
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("All files", "*.*")],
                initialfile=default_name,
                initialdir=os.path.expanduser("~"),
            )
            root.destroy()
            if not path:
                return

            data = self._report.to_json_dict()
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)

            self.progress_label.text = t("benchmark_saved", name=os.path.basename(path))
        except Exception as exc:
            self.progress_label.text = t("benchmark_error", e=str(exc))

    # ── Screen lifecycle ───────────────────────────────────────────────────

    def on_enter(self, *args):
        load_lang()
        self._update_texts()
        self._refresh_lang_buttons()
        self._refresh_model_buttons()
        register_refresh_hook(self._on_theme_refresh)
        self._on_theme_refresh()

    def on_leave(self, *args):
        unregister_refresh_hook(self._on_theme_refresh)
        self._abort.set()
        if self._runner is not None:
            self._runner.stop_current_recording()

    def _on_theme_refresh(self):
        th = get()
        text_c = list(th["text"])
        normal = list(th["btn_normal"])
        accent = list(th["btn_accent"])

        self.back_btn.btn_color = normal
        self.back_btn.color = text_c
        self.title_label.color = text_c
        self._lang_hdr.color = accent
        self._model_hdr.color = accent
        self.config_label.color = text_c
        self.progress_label.color = text_c
        self.summary_label.color = text_c
        self.run_btn.btn_color = accent
        self.run_btn.color = text_c
        self.done_btn.btn_color = normal
        self.done_btn.color = text_c
        self.rerun_btn.btn_color = normal
        self.rerun_btn.color = text_c
        self.save_btn.btn_color = normal
        self.save_btn.color = text_c
        for btn in self._lang_btns.values():
            btn.color = text_c
        for btn in self._model_btns.values():
            btn.color = text_c
        self._refresh_lang_buttons()
        self._refresh_model_buttons()
