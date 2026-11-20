"""Chế độ agent: launcher chủ động kết nối ra server, server gọi MCP của máy này qua kết nối đó.

Máy local thường nằm sau NAT và MCP không có xác thực, nên không mở cổng nào. Launcher là client đi ra
(WebSocket, wss://) và chuyển lời gọi HTTP của server vào gateway nội bộ http://127.0.0.1:8764.
Tắt mặc định; không cấu hình hoặc đang tắt thì gateway chạy y như cũ.

Giao thức (HTTP-over-WebSocket, khung văn bản JSON):
  agent -> server  {"type":"hello","machine_id","launcher_version","active","mode","servers":[...]}
  server -> agent  {"type":"request","id","method","path","headers","body_b64"}
  agent -> server  {"type":"response_start","id","status","headers"} + {"type":"response_chunk","id","data_b64"}*
                   + {"type":"response_end","id"}      hoặc  {"type":"error","id","code","message"}
  server -> agent  {"type":"cancel","id"}  = BỎ KẾT QUẢ; lệnh CAD đang chạy vẫn chạy tới hết (không dừng được AutoCAD)

Token là bí mật: không ghi vào log, không nằm trong trạng thái trả ra ngoài.
"""
import asyncio
import base64
import binascii
import json
import logging
import os
import random
import re
import subprocess
import time
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlsplit

LOCAL_BASE = "http://127.0.0.1:8764"
PATH_RE = re.compile(r"^/(beiming|puran|dutoan|litebim|litecad)/mcp$")
METHODS = frozenset({"GET", "POST", "DELETE"})
# Chỉ các header MCP cần thiết; không chuyển `authorization` của server xuống gateway nội bộ.
REQUEST_HEADERS = ("content-type", "accept", "mcp-session-id", "mcp-protocol-version", "last-event-id")
RESPONSE_HEADERS = ("content-type", "mcp-session-id", "cache-control")
DEFAULT_BLOCKED_TOOLS = ("launcher_set_backend",)  # đổi backend của cả máy; không cho remote mặc định
MAX_REQUEST_BODY = 4 * 1024 * 1024
MAX_CONCURRENT = 4
CHUNK_BYTES = 192 * 1024
MAX_FRAME_BYTES = 16 * 1024 * 1024
PING_SECONDS = 20
BACKOFF = (1, 2, 4, 8, 15, 30, 60)
IDLE_SECONDS = 3.0
AUTH_HTTP = (401, 403)
AUTH_CLOSE = (1008, 4401, 4403)
INLINE_IMAGE_DEFAULT = 2 * 1024 * 1024
ENV_ALLOW_WS = "AUTOCAD_MCP_REMOTE_ALLOW_WS"
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")

log = logging.getLogger("remote_agent")


# ---- cấu hình ------------------------------------------------------------

@dataclass(frozen=True)
class Config:
    enabled: bool
    url: str
    machine_id: str
    token: str
    blocked: frozenset
    problem: str = ""

    def signature(self):
        return (self.enabled, self.url, self.machine_id, self.token, self.blocked)

    @property
    def host(self):
        return urlsplit(self.url).hostname or ""


def _blocked_from(settings):
    raw = settings.get("remote_blocked_tools")
    if raw is None:
        return frozenset(DEFAULT_BLOCKED_TOOLS)
    if isinstance(raw, str):
        raw = raw.split(",")
    return frozenset(str(name).strip() for name in raw if str(name).strip())


