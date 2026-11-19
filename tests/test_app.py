import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from app import FileSorterApp, _switch_image
from settings import DEFAULT_EXTENSIONS


class AppIntegrationTests(unittest.TestCase):
    def test_switch_image_has_antialiased_edge_pixels(self):
        root = tk.Tk()
        root.withdraw()
        try:
            image = _switch_image(root, True)
            colors = {image.get(x, y) for x in range(42) for y in range(24)}
            self.assertTrue(colors - {(0, 0, 0), (98, 214, 189), (244, 248, 248)})
        finally:
            root.destroy()

    def test_restore_defaults_is_a_draft_until_saved(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FileSorterApp(root)
            app.extensions.set(".custom")
            app.open_format_settings()
            dialog = next(child for child in root.winfo_children() if isinstance(child, tk.Toplevel))
            frame = dialog.winfo_children()[0]
            entry = next(child for child in frame.winfo_children() if child.winfo_class() == "TEntry")
            button = next(child for child in frame.winfo_children()
                          if child.winfo_class() == "TButton" and child.cget("text") == "По умолчанию")
            button.invoke()
            self.assertEqual(entry.get(), ", ".join(DEFAULT_EXTENSIONS))
            self.assertEqual(app.extensions.get(), ".custom")
            dialog.destroy()
        finally:
            root.destroy()

    def test_switches_update_mode_and_recursive_selection(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FileSorterApp(root)
            self.assertEqual(app.mode.get(), "copy")
            self.assertFalse(app.recursive.get())
            app.mode_switch.invoke()
            app.recursive_switch.invoke()
            self.assertEqual(app.mode.get(), "move")
            self.assertTrue(app.recursive.get())
            self.assertIn("исходной папки", app._recursive_label.get())
        finally:
            root.destroy()

    def test_copy_with_conflict_renames_and_reports_result(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, destination = base / "source", base / "destination"
            source.mkdir()
            destination.mkdir()
            name = "2026-11-19 16-50-20.mp4"
            (source / name).write_bytes(b"new video")
            target = destination / "19.11.26"
            target.mkdir()
            (target / name).write_bytes(b"original")
            root = tk.Tk()
            root.withdraw()
            try:
                app = FileSorterApp(root)
                app.settings_path = base / "settings.json"
                app.source.set(str(source))
                app.destination.set(str(destination))
                with patch("app.ask_conflict", return_value=("rename", False)):
                    app.start()
                    deadline = time.monotonic() + 10
                    while app.running and time.monotonic() < deadline:
                        root.update()
                        time.sleep(0.01)
                self.assertFalse(app.running, "sorting did not complete")
                self.assertEqual((target / name).read_bytes(), b"original")
                self.assertEqual((target / "2026-11-19 16-50-20 (1).mp4").read_bytes(), b"new video")
                self.assertEqual((source / name).read_bytes(), b"new video")
                self.assertIn("Обработано: 1", app.validation_status.get())
            finally:
                root.destroy()


if __name__ == "__main__":
    unittest.main()
