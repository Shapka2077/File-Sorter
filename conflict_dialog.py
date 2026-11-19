import tkinter as tk
from tkinter import ttk

from windows_theme import apply_dark_titlebar


class ConflictDialog(tk.Toplevel):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.title("Совпадение имён")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#101820")
        self.choice = "cancel"
        self.apply_all = tk.BooleanVar(value=False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        style = ttk.Style(self)
        style.configure("Conflict.TFrame", background="#101820")
        style.configure("ConflictCard.TFrame", background="#1a2730")
        style.configure("ConflictTitle.TLabel", background="#101820", foreground="#f4f8f8",
                        font=("Segoe UI", 18, "bold"))
        style.configure("ConflictMuted.TLabel", background="#101820", foreground="#aebfc5",
                        font=("Segoe UI", 10))
        style.configure("ConflictPath.TLabel", background="#1a2730", foreground="#f4f8f8",
                        font=("Segoe UI", 10), padding=12)
        style.configure("Conflict.TCheckbutton", background="#101820", foreground="#eaf1f3",
                        font=("Segoe UI", 10), indicatorcolor="#24343e")
        style.map("Conflict.TCheckbutton", background=[("active", "#101820")],
                  indicatorcolor=[("selected", "#62d6bd")])
        style.configure("Conflict.TButton", background="#30434b", foreground="#f4f8f8",
                        font=("Segoe UI", 10), padding=(12, 9), borderwidth=0)
        style.map("Conflict.TButton", background=[("active", "#415960")])
        style.configure("Replace.TButton", background="#d79b6a", foreground="#24180f",
                        font=("Segoe UI", 10, "bold"), padding=(12, 9), borderwidth=0)
        style.map("Replace.TButton", background=[("active", "#efba8e")])

        frame = ttk.Frame(self, padding=24, style="Conflict.TFrame")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Файл уже существует", style="ConflictTitle.TLabel").pack(
            anchor="w"
        )
        ttk.Label(frame, text="В папке назначения найден файл с таким именем.",
                  style="ConflictMuted.TLabel").pack(anchor="w", pady=(5, 14))
        card = ttk.Frame(frame, style="ConflictCard.TFrame")
        card.pack(fill="x")
        ttk.Label(card, text=str(path), wraplength=500, style="ConflictPath.TLabel").pack(
            anchor="w", fill="x"
        )
        ttk.Label(frame, text="Выберите, как поступить с новым файлом:",
                  style="ConflictMuted.TLabel").pack(anchor="w", pady=(16, 0))
        ttk.Checkbutton(
            frame, text="Применить к остальным конфликтам", variable=self.apply_all,
            style="Conflict.TCheckbutton"
        ).pack(anchor="w", pady=(10, 18))
        buttons = ttk.Frame(frame, style="Conflict.TFrame")
        buttons.pack(fill="x")
        for index, (label, choice) in enumerate((
            ("Пропустить", "skip"),
            ("Заменить", "replace"),
            ("Переименовать", "rename"),
            ("Остановить", "cancel"),
        )):
            ttk.Button(
                buttons, text=label, command=lambda value=choice: self.choose(value),
                style="Replace.TButton" if choice == "replace" else "Conflict.TButton",
            ).grid(row=index // 2, column=index % 2, sticky="ew", padx=(0, 6), pady=(0, 6))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        self.update_idletasks()
        apply_dark_titlebar(self)
        self.grab_set()

    def choose(self, choice):
        self.choice = choice
        self.destroy()


def ask_conflict(parent, path):
    dialog = ConflictDialog(parent, path)
    parent.wait_window(dialog)
    return dialog.choice, dialog.apply_all.get()
