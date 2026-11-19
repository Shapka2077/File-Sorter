import tkinter as tk
from tkinter import ttk


class ConflictDialog(tk.Toplevel):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.title("Совпадение имён")
        self.transient(parent)
        self.resizable(False, False)
        self.choice = "cancel"
        self.apply_all = tk.BooleanVar(value=False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=f"Файл уже существует:\n{path}\n\nЧто сделать?",
            wraplength=520,
        ).pack(anchor="w")
        ttk.Checkbutton(
            frame, text="Применить к остальным конфликтам", variable=self.apply_all
        ).pack(anchor="w", pady=12)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        for label, choice in (
            ("Пропустить", "skip"),
            ("Заменить", "replace"),
            ("Переименовать", "rename"),
            ("Остановить", "cancel"),
        ):
            ttk.Button(
                buttons, text=label, command=lambda value=choice: self.choose(value)
            ).pack(side="left", padx=3)
        self.grab_set()

    def choose(self, choice):
        self.choice = choice
        self.destroy()


def ask_conflict(parent, path):
    dialog = ConflictDialog(parent, path)
    parent.wait_window(dialog)
    return dialog.choice, dialog.apply_all.get()
