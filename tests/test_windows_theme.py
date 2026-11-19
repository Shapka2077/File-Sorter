import unittest
from unittest.mock import MagicMock, patch

import windows_theme


class DarkTitlebarTests(unittest.TestCase):
    def test_other_platform_is_noop(self):
        window = MagicMock()
        with patch.object(windows_theme.sys, "platform", "linux"):
            self.assertFalse(windows_theme.apply_dark_titlebar(window))
        window.winfo_id.assert_not_called()

    def test_windows_uses_outer_window_handle(self):
        window = MagicMock()
        window.winfo_id.return_value = 10
        libraries = MagicMock()
        libraries.user32.GetParent.return_value = 20
        libraries.dwmapi.DwmSetWindowAttribute.return_value = 0
        with patch.object(windows_theme.sys, "platform", "win32"):
            with patch.object(windows_theme.ctypes, "windll", libraries, create=True):
                self.assertTrue(windows_theme.apply_dark_titlebar(window))
        args = libraries.dwmapi.DwmSetWindowAttribute.call_args.args
        self.assertEqual(args[0].value, 20)
        self.assertEqual(args[1], 20)

    def test_falls_back_to_older_attribute(self):
        window = MagicMock()
        window.winfo_id.return_value = 10
        libraries = MagicMock()
        libraries.user32.GetParent.return_value = 0
        libraries.dwmapi.DwmSetWindowAttribute.side_effect = [1, 0]
        with patch.object(windows_theme.sys, "platform", "win32"):
            with patch.object(windows_theme.ctypes, "windll", libraries, create=True):
                self.assertTrue(windows_theme.apply_dark_titlebar(window))
        self.assertEqual(libraries.dwmapi.DwmSetWindowAttribute.call_args.args[1], 19)


if __name__ == "__main__":
    unittest.main()
