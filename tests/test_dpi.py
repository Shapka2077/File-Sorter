import unittest
from unittest.mock import MagicMock, patch

import dpi


class HighDpiTests(unittest.TestCase):
    def test_does_nothing_on_other_platforms(self):
        with patch.object(dpi.sys, "platform", "linux"):
            self.assertFalse(dpi.enable_high_dpi())

    def test_uses_per_monitor_v2_when_available(self):
        libraries = MagicMock()
        libraries.user32.SetProcessDpiAwarenessContext.return_value = 1
        with patch.object(dpi.sys, "platform", "win32"):
            with patch.object(dpi.ctypes, "windll", libraries, create=True):
                self.assertTrue(dpi.enable_high_dpi())
        libraries.user32.SetProcessDpiAwarenessContext.assert_called_once()
        libraries.shcore.SetProcessDpiAwareness.assert_not_called()

    def test_falls_back_if_new_api_unavailable(self):
        libraries = MagicMock()
        libraries.user32.SetProcessDpiAwarenessContext.side_effect = OSError()
        libraries.shcore.SetProcessDpiAwareness.return_value = 0
        with patch.object(dpi.sys, "platform", "win32"):
            with patch.object(dpi.ctypes, "windll", libraries, create=True):
                self.assertTrue(dpi.enable_high_dpi())
        libraries.shcore.SetProcessDpiAwareness.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
