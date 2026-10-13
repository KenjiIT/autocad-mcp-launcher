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
from cad_adapter import prove_connection
SERVERS = {
    "puran": ("autocad_puran", ROOT / "puran-water-autocad-mcp", 8875),
    "beiming": ("autocad_beiming", ROOT / "beiming183-cloud-AutoCAD-MCP", 8876),
}
LOG_DIR = ROOT / "launcher" / "logs"
HOP_HEADERS = {"connection", "transfer-encoding", "content-length", "host", "keep-alive"}
TOOL_CACHE = {}


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def cad_window_alive(hwnd):
    return bool(hwnd and ctypes.windll.user32.IsWindow(int(hwnd)))


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
    def __init__(self):
        self.lock = asyncio.Lock()
        self.active = None
        self.active_hwnd = None
        self.process = None
        self.log = None
        self.state = "Đang chờ agent chọn MCP"
        self.error = None

    async def select(self, key):
        async with self.lock:
            if (self.active == key and self.process and self.process.poll() is None
                    and cad_window_alive(self.active_hwnd)):
                return
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
            self.state = f"Đang kết nối {name} với AutoCAD"
            self.error = None
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            python = repo / ".venv" / "Scripts" / "python.exe"
            if not python.is_file():
                raise RuntimeError(f"Thiếu môi trường Python: {python}. Mở app để cài thư viện.")
            if listening(port):
                raise RuntimeError(f"Cổng nội bộ {port} đã được sử dụng")
            self.log = (LOG_DIR / f"{name}.log").open("a", encoding="utf-8", buffering=1)
            env = os.environ.copy()
            env["AUTOCAD_MCP_BACKEND"] = "file_ipc"
            env["AUTOCAD_MCP_AUTOSTART"] = "false"
            if key == "beiming":
                env["AUTOCAD_MCP_OUTPUT_ROOT"] = str(repo / "output")
                env["AUTOCAD_MCP_LISP_PATH"] = str(repo / "lisp-code" / "mcp_dispatch.lsp")
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
                payload = await prove_connection(name, repo, port)
                self.active_hwnd = (payload.get("hwnd")
                                    or (payload.get("autocad") or {}).get("hwnd")
                                    or (payload.get("worker") or {}).get("hwnd"))
                self.active = key
                self.state = f"Đã kết nối AutoCAD qua {name}"
            except Exception as exc:
                self.error = str(exc)
                self.state = f"Chưa kết nối AutoCAD qua {name}"
                await asyncio.to_thread(kill_tree, self.process)
                self.process = None
                self.active_hwnd = None
                if self.log:
                    self.log.close()
                    self.log = None
                raise

    async def forward(self, key, request):
        # Lock also covers the in-flight call. Switching cannot interrupt a CAD write.
        async with self.lock:
            if self.active != key or not self.process or self.process.poll() is not None:
                return JSONResponse({"error": "MCP đang chuyển, thử lại"}, status_code=503)
            _, _, port = SERVERS[key]
            headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
            try:
                async with httpx.AsyncClient(timeout=300) as client:
                    response = await client.request(
                        request.method, f"http://127.0.0.1:{port}/mcp",
                        headers=headers, content=await request.body())
                outbound = {k: v for k, v in response.headers.items()
                            if k.lower() not in HOP_HEADERS}
                return Response(response.content, status_code=response.status_code, headers=outbound)
            except Exception as exc:
                self.error = str(exc)
                return JSONResponse({"error": str(exc)}, status_code=502)

    async def shutdown(self):
        async with self.lock:
            await asyncio.to_thread(kill_tree, self.process)
            self.process = None
            self.active = None
            self.active_hwnd = None
            if self.log:
                self.log.close()
                self.log = None


board = Switchboard()


async def tool_schema(key):
    if key in TOOL_CACHE:
        return TOOL_CACHE[key]
    _, repo, _ = SERVERS[key]
    python = repo / ".venv" / "Scripts" / "python.exe"
    code = (
        "import asyncio,json; from autocad_mcp.server import mcp; "
        "print(json.dumps([t.model_dump(by_alias=True,exclude_none=True) "
        "for t in asyncio.run(mcp.list_tools())]))"
    )
    result = await asyncio.to_thread(
        subprocess.run, [str(python), "-c", code], cwd=repo,
        capture_output=True, text=True, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(f"Không đọc được danh sách công cụ {key}: {result.stderr[-500:]}")
    TOOL_CACHE[key] = json.loads(result.stdout)
    return TOOL_CACHE[key]


def rpc_result(request_id, result):
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


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
    try:
        await board.select(key)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    return await board.forward(key, request)


async def status_route(request: Request):
    return JSONResponse({"active": board.active, "state": board.state, "error": board.error})


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
    Route("/{key}/mcp", mcp_route, methods=["GET", "POST", "DELETE"]),
], lifespan=lifespan)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8764, access_log=False)
