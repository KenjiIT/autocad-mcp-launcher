"""Exclusive local MCP switchboard. Agent traffic selects the active checkout."""
import asyncio
import ctypes
import json
import os
import socket
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "launcher"))
import acad_pid
from logfile import RotatingLog, start_logged
import knowledge_propose
import knowledge_read
import litebim_bridge
import litebim_reference
import remote_agent
import skillgate
import skillserve
from cad_adapter import find_lt_window, prove_connection, prove_offline
SERVERS = {
    "puran": ("autocad_puran", ROOT / "puran-water-autocad-mcp", 8875),
    "beiming": ("autocad_beiming", ROOT / "autocad-beiming-mcp", 8876),
}
DUTOAN_DIR = ROOT / "du-toan-mcp"
DUTOAN_PORT = 8877
LOG_DIR = ROOT / "launcher" / "logs"
SKILLS_ROOT = ROOT / ".claude" / "skills"
HOP_HEADERS = {"connection", "transfer-encoding", "content-length", "host", "keep-alive", skillgate.HEADER}
gate = skillgate.SkillGate()


def gate_active():
    """Chặn khi đã bật VÀ skill điều phối có trên máy này (không có thì agent không mở khóa được)."""
    return (skillgate.enabled(knowledge_propose.load_settings())
            and (SKILLS_ROOT / skillgate.REQUIRED_SKILL / "SKILL.md").is_file())
TOOL_CACHE = {}
BACKEND_TOOL = {
    "name": "launcher_set_backend",
    "description": (
        "Chọn backend cho launcher. Mặc định là AutoCAD. Chỉ gọi mode=ezdxf sau khi "
        "đã hỏi người dùng và được đồng ý xuất DXF thay cho AutoCAD; DXF không phải DWG. "
        "Gọi mode=autocad để quay lại AutoCAD. Lưu DXF trước khi đổi MCP hoặc backend. "
        "Chỉ tạo DXF khi người dùng yêu cầu hoặc không có kết nối AutoCAD; AutoCAD đang kết nối thì không tự xuất DXF."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["autocad", "ezdxf"]},
            "user_confirmed": {"type": "boolean", "description": "True sau khi người dùng đồng ý dùng DXF."},
        },
        "required": ["mode"],
    },
}
SKILLS_TOOL = {
    "name": "skills",
    "description": (
        "Đọc bộ skill (quy trình, quy tắc) của dự án AutoCAD. BẮT BUỘC gọi trước khi gọi tool CAD: "
        "operation=get, name=autocad-agent-coordinator, rồi làm theo. operation=list liệt kê skill; "
        "operation=get với path đọc tệp tham chiếu của skill."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["list", "get"]},
            "name": {"type": "string", "description": "Tên skill, ví dụ autocad-agent-coordinator."},
            "path": {"type": "string", "description": "Tệp tham chiếu trong skill, ví dụ references/catalog.md."},
        },
        "required": ["operation"],
    },
    "annotations": {"readOnlyHint": True},
}


def skills_call(arguments):
    """Run the read-only `skills` tool; returns (payload, is_error)."""
    operation = arguments.get("operation")
    try:
        if operation == "list":
            return {"ok": True, "skills": skillserve.list_skills(SKILLS_ROOT)}, False
        if operation == "get":
            return {"ok": True, **skillserve.read_skill(SKILLS_ROOT, arguments.get("name"), arguments.get("path"))}, False
    except (ValueError, OSError) as exc:
        return {"ok": False, "error": str(exc)}, True
    return {"ok": False, "error": "operation phải là list hoặc get"}, True


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def cad_window_alive(hwnd):
    return bool(hwnd and ctypes.windll.user32.IsWindow(int(hwnd)))


def autocad_available():
    if find_lt_window():
        return True
    try:
        from autocad_mcp.backends.file_ipc import find_autocad_window
        if find_autocad_window():
            return True
    except (ImportError, OSError):
        pass
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            win32com.client.GetActiveObject("AutoCAD.Application")
            return True
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return False


class AutoCADUnavailable(RuntimeError):
    pass


def kill_tree(process):
    if process is None or process.poll() is not None:
        return
    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


