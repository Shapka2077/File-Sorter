import tempfile
import unittest
from pathlib import Path

from settings import DEFAULT_EXTENSIONS, load_extensions, save_extensions


class ExtensionSettingsTests(unittest.TestCase):
    def test_missing_settings_use_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_extensions(Path(directory) / "settings.json"), DEFAULT_EXTENSIONS)

    def test_extensions_persist_and_are_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_extensions(path, [" .MP4 ", "custom", ".mp4"])
            self.assertEqual(load_extensions(path), (".mp4", ".custom"))

    def test_invalid_extension_is_rejected_without_overwriting_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_extensions(path, [".mp4"])
            with self.assertRaises(ValueError):
                save_extensions(path, [".mp4", "../bad"])
            self.assertEqual(load_extensions(path), (".mp4",))

    def test_corrupt_settings_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_extensions(path)


if __name__ == "__main__":
    unittest.main()
