"""AutoCAD readiness boundary for the two upstream implementations.

The real AutoCAD handshake can only be confirmed on a running CAD session.
Keep that product-specific work here, and fail closed when it cannot be proved.
"""
import asyncio
import ctypes
import json
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _set_trusted_path(repo: Path) -> str:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        doc = win32com.client.GetActiveObject("AutoCAD.Application").ActiveDocument
        original = str(doc.GetVariable("TRUSTEDPATHS"))
        folder = str((repo / "lisp-code").resolve())
        paths = [item.strip('"') for item in original.split(";") if item]
        if folder.casefold() not in {item.casefold() for item in paths}:
            updated = f"{original};{folder}" if original else folder
            doc.SetVariable("TRUSTEDPATHS", updated)
        return original
    finally:
        pythoncom.CoUninitialize()


def _restore_trusted_path(original: str) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        doc = win32com.client.GetActiveObject("AutoCAD.Application").ActiveDocument
        if str(doc.GetVariable("TRUSTEDPATHS")) != original:
            doc.SetVariable("TRUSTEDPATHS", original)
    finally:
        pythoncom.CoUninitialize()


async def _call_system(port: int, operation: str) -> dict:
    async with streamablehttp_client(f"http://127.0.0.1:{port}/mcp") as (read, write, _):
        async with ClientSession(read, write) as client:
            await client.initialize()
            result = await client.call_tool("system", {"operation": operation})
            for block in result.content:
                if getattr(block, "type", "") == "text":
                    try:
                        return json.loads(block.text)
                    except json.JSONDecodeError:
                        return {"ok": False, "error": block.text}
            return {"ok": False, "error": "MCP không trả trạng thái dạng văn bản"}


def _load_puran_dispatcher(repo: Path) -> None:
    """Load v3 through the command window, as the puran backend itself does."""
    import win32gui
    from autocad_mcp.backends.file_ipc import find_autocad_window

    hwnd = find_autocad_window()
    if not hwnd:
        raise RuntimeError("Không tìm thấy cửa sổ AutoCAD có bản vẽ đang mở")
    mdi = []

    def collect(child, _):
        if win32gui.GetClassName(child) == "MDIClient":
            mdi.append(child)
            return False
        return True

    win32gui.EnumChildWindows(hwnd, collect, None)
    target = mdi[0] if mdi else hwnd
    post = ctypes.windll.user32.PostMessageW
    for _ in range(2):
        post(target, 0x0100, 0x1B, 0)
        post(target, 0x0101, 0x1B, 0)
    time.sleep(0.05)
    lisp = (repo / "lisp-code" / "mcp_dispatch.lsp").resolve()
    command = '(load "' + lisp.as_posix() + '")'
    for char in command:
        if not post(target, 0x0102, ord(char), 0):
            raise RuntimeError("Không gửi được lệnh tải LISP vào AutoCAD")
    post(target, 0x0102, 0x0D, 0)


async def prove_connection(name: str, repo: Path, port: int) -> dict:
    try:
        original = await asyncio.to_thread(_set_trusted_path, repo)
    except Exception as exc:
        raise RuntimeError(
            f"Không chuẩn bị được đường dẫn LISP cho {name}. "
            "Mở một bản vẽ AutoCAD và đóng mọi hộp thoại đang che cửa sổ. "
            f"Chi tiết: {exc}"
        ) from exc
    try:
        if name == "autocad_puran":
            await asyncio.to_thread(_load_puran_dispatcher, repo)
            operation = "status"
        else:
            operation = "ensure_ready"

        last = None
        attempts = 2 if name == "autocad_puran" else 1
        timeout = 20 if name == "autocad_puran" else 45
        for index in range(attempts):
            try:
                last = await asyncio.wait_for(_call_system(port, operation), timeout=timeout)
                payload = last.get("payload") or {}
                if name == "autocad_puran":
                    if last.get("ok") and payload.get("backend") == "file_ipc":
                        return payload
                elif (last.get("ok") and payload.get("ready") is True
                      and payload.get("transport") in ("file_ipc", "native_pipe")):
                    return payload
            except asyncio.TimeoutError:
                last = {"ok": False, "error": f"{operation} quá thời hạn {timeout} giây"}
            except Exception as exc:
                last = {"ok": False, "error": str(exc)}
            if index + 1 < attempts:
                await asyncio.sleep(1)
        raise RuntimeError(f"AutoCAD chưa kết nối với {name}: {last}")
    finally:
        await asyncio.to_thread(_restore_trusted_path, original)
