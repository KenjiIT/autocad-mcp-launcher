"""Remember which AutoCAD process the agent session is bound to.

With several AutoCAD windows open the adapters refuse to guess, so the first
process a session connects to is saved and every later call is pinned to it
through AUTOCAD_MCP_ACAD_PID.  A PID that no longer belongs to AutoCAD is
dropped, and an explicit user-set variable is never overwritten.
"""
import ctypes
import json
import os
import time
from ctypes import wintypes
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent / "state" / "acad_session.json"
ENV_NAME = "AUTOCAD_MCP_ACAD_PID"
_ACAD_EXES = {"acad.exe", "acadlt.exe"}
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_EXPLICIT = os.environ.get(ENV_NAME, "").strip()
_managed = False


def process_image(pid: int) -> str:
    """Executable name of a live process, or an empty string."""
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return Path(buffer.value).name.lower()
    finally:
        kernel32.CloseHandle(handle)


def is_autocad(pid) -> bool:
    try:
        return process_image(int(pid)) in _ACAD_EXES
    except (TypeError, ValueError, OSError):
        return False


def saved_pid():
    try:
        pid = int(json.loads(STATE_FILE.read_text(encoding="utf-8")).get("pid"))
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return pid if is_autocad(pid) else None


def save(pid, document=None) -> None:
    """Persist the process a session just connected to."""
    if not is_autocad(pid) or (_EXPLICIT and not _managed):
        return
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps({
        "pid": int(pid), "document": document, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False), encoding="utf-8")
    temporary.replace(STATE_FILE)


def apply():
    """Pin this process's environment to the saved AutoCAD PID; return it.

    A variable the user set before launch always wins.  Otherwise the saved
    PID is used while it is alive, and a stale one is removed.
    """
    global _managed
    if _EXPLICIT:
        return int(_EXPLICIT) if _EXPLICIT.isdigit() else None
    pid = saved_pid()
    if pid is None:
        if _managed:
            os.environ.pop(ENV_NAME, None)
            _managed = False
        try:
            STATE_FILE.unlink()
        except OSError:
            pass
        return None
    os.environ[ENV_NAME] = str(pid)
    _managed = True
    return pid
