"""Chế độ agent: launcher kết nối ra server và chuyển lời gọi MCP vào gateway nội bộ (R1-R5 của đề xuất cad-web)."""
import asyncio
import base64
import json
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "launcher"))
websockets = pytest.importorskip("websockets")
from websockets.asyncio.server import serve  # noqa: E402

import remote_agent as ra  # noqa: E402

TOKEN = "tok-SECRET-123"
ENV = {ra.ENV_ALLOW_WS: "1"}


def b64(data):
    return base64.b64encode(data).decode("ascii")


# ---- "gateway nội bộ" giả --------------------------------------------------------

class LocalGateway:
    def __init__(self):
        self.calls = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def handle_any(self):
                length = int(self.headers.get("content-length") or 0)
                body = self.rfile.read(length) if length else b""
                outer.calls.append({"method": self.command, "path": self.path,
                                    "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
                if b"slow" in body:
                    time.sleep(0.5)
                if b"big" in body:
                    payload, ctype = b"x" * (500 * 1024), "text/event-stream"
                else:
                    payload, ctype = b'{"ok":true}', "application/json"
                self.send_response(200)
                self.send_header("content-type", ctype)
                self.send_header("mcp-session-id", "sess-1")
                self.send_header("x-secret", "local-only")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = do_DELETE = handle_any

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def local():
    gateway = LocalGateway()
    yield gateway
    gateway.close()


# ---- server WebSocket giả ---------------------------------------------------------

class FakeServer:
    def __init__(self, token=TOKEN):
        self.token = token
        self.attempts = 0       # số lần bắt tay (kể cả bị từ chối)
        self.hellos = []
        self.inbox = []         # khung nhận từ agent
        self.ws = None
        self.on_connect = None  # coroutine(ws) chạy ngay sau hello (ví dụ đóng với mã cụ thể)
        self.server = None
        self.url = ""

    async def process_request(self, connection, request):
        self.attempts += 1
        if request.headers.get("Authorization") != f"Bearer {self.token}":
            return connection.respond(HTTPStatus.UNAUTHORIZED, "unauthorized\n")
        return None

    async def handler(self, ws):
        self.ws = ws
        try:
            self.hellos.append(json.loads(await ws.recv()))
            if self.on_connect:
                await self.on_connect(ws)
            async for message in ws:
                self.inbox.append(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            pass

    async def start(self):
        self.server = await serve(self.handler, "127.0.0.1", 0, process_request=self.process_request)
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"
        return self

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

    async def send(self, frame):
        await self.ws.send(json.dumps(frame))

    def frames(self, request_id, kind=None):
        return [f for f in self.inbox if f.get("id") == request_id and (kind is None or f["type"] == kind)]


async def until(predicate, timeout=6.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        await asyncio.sleep(0.02)
    return False


def request(request_id, body=b"", path="/beiming/mcp", method="POST", headers=None):
    return {"type": "request", "id": request_id, "method": method, "path": path,
            "headers": headers or {"content-type": "application/json"}, "body_b64": b64(body)}


class Harness:
    """Chạy run_forever với cấu hình `settings` (dict sửa được giữa chừng) rồi dừng gọn."""

    def __init__(self, server, local, **overrides):
        self.server, self.local = server, local
        self.settings = {"remote_agent_enabled": True, "remote_server_url": server.url,
                         "remote_machine_id": "may-1", "remote_machine_token": TOKEN}
        self.settings.update(overrides)
        self.state = ra.AgentState()
        self.task = None

    async def __aenter__(self):
        async def status():
            return {"active": "beiming", "mode": "autocad", "servers": ["beiming", "puran", "dutoan"]}

        self.task = asyncio.ensure_future(ra.run_forever(
            lambda: dict(self.settings), status_source=status, version="9.9.9", local_base=self.local.base,
            backoff=(0.05, 0.1), idle=0.05, state=self.state, env=ENV, jitter=False))
        return self

    async def __aexit__(self, *exc):
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)


def run(coro):
    return asyncio.run(coro)


# ---- cấu hình (R1, R3) ----------------------------------------------------------------

def test_disabled_or_empty_config_changes_nothing():
    assert not ra.read_config({}).enabled and ra.read_config({}).problem == ""
    cfg = ra.read_config({"remote_server_url": "wss://x.test", "remote_machine_token": "t"})
    assert not cfg.enabled and cfg.problem == ""


@pytest.mark.parametrize("settings, fragment", [
    ({}, "địa chỉ server"),
    ({"remote_server_url": "https://x.test"}, "wss://"),
    ({"remote_server_url": "ws://example.test"}, "wss://"),
    ({"remote_server_url": "wss://"}, "tên máy chủ"),
    ({"remote_server_url": "wss://x.test"}, "mã máy"),
    ({"remote_server_url": "wss://x.test", "remote_machine_id": "m"}, "token"),
])
def test_enabled_but_unusable_config_reports_why(settings, fragment):
    cfg = ra.read_config({"remote_agent_enabled": True, **settings}, env={})
    assert fragment.lower() in cfg.problem.lower()


def test_ws_only_for_localhost_and_only_with_the_flag():
    base = {"remote_agent_enabled": True, "remote_machine_id": "m", "remote_machine_token": "t"}
    assert ra.read_config({**base, "remote_server_url": "ws://127.0.0.1:9"}, env={}).problem
    assert not ra.read_config({**base, "remote_server_url": "ws://127.0.0.1:9"}, env=ENV).problem
    assert not ra.read_config({**base, "remote_server_url": "ws://localhost:9"}, env=ENV).problem
    assert ra.read_config({**base, "remote_server_url": "ws://example.test:9"}, env=ENV).problem
    assert not ra.read_config({**base, "remote_server_url": "wss://example.test"}, env={}).problem


def test_launcher_set_backend_is_blocked_by_default_and_configurable():
    assert ra.read_config({}).blocked == frozenset({"launcher_set_backend"})
    assert ra.read_config({"remote_blocked_tools": []}).blocked == frozenset()
    assert ra.read_config({"remote_blocked_tools": "a, b"}).blocked == frozenset({"a", "b"})


def test_state_never_contains_the_token(tmp_path, local):
    async def scenario():
        server = await FakeServer().start()
        ra.configure_logging(tmp_path)
        try:
            async with Harness(server, local) as h:
                assert await until(lambda: server.hellos)
                await server.send(request("r1", b'{"x":1}', headers={"authorization": "Bearer " + TOKEN, "content-type": "application/json"}))
                assert await until(lambda: server.frames("r1", "response_end"))
                assert TOKEN not in json.dumps(h.state.snapshot())
        finally:
            await server.stop()

    run(scenario())
    for handler in list(ra.log.handlers):
        handler.flush()
    text = (tmp_path / "remote_agent.log").read_text(encoding="utf-8")
    assert TOKEN not in text and "Bearer" not in text and '{"x":1}' not in text
    assert "/beiming/mcp" in text and "127.0.0.1" in text


# ---- xác thực và nối lại (R5.1, R5.2) -----------------------------------------------------

def test_wrong_token_is_reported_and_not_retried():
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, LocalGateway(), remote_machine_token="sai") as h:
                assert await until(lambda: h.state.status == "auth_error")
                before = server.attempts
                await asyncio.sleep(0.6)
                assert server.attempts == before == 1
                h.settings["remote_machine_token"] = TOKEN   # đổi token thì thử lại
                assert await until(lambda: server.hellos and h.state.status == "connected")
        finally:
            await server.stop()

    run(scenario())


def test_server_closing_with_an_auth_code_stops_reconnecting():
    async def scenario():
        server = await FakeServer().start()

        async def revoke(ws):
            await ws.close(4401, "token revoked")

        server.on_connect = revoke
        try:
            async with Harness(server, LocalGateway()) as h:
                assert await until(lambda: h.state.status == "auth_error")
                await asyncio.sleep(0.5)
                assert server.attempts == 1
        finally:
            await server.stop()

    run(scenario())


def test_reconnects_with_backoff_and_keeps_working(local):
    async def scenario():
        server = await FakeServer().start()
        first = {"done": False}

        async def drop_once(ws):
            if not first["done"]:
                first["done"] = True
                await ws.close(1011, "restart")

        server.on_connect = drop_once
        try:
            async with Harness(server, local) as h:
                assert await until(lambda: len(server.hellos) >= 2)
                assert server.attempts >= 2 and h.state.status == "connected"
                await server.send(request("after", b"{}"))
                assert await until(lambda: server.frames("after", "response_end"))
        finally:
            await server.stop()

    run(scenario())


def test_disabled_agent_never_connects(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local, remote_agent_enabled=False) as h:
                await asyncio.sleep(0.4)
                assert server.attempts == 0 and h.state.status == "off"
                h.settings["remote_agent_enabled"] = True
                assert await until(lambda: h.state.status == "connected")
                h.settings["remote_agent_enabled"] = False
                assert await until(lambda: h.state.status == "off")
        finally:
            await server.stop()

    run(scenario())


def test_hello_describes_this_machine(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                assert server.hellos[0] == {"type": "hello", "machine_id": "may-1", "launcher_version": "9.9.9",
                                            "active": "beiming", "mode": "autocad",
                                            "servers": ["beiming", "puran", "dutoan"]}
        finally:
            await server.stop()

    run(scenario())


# ---- chuyển lời gọi (R5.3, R5.4) -------------------------------------------------------------

def test_mcp_call_goes_through_with_only_the_allowed_headers(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                await server.send(request("r1", b'{"jsonrpc":"2.0","id":1,"method":"initialize"}', headers={
                    "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": "sess-1", "MCP-Protocol-Version": "2025-03-26", "Authorization": "Bearer server-secret",
                    "X-Anything": "no", "Cookie": "c=1"}))
                assert await until(lambda: server.frames("r1", "response_end"))
        finally:
            await server.stop()
        call = local.calls[0]
        assert (call["method"], call["path"]) == ("POST", "/beiming/mcp")
        assert call["body"] == b'{"jsonrpc":"2.0","id":1,"method":"initialize"}'
        assert call["headers"]["mcp-session-id"] == "sess-1" and call["headers"]["mcp-protocol-version"] == "2025-03-26"
        assert "authorization" not in call["headers"] and "x-anything" not in call["headers"] and "cookie" not in call["headers"]
        start = server.frames("r1", "response_start")[0]
        assert start["status"] == 200
        assert start["headers"] == {"content-type": "application/json", "mcp-session-id": "sess-1"}  # x-secret không ra ngoài
        data = b"".join(base64.b64decode(f["data_b64"]) for f in server.frames("r1", "response_chunk"))
        assert data == b'{"ok":true}'

    run(scenario())


def test_large_sse_body_arrives_in_order(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                await server.send(request("big", b"big"))
                assert await until(lambda: server.frames("big", "response_end"))
        finally:
            await server.stop()
        mine = [f["type"] for f in server.inbox if f.get("id") == "big"]
        assert mine[0] == "response_start" and mine[-1] == "response_end"
        assert mine.count("response_chunk") == 3 and set(mine[1:-1]) == {"response_chunk"}
        assert b"".join(base64.b64decode(f["data_b64"]) for f in server.frames("big", "response_chunk")) == b"x" * (500 * 1024)
        assert server.frames("big", "response_start")[0]["headers"]["content-type"] == "text/event-stream"

    run(scenario())


def test_cancel_drops_the_result_but_the_call_still_finishes(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                await server.send(request("slow1", b"slow"))
                assert await until(lambda: local.calls)
                await server.send({"type": "cancel", "id": "slow1"})
                await asyncio.sleep(1.0)
                assert server.frames("slow1") == []              # không có khung nào cho yêu cầu đã hủy
                await server.send(request("next", b"{}"))        # kết nối vẫn dùng được
                assert await until(lambda: server.frames("next", "response_end"))
        finally:
            await server.stop()
        assert [c["body"] for c in local.calls] == [b"slow", b"{}"]

    run(scenario())


def test_extra_requests_beyond_the_limit_are_answered_busy(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                for index in range(ra.MAX_CONCURRENT + 1):
                    await server.send(request(f"s{index}", b"slow"))
                assert await until(lambda: server.frames(f"s{ra.MAX_CONCURRENT}", "error"))
                assert server.frames(f"s{ra.MAX_CONCURRENT}", "error")[0]["code"] == "BUSY"
                assert await until(lambda: all(server.frames(f"s{i}", "response_end") for i in range(ra.MAX_CONCURRENT)))
        finally:
            await server.stop()

    run(scenario())


# ---- giới hạn (R5.6, R5.7) ---------------------------------------------------------------------

@pytest.mark.parametrize("path, method, code", [
    ("/status", "GET", "FORBIDDEN_PATH"),
    ("/puran/select", "POST", "FORBIDDEN_PATH"),
    ("/dutoan/stop", "POST", "FORBIDDEN_PATH"),
    ("/beiming/mcp/extra", "POST", "FORBIDDEN_PATH"),
    ("/beiming/mcpx", "POST", "FORBIDDEN_PATH"),
    ("/beiming/mcp?x=1", "POST", "FORBIDDEN_PATH"),
    ("/unknown/mcp", "POST", "FORBIDDEN_PATH"),
    ("/beiming/mcp", "PUT", "METHOD_NOT_ALLOWED"),
])
def test_paths_and_methods_outside_the_allowlist_never_reach_the_gateway(local, path, method, code):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                await server.send(request("x", b"{}", path=path, method=method))
                assert await until(lambda: server.frames("x", "error"))
        finally:
            await server.stop()
        assert server.frames("x", "error")[0]["code"] == code
        assert local.calls == []

    run(scenario())


def test_oversized_body_is_refused_but_the_connection_stays(local, monkeypatch):
    monkeypatch.setattr(ra, "MAX_REQUEST_BODY", 1000)

    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                await server.send(request("big", b"a" * 2000))
                assert await until(lambda: server.frames("big", "error"))
                await server.send(request("ok", b"{}"))
                assert await until(lambda: server.frames("ok", "response_end"))
        finally:
            await server.stop()
        assert server.frames("big", "error")[0]["code"] == "TOO_LARGE" and len(local.calls) == 1

    run(scenario())


def test_a_frame_beyond_the_websocket_limit_closes_the_connection_and_it_reconnects(local, monkeypatch):
    monkeypatch.setattr(ra, "MAX_FRAME_BYTES", 4096)

    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local) as h:
                assert await until(lambda: server.hellos)
                await server.send(request("huge", b"a" * 10000))
                assert await until(lambda: len(server.hellos) >= 2)
                assert local.calls == [] and await until(lambda: h.state.status == "connected")
        finally:
            await server.stop()

    run(scenario())


def test_bad_base64_is_a_clean_error(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                frame = request("bad", b"")
                frame["body_b64"] = "!!!not base64!!!"
                await server.send(frame)
                assert await until(lambda: server.frames("bad", "error"))
        finally:
            await server.stop()
        assert server.frames("bad", "error")[0]["code"] == "BAD_REQUEST" and local.calls == []

    run(scenario())


def test_unreachable_gateway_is_an_error_frame():
    async def scenario():
        server = await FakeServer().start()
        try:
            dead = LocalGateway()
            dead.close()
            async with Harness(server, dead):
                assert await until(lambda: server.hellos)
                await server.send(request("x", b"{}"))
                assert await until(lambda: server.frames("x", "error"))
        finally:
            await server.stop()
        assert server.frames("x", "error")[0]["code"] == "LOCAL_UNAVAILABLE"

    run(scenario())


# ---- tool bị chặn ----------------------------------------------------------------------------

def call_body(name, request_id=7):
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                       "params": {"name": name, "arguments": {"mode": "ezdxf"}}}).encode()


def test_blocked_tool_gets_a_clear_tool_error_and_is_not_forwarded(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local):
                assert await until(lambda: server.hellos)
                await server.send(request("b", call_body("launcher_set_backend")))
                assert await until(lambda: server.frames("b", "response_end"))
                await server.send(request("b2", b"[" + call_body("drawing") + b"," + call_body("launcher_set_backend", 8) + b"]"))
                assert await until(lambda: server.frames("b2", "error"))
        finally:
            await server.stop()
        assert local.calls == []
        body = json.loads(b"".join(base64.b64decode(f["data_b64"]) for f in server.frames("b", "response_chunk")))
        assert body["id"] == 7 and body["result"]["isError"] is True
        assert json.loads(body["result"]["content"][0]["text"])["code"] == "TOOL_BLOCKED"
        assert server.frames("b2", "error")[0]["code"] == "TOOL_BLOCKED"

    run(scenario())


def test_other_tools_and_an_emptied_blocklist_are_forwarded(local):
    async def scenario():
        server = await FakeServer().start()
        try:
            async with Harness(server, local) as h:
                assert await until(lambda: server.hellos)
                await server.send(request("ok", call_body("drawing")))
                assert await until(lambda: server.frames("ok", "response_end"))
                h.settings["remote_blocked_tools"] = []        # đổi cấu hình: nối lại với danh sách mới
                assert await until(lambda: len(server.hellos) >= 2)
                await server.send(request("now", call_body("launcher_set_backend")))
                assert await until(lambda: server.frames("now", "response_end"))
        finally:
            await server.stop()
        assert [json.loads(c["body"])["params"]["name"] for c in local.calls] == ["drawing", "launcher_set_backend"]

    run(scenario())


# ---- R4 (cách A), tệp cấu hình ------------------------------------------------------------------

def test_inline_images_are_enabled_only_in_agent_mode():
    assert ra.inline_image_env({}) == {} and ra.inline_image_env({"remote_agent_enabled": False}) == {}
    env = ra.inline_image_env({"remote_agent_enabled": True})
    assert env == {"AUTOCAD_MCP_ALLOW_INLINE_IMAGES": "true", "AUTOCAD_MCP_MAX_INLINE_IMAGE_BYTES": str(2 * 1024 * 1024)}
    assert ra.inline_image_env({"remote_agent_enabled": True, "remote_inline_image_max_bytes": 10})[
        "AUTOCAD_MCP_MAX_INLINE_IMAGE_BYTES"] == "16384"
    assert ra.inline_image_env({"remote_agent_enabled": True, "remote_inline_image_max_bytes": 10 ** 9})[
        "AUTOCAD_MCP_MAX_INLINE_IMAGE_BYTES"] == str(8 * 1024 * 1024)
    assert ra.inline_image_env({"remote_agent_enabled": True, "remote_inline_image_max_bytes": "abc"})[
        "AUTOCAD_MCP_MAX_INLINE_IMAGE_BYTES"] == str(2 * 1024 * 1024)


def test_importing_the_module_does_not_need_httpx():
    # Launcher GUI chạy bằng Python hệ thống (không có httpx); chỉ gateway có. Import hỏng thì app không mở được.
    import subprocess
    code = ("import sys; sys.modules['httpx'] = None; sys.path.insert(0, sys.argv[1]); import remote_agent; "
            "print(remote_agent.read_config({}).enabled, remote_agent.describe({'status': 'connected', 'host': 'h'}))")
    done = subprocess.run([sys.executable, "-c", code, str(Path(__file__).resolve().parents[2] / "launcher")],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "False đã kết nối tới h"


def test_status_text_for_the_ui():
    assert ra.describe({}) == "" and ra.describe({"status": "off"}) == ""
    assert "đã kết nối tới srv.test" in ra.describe({"status": "connected", "host": "srv.test"})
    assert "nối lại sau 4s" in ra.describe({"status": "retrying", "detail": "OSError; nối lại sau 4s"})
    assert "token" in ra.describe({"status": "auth_error"})
    assert "websockets" in ra.describe({"status": "missing_lib"})
    assert ra.describe({"status": "config_error", "detail": "Chưa nhập token."}) == "Chưa nhập token."


def test_gateway_status_reports_the_agent_without_the_token():
    gateway = pytest.importorskip("gateway")
    ra.STATE.set("connected", "", machine_id="may-1", host="srv.test")
    try:
        body = json.loads(asyncio.run(gateway.status_route(None)).body)
    finally:
        ra.STATE.set("off", "")
    assert body["remote_agent"]["status"] == "connected" and body["remote_agent"]["host"] == "srv.test"
    assert "token" not in json.dumps(body).lower()


def test_gateway_tells_beiming_to_inline_images_only_in_agent_mode():
    gateway = pytest.importorskip("gateway")
    assert gateway.remote_agent is ra and callable(gateway.launcher_version)


@pytest.mark.skipif(sys.platform != "win32", reason="icacls")
def test_token_file_is_restricted_to_the_owner(tmp_path, monkeypatch):
    target = tmp_path / "settings.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("USERNAME", "minh")
    monkeypatch.setenv("USERDOMAIN", "PC")
    calls = []

    class Done:
        returncode = 0

    def fake_run(command, **kwargs):
        calls.append(command)
        return Done()

    assert ra.restrict_to_owner(target, run=fake_run) is True
    assert calls[0][:4] == ["icacls", str(target), "/inheritance:r", "/grant:r"] and calls[0][4] == "PC\\minh:(F)"

    class Fail:
        returncode = 5

    assert ra.restrict_to_owner(target, run=lambda *a, **k: Fail()) is False