class Switchboard:
    def __init__(self, mode="autocad"):
        self.lock = asyncio.Lock()
        # One AutoCAD-facing MCP process is active at a time. Queue tool calls
        # so several agents can submit work without overlapping CAD commands.
        self.request_lock = asyncio.Lock()
        self.queued_requests = 0
        self.active_request = None
        self.idle = asyncio.Event()
        self.idle.set()
        self.inflight = 0
        self.mode = mode
        self.active = None
        self.active_hwnd = None
        self.acad_pid = None
        self.process = None
        self.log = None
        self.state = "Gateway sẵn sàng; agent sẽ thử AutoCAD khi gọi tool"
        self.error = None

    async def select(self, key):
        async with self.lock:
            if (self.active == key and self.process and self.process.poll() is None
                    and (self.mode == "ezdxf" or cad_window_alive(self.active_hwnd))):
                return
            # Wait until in-flight CAD work finishes before stopping its server.
            await self.idle.wait()
            # Pin every AutoCAD lookup to the process this session used before.
            self.acad_pid = acad_pid.apply()
            if self.mode == "autocad" and not await asyncio.to_thread(autocad_available):
                self.error = "AutoCAD hiện không chạy hoặc chưa mở bản vẽ. Hãy hỏi người dùng có muốn xuất DXF thay thế không."
                self.state = "Đang chờ AutoCAD hoặc quyết định của người dùng"
                raise AutoCADUnavailable(self.error)
            if self.process:
                self.state = f"Đang ngắt {self.active}"
                await asyncio.to_thread(kill_tree, self.process)
                self.process = None
                self.active = None
                self.active_hwnd = None
                if self.log:
                    self.log.close()
                    self.log = None
            name, repo, port = SERVERS[key]
            self.state = (f"Đang mở {name} ở chế độ DXF offline" if self.mode == "ezdxf"
                          else f"Đang kết nối {name} với AutoCAD")
            self.error = None
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            python = repo / ".venv" / "Scripts" / "python.exe"
            if not python.is_file():
                raise RuntimeError(f"Thiếu môi trường Python: {python}. Mở app để cài thư viện.")
            if listening(port):
                raise RuntimeError(f"Cổng nội bộ {port} đã được sử dụng")
            self.log = RotatingLog(LOG_DIR / f"{name}.log")
            env = os.environ.copy()
            env["AUTOCAD_MCP_BACKEND"] = "ezdxf" if self.mode == "ezdxf" else "file_ipc"
            env["AUTOCAD_MCP_AUTOSTART"] = "false"
            if self.mode == "ezdxf":
                # Honor an explicit DXF path supplied by the agent or user.
                env["AUTOCAD_MCP_ALLOW_EXTERNAL_OUTPUTS"] = "true"
            if key == "beiming":
                env["AUTOCAD_MCP_OUTPUT_ROOT"] = str(repo / "output")
                env["AUTOCAD_MCP_LISP_PATH"] = str(repo / "lisp-code" / "mcp_dispatch.lsp")
                # Keep Beiming on COM/file IPC; its native worker can contend with COM.
                env["AUTOCAD_MCP_NATIVE_PLUGIN"] = "off"
                env["AUTOCAD_MCP_READ_TIMEOUT"] = "600"
                env["AUTOCAD_MCP_IPC_TIMEOUT"] = "300"
                env["AUTOCAD_MCP_DOCUMENT_TIMEOUT"] = "120"
                # Chế độ agent từ xa: cho view get_screenshot (include_image=true) trả ảnh trực tiếp; tắt thì không đổi.
                env.update(remote_agent.inline_image_env(knowledge_propose.load_settings()))
            self.process = start_logged(
                [str(python), str(ROOT / "launcher" / "serve.py"), str(repo), str(port)],
                self.log, cwd=repo, env=env)
            try:
                for _ in range(150):
                    if self.process.poll() is not None:
                        raise RuntimeError(f"{name} thoát khi khởi động; xem launcher/logs/{name}.log")
                    if listening(port):
                        break
                    await asyncio.sleep(0.1)
                else:
                    raise RuntimeError(f"{name} chưa mở cổng nội bộ {port}")
                if self.mode == "ezdxf":
                    payload = await prove_offline(port)
                    self.active_hwnd = None
                else:
                    payload = await prove_connection(name, repo, port)
                    self.active_hwnd = (payload.get("hwnd")
                                        or (payload.get("autocad") or {}).get("hwnd")
                                        or (payload.get("worker") or {}).get("hwnd"))
                    connected = (payload.get("process_id")
                                 or (payload.get("autocad") or {}).get("process_id"))
                    if connected:
                        acad_pid.save(connected, (payload.get("autocad") or {}).get("active_document"))
                        self.acad_pid = connected
                self.active = key
                self.state = (f"{name} đang làm việc với DXF offline" if self.mode == "ezdxf"
                              else f"Đã kết nối AutoCAD qua {name}")
            except Exception as exc:
                self.error = str(exc)
                self.state = f"Không thể mở {name}"
                await asyncio.to_thread(kill_tree, self.process)
                self.process = None
                self.active_hwnd = None
                if self.log:
                    self.log.close()
                    self.log = None
                raise

    async def set_mode(self, mode, user_confirmed=False):
        if mode not in ("autocad", "ezdxf"):
            raise ValueError("Backend phải là autocad hoặc ezdxf")
        if mode == "ezdxf" and user_confirmed is not True:
            raise ValueError("Cần hỏi và nhận đồng ý của người dùng trước khi chuyển sang DXF")
        async with self.lock:
            if self.mode == mode:
                return
            await self.idle.wait()
            await asyncio.to_thread(kill_tree, self.process)
            self.process = None
            self.active = None
            self.active_hwnd = None
            if self.log:
                self.log.close()
                self.log = None
            self.mode = mode
            self.error = None
            self.state = ("Đã chọn DXF offline" if mode == "ezdxf"
                          else "Đã chọn AutoCAD; đang chờ agent gọi tool")

    async def forward(self, key, request, read_timeout=720):
        # Hold the state lock only while validating the selected server. Long
        # CAD requests must not block gateway status and protocol traffic.
        async with self.lock:
            if (self.active != key or not self.process
                    or self.process.poll() is not None):
                return JSONResponse({"error": "MCP backend is changing; retry shortly"}, status_code=503)
            _, _, port = SERVERS[key]
            headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
            self.inflight += 1
            self.idle.clear()
        try:
            timeout = httpx.Timeout(connect=10, read=read_timeout, write=30, pool=10)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    request.method, f"http://127.0.0.1:{port}/mcp",
                    headers=headers, content=await request.body())
            outbound = {k: v for k, v in response.headers.items()
                        if k.lower() not in HOP_HEADERS}
            return Response(response.content, status_code=response.status_code, headers=outbound)
        except Exception as exc:
            self.error = str(exc)
            return JSONResponse({"error": str(exc)}, status_code=502)
        finally:
            # select() may hold self.lock while waiting for this call to finish.
            self.inflight = max(0, self.inflight - 1)
            if self.inflight == 0:
                self.idle.set()

    async def shutdown(self):
        async with self.lock:
            await asyncio.to_thread(kill_tree, self.process)
            self.process = None
            self.active = None
            self.active_hwnd = None
            if self.log:
                self.log.close()
                self.log = None

    @asynccontextmanager
    async def request_slot(self, key, tool_name):
        self.queued_requests += 1
        try:
            await self.request_lock.acquire()
        finally:
            self.queued_requests = max(0, self.queued_requests - 1)
        self.active_request = {"backend": key, "tool": tool_name}
        try:
            yield
        finally:
            self.active_request = None
            self.request_lock.release()


