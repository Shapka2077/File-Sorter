"""Настольный интерфейс File Sorter."""

import tkinter as tk
import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import validation
from conflict_dialog import ask_conflict
from settings import DEFAULT_EXTENSIONS, load_extensions, save_extensions
from sorter import sort_videos
from windows_theme import apply_dark_titlebar


def _switch_image(root, on, disabled=False):
    """Draw antialiased switch edges by averaging subpixel samples."""
    image = tk.PhotoImage(master=root, width=42, height=24)
    track = ("#38544f" if on else "#34444b") if disabled else (
        "#62d6bd" if on else "#526770"
    )
    knob = "#829397" if disabled else "#f4f8f8"
    def rgb(color):
        return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))

    background, track_color, knob_color = map(rgb, ("#101820", track, knob))
    for y in range(24):
        row = []
        for x in range(42):
            totals = [0, 0, 0]
            for sy in range(4):
                for sx in range(4):
                    px, py = x + (sx + 0.5) / 4, y + (sy + 0.5) / 4
                    dx, dy = max(12 - px, 0, px - 30), py - 12
                    color = background
                    if dx * dx + dy * dy <= 12 ** 2:
                        color = track_color
                    if (px - (30 if on else 12)) ** 2 + dy ** 2 <= 8 ** 2:
                        color = knob_color
                    for channel in range(3):
                        totals[channel] += color[channel]
            row.append("#%02x%02x%02x" % tuple(value // 16 for value in totals))
        image.put("{" + " ".join(row) + "}", to=(0, y))
    return image


class FileSorterApp:
    def __init__(self, root):
        self.root = root
        root.title("File Sorter")
        root.minsize(480, 480)
        root.configure(background="#101820")

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#101820", foreground="#eaf1f3")
        style.configure("TFrame", background="#101820")
        style.configure("Card.TFrame", background="#1a2730")
        style.configure("TLabel", background="#101820", foreground="#eaf1f3")
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), foreground="#f4f8f8")
        style.configure("Eyebrow.TLabel", font=("Segoe UI", 9, "bold"), foreground="#62d6bd")
        style.configure("Muted.TLabel", foreground="#aebfc5")
        style.configure("Card.TLabel", background="#1a2730")
        style.configure("CardMuted.TLabel", background="#1a2730", foreground="#b2c2c6")
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground="#eaf1f3")
        style.configure("TEntry", fieldbackground="#24343e", foreground="#f4f8f8",
                        insertcolor="#f4f8f8", bordercolor="#40545c", padding=8)
        style.map("TEntry", bordercolor=[("focus", "#62d6bd")])
        style.configure("TButton", background="#30434b", foreground="#f4f8f8",
                        borderwidth=0, padding=(15, 9))
        style.map("TButton", background=[("active", "#415960"), ("disabled", "#25343a")],
                  foreground=[("disabled", "#829397")])
        style.configure("Accent.TButton", background="#62d6bd", foreground="#10231f",
                        font=("Segoe UI", 10, "bold"), padding=(20, 11))
        style.map("Accent.TButton", background=[("active", "#8ce5d3"), ("disabled", "#38544f")],
                  foreground=[("disabled", "#8aaba4")])
        style.configure("TCheckbutton", background="#101820", foreground="#eaf1f3",
                        indicatorcolor="#24343e", padding=3)
        style.map("TCheckbutton", background=[("active", "#101820")],
                  indicatorcolor=[("selected", "#62d6bd")])
        style.configure("TRadiobutton", background="#1a2730", foreground="#eaf1f3",
                        indicatorcolor="#24343e", padding=4)
        style.map("TRadiobutton", background=[("active", "#1a2730")],
                  indicatorcolor=[("selected", "#62d6bd")])
        self._switch_images = [
            _switch_image(root, on, disabled)
            for disabled in (False, True) for on in (False, True)
        ]
        style.element_create(
            "Switch.indicator", "image", self._switch_images[0],
            ("disabled", "selected", self._switch_images[3]),
            ("disabled", self._switch_images[2]),
            ("selected", self._switch_images[1]),
            width=46, sticky="w",
        )
        style.layout("Switch.TCheckbutton", [
            ("Checkbutton.padding", {"sticky": "nswe", "children": [
                ("Switch.indicator", {"side": "left", "sticky": ""}),
                ("Checkbutton.focus", {"side": "left", "sticky": "w", "children": [
                    ("Checkbutton.label", {"sticky": "nswe"})
                ]}),
            ]}),
        ])
        style.configure("Switch.TCheckbutton", background="#101820",
                        foreground="#eaf1f3", padding=(3, 4))
        style.map("Switch.TCheckbutton", background=[("active", "#101820")],
                  foreground=[("disabled", "#829397")])

        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.mode = tk.StringVar(value="copy")
        self.recursive = tk.BooleanVar(value=False)
        self._move_enabled = tk.BooleanVar(value=False)
        self._mode_label = tk.StringVar()
        self._recursive_label = tk.StringVar()
        self._move_enabled.trace_add("write", self._move_changed)
        self.mode.trace_add("write", self._mode_changed)
        self.recursive.trace_add("write", self._recursive_changed)
        self._mode_changed()
        self._recursive_changed()
        self.settings_path = Path(os.environ.get("APPDATA") or Path.home()) / "File Sorter" / "settings.json"
        try:
            extensions = load_extensions(self.settings_path)
        except (ValueError, OSError) as error:
            extensions = DEFAULT_EXTENSIONS
            messagebox.showwarning("Настройки", str(error), parent=root)
        self.extensions = tk.StringVar(value=", ".join(extensions))
        self.validation_status = tk.StringVar(value="Выберите папки и проверьте пути.")
        self.events = queue.Queue()
        self.running = False
        self.conflict_choice = None
        root.protocol("WM_DELETE_WINDOW", self.close)

        frame = ttk.Frame(root, padding=(28, 24))
        frame.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="File Sorter", style="Title.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )
        ttk.Label(frame, text="Наведите порядок в видео по дате из имени файла.",
                  style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 18))

        paths = ttk.Frame(frame)
        paths.grid(row=3, column=0, sticky="ew")
        paths.columnconfigure(0, weight=1)
        for row, label, variable in (
            (0, "01  ИСХОДНАЯ ПАПКА", self.source),
            (2, "02  ПАПКА НАЗНАЧЕНИЯ", self.destination),
        ):
            ttk.Label(paths, text=label, style="Section.TLabel").grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
            )
            ttk.Entry(paths, textvariable=variable).grid(
                row=row + 1, column=0, sticky="ew", padx=(0, 8), pady=(0, 14)
            )
            ttk.Button(
                paths, text="Обзор...", command=lambda var=variable: self.choose_directory(var)
            ).grid(row=row + 1, column=1, sticky="ew", pady=(0, 14))

        explanation = ttk.Label(frame, text="В папке назначения создаются папки по датам "
                                "из имён файлов, например 19.11.26. В них будут разложены видео.",
                                style="Muted.TLabel", wraplength=600)
        explanation.grid(
            row=4, column=0, sticky="w", pady=(0, 14)
        )

        self.mode_switch = ttk.Checkbutton(
            frame, textvariable=self._mode_label, variable=self._move_enabled,
            style="Switch.TCheckbutton", takefocus=True,
        )
        self.mode_switch.grid(row=5, column=0, sticky="w", pady=(0, 4))
        self.recursive_switch = ttk.Checkbutton(
            frame, textvariable=self._recursive_label, variable=self.recursive,
            style="Switch.TCheckbutton", takefocus=True,
        )
        self.recursive_switch.grid(row=6, column=0, sticky="w", pady=(0, 12))
        ttk.Button(frame, text="Настройки форматов", command=self.open_format_settings).grid(
            row=7, column=0, sticky="w"
        )
        actions = ttk.Frame(frame)
        actions.grid(row=8, column=0, sticky="ew", pady=(20, 0))
        self.start_button = ttk.Button(actions, text="Начать сортировку", command=self.start,
                                       style="Accent.TButton")
        self.start_button.pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Проверить пути", command=self.check_paths).pack(side="left")
        status = ttk.Label(frame, textvariable=self.validation_status, wraplength=600,
                           style="Muted.TLabel")
        status.grid(row=9, column=0, sticky="w", pady=(12, 0))

        def resize_labels(event):
            width = max(200, event.width - 56)
            explanation.configure(wraplength=width)
            status.configure(wraplength=width)

        root.bind("<Configure>", lambda event: resize_labels(event) if event.widget is root else None,
                  add="+")
        root.update_idletasks()
        root.minsize(480, root.winfo_reqheight())
        apply_dark_titlebar(root)

    def _move_changed(self, *_):
        self.mode.set("move" if self._move_enabled.get() else "copy")

    def _mode_changed(self, *_):
        moving = self.mode.get() == "move"
        if self._move_enabled.get() != moving:
            self._move_enabled.set(moving)
        self._mode_label.set("Режим: перемещение" if moving else "Режим: копирование")

    def _recursive_changed(self, *_):
        self._recursive_label.set(
            "Подпапки исходной папки: поиск включён" if self.recursive.get()
            else "Подпапки исходной папки: поиск выключен"
        )

    def open_format_settings(self):
        window = tk.Toplevel(self.root)
        window.withdraw()
        window.title("Настройки форматов")
        window.transient(self.root)
        window.configure(background="#101820")
        window.minsize(380, 160)
        draft = tk.StringVar(window, value=self.extensions.get())
        frame = ttk.Frame(window, padding=20)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="Форматы видео через запятую").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        entry = ttk.Entry(frame, textvariable=draft)
        entry.grid(row=1, column=0, columnspan=2, sticky="ew")

        def save():
            try:
                save_extensions(self.settings_path, draft.get().split(","))
                self.extensions.set(", ".join(load_extensions(self.settings_path)))
            except (ValueError, OSError) as error:
                messagebox.showerror("Настройки", str(error), parent=window)
                return
            self.validation_status.set("Форматы сохранены.")
            window.destroy()

        ttk.Button(frame, text="По умолчанию",
                   command=lambda: draft.set(", ".join(DEFAULT_EXTENSIONS))).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(14, 0)
        )
        ttk.Button(frame, text="Сохранить", command=save).grid(
            row=3, column=0, sticky="w", pady=(14, 0)
        )
        ttk.Button(frame, text="Отмена", command=window.destroy).grid(
            row=3, column=1, sticky="e", pady=(14, 0)
        )
        window.bind("<Escape>", lambda event: window.destroy())
        window.update_idletasks()
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - window.winfo_reqwidth()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - window.winfo_reqheight()) // 2
        window.geometry(f"+{max(0, x)}+{max(0, y)}")
        window.deiconify()
        apply_dark_titlebar(window)
        entry.focus_set()

    def choose_directory(self, variable):
        directory = filedialog.askdirectory(parent=self.root, mustexist=True)
        if directory:
            variable.set(directory)

    def check_paths(self):
        error = validation.validate_paths(
            self.source.get(), self.destination.get(), self.recursive.get()
        )
        self.validation_status.set(error if error is not None else "Пути проверены.")

    def save_formats(self):
        try:
            save_extensions(self.settings_path, self.extensions.get().split(","))
            self.extensions.set(", ".join(load_extensions(self.settings_path)))
        except (ValueError, OSError) as error:
            messagebox.showerror("Настройки", str(error), parent=self.root)
            return
        self.validation_status.set("Форматы сохранены.")

    def start(self):
        if self.running:
            return
        source, destination = self.source.get(), self.destination.get()
        recursive, mode = self.recursive.get(), self.mode.get()
        error = validation.validate_paths(source, destination, recursive)
        if error:
            messagebox.showerror("Папки", error, parent=self.root)
            return
        try:
            save_extensions(self.settings_path, self.extensions.get().split(","))
            extensions = load_extensions(self.settings_path)
            self.extensions.set(", ".join(extensions))
        except (ValueError, OSError) as error:
            messagebox.showerror("Настройки", str(error), parent=self.root)
            return
        self.running = True
        self.conflict_choice = None
        self.start_button.configure(state="disabled")
        self.validation_status.set("Выполняется сортировка...")

        def resolve_conflict(path):
            if self.conflict_choice is not None:
                return self.conflict_choice
            response = {}
            ready = threading.Event()
            self.events.put(("conflict", path, response, ready))
            ready.wait()
            return response["choice"]

        def work():
            try:
                result = sort_videos(
                    source, destination, extensions, recursive, mode, resolve_conflict
                )
                self.events.put(("done", result))
            except Exception as error:
                self.events.put(("error", error))

        threading.Thread(target=work, daemon=True).start()
        self.root.after(100, self.process_events)

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "conflict":
                    _, path, response, ready = event
                    try:
                        choice, apply_all = ask_conflict(self.root, path)
                        if apply_all and choice != "cancel":
                            self.conflict_choice = choice
                        response["choice"] = choice
                    finally:
                        response.setdefault("choice", "cancel")
                        ready.set()
                else:
                    self.running = False
                    self.start_button.configure(state="normal")
                    if event[0] == "error":
                        self.validation_status.set("Сортировка не выполнена.")
                        messagebox.showerror("Ошибка сортировки", str(event[1]), parent=self.root)
                    else:
                        self.show_report(event[1])
        except queue.Empty:
            pass
        if self.running:
            self.root.after(100, self.process_events)

    def show_report(self, report):
        summary = (
            f"Обработано: {len(report.processed)}; "
            f"пропущено: {len(report.skipped)}; ошибок: {len(report.errors)}."
        )
        if report.cancelled:
            summary += " Сортировка остановлена пользователем."
        self.validation_status.set(summary)
        window = tk.Toplevel(self.root)
        window.title("Результат сортировки")
        window.geometry("700x450")
        window.configure(background="#101820")
        ttk.Label(window, text=summary, wraplength=650, padding=10).pack(anchor="w")
        text = tk.Text(window, wrap="word", background="#1a2730", foreground="#eaf1f3",
                       insertbackground="#eaf1f3", relief="flat", padx=12, pady=12,
                       font=("Segoe UI", 10))
        text.pack(fill="both", expand=True, padx=10, pady=10)
        for item in report.processed:
            text.insert("end", f"Обработан: {item.source}\n  → {item.destination}\n")
        for item in report.skipped:
            reason = "дата не распознана" if item.reason == "invalid_date" else "конфликт имён"
            text.insert("end", f"Пропущен ({reason}): {item.source}\n")
        for item in report.errors:
            text.insert("end", f"Ошибка: {item.source}\n  {item.error}\n")
            if item.possibly_partial:
                text.insert(
                    "end",
                    f"  Перенос мог завершиться частично. Проверьте исходник и {item.destination}\n",
                )
        text.configure(state="disabled")
        window.update_idletasks()
        apply_dark_titlebar(window)

    def close(self):
        if self.running:
            messagebox.showinfo(
                "Сортировка выполняется",
                "Дождитесь завершения сортировки, прежде чем закрыть программу.",
                parent=self.root,
            )
            return
        self.root.destroy()


def main():
    from dpi import enable_high_dpi

    enable_high_dpi()
    root = tk.Tk()
    FileSorterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
