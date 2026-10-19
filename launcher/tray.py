"""Windows tray icon with its own native window; Tk's window is never subclassed."""

import ctypes
import hashlib
import os
import queue
from ctypes import wintypes
from pathlib import Path


WM_APP = 0x8000
WM_TRAY = WM_APP + 1
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
NIM_ADD = 0
NIM_DELETE = 2
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4
IDI_APPLICATION = 32512
APP_ID = hashlib.sha256(str(Path(__file__).resolve().parent.parent).casefold().encode()).hexdigest()[:12]
CLASS_PREFIX = f"AutoCADMCPTray_{APP_ID}_"


class Guid(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE * 8)]


class NotifyIconData(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", Guid), ("hBalloonIcon", wintypes.HICON),
    ]


class Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t)


class WndClass(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]


def restore_existing():
    """Ask an already running launcher to show its Tk window again."""
    user32 = ctypes.windll.user32
    enum_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, ctypes.c_ssize_t)
    user32.EnumWindows.argtypes = [enum_callback, ctypes.c_ssize_t]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.PostMessageW.argtypes = [
        wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
    user32.PostMessageW.restype = wintypes.BOOL
    found = False

    def visit(hwnd, _):
        nonlocal found
        name = ctypes.create_unicode_buffer(128)
        if user32.GetClassNameW(hwnd, name, len(name)) and name.value.startswith(CLASS_PREFIX):
            found = bool(user32.PostMessageW(hwnd, WM_TRAY, 0, WM_LBUTTONUP))
            return False
        return True

    callback = enum_callback(visit)
    user32.EnumWindows(callback, 0)
    return found


class TrayIcon:
    def __init__(self, root, on_open, on_menu):
        self.root = root
        self.on_open = on_open
        self.on_menu = on_menu
        self.events = queue.SimpleQueue()
        self.user32 = ctypes.windll.user32
        self.shell32 = ctypes.windll.shell32
        self.kernel32 = ctypes.windll.kernel32
        self.user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        self.user32.LoadIconW.restype = wintypes.HICON
        self.user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
        self.user32.RegisterWindowMessageW.restype = wintypes.UINT
        self.user32.DefWindowProcW.argtypes = [
            wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
        self.user32.DefWindowProcW.restype = LRESULT
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(Point)]
        self.user32.GetCursorPos.restype = wintypes.BOOL
        self.user32.RegisterClassW.argtypes = [ctypes.POINTER(WndClass)]
        self.user32.RegisterClassW.restype = wintypes.ATOM
        self.user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
        self.user32.UnregisterClassW.restype = wintypes.BOOL
        self.user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HANDLE, wintypes.HINSTANCE, ctypes.c_void_p]
        self.user32.CreateWindowExW.restype = wintypes.HWND
        self.user32.DestroyWindow.argtypes = [wintypes.HWND]
        self.user32.DestroyWindow.restype = wintypes.BOOL
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
        self.shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NotifyIconData)]
        self.shell32.Shell_NotifyIconW.restype = wintypes.BOOL

        self.instance = self.kernel32.GetModuleHandleW(None)
        self.class_name = f"{CLASS_PREFIX}{os.getpid()}"
        self.taskbar_created = self.user32.RegisterWindowMessageW("TaskbarCreated")
        self.callback = WNDPROC(self._window_proc)
        window_class = WndClass()
        window_class.lpfnWndProc = self.callback
        window_class.hInstance = self.instance
        window_class.lpszClassName = self.class_name
        if not self.user32.RegisterClassW(ctypes.byref(window_class)):
            raise ctypes.WinError()

        self.hwnd = self.user32.CreateWindowExW(
            0, self.class_name, self.class_name, 0, 0, 0, 0, 0,
            None, None, self.instance, None)
        if not self.hwnd:
            self.user32.UnregisterClassW(self.class_name, self.instance)
            raise ctypes.WinError()

        self.nid = NotifyIconData()
        self.nid.cbSize = ctypes.sizeof(NotifyIconData)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.nid.uCallbackMessage = WM_TRAY
        self.nid.hIcon = self.user32.LoadIconW(None, IDI_APPLICATION)
        self.nid.szTip = "AutoCAD MCP Launcher"
        self.added = bool(self.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid)))
        if not self.added:
            self.user32.DestroyWindow(self.hwnd)
            self.user32.UnregisterClassW(self.class_name, self.instance)
            raise ctypes.WinError()

    def _window_proc(self, hwnd, message, wparam, lparam):
        try:
            if message == WM_TRAY:
                if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    self.events.put(("open", None))
                elif lparam == WM_RBUTTONUP:
                    point = Point()
                    if self.user32.GetCursorPos(ctypes.byref(point)):
                        self.events.put(("menu", (point.x, point.y)))
                return 0
            if message == self.taskbar_created and hasattr(self, "nid"):
                self.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid))
        except Exception:
            # Exceptions cannot propagate safely through a Windows callback.
            return 0
        return self.user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def poll(self):
        while True:
            try:
                event, point = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "open":
                self.on_open()
            else:
                self.on_menu(*point)

    def close(self):
        if self.added:
            self.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
            self.added = False
        if self.hwnd:
            self.user32.DestroyWindow(self.hwnd)
            self.hwnd = None
        self.user32.UnregisterClassW(self.class_name, self.instance)