board = Switchboard()


class DutoanService:
    """The estimating MCP. It never touches AutoCAD, so it bypasses the switchboard.

    One process serves every agent; it starts on the first call and can be stopped
    (``/dutoan/stop``) so the launcher can replace dutoan.db while nobody holds it.
    """

    def __init__(self, repo=DUTOAN_DIR, port=DUTOAN_PORT):
        self.repo = repo
        self.port = port
        self.lock = asyncio.Lock()
        self.process = None
        self.log = None
        self.error = None

    def python(self):
        return self.repo / ".venv" / "Scripts" / "python.exe"

    def available(self):
        return (self.repo / "src" / "dutoan_mcp" / "server.py").is_file() and self.python().is_file()

    def running(self):
        return bool(self.process and self.process.poll() is None)

    async def ensure(self):
        async with self.lock:
            if self.running() and listening(self.port):
                return
            await self._stop_locked()
            if not self.available():
                raise RuntimeError(f"Thiếu môi trường Python của dutoan: {self.python()}. Mở app để cài thư viện.")
            if listening(self.port):
                raise RuntimeError(f"Cổng nội bộ {self.port} đã được sử dụng")
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            self.log = RotatingLog(LOG_DIR / "dutoan.log")
            self.process = start_logged(
                [str(self.python()), str(ROOT / "launcher" / "serve_dutoan.py"), str(self.repo), str(self.port)],
                self.log, cwd=self.repo, env=os.environ.copy())
            for _ in range(300):
                if self.process.poll() is not None:
                    await self._stop_locked()
                    raise RuntimeError("dutoan thoát khi khởi động; xem launcher/logs/dutoan.log")
                if listening(self.port):
                    self.error = None
                    return
                await asyncio.sleep(0.1)
            await self._stop_locked()
            raise RuntimeError(f"dutoan chưa mở cổng nội bộ {self.port}")

    async def proxy(self, request):
        # No standalone event stream: the server is stateless, and a GET would hang.
        if request.method == "GET":
            return Response(status_code=405)
        if request.method == "DELETE":
            return Response(status_code=200)
        try:
            await self.ensure()
        except Exception as exc:
            self.error = str(exc)
            return JSONResponse({"error": str(exc)}, status_code=503)
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
        try:
            timeout = httpx.Timeout(connect=10, read=120, write=30, pool=10)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    request.method, f"http://127.0.0.1:{self.port}/mcp",
                    headers=headers, content=await request.body())
            outbound = {k: v for k, v in response.headers.items() if k.lower() not in HOP_HEADERS}
            return Response(response.content, status_code=response.status_code, headers=outbound)
        except Exception as exc:
            self.error = str(exc)
            return JSONResponse({"error": str(exc)}, status_code=502)

    async def _stop_locked(self):
        if self.process:
            await asyncio.to_thread(kill_tree, self.process)
        self.process = None
        if self.log:
            self.log.close()
            self.log = None

    async def stop(self):
        async with self.lock:
            await self._stop_locked()

    def status(self):
        return {"available": self.available(), "running": self.running(), "error": self.error}


