import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import file_operations
from file_operations import transfer_file


class FileOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source" / "video.mp4"
        self.source.parent.mkdir()
        self.source.write_bytes(b"new video")
        self.destination = self.root / "destination" / "video.mp4"
        self.destination.parent.mkdir()

    def test_copy_preserves_source(self):
        result = transfer_file(self.source, self.destination, mode="copy")
        self.assertEqual(result, self.destination)
        self.assertEqual(self.source.read_bytes(), b"new video")
        self.assertEqual(result.read_bytes(), b"new video")

    def test_move_removes_source_after_success(self):
        result = transfer_file(self.source, self.destination, mode="move")
        self.assertEqual(result.read_bytes(), b"new video")
        self.assertFalse(self.source.exists())

    def test_default_conflict_skips_without_overwriting(self):
        self.destination.write_bytes(b"old video")
        self.assertIsNone(transfer_file(self.source, self.destination, mode="move"))
        self.assertEqual(self.destination.read_bytes(), b"old video")
        self.assertTrue(self.source.exists())

    def test_rename_finds_first_available_suffix(self):
        self.destination.write_bytes(b"old")
        (self.destination.parent / "video (1).mp4").write_bytes(b"other")
        result = transfer_file(self.source, self.destination, mode="copy", conflict="rename")
        self.assertEqual(result.name, "video (2).mp4")
        self.assertEqual(result.read_bytes(), b"new video")
        self.assertEqual(self.destination.read_bytes(), b"old")

    def test_replace_requires_explicit_policy(self):
        self.destination.write_bytes(b"old")
        result = transfer_file(self.source, self.destination, mode="move", conflict="replace")
        self.assertEqual(result.read_bytes(), b"new video")
        self.assertFalse(self.source.exists())

    def test_same_file_is_rejected_even_with_replace_or_rename(self):
        for conflict in ("skip", "rename", "replace"):
            with self.subTest(conflict=conflict):
                with self.assertRaises(ValueError):
                    transfer_file(self.source, self.source, mode="move", conflict=conflict)
                self.assertEqual(self.source.read_bytes(), b"new video")

    def test_hard_link_to_source_is_rejected(self):
        import os
        os.link(self.source, self.destination)
        with self.assertRaises(ValueError):
            transfer_file(self.source, self.destination, mode="move", conflict="replace")
        self.assertEqual(self.source.read_bytes(), b"new video")

    def test_invalid_options_do_not_modify_files(self):
        for options in ({"mode": "bad"}, {"mode": "copy", "conflict": "bad"}):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    transfer_file(self.source, self.destination, **options)
                self.assertFalse(self.destination.exists())
                self.assertTrue(self.source.exists())

    def test_copy_error_preserves_source_and_existing_destination(self):
        self.destination.write_bytes(b"old")
        with patch.object(file_operations.shutil, "copyfileobj", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                transfer_file(self.source, self.destination, mode="move", conflict="replace")
        self.assertEqual(self.source.read_bytes(), b"new video")
        self.assertEqual(self.destination.read_bytes(), b"old")
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])

    def test_conflict_created_during_publish_is_never_overwritten(self):
        original_link = file_operations.os.link
        def race(src, dst):
            Path(dst).write_bytes(b"racing file")
            return original_link(src, dst)
        with patch.object(file_operations.os, "link", side_effect=race):
            result = transfer_file(self.source, self.destination, mode="move", conflict="skip")
        self.assertIsNone(result)
        self.assertEqual(self.destination.read_bytes(), b"racing file")
        self.assertTrue(self.source.exists())

    def test_delete_error_keeps_source_and_completed_destination(self):
        original_unlink = Path.unlink
        def fail_source(path, *args, **kwargs):
            if path == self.source:
                raise PermissionError("cannot remove source")
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", fail_source):
            with self.assertRaises(PermissionError):
                transfer_file(self.source, self.destination, mode="move")
        self.assertEqual(self.source.read_bytes(), b"new video")
        self.assertEqual(self.destination.read_bytes(), b"new video")


if __name__ == "__main__":
    unittest.main()