def read_config(settings, env=None):
    """Đọc và kiểm cấu hình từ settings.json. `problem` khác rỗng khi đang bật mà cấu hình chưa dùng được."""
    settings = settings if isinstance(settings, dict) else {}
    env = os.environ if env is None else env
    enabled = settings.get("remote_agent_enabled") is True
    url = str(settings.get("remote_server_url") or "").strip()
    machine_id = str(settings.get("remote_machine_id") or "").strip()
    token = str(settings.get("remote_machine_token") or "").strip()
    cfg = dict(enabled=enabled, url=url, machine_id=machine_id, token=token, blocked=_blocked_from(settings))
    if not enabled:
        return Config(**cfg)
    parts = urlsplit(url)
    if not url:
        return Config(**cfg, problem="Chưa nhập địa chỉ server.")
    if parts.scheme == "ws":
        allowed = str(env.get(ENV_ALLOW_WS, "")).strip().lower() in ("1", "true", "yes", "on")
        if not (allowed and (parts.hostname or "") in LOCAL_HOSTS):
            return Config(**cfg, problem="Chỉ chấp nhận wss://. ws:// chỉ dùng để thử với localhost và phải bật cờ "
                                         f"{ENV_ALLOW_WS}=1.")
    elif parts.scheme != "wss":
        return Config(**cfg, problem="Địa chỉ server phải bắt đầu bằng wss://.")
    if not parts.hostname:
        return Config(**cfg, problem="Địa chỉ server thiếu tên máy chủ.")
    if not machine_id:
        return Config(**cfg, problem="Chưa nhập mã máy.")
    if not token:
        return Config(**cfg, problem="Chưa nhập token.")
    return Config(**cfg)


def inline_image_env(settings):
    """Biến môi trường cho Beiming để `view get_screenshot` (include_image=true) trả ảnh trực tiếp.

    Chỉ khi chế độ agent đang bật, vì khi server ở máy khác thì đường dẫn ảnh trên máy này vô dụng.
    Agent local không đổi: ảnh vẫn chỉ kèm theo khi lời gọi xin `include_image`."""
    settings = settings if isinstance(settings, dict) else {}
    if settings.get("remote_agent_enabled") is not True:
        return {}
    try:
        limit = int(settings.get("remote_inline_image_max_bytes") or INLINE_IMAGE_DEFAULT)
    except (TypeError, ValueError):
        limit = INLINE_IMAGE_DEFAULT
    limit = max(16384, min(limit, 8 * 1024 * 1024))
    return {"AUTOCAD_MCP_ALLOW_INLINE_IMAGES": "true", "AUTOCAD_MCP_MAX_INLINE_IMAGE_BYTES": str(limit)}


# ---- trạng thái (không chứa token) -----------------------------------------

class AgentState:
    def __init__(self):
        self.status = "off"
        self.detail = ""
        self.since = time.time()
        self.machine_id = ""
        self.host = ""

    def set(self, status, detail="", machine_id=None, host=None):
        if status != self.status:
            self.since = time.time()
        self.status, self.detail = status, detail
        if machine_id is not None:
            self.machine_id = machine_id
        if host is not None:
            self.host = host

    def snapshot(self):
        return {"status": self.status, "detail": self.detail, "since": self.since,
                "machine_id": self.machine_id, "host": self.host}


STATE = AgentState()


def describe(snapshot):
    """Một câu ngắn cho giao diện; rỗng khi chế độ agent đang tắt."""
    snapshot = snapshot or {}
    status, host = snapshot.get("status", "off"), snapshot.get("host") or "server"
    detail = snapshot.get("detail") or ""
    return {
        "off": "",
        "connecting": f"đang nối tới {host}…",
        "connected": f"đã kết nối tới {host}",
        "retrying": f"mất kết nối, {detail}" if detail else "mất kết nối, đang nối lại",
        "auth_error": "server từ chối token; đổi token rồi lưu lại",
        "missing_lib": "chưa cài thư viện websockets",
        "config_error": detail or "cấu hình chưa dùng được",
        "error": detail or "lỗi không mong đợi",
    }.get(status, "")


