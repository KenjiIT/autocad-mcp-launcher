"""Cầu nối gateway -> LiteBIM và LiteCAD (cùng hãng, cùng giao thức), giống cách ``*-mcp.exe`` của chúng tự nối.

LiteBIM (và LiteCAD) mở sẵn một named pipe ``\\\\.\\pipe\\litebim-mcp-<tên người dùng Windows>``; trên pipe
đó là JSON-RPC MCP, mỗi thông điệp một dòng. ``litebim-mcp.exe`` chỉ là cầu stdio nối tới pipe này. Gateway
của launcher làm cùng việc, nhưng phục vụ qua HTTP (``/litebim/mcp``) để dùng chung với Codex, Claude Code,
Claude Desktop, Cursor và chế độ agent từ xa.

Một kết nối pipe dùng chung, tuần tự (khóa): LiteBIM xử lý từng lệnh một trên giao diện của nó. LiteBIM chưa
mở thì ``initialize`` vẫn thành công, ``tools/list`` trả danh sách rỗng và ``tools/call`` báo lỗi rõ ràng,
như ``litebim-mcp.exe``; mở LiteBIM xong dùng được ngay, không phải khởi động lại agent.
"""
import ctypes
import itertools
import json
import os
import sys
import threading
import time

PIPE_PREFIX = "litebim-mcp-"
PRODUCTS = {  # khóa gateway -> (tên sản phẩm, tiền tố pipe, thư mục cài, tệp chạy)
    "litebim": ("LiteBIM", "litebim-mcp-", "LiteBIM", "LiteBIM.exe"),
    "litecad": ("LiteCAD", "litecad-mcp-", "LiteCAD", "LiteCAD.exe"),
}
PIPE_ENV = "g_MCP_PIPE"  # LiteBIM cho phép đổi tên pipe bằng biến này
PROTOCOL = "2025-06-18"
READ_TIMEOUT = 120  # run_script tối đa 30 giây; view và danh sách lớn cần thêm thời gian


def not_open(title):
    return (f"{title} chưa mở hoặc MCP của nó đang tắt: mở {title} rồi bật MCP "
            f"(Tùy chọn > AI, hoặc lệnh MCP, rồi chọn On). Công cụ sẽ dùng được ngay khi {title} sẵn sàng.")


NOT_OPEN = not_open("LiteBIM")  # giữ cho mã và test cũ


class LiteBimUnavailable(RuntimeError):
    """Không nối được pipe của LiteBIM (chưa mở, MCP tắt, hoặc đang bận)."""


# ---- Windows named pipe (ctypes, đọc bằng PeekNamedPipe nên không bị chặn) ----

def _pipe_dir():
    return "\\\\.\\pipe\\"


def pipe_candidates(prefix=PIPE_PREFIX):
    """Tên pipe có thể dùng, ưu tiên biến môi trường, rồi pipe của người dùng hiện tại, rồi mọi pipe cùng tiền tố."""
    names = []
    override = os.environ.get(PIPE_ENV)
    if override and override.replace("\\", "/").rsplit("/", 1)[-1].lower().startswith(prefix):  # biến chung cho cả hai app
        names.append(override if override.startswith("\\\\") else _pipe_dir() + override)
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if user:
        names.append(_pipe_dir() + prefix + user)
    try:
        for item in os.listdir(_pipe_dir()):
            if item.lower().startswith(prefix):
                names.append(_pipe_dir() + item)
    except OSError:
        pass
    seen, ordered = set(), []
    for name in names:
        if name.lower() not in seen:
            seen.add(name.lower())
            ordered.append(name)
    return ordered


def pipe_present(prefix=PIPE_PREFIX):
    """Ứng dụng đang mở và bật MCP (pipe của nó có mặt), chưa cần nối."""
    try:
        return any(item.lower().startswith(prefix) for item in os.listdir(_pipe_dir()))
    except OSError:
        return False


def installed(product="litebim"):
    """Sản phẩm có cài trên máy này không (dùng để quyết định có thêm MCP này vào agent)."""
    _, _, folder, exe = PRODUCTS[product]
    roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432"), os.environ.get("LOCALAPPDATA")]
    for root in roots:
        if root and os.path.isfile(os.path.join(root, folder, exe)):
            return True
        if root and os.path.isfile(os.path.join(root, "Programs", folder, exe)):
            return True
    return False