dutoan = DutoanService()
litebim = litebim_bridge.LiteBimBridge(product="litebim")
litecad = litebim_bridge.LiteBimBridge(product="litecad")
PIPE_BRIDGES = {"litebim": lambda: litebim, "litecad": lambda: litecad}  # tra lúc gọi để test thay được


PIPE_SKILLS_NOTE = (
    "Dự án có bộ skill nghiệp vụ dùng chung (thiết kế nhà ở, mặt bằng chung cư, hồ sơ và tiêu chuẩn xây dựng, "
    "tra định mức, tri thức chung). Trước khi dựng, sửa hay đo mô hình: gọi tool `skills` với operation=list, chọn mọi "
    "skill khớp yêu cầu rồi nạp từng skill bằng operation=get (tệp tham chiếu: operation=get, name, path) và làm theo "
    "phần nghiệp vụ. Skill tên autocad-* viết cho AutoCAD: vẫn dùng quy tắc nghiệp vụ trong đó, còn bước gọi tool CAD "
    "thì thay bằng tool của ứng dụng này."
)
PIPE_SKILLS_TOOL = {**SKILLS_TOOL, "description": (
    "Đọc bộ skill (quy trình, quy tắc nghiệp vụ) của dự án. Gọi trước khi dựng hoặc sửa mô hình: operation=list "
    "liệt kê skill, operation=get với name nạp một skill, thêm path để đọc tệp tham chiếu của skill."
)}


