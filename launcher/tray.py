"""Small Windows notification-area icon for the Tk launcher, without dependencies."""

import ctypes
from ctypes import wintypes


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
GWLP_WNDPROC = -4
IDI_APPLICATION = 32512


class Guid(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


class NotifyIconData(ctypes.Structure):
    # Use the complete Windows structure so cbSize is accepted by current shells.
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", Guid),
        ("hBalloonIcon", wintypes.HICON),
    ]


class Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t)


class TrayIcon:
    def __init__(self, root, on_open, on_menu):
        self.root = root
        self.on_open = on_open
        self.on_menu = on_menu
        self.user32 = ctypes.windll.user32
        self.shell32 = ctypes.windll.shell32
        self.user32.GetParent.argtypes = [wintypes.HWND]
        self.user32.GetParent.restype = wintypes.HWND
        self.user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        self.user32.LoadIconW.restype = wintypes.HICON
        self.user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
        self.user32.RegisterWindowMessageW.restype = wintypes.UINT
        self.user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
            ctypes.c_size_t, ctypes.c_ssize_t]
        self.user32.CallWindowProcW.restype = LRESULT
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(Point)]
        self.user32.GetCursorPos.restype = wintypes.BOOL
        self.shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NotifyIconData)]
        self.shell32.Shell_NotifyIconW.restype = wintypes.BOOL

        # Tk's visible wrapper is the parent of the window returned by winfo_id().
        root.update_idletasks()
        self.hwnd = self.user32.GetParent(root.winfo_id()) or root.winfo_id()
        self.taskbar_created = self.user32.RegisterWindowMessageW("TaskbarCreated")
        self.nid = NotifyIconData()
        self.nid.cbSize = ctypes.sizeof(NotifyIconData)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.nid.uCallbackMessage = WM_TRAY
        self.nid.hIcon = self.user32.LoadIconW(None, IDI_APPLICATION)
        self.nid.szTip = "AutoCAD MCP Launcher"

        set_window_proc = getattr(self.user32, "SetWindowLongPtrW", None)
        if set_window_proc is None:
            set_window_proc = self.user32.SetWindowLongW
        set_window_proc.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        set_window_proc.restype = ctypes.c_void_p
        self.set_window_proc = set_window_proc
        self.callback = WNDPROC(self._window_proc)
        self.old_proc = self.set_window_proc(
            self.hwnd, GWLP_WNDPROC, ctypes.cast(self.callback, ctypes.c_void_p))
        if not self.old_proc:
            raise OSError("Không thể gắn biểu tượng vào khay hệ thống")
        self.added = bool(self.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid)))
        if not self.added:
            self.set_window_proc(self.hwnd, GWLP_WNDPROC, self.old_proc)
            raise OSError("Không thể tạo biểu tượng khay hệ thống")

    def _window_proc(self, hwnd, message, wparam, lparam):
        if message == WM_TRAY:
            if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self.root.after(0, self.on_open)
            elif lparam == WM_RBUTTONUP:
                point = Point()
                if self.user32.GetCursorPos(ctypes.byref(point)):
                    self.root.after(0, lambda: self.on_menu(point.x, point.y))
            return 0
        if message == self.taskbar_created:
            self.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid))
        return self.user32.CallWindowProcW(self.old_proc, hwnd, message, wparam, lparam)

    def close(self):
        if self.added:
            self.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
            self.added = False
        if self.old_proc:
            self.set_window_proc(self.hwnd, GWLP_WNDPROC, self.old_proc)
            self.old_proc = None