class WinPipe:
    """Một kết nối tới pipe; đọc theo dòng có hạn chờ."""

    def __init__(self, path):
        if sys.platform != "win32":
            raise LiteBimUnavailable("Chỉ chạy trên Windows.")
        from ctypes import wintypes
        self._k32 = kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                    wintypes.LPVOID]
        kernel.WriteFile.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                     wintypes.LPVOID]
        kernel.PeekNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID,
                                         ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._wt = wintypes
        handle = kernel.CreateFileW(path, 0xC0000000, 0, None, 3, 0, None)  # đọc+ghi, OPEN_EXISTING
        if handle in (None, wintypes.HANDLE(-1).value):
            code = ctypes.get_last_error()
            raise LiteBimUnavailable(f"không mở được pipe (mã Windows {code})")
        self._handle = handle
        self._buffer = b""

    def write_line(self, text):
        data = text.encode("utf-8") + b"\n"
        view = (ctypes.c_char * len(data)).from_buffer_copy(data)
        written = self._wt.DWORD(0)
        total = 0
        while total < len(data):
            ok = self._k32.WriteFile(self._handle, ctypes.byref(view, total), len(data) - total, ctypes.byref(written), None)
            if not ok:
                raise ConnectionError(f"ghi pipe lỗi (mã Windows {ctypes.get_last_error()})")
            total += written.value

    def read_line(self, timeout):
        deadline = time.monotonic() + timeout
        while True:
            cut = self._buffer.find(b"\n")
            if cut >= 0:
                line, self._buffer = self._buffer[:cut], self._buffer[cut + 1:]
                return line.decode("utf-8", "replace")
            available = self._wt.DWORD(0)
            if not self._k32.PeekNamedPipe(self._handle, None, 0, None, ctypes.byref(available), None):
                raise ConnectionError(f"pipe đã đóng (mã Windows {ctypes.get_last_error()})")
            if available.value:
                size = min(available.value, 1 << 20)
                chunk = ctypes.create_string_buffer(size)
                got = self._wt.DWORD(0)
                if not self._k32.ReadFile(self._handle, chunk, size, ctypes.byref(got), None):
                    raise ConnectionError(f"đọc pipe lỗi (mã Windows {ctypes.get_last_error()})")
                self._buffer += chunk.raw[:got.value]
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("LiteBIM không trả lời kịp")
            time.sleep(0.01)

    def close(self):
        handle, self._handle = self._handle, None
        if handle:
            self._k32.CloseHandle(handle)


def open_pipe(prefix=PIPE_PREFIX):
    last = "không thấy pipe của ứng dụng"
    for path in pipe_candidates(prefix):
        try:
            return WinPipe(path)
        except LiteBimUnavailable as exc:
            last = str(exc)
    raise LiteBimUnavailable(last)


def status(product, info):
    """(mức, mô tả ngắn) cho dòng dịch vụ ở tab Điều khiển. Mức: ok / busy / off."""
    info = info or {}
    if info.get("connected"):
        return "ok", "Đã nối qua gateway"
    if info.get("available"):
        return "ok", "Đang mở, MCP bật (nối khi agent gọi)"
    return "off", "Chưa mở hoặc MCP đang tắt"


def describe(product, info):
    """Dòng trạng thái ở tab Điều khiển."""
    title = PRODUCTS[product][0]
    info = info or {}
    if info.get("connected"):
        return f"●  {title}  ·  Đang nối qua gateway"
    if info.get("available"):
        return f"●  {title}  ·  Đang mở, MCP bật (nối khi agent gọi)"
    return f"○  {title}  ·  Chưa mở hoặc MCP đang tắt (Tùy chọn > AI > MCP: On)"


# ---- cầu nối ---------------------------------------------------------------

