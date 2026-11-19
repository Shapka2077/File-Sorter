import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scanner import scan_videos


class ScannerTests(unittest.TestCase):
    def test_extensions_are_case_insensitive_and_files_are_not_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            video = source / "2024-02-29 12-34-56.MP4"
            video.write_bytes(b"video")
            (source / "2024-02-29.txt").touch()
            (source / "2024-02-29.mov").mkdir()

            records = scan_videos(source, iter(["mp4", ".MOV"]), False)

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].path, video)
            self.assertEqual(records[0].date, date(2024, 2, 29))
            self.assertEqual(video.read_bytes(), b"video")

    def test_dates_must_be_valid_and_at_start_of_name(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            names = [
                "2024-02-29.mp4",
                "2023-02-29.mp4",
                "0000-01-01.mp4",
                "prefix 2024-01-01.mp4",
                "2024-1-01.mp4",
                "no-date.mp4",
            ]
            for name in names:
                (source / name).touch()

            records = scan_videos(source, [".mp4"], False)
            dates = {record.path.name: record.date for record in records}

            self.assertEqual(dates.pop("2024-02-29.mp4"), date(2024, 2, 29))
            self.assertEqual(dates, {name: None for name in names[1:]})

    def test_recursive_scan_includes_nested_files_only_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            nested = source / "nested"
            nested.mkdir()
            top_video = source / "2024-01-01.mp4"
            nested_video = nested / "2024-01-02.mp4"
            top_video.touch()
            nested_video.touch()

            flat = scan_videos(source, [".mp4"], False)
            recursive = scan_videos(source, [".mp4"], True)

            self.assertEqual({record.path for record in flat}, {top_video})
            self.assertEqual(
                {record.path for record in recursive}, {top_video, nested_video}
            )

    def test_missing_directory_error_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                scan_videos(Path(directory) / "missing", [".mp4"], True)

    def test_nested_access_error_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            nested = source / "nested"
            nested.mkdir()
            import os

            real_scandir = os.scandir

            def scandir(path):
                if Path(path) == nested:
                    raise PermissionError("access denied")
                return real_scandir(path)

            with patch("scanner.os.scandir", side_effect=scandir):
                with self.assertRaises(PermissionError):
                    scan_videos(source, [".mp4"], True)


if __name__ == "__main__":
    unittest.main()
