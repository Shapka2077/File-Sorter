import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sorter import sort_videos


class SortVideosTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source"
        self.destination = root / "destination"
        self.source.mkdir()
        self.destination.mkdir()

    def run_sort(self, callback=lambda path: "skip", mode="copy", recursive=False):
        return sort_videos(self.source, self.destination, ["mp4"], recursive, mode, callback)

    def test_copies_dated_files_and_reports_invalid_dates(self):
        (self.source / "2026-11-19 video.mp4").write_text("video")
        (self.source / "unknown.mp4").write_text("unknown")
        report = self.run_sort()
        self.assertEqual((self.destination / "19.11.26" / "2026-11-19 video.mp4").read_text(), "video")
        self.assertEqual(len(report.processed), 1)
        self.assertEqual(len(report.skipped), 1)
        self.assertEqual(report.skipped[0].reason, "invalid_date")
        self.assertFalse(report.errors)
        self.assertFalse(report.cancelled)

    def test_each_conflict_asks_and_rename_preserves_existing_files(self):
        folder = self.destination / "19.11.26"
        folder.mkdir()
        for name in ("2026-11-19 a.mp4", "2026-11-19 b.mp4"):
            (self.source / name).write_text("new")
            (folder / name).write_text("old")
        calls = []
        report = self.run_sort(lambda path: calls.append(path) or "rename")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(report.processed), 2)
        for name in ("2026-11-19 a.mp4", "2026-11-19 b.mp4"):
            self.assertEqual((folder / name).read_text(), "old")
            self.assertEqual((folder / (Path(name).stem + " (1).mp4")).read_text(), "new")

    def test_cancel_stops_and_keeps_conflicting_file(self):
        name = "2026-11-19 a.mp4"
        (self.source / name).write_text("new")
        folder = self.destination / "19.11.26"
        folder.mkdir()
        (folder / name).write_text("old")
        report = self.run_sort(lambda path: "cancel", mode="move")
        self.assertTrue(report.cancelled)
        self.assertEqual((folder / name).read_text(), "old")
        self.assertTrue((self.source / name).exists())

    def test_rejects_recursive_destination_inside_source(self):
        nested = self.source / "nested"
        nested.mkdir()
        with self.assertRaises(ValueError):
            sort_videos(self.source, nested, ["mp4"], True, "copy", lambda p: "skip")

    def test_race_after_absence_check_asks_before_replacing(self):
        name = "2026-11-19 a.mp4"
        (self.source / name).write_text("new")
        import sorter
        real_transfer = sorter.transfer_file
        calls = []

        def race(source, destination, **kwargs):
            if not calls:
                destination.write_text("raced")
                calls.append(True)
            return real_transfer(source, destination, **kwargs)

        prompts = []
        with patch("sorter.transfer_file", side_effect=race):
            report = self.run_sort(lambda path: prompts.append(path) or "skip")
        self.assertEqual(len(prompts), 1)
        self.assertEqual((self.destination / "19.11.26" / name).read_text(), "raced")
        self.assertEqual(report.skipped[0].reason, "conflict")

    def test_replace_and_move_are_explicit(self):
        name = "2026-11-19 a.mp4"
        (self.source / name).write_text("new")
        folder = self.destination / "19.11.26"
        folder.mkdir()
        (folder / name).write_text("old")
        report = self.run_sort(lambda path: "replace", mode="move")
        self.assertEqual((folder / name).read_text(), "new")
        self.assertFalse((self.source / name).exists())
        self.assertEqual(report.processed[0].destination, folder / name)

    def test_file_error_continues_and_reports_possible_partial_move(self):
        names = ("2026-11-19 a.mp4", "2026-11-19 b.mp4")
        for name in names:
            (self.source / name).write_text(name)
        import sorter
        real_transfer = sorter.transfer_file

        def fail_one(source, destination, **kwargs):
            if source.name == names[0]:
                destination.write_text("published")
                raise OSError("source removal failed")
            return real_transfer(source, destination, **kwargs)

        with patch("sorter.transfer_file", side_effect=fail_one):
            report = self.run_sort(mode="move")
        self.assertEqual(len(report.errors), 1)
        self.assertTrue(report.errors[0].possibly_partial)
        self.assertEqual(report.errors[0].source, self.source / names[0])
        self.assertTrue((self.source / names[0]).exists())
        self.assertEqual(len(report.processed), 1)
        self.assertFalse((self.source / names[1]).exists())

    def test_scan_failure_prevents_all_transfers(self):
        (self.source / "2026-11-19 a.mp4").write_text("new")
        with patch("sorter.scan_videos", side_effect=OSError("scan failed")):
            with self.assertRaises(OSError):
                self.run_sort()
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_recursive_scan_and_non_video_files(self):
        folder = self.source / "nested"
        folder.mkdir()
        (folder / "2026-11-19 a.MP4").write_text("video")
        (folder / "2026-11-19 b.txt").write_text("text")
        report = self.run_sort(recursive=True)
        self.assertEqual(len(report.processed), 1)
        self.assertEqual((self.destination / "19.11.26" / "2026-11-19 a.MP4").read_text(), "video")


if __name__ == "__main__":
    unittest.main()