def pipe_with_skills(bridge, item):
    """LiteBIM/LiteCAD đi thẳng qua pipe, nhưng vẫn có tool `skills` và lời dặn đọc skill như hai MCP AutoCAD."""
    method = item.get("method")
    if method == "tools/call" and (item.get("params") or {}).get("name") == "skills":
        payload, is_error = skills_call((item.get("params") or {}).get("arguments") or {})
        return {"jsonrpc": "2.0", "id": item.get("id"), "result": {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": is_error}}
    reply = bridge.handle(item)
    result = reply.get("result") if isinstance(reply, dict) else None
    remember_reference(bridge, item, result)
    if method == "initialize" and isinstance(result, dict):
        result["instructions"] = (str(result.get("instructions") or "") + "\n\n" + PIPE_SKILLS_NOTE).strip()
    elif method == "tools/list" and isinstance(result, dict) and isinstance(result.get("tools"), list):
        if not any(t.get("name") == "skills" for t in result["tools"] if isinstance(t, dict)):
            result["tools"] = [*result["tools"], PIPE_SKILLS_TOOL]
    return reply


def remember_reference(bridge, item, result):
    """Giữ tài liệu get_reference trong launcher/state/<sản phẩm>/reference/ (xem litebim_reference.py)."""
    try:
        method, params = item.get("method"), item.get("params") or {}
        if method == "tools/call" and params.get("name") == litebim_reference.TOOL and not params.get("arguments"):
            text = litebim_reference._text_of(result)
            version = str(((bridge._hello or {}).get("serverInfo") or {}).get("version") or "")
            if text and version:
                litebim_reference.store(bridge.product, bridge.title, version, text)
        elif method == "initialize" and isinstance(result, dict):
            version = str((result.get("serverInfo") or {}).get("version") or "")
            meta = litebim_reference.read_meta(bridge.product)
            if version and version != "launcher" and (not meta or meta.get("version") != version):
                litebim_reference.refresh_async(bridge)   # LiteBIM mới mở hoặc đổi phiên bản
    except Exception as exc:  # không để việc ghi bộ đệm làm hỏng lệnh của agent
        print(f"reference cache: {exc}", file=sys.stderr)


async def reference_route(request: Request):
    """GET: tài liệu API đã lưu (markdown) của litebim/litecad; ?info=1 trả đường dẫn/phiên bản. POST .../refresh: lấy lại."""
    key = request.path_params["key"]
    if key not in PIPE_BRIDGES:
        return JSONResponse({"error": "Unknown product"}, status_code=404)
    if request.method == "POST":
        result = await asyncio.to_thread(litebim_reference.refresh, PIPE_BRIDGES[key](), True)
        return JSONResponse({**result, **litebim_reference.info(key)}, status_code=200 if result.get("state") in ("updated", "current") else 409)
    data = litebim_reference.info(key)
    if request.query_params.get("info") or not data["available"]:
        return JSONResponse(data, status_code=200 if data["available"] else 404)
    path = Path(data["path"])
    return Response(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8",
                    headers={"X-Reference-Version": str(data.get("version") or "")})


async def litebim_route(request: Request, bridge=None):
    """MCP của LiteBIM hoặc LiteCAD qua pipe của chúng. Không dùng AutoCAD và không qua cổng chặn skill."""
    if request.method == "GET":
        return Response(status_code=405)
    if request.method == "DELETE":
        return Response(status_code=200)
    try:
        message = await request.json()
    except ValueError:
        return JSONResponse({"error": "Invalid JSON-RPC request"}, status_code=400)
    batch = message if isinstance(message, list) else [message]
    if not all(isinstance(item, dict) for item in batch):
        return JSONResponse({"error": "Invalid JSON-RPC request"}, status_code=400)
    target = bridge or litebim
    replies = [reply for reply in [await asyncio.to_thread(pipe_with_skills, target, item) for item in batch] if reply is not None]
    if not replies:
        return Response(status_code=202)
    return JSONResponse(replies if isinstance(message, list) else replies[0])




async def tool_schema(key):
    if key in TOOL_CACHE:
        return TOOL_CACHE[key]
    _, repo, _ = SERVERS[key]
    python = repo / ".venv" / "Scripts" / "python.exe"
    code = (
        "import asyncio,json,sys; "
        f"sys.path.insert(0, {str(ROOT / 'launcher')!r}); "
        "from autocad_mcp.server import mcp; "
    )
    code += (
        "print(json.dumps([t.model_dump(by_alias=True,exclude_none=True) "
        "for t in asyncio.run(mcp.list_tools())]))"
    )
    result = await asyncio.to_thread(
        subprocess.run, [str(python), "-c", code], cwd=repo,
        capture_output=True, text=True, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(f"Không đọc được danh sách công cụ {key}: {result.stderr[-500:]}")
    TOOL_CACHE[key] = [*json.loads(result.stdout), BACKEND_TOOL, SKILLS_TOOL, knowledge_read.TOOL, knowledge_propose.TOOL]
    return TOOL_CACHE[key]


def rpc_result(request_id, result):
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


def rpc_tool_result(request_id, payload, is_error=False):
    return rpc_result(request_id, {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
        "isError": is_error,
    })


async def mcp_route(request: Request):
    key = request.path_params["key"]
    if key not in SERVERS:
        return JSONResponse({"error": "Unknown MCP"}, status_code=404)
    if request.method == "GET":
        return Response(status_code=405)
    if request.method == "DELETE":
        gate.end_session(request.headers.get(skillgate.HEADER))
        return Response(status_code=200)
    try:
        message = await request.json()
    except ValueError:
        return JSONResponse({"error": "Invalid JSON-RPC request"}, status_code=400)
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        requested = message.get("params", {}).get("protocolVersion", "2025-03-26")
        gated = gate_active()
        skill_text = skillserve.INSTRUCTIONS + (" " + skillgate.NOTE if gated else "")
        response = rpc_result(request_id, {
            "protocolVersion": requested,
            "capabilities": {"tools": {"listChanged": False}, "prompts": {"listChanged": False}},
            "serverInfo": {"name": SERVERS[key][0], "version": "1.0.0"},
            "instructions": skill_text + chr(10) * 2 + knowledge_read.INSTRUCTIONS,
        })
        if gated:
            # Mã phiên để biết phiên nào đã đọc skill điều phối (xem skillgate.py).
            response.headers["Mcp-Session-Id"] = gate.new_session()
        return response
    if method == "notifications/initialized":
        return Response(status_code=202)
    if method == "ping":
        return rpc_result(request_id, {})
    if method == "tools/list":
        try:
            return rpc_result(request_id, {"tools": await tool_schema(key)})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)
    if method == "prompts/list":
        return rpc_result(request_id, {"prompts": [
            {"name": item["name"], "description": item["description"]}
            for item in skillserve.list_skills(SKILLS_ROOT)]})
    if method == "prompts/get":
        name = (message.get("params") or {}).get("name")
        try:
            skill = skillserve.read_skill(SKILLS_ROOT, name)
        except (ValueError, OSError) as exc:
            return JSONResponse({"jsonrpc": "2.0", "id": request_id,
                                 "error": {"code": -32602, "message": str(exc)}})
        return rpc_result(request_id, {"description": name, "messages": [
            {"role": "user", "content": {"type": "text", "text": skill["content"]}}]})
    if method == "resources/list":
        return rpc_result(request_id, {"resources": []})
    if method != "tools/call":
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id,
             "error": {"code": -32601, "message": f"Unsupported method: {method}"}},
            status_code=200)
    params = message.get("params") or {}
    if params.get("name") == "skills":
        payload, is_error = skills_call(params.get("arguments") or {})
        if not is_error and skillgate.counts_as_read("skills", params.get("arguments")):
            gate.mark_read(request.headers.get(skillgate.HEADER))
        return rpc_tool_result(request_id, payload, is_error)
    if params.get("name") == "knowledge":
        payload, is_error = await asyncio.to_thread(knowledge_read.call, params.get("arguments") or {})
        return rpc_tool_result(request_id, payload, is_error)
    if params.get("name") == "knowledge_propose":
        payload, is_error = await asyncio.to_thread(knowledge_propose.propose, params.get("arguments") or {})
        return rpc_tool_result(request_id, payload, is_error)
    if params.get("name") == "launcher_set_backend":
        arguments = params.get("arguments") or {}
        try:
            await board.set_mode(arguments.get("mode"), arguments.get("user_confirmed"))
            return rpc_tool_result(request_id, {"ok": True, "mode": board.mode,
                                                "state": board.state})
        except (ValueError, RuntimeError) as exc:
            return rpc_tool_result(request_id, {"ok": False, "error": str(exc)}, True)
    try:
        await board.select(key)
    except AutoCADUnavailable as exc:
        return rpc_tool_result(request_id, {
            "ok": False, "code": "AUTOCAD_UNAVAILABLE", "error": str(exc),
            "question_for_user": "AutoCAD hiện không chạy. Bạn có muốn tôi xuất bản vẽ dạng DXF thay thế không?",
            "next_tool_after_yes": "launcher_set_backend",
            "next_arguments_after_yes": {"mode": "ezdxf", "user_confirmed": True},
        }, True)
    except Exception as exc:
        return rpc_tool_result(request_id, {"ok": False, "error": str(exc)}, True)
    return await board.forward(
        key, request,
        read_timeout=960 if key == "beiming" and params.get("name") == "copy_region_between_dwgs"
        else 900 if key == "beiming" and params.get("name") == "delete_batching"
        else 900 if key == "beiming" and params.get("name") == "copy_batching"
        else 720 if key == "beiming" else 360,
    )


