import tempfile
import unittest
from pathlib import Path

from validation import validate_paths


class PathValidationTests(unittest.TestCase):
    def test_valid_directories_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            destination = Path(directory) / "destination"
            source.mkdir()
            destination.mkdir()
            self.assertIsNone(validate_paths(str(source), str(destination)))

    def test_empty_paths_are_rejected(self):
        self.assertIsNotNone(validate_paths("", ""))

    def test_nonexistent_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNotNone(validate_paths(directory, str(Path(directory) / "missing")))

    def test_file_is_not_a_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "video.mp4"
            file.touch()
            self.assertIsNotNone(validate_paths(str(file), directory))

    def test_same_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNotNone(validate_paths(directory, str(Path(directory) / ".")))

    def test_nested_destination_rejected_when_recursive(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "destination"
            destination.mkdir()
            self.assertIsNotNone(validate_paths(directory, str(destination), recursive=True))
            self.assertIsNone(validate_paths(directory, str(destination), recursive=False))


if __name__ == "__main__":
    unittest.main()
