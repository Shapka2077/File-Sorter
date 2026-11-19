"""Opt native Tk windows into Windows' dark title bars when supported."""

import ctypes
import sys


def apply_dark_titlebar(window) -> bool:
    if sys.platform != "win32":
        return False
    try:
        window.update_idletasks()
        user32 = ctypes.windll.user32
        user32.GetParent.restype = ctypes.c_void_p
        handle = window.winfo_id()
        parent = user32.GetParent(ctypes.c_void_p(handle))
        hwnd = ctypes.c_void_p(parent or handle)
        enabled = ctypes.c_int(1)
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
            )
            if result == 0:
                return True
    except (AttributeError, OSError):
        pass
    return False