async def queued_mcp_route(request: Request):
    """Serialize tool calls across agents through the active CAD process."""
    if request.path_params["key"] == "dutoan":
        return await dutoan.proxy(request)
    if request.path_params["key"] in PIPE_BRIDGES:
        return await litebim_route(request, PIPE_BRIDGES[request.path_params["key"]]())
    if request.method != "POST":
        return await mcp_route(request)
    try:
        message = await request.json()
    except ValueError:
        return await mcp_route(request)
    if message.get("method") != "tools/call":
        return await mcp_route(request)
    key = request.path_params["key"]
    tool_name = (message.get("params") or {}).get("name", "")
    if tool_name in ("skills", "knowledge", "knowledge_propose"):  # no CAD involved; never wait behind a CAD request
        return await mcp_route(request)
    # Refuse before queueing, so a blocked call never waits behind CAD work.
    if key in SERVERS and gate_active() and gate.blocks(tool_name, request.headers.get(skillgate.HEADER)):
        return rpc_tool_result(message.get("id"), skillgate.refusal(tool_name), True)
    async with board.request_slot(key, tool_name):
        return await mcp_route(request)


async def status_route(request: Request):
    return JSONResponse({"active": board.active, "mode": board.mode,
                         "state": board.state,
                         "error": board.error,
                         "acad_pid": board.acad_pid,
                         "queued_requests": board.queued_requests,
                         "active_request": board.active_request,
                         "dutoan": dutoan.status(),
                         "litebim": litebim.status(),
                         "litecad": litecad.status(),
                         "reference": {k: litebim_reference.info(k) for k in PIPE_BRIDGES},
                         "remote_agent": remote_agent.STATE.snapshot()})


