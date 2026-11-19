import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from app import FileSorterApp


class AppIntegrationTests(unittest.TestCase):
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