def configure_logging(log_dir):
    """Ghi remote_agent.log (xoay vòng). Chỉ ghi tên máy chủ, mã yêu cầu, đường dẫn và mã trạng thái."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    if any(isinstance(h, RotatingFileHandler) for h in log.handlers):
        return
    handler = RotatingFileHandler(log_dir / "remote_agent.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


def restrict_to_owner(path, run=subprocess.run):
    """Cố gắng để chỉ chủ tài khoản đọc được tệp (có token). Hỏng thì trả lại quyền thừa kế, không để khóa mất tệp."""
    path = Path(path)
    user = os.environ.get("USERNAME", "")
    if not user or not path.is_file() or os.name != "nt":
        return False
    principal = f"{os.environ.get('USERDOMAIN', '')}\\{user}" if os.environ.get("USERDOMAIN") else user
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        done = run(["icacls", str(path), "/inheritance:r", "/grant:r", f"{principal}:(F)"],
                   capture_output=True, text=True, timeout=20, creationflags=flags)
        if done.returncode != 0:
            return False
        path.read_bytes()  # còn đọc được thì thôi
        return True
    except (OSError, subprocess.SubprocessError):
        try:
            run(["icacls", str(path), "/reset"], capture_output=True, text=True, timeout=20, creationflags=flags)
        except (OSError, subprocess.SubprocessError):
            pass
        return False


# ---- khung và lời gọi ----------------------------------------------------------

def error_frame(request_id, code, message):
    return {"type": "error", "id": request_id, "code": code, "message": message}


def find_blocked(body, blocked):
    """Các lời gọi tool bị chặn trong thân JSON-RPC (một thông điệp hoặc cả lô): [(id, tên tool)]."""
    if not blocked or not body:
        return []
    try:
        data = json.loads(body)
    except ValueError:
        return []
    messages = data if isinstance(data, list) else [data]
    found = []
    for message in messages:
        if isinstance(message, dict) and message.get("method") == "tools/call":
            params = message.get("params")
            if isinstance(params, dict) and params.get("name") in blocked:
                found.append((message.get("id"), params["name"]))
    return found


def blocked_result(request_id, tool):
    payload = {"ok": False, "code": "TOOL_BLOCKED",
               "error": f"Tool `{tool}` bị chặn với kết nối từ xa trên máy này (cấu hình của launcher)."}
    return {"jsonrpc": "2.0", "id": request_id, "result": {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": True}}


def _lower(headers):
    return {str(k).lower(): str(v) for k, v in (headers or {}).items()} if isinstance(headers, dict) else {}


class Connection:
    """Một kết nối WebSocket đang mở: nhận khung `request`/`cancel`, chuyển vào gateway nội bộ."""

    def __init__(self, ws, cfg, *, local_base=LOCAL_BASE, client=None):
        self.ws = ws
        self.cfg = cfg
        self.local_base = local_base.rstrip("/")
        self.client = client
        self.send_lock = asyncio.Lock()
        self.tasks = {}
        self.cancelled = set()

    async def send(self, frame):
        async with self.send_lock:
            await self.ws.send(json.dumps(frame, ensure_ascii=False, separators=(",", ":")))

    async def serve(self, hello):
        await self.send(hello)
        try:
            async for raw in self.ws:
                await self.on_message(raw)
        except Exception as exc:  # ConnectionClosed và lỗi giao thức: kết thúc phiên, vòng ngoài sẽ nối lại
            if type(exc).__name__ not in ("ConnectionClosed", "ConnectionClosedError", "ConnectionClosedOK"):
                log.warning("phiên kết thúc do %s", type(exc).__name__)
        finally:
            for task in list(self.tasks.values()):
                task.cancel()
            if self.tasks:
                await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        return getattr(self.ws, "close_code", None)

    async def on_message(self, raw):
        if not isinstance(raw, str):
            return  # chỉ nhận khung văn bản
        try:
            frame = json.loads(raw)
        except ValueError:
            return
        if not isinstance(frame, dict):
            return
        kind, request_id = frame.get("type"), frame.get("id")
        if kind == "cancel" and isinstance(request_id, str) and request_id in self.tasks:
            self.cancelled.add(request_id)
        elif kind == "request":
            if not isinstance(request_id, str) or not request_id or len(request_id) > 80:
                return
            if request_id in self.tasks:
                await self.send(error_frame(request_id, "DUPLICATE_ID", "Mã yêu cầu đang được xử lý."))
            elif len(self.tasks) >= MAX_CONCURRENT:
                await self.send(error_frame(request_id, "BUSY", f"Đang xử lý {MAX_CONCURRENT} lời gọi; thử lại sau."))
            else:
                task = asyncio.ensure_future(self.handle(frame))
                self.tasks[request_id] = task
                task.add_done_callback(lambda _t, rid=request_id: (self.tasks.pop(rid, None), self.cancelled.discard(rid)))

    async def respond(self, request_id, status, headers, body):
        await self.send({"type": "response_start", "id": request_id, "status": status, "headers": headers})
        for start in range(0, len(body), CHUNK_BYTES):
            data = base64.b64encode(body[start:start + CHUNK_BYTES]).decode("ascii")
            await self.send({"type": "response_chunk", "id": request_id, "data_b64": data})
        await self.send({"type": "response_end", "id": request_id})

    async def handle(self, frame):
        import httpx  # chỉ gateway có httpx; launcher GUI (Python hệ thống) chỉ cần các hàm cấu hình
        request_id = frame["id"]
        method = str(frame.get("method") or "").upper()
        path = frame.get("path")

        async def refuse(code, message):
            log.info("từ chối %s %s: %s", method, path, code)
            await self.send(error_frame(request_id, code, message))

        if method not in METHODS:
            return await refuse("METHOD_NOT_ALLOWED", "Chỉ chấp nhận GET, POST, DELETE.")
        if not isinstance(path, str) or not PATH_RE.match(path):
            return await refuse("FORBIDDEN_PATH", "Chỉ cho phép /beiming/mcp, /puran/mcp, /dutoan/mcp, /litebim/mcp, /litecad/mcp.")
        try:
            body = base64.b64decode(frame.get("body_b64") or "", validate=True)
        except (binascii.Error, ValueError, TypeError):
            return await refuse("BAD_REQUEST", "body_b64 không phải base64 hợp lệ.")
        if len(body) > MAX_REQUEST_BODY:
            return await refuse("TOO_LARGE", f"Thân yêu cầu vượt {MAX_REQUEST_BODY} byte.")
        blocked = find_blocked(body, self.cfg.blocked)
        if blocked:
            try:
                single = json.loads(body)
            except ValueError:
                single = None
            if isinstance(single, dict):
                request, tool = blocked[0]
                log.info("chặn tool %s (yêu cầu %s)", tool, request_id)
                payload = json.dumps(blocked_result(request, tool), ensure_ascii=False).encode("utf-8")
                return await self.respond(request_id, 200, {"content-type": "application/json"}, payload)
            return await refuse("TOOL_BLOCKED", "Lô JSON-RPC có tool bị chặn với kết nối từ xa.")
        incoming = _lower(frame.get("headers"))
        headers = {name: incoming[name] for name in REQUEST_HEADERS if name in incoming}
        if request_id in self.cancelled:
            return  # bị hủy trước khi bắt đầu: không gọi gì cả
        started = time.time()
        try:
            response = await self.client.request(method, self.local_base + path, headers=headers, content=body)
        except httpx.ConnectError:
            return await refuse("LOCAL_UNAVAILABLE", "Gateway nội bộ không phản hồi.")
        except httpx.TimeoutException:
            return await refuse("LOCAL_TIMEOUT", "Gateway nội bộ không trả lời kịp.")
        except httpx.HTTPError as exc:
            return await refuse("LOCAL_ERROR", f"Lỗi gọi gateway nội bộ ({type(exc).__name__}).")
        if request_id in self.cancelled:
            log.info("bỏ kết quả của yêu cầu %s (cancel)", request_id)
            return
        outgoing = {k: v for k, v in _lower(dict(response.headers)).items() if k in RESPONSE_HEADERS}
        log.info("%s %s -> %s (%.1fs, %d byte)", method, path, response.status_code, time.time() - started,
                 len(response.content))
        await self.respond(request_id, response.status_code, outgoing, response.content)


# ---- vòng nối lại -----------------------------------------------------------------

def default_connect():
    try:
        from websockets.asyncio.client import connect
    except ImportError:
        return None
    return connect


def _status_code(exc):
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) or getattr(exc, "status_code", None)


async def _watch_config(read_settings, signature, ws, idle, env):
    while True:
        await asyncio.sleep(idle)
        if read_config(read_settings(), env).signature() != signature:
            await ws.close(1000, "cấu hình đã đổi")
            return


async def run_forever(read_settings, *, status_source=None, version="", local_base=LOCAL_BASE, connect=None,
                      backoff=BACKOFF, idle=IDLE_SECONDS, state=STATE, env=None, jitter=True):
    """Chạy suốt đời gateway. Không bao giờ ném lỗi ra ngoài (trừ hủy tác vụ)."""
    halted = None   # chữ ký cấu hình bị từ chối xác thực: không nối lại cho tới khi cấu hình đổi
    attempt = 0
    while True:
        try:
            cfg = read_config(read_settings(), env)
            if not cfg.enabled:
                state.set("off", "")
                attempt, halted = 0, None
                await asyncio.sleep(idle)
                continue
            if cfg.problem:
                state.set("config_error", cfg.problem, machine_id=cfg.machine_id)
                await asyncio.sleep(idle)
                continue
            if halted == cfg.signature():
                await asyncio.sleep(idle)
                continue
            connector = connect or default_connect()
            if connector is None:
                state.set("missing_lib", "Chưa cài thư viện websockets.", machine_id=cfg.machine_id, host=cfg.host)
                await asyncio.sleep(idle)
                continue
            state.set("connecting", "", machine_id=cfg.machine_id, host=cfg.host)
            log.info("kết nối tới %s (mã máy %s)", cfg.host, cfg.machine_id)
            try:
                async with connector(cfg.url, additional_headers={"Authorization": f"Bearer {cfg.token}"},
                                     max_size=MAX_FRAME_BYTES, ping_interval=PING_SECONDS, ping_timeout=PING_SECONDS,
                                     open_timeout=15) as ws:
                    attempt = 0
                    state.set("connected", "", machine_id=cfg.machine_id, host=cfg.host)
                    log.info("đã nối tới %s", cfg.host)
                    info = (await status_source()) if status_source else {}
                    hello = {"type": "hello", "machine_id": cfg.machine_id, "launcher_version": version,
                             "active": info.get("active"), "mode": info.get("mode"),
                             "servers": info.get("servers") or ["beiming", "puran", "dutoan"]}
                    watcher = asyncio.ensure_future(_watch_config(read_settings, cfg.signature(), ws, idle, env))
                    import httpx
                    timeout = httpx.Timeout(connect=10, read=1000, write=30, pool=10)
                    try:
                        async with httpx.AsyncClient(timeout=timeout) as client:
                            code = await Connection(ws, cfg, local_base=local_base, client=client).serve(hello)
                    finally:
                        watcher.cancel()
                        await asyncio.gather(watcher, return_exceptions=True)
                    log.info("kết nối đóng (mã %s)", code)
                    if code in AUTH_CLOSE:
                        halted = cfg.signature()
                        state.set("auth_error", "Server từ chối token. Đổi token rồi lưu lại.", machine_id=cfg.machine_id,
                                  host=cfg.host)
                        continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if _status_code(exc) in AUTH_HTTP:
                    halted = cfg.signature()
                    log.warning("server từ chối xác thực (HTTP %s)", _status_code(exc))
                    state.set("auth_error", "Server từ chối token. Đổi token rồi lưu lại.", machine_id=cfg.machine_id,
                              host=cfg.host)
                    continue
                log.warning("không nối được: %s", type(exc).__name__)
                reason = type(exc).__name__
            else:
                reason = "kết nối đã đóng"
            delay = backoff[min(attempt, len(backoff) - 1)]
            delay = delay * (0.75 + random.random() * 0.5) if jitter else delay
            attempt += 1
            state.set("retrying", f"{reason}; nối lại sau {delay:.0f}s", machine_id=cfg.machine_id, host=cfg.host)
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            state.set("off", "")
            raise
        except Exception as exc:  # không để tác vụ nền chết im lặng
            log.error("lỗi không mong đợi: %s", type(exc).__name__)
            state.set("error", f"Lỗi không mong đợi ({type(exc).__name__}).")
            await asyncio.sleep(max(idle, 1.0))