async def dutoan_stop_route(request: Request):
    """Drop the dutoan process (it restarts on the next call) so dutoan.db can be replaced."""
    await dutoan.stop()
    return JSONResponse({"stopped": True})


async def select_route(request: Request):
    key = request.path_params["key"]
    if key not in SERVERS:
        return JSONResponse({"error": "Unknown MCP"}, status_code=404)
    try:
        await board.select(key)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    return JSONResponse({"active": board.active, "state": board.state})


def launcher_version():
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


async def remote_status():
    """Cho khung hello của chế độ agent: MCP nào đang hoạt động và chế độ backend."""
    servers = list(SERVERS) + (["dutoan"] if dutoan.available() else []) + [key for key in ("litebim", "litecad") if litebim_bridge.installed(key)]
    return {"active": board.active, "mode": board.mode, "servers": servers}


@asynccontextmanager
async def lifespan(_app):
    # Chế độ agent (kết nối ra server) chạy như tác vụ nền; tắt mặc định nên không ảnh hưởng gì khi chưa cấu hình.
    remote_agent.configure_logging(LOG_DIR)
    for key in PIPE_BRIDGES:   # LiteBIM đang mở mà chưa có tài liệu / đổi phiên bản: lấy ngay
        if litebim_bridge.installed(key):
            litebim_reference.refresh_async(PIPE_BRIDGES[key]())
    remote_task = asyncio.ensure_future(remote_agent.run_forever(
        knowledge_propose.load_settings, status_source=remote_status, version=launcher_version()))
    yield
    remote_task.cancel()
    await asyncio.gather(remote_task, return_exceptions=True)
    await dutoan.stop()
    litebim.close()
    litecad.close()
    await board.shutdown()


app = Starlette(routes=[
    Route("/status", status_route),
    Route("/dutoan/stop", dutoan_stop_route, methods=["POST"]),
    Route("/{key}/select", select_route, methods=["POST"]),
    Route("/{key}/reference", reference_route, methods=["GET"]),
    Route("/{key}/reference/refresh", reference_route, methods=["POST"]),
    Route("/{key}/mcp", queued_mcp_route, methods=["GET", "POST", "DELETE"]),
], lifespan=lifespan)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8764, access_log=False)
