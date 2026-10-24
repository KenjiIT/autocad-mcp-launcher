"""Locate the AutoCAD LT frame window.

Standalone on purpose: the launcher gateway loads this file by path from a
Python environment where ``autocad_mcp`` is a different package.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def find_lt_window() -> tuple[int, int] | None:
    """Select one LT frame by executable and optional PID; never guess among peers."""
    if sys.platform != "win32":
        return None
    import win32api
    import win32con
    import win32gui
    import win32process

    selected_pid = os.environ.get("AUTOCAD_MCP_ACAD_PID", "").strip()
    try:
        selected_pid_int = int(selected_pid) if selected_pid else None
    except ValueError:
        return None
    found: list[tuple[int, int]] = []

    def collect(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        handle = None
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if selected_pid_int is not None and pid != selected_pid_int:
                return True
            handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
            )
            # Floating palettes (Quick Properties, ...) are also titled top-level
            # windows of acadlt.exe; only the MDI frame owns the command line.
            if (Path(win32process.GetModuleFileNameEx(handle, 0)).name.lower() == "acadlt.exe"
                    and win32gui.GetWindowText(hwnd)
                    and "MDIFrame" in win32gui.GetClassName(hwnd)):
                found.append((int(hwnd), int(pid)))
        except Exception:
            pass
        finally:
            if handle is not None:
                win32api.CloseHandle(handle)
        return True

    win32gui.EnumWindows(collect, None)
    return found[0] if len({pid for _, pid in found}) == 1 else None