class LiteBimBridge:
    """Chuyển thông điệp MCP từ HTTP xuống pipe của LiteBIM, tuần tự, tự nối lại khi LiteBIM mở lại."""

    def __init__(self, connect=None, timeout=READ_TIMEOUT, product="litebim"):
        self.product = product
        self.title, self.prefix = PRODUCTS[product][0], PRODUCTS[product][1]
        self._connect = connect or (lambda: open_pipe(self.prefix))
        self._timeout = timeout
        self._lock = threading.Lock()
        self._ids = itertools.count(1)
        self._pipe = None
        self._hello = None  # kết quả initialize của LiteBIM lần nối gần nhất
        self.error = None

    # -- kết nối --
    def _drop(self):
        pipe, self._pipe = self._pipe, None
        if pipe:
            try:
                pipe.close()
            except Exception:
                pass

    def _exchange(self, pipe, message):
        """Gửi một yêu cầu rồi đọc tới khi có phản hồi cùng id (bỏ qua thông báo LiteBIM tự gửi)."""
        wanted = message["id"]
        pipe.write_line(json.dumps(message, ensure_ascii=False))
        deadline = time.monotonic() + self._timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("LiteBIM không trả lời kịp")
            line = pipe.read_line(remaining)
            if not line.strip():
                continue
            try:
                reply = json.loads(line)
            except ValueError:
                continue
            if isinstance(reply, dict) and reply.get("id") == wanted and ("result" in reply or "error" in reply):
                return reply

    def _ensure(self):
        if self._pipe is not None:
            return
        try:
            pipe = self._connect()
        except LiteBimUnavailable:
            raise
        except OSError as exc:
            raise LiteBimUnavailable(str(exc)) from exc
        try:
            reply = self._exchange(pipe, {"jsonrpc": "2.0", "id": next(self._ids), "method": "initialize",
                                          "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                                                     "clientInfo": {"name": "autocad-mcp-launcher", "version": "1"}}})
            pipe.write_line(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        except (OSError, TimeoutError, ConnectionError) as exc:
            try:
                pipe.close()
            except Exception:
                pass
            raise LiteBimUnavailable(f"{self.title} không trả lời lệnh khởi tạo: {exc}") from exc
        self._pipe = pipe
        self._hello = reply.get("result") or {}
        self.error = None

    # -- trạng thái --
    def status(self):
        return {"installed": installed(self.product), "available": pipe_present(self.prefix),
                "connected": self._pipe is not None, "error": self.error}

    # -- xử lý một thông điệp (chạy trong luồng riêng, xem handle_async) --
    def handle(self, message):
        """Trả về thông điệp phản hồi (dict) hoặc None nếu là thông báo không cần phản hồi."""
        method = message.get("method")
        request_id = message.get("id")
        if request_id is None:
            return None  # thông báo từ client (initialized, cancelled...): LiteBIM đã được khởi tạo bởi cầu nối
        with self._lock:
            return self._handle_locked(message, method, request_id)

    def _handle_locked(self, message, method, request_id):
        for attempt in (1, 2):
            try:
                self._ensure()
            except LiteBimUnavailable as exc:
                self.error = str(exc)
                return self._offline(method, request_id)
            if method == "initialize":
                return self._initialize_reply(message, request_id)
            forwarded = dict(message)
            forwarded["id"] = next(self._ids)
            try:
                reply = self._exchange(self._pipe, forwarded)
            except TimeoutError:
                self._drop()  # lệnh có thể còn chạy trong LiteBIM; không gửi lại, nối lại ở lần sau
                self.error = f"{self.title} không trả lời kịp"
                return self._failure(method, request_id, f"{self.title} không trả lời kịp; lệnh có thể vẫn đang chạy trong {self.title}, "
                                                         "kiểm tra bản vẽ/mô hình trước khi gọi lại.")
            except (OSError, ConnectionError) as exc:
                self._drop()
                self.error = str(exc)
                if attempt == 1 and method != "tools/call":
                    continue  # kết nối cũ đã chết (LiteBIM mở lại): nối lại một lần
                return self._failure(method, request_id, f"Mất kết nối với {self.title} ({exc}); gọi lại sau khi {self.title} sẵn sàng.")
            reply["id"] = request_id
            return reply
        return self._offline(method, request_id)

    def _initialize_reply(self, message, request_id):
        hello = dict(self._hello or {})
        hello["protocolVersion"] = (message.get("params") or {}).get("protocolVersion") or hello.get("protocolVersion") or PROTOCOL
        return {"jsonrpc": "2.0", "id": request_id, "result": hello}

    def _offline(self, method, request_id):
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": self.product, "title": self.title, "version": "launcher"},
                "instructions": not_open(self.title)}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": []}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method in ("resources/list", "prompts/list"):
            return {"jsonrpc": "2.0", "id": request_id, "result": {method.split("/")[0]: []}}
        return self._failure(method, request_id, not_open(self.title))

    @staticmethod
    def _failure(method, request_id, text):
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": text}], "isError": True}}
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": text}}

    def close(self):
        with self._lock:
            self._drop()
