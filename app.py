"""Интерфейс File Sorter без выполнения операций над файлами."""

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


class FileSorterApp:
    def __init__(self, root):
        self.root = root
        root.title("File Sorter")
        root.minsize(560, 300)

        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.mode = tk.StringVar(value="copy")
        self.recursive = tk.BooleanVar(value=False)
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

        frame = ttk.Frame(root, padding=20)
        frame.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Исходная папка:").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.source).grid(
            row=0, column=1, sticky="ew", padx=8, pady=6
        )
        ttk.Button(
            frame, text="Обзор...", command=lambda: self.choose_directory(self.source)
        ).grid(row=0, column=2, pady=6)

        ttk.Label(frame, text="Папка назначения:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.destination).grid(
            row=1, column=1, sticky="ew", padx=8, pady=6
        )
        ttk.Button(
            frame, text="Обзор...", command=lambda: self.choose_directory(self.destination)
        ).grid(row=1, column=2, pady=6)

        modes = ttk.LabelFrame(frame, text="Режим", padding=8)
        modes.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)
        ttk.Radiobutton(modes, text="Копирование", variable=self.mode, value="copy").pack(
            side="left", padx=(0, 20)
        )
        ttk.Radiobutton(modes, text="Перемещение", variable=self.mode, value="move").pack(
            side="left"
        )

        ttk.Checkbutton(
            frame, text="Искать во вложенных папках", variable=self.recursive
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=6)
        ttk.Label(frame, text="Форматы видео:").grid(row=4, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.extensions).grid(
            row=4, column=1, sticky="ew", padx=8, pady=6
        )
        ttk.Button(frame, text="Сохранить", command=self.save_formats).grid(
            row=4, column=2, pady=6
        )
        ttk.Button(frame, text="Проверить пути", command=self.check_paths).grid(
            row=5, column=0, sticky="w", pady=6
        )
        ttk.Label(frame, textvariable=self.validation_status, wraplength=500).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=6
        )
        self.start_button = ttk.Button(frame, text="Начать сортировку", command=self.start)
        self.start_button.grid(row=7, column=0, sticky="w", pady=6)

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
        ttk.Label(window, text=summary, wraplength=650, padding=10).pack(anchor="w")
        text = tk.Text(window, wrap="word")
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
    root = tk.Tk()
    FileSorterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
