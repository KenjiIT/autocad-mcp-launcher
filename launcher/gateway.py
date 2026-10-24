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
from cad_adapter import find_lt_window, prove_connection, prove_offline
SERVERS = {
    "puran": ("autocad_puran", ROOT / "puran-water-autocad-mcp", 8875),
    "beiming": ("autocad_beiming", ROOT / "autocad-beiming-mcp-custom", 8876),
}
LOG_DIR = ROOT / "launcher" / "logs"
HOP_HEADERS = {"connection", "transfer-encoding", "content-length", "host", "keep-alive"}
TOOL_CACHE = {}
BACKEND_TOOL = {
    "name": "launcher_set_backend",
    "description": (
        "Chọn backend cho launcher. Mặc định là AutoCAD. Chỉ gọi mode=ezdxf sau khi "
        "đã hỏi người dùng và được đồng ý xuất DXF thay cho AutoCAD; DXF không phải DWG. "
        "Gọi mode=autocad để quay lại AutoCAD. Lưu DXF trước khi đổi MCP hoặc backend."
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
            self.log = (LOG_DIR / f"{name}.log").open("a", encoding="utf-8", buffering=1)
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
            self.process = subprocess.Popen(
                [str(python), str(ROOT / "launcher" / "serve.py"), str(repo), str(port)],
                cwd=repo, env=env, stdin=subprocess.DEVNULL,
                stdout=self.log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
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
    TOOL_CACHE[key] = [*json.loads(result.stdout), BACKEND_TOOL]
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
        return Response(status_code=200)
    try:
        message = await request.json()
    except ValueError:
        return JSONResponse({"error": "Invalid JSON-RPC request"}, status_code=400)
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        requested = message.get("params", {}).get("protocolVersion", "2025-03-26")
        return rpc_result(request_id, {
            "protocolVersion": requested,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVERS[key][0], "version": "1.0.0"},
        })
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
        return rpc_result(request_id, {"prompts": []})
    if method == "resources/list":
        return rpc_result(request_id, {"resources": []})
    if method != "tools/call":
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id,
             "error": {"code": -32601, "message": f"Unsupported method: {method}"}},
            status_code=200)
    params = message.get("params") or {}
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
    async with board.request_slot(key, tool_name):
        return await mcp_route(request)


async def status_route(request: Request):
    return JSONResponse({"active": board.active, "mode": board.mode,
                         "state": board.state,
                         "error": board.error,
                         "acad_pid": board.acad_pid,
                         "queued_requests": board.queued_requests,
                         "active_request": board.active_request})


async def select_route(request: Request):
    key = request.path_params["key"]
    if key not in SERVERS:
        return JSONResponse({"error": "Unknown MCP"}, status_code=404)
    try:
        await board.select(key)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    return JSONResponse({"active": board.active, "state": board.state})


@asynccontextmanager
async def lifespan(_app):
    yield
    await board.shutdown()


app = Starlette(routes=[
    Route("/status", status_route),
    Route("/{key}/select", select_route, methods=["POST"]),
    Route("/{key}/mcp", queued_mcp_route, methods=["GET", "POST", "DELETE"]),
], lifespan=lifespan)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8764, access_log=False)
