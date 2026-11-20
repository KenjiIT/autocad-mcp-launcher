"""LiteBIM is served over HTTP through the gateway, bridged to LiteBIM's own named pipe."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"
sys.path.insert(0, str(LAUNCHER))

import litebim_bridge as lb  # noqa: E402
import agentconfig  # noqa: E402

HELLO = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {"listChanged": False}},
         "serverInfo": {"name": "litebim", "title": "LiteBIM", "version": "27.4.19"}, "instructions": "Ask model_summary first."}
TOOLS = [{"name": "model_summary", "description": "x", "inputSchema": {"type": "object"}}]


class FakePipe:
    """A LiteBIM stand-in: newline JSON-RPC, answers like the real MCP server."""

    def __init__(self, tools_delay=False, die_after=None, silent_on=None):
        self.out = []
        self.seen = []
        self.closed = False
        self.die_after = die_after
        self.silent_on = silent_on

    def write_line(self, text):
        if self.closed:
            raise ConnectionError("closed")
        message = json.loads(text)
        self.seen.append(message)
        if "id" not in message:
            return
        method = message["method"]
        if self.die_after is not None and len([m for m in self.seen if "id" in m]) > self.die_after:
            self.closed = True
            raise ConnectionError("broken pipe")
        if method == self.silent_on:
            return
        if method == "initialize":
            result = HELLO
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            result = {"content": [{"type": "text", "text": "Levels: Level 1"}], "isError": False}
        else:
            result = {}
        # an unsolicited notification first, as LiteBIM may send; the bridge must skip it
        self.out.append(json.dumps({"jsonrpc": "2.0", "method": "notifications/tools/list_changed"}))
        self.out.append(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}))

    def read_line(self, timeout):
        if self.out:
            return self.out.pop(0)
        raise TimeoutError("no reply")

    def close(self):
        self.closed = True


def bridge_with(*pipes):
    queue = list(pipes)
    connects = []

    def connect():
        if not queue:
            raise lb.LiteBimUnavailable("no pipe")
        connects.append(1)
        return queue.pop(0)

    return lb.LiteBimBridge(connect=connect, timeout=1), connects


def call(bridge, method, request_id, params=None):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return bridge.handle(message)


def test_initialize_returns_litebims_own_instructions_and_the_clients_protocol():
    bridge, _ = bridge_with(FakePipe())
    reply = call(bridge, "initialize", "a", {"protocolVersion": "2025-03-26"})
    assert reply["id"] == "a"
    assert reply["result"]["protocolVersion"] == "2025-03-26"
    assert reply["result"]["serverInfo"]["name"] == "litebim"
    assert "model_summary" in reply["result"]["instructions"]


def test_client_ids_are_restored_and_server_notifications_skipped():
    pipe = FakePipe()
    bridge, _ = bridge_with(pipe)
    reply = call(bridge, "tools/list", 41)
    assert reply == {"jsonrpc": "2.0", "id": 41, "result": {"tools": TOOLS}}
    sent = [m for m in pipe.seen if m.get("method") == "tools/list"][0]
    assert sent["id"] != 41  # the bridge uses its own ids on the shared pipe


def test_handshake_is_done_once_and_calls_share_the_connection():
    pipe = FakePipe()
    bridge, connects = bridge_with(pipe)
    call(bridge, "tools/list", 1)
    reply = call(bridge, "tools/call", 2, {"name": "model_summary", "arguments": {}})
    assert reply["result"]["content"][0]["text"] == "Levels: Level 1"
    assert len(connects) == 1
    assert [m["method"] for m in pipe.seen if "method" in m].count("initialize") == 1
    assert any(m.get("method") == "notifications/initialized" for m in pipe.seen)


def test_client_notifications_get_no_reply_and_are_not_forwarded():
    pipe = FakePipe()
    bridge, _ = bridge_with(pipe)
    assert bridge.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert pipe.seen == []


def test_litebim_closed_still_initializes_lists_no_tools_and_explains_on_call():
    bridge, _ = bridge_with()
    assert "LiteBIM" in call(bridge, "initialize", 1, {})["result"]["instructions"]
    assert call(bridge, "tools/list", 2)["result"]["tools"] == []
    reply = call(bridge, "tools/call", 3, {"name": "model_summary"})
    assert reply["result"]["isError"] is True and "chưa mở" in reply["result"]["content"][0]["text"]
    assert bridge.status()["connected"] is False


def test_it_reconnects_when_litebim_is_opened_later():
    bridge, _ = bridge_with()
    assert call(bridge, "tools/list", 1)["result"]["tools"] == []
    bridge._connect = lambda: FakePipe()
    assert call(bridge, "tools/list", 2)["result"]["tools"] == TOOLS


def test_dead_pipe_is_reconnected_once_for_reads():
    first = FakePipe(die_after=1)  # answers the handshake, then dies
    second = FakePipe()
    bridge, connects = bridge_with(first, second)
    assert call(bridge, "tools/list", 1)["result"]["tools"] == TOOLS
    assert len(connects) == 2


def test_dead_pipe_is_never_retried_for_a_tool_call():
    first = FakePipe(die_after=1)
    bridge, connects = bridge_with(first, FakePipe())
    reply = call(bridge, "tools/call", 1, {"name": "run_script", "arguments": {}})
    assert reply["result"]["isError"] is True and "Mất kết nối" in reply["result"]["content"][0]["text"]
    assert len(connects) == 1  # a script may already have run; sending it again could build twice


def test_timeout_drops_the_connection_and_warns_the_command_may_still_run():
    pipe = FakePipe(silent_on="tools/call")
    bridge, _ = bridge_with(pipe)
    reply = call(bridge, "tools/call", 1, {"name": "run_script", "arguments": {}})
    assert reply["result"]["isError"] is True and "có thể vẫn đang chạy" in reply["result"]["content"][0]["text"]
    assert pipe.closed and bridge.status()["connected"] is False


def test_pipe_candidates_prefer_the_override_then_the_current_user(monkeypatch):
    monkeypatch.setenv("USERNAME", "someone")
    monkeypatch.delenv(lb.PIPE_ENV, raising=False)
    monkeypatch.setattr(lb.os, "listdir", lambda _: ["other", "LiteBIM-mcp-zed", "litebim-mcp-someone"])
    names = lb.pipe_candidates()
    assert names[0].endswith("litebim-mcp-someone") and any(n.endswith("LiteBIM-mcp-zed") for n in names)
    assert len(names) == len({n.lower() for n in names})
    monkeypatch.setenv(lb.PIPE_ENV, "litebim-mcp-custom")
    assert lb.pipe_candidates()[0].endswith("\\pipe\\litebim-mcp-custom")


# ---- gateway route -----------------------------------------------------------

gateway = pytest.importorskip("gateway")


class FakeRequest:
    def __init__(self, method="POST", body=b"{}"):
        self.method = method
        self.path_params = {"key": "litebim"}
        self.headers = {"content-type": "application/json"}
        self._body = body

    async def json(self):
        return json.loads(self._body)


def run(coro):
    return asyncio.run(coro)


def post(payload):
    return FakeRequest("POST", json.dumps(payload).encode())


def test_gateway_routes_litebim_around_the_cad_switchboard(monkeypatch):
    bridge, _ = bridge_with(FakePipe())
    monkeypatch.setattr(gateway, "litebim", bridge)
    monkeypatch.setattr(gateway.board, "select", lambda *_: (_ for _ in ()).throw(AssertionError("switchboard used")))
    response = run(gateway.queued_mcp_route(post({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                                                  "params": {"name": "model_summary", "arguments": {}}})))
    body = json.loads(response.body)
    assert response.status_code == 200 and body["id"] == 5 and body["result"]["isError"] is False


def test_gateway_get_delete_and_notifications(monkeypatch):
    bridge, _ = bridge_with(FakePipe())
    monkeypatch.setattr(gateway, "litebim", bridge)
    assert run(gateway.queued_mcp_route(FakeRequest("GET"))).status_code == 405
    assert run(gateway.queued_mcp_route(FakeRequest("DELETE"))).status_code == 200
    assert run(gateway.queued_mcp_route(post({"jsonrpc": "2.0", "method": "notifications/initialized"}))).status_code == 202


def test_gateway_handles_batches_and_bad_bodies(monkeypatch):
    bridge, _ = bridge_with(FakePipe())
    monkeypatch.setattr(gateway, "litebim", bridge)
    response = run(gateway.queued_mcp_route(post([{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                                                  {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])))
    assert [item["id"] for item in json.loads(response.body)] == [1, 2]
    assert run(gateway.queued_mcp_route(FakeRequest("POST", b"not json"))).status_code == 400
    assert run(gateway.queued_mcp_route(post([1, 2]))).status_code == 400


def test_gateway_status_reports_litebim():
    assert set(gateway.litebim.status()) == {"installed", "available", "connected", "error"}
    assert set(gateway.litecad.status()) == set(gateway.litebim.status())


# ---- agent configuration and remote mode -------------------------------------

def test_litebim_is_added_to_agents_only_when_installed(tmp_path):
    ctx = agentconfig.Context(home=tmp_path, appdata=tmp_path, localappdata=tmp_path, backup_dir=tmp_path / "b")
    assert "litebim" not in agentconfig.names(ctx)
    ctx.litebim = True
    assert agentconfig.names(ctx)[-1] == "litebim"
    assert agentconfig.url("litebim") == "http://127.0.0.1:8764/litebim/mcp"
    assert "litebim" in agentconfig.snippet("OpenAI Codex", ctx)
    assert "mcp add --transport http --scope user litebim http://127.0.0.1:8764/litebim/mcp" in agentconfig.snippet("Claude Code", ctx)
    desktop = json.loads(agentconfig.snippet("Claude Desktop", ctx))["mcpServers"]["litebim"]
    assert desktop["args"][-1] == "litebim"


def test_remote_agent_may_call_litebim_but_not_its_other_paths():
    import remote_agent
    assert remote_agent.PATH_RE.match("/litebim/mcp")
    assert not remote_agent.PATH_RE.match("/litebim/select")


# ---- LiteCAD uses the same bridge with its own pipe and wording -----------------

def test_litecad_has_its_own_pipe_prefix_name_and_messages(monkeypatch):
    monkeypatch.setenv("USERNAME", "someone")
    monkeypatch.delenv(lb.PIPE_ENV, raising=False)
    monkeypatch.setattr(lb.os, "listdir", lambda _: ["litebim-mcp-someone", "litecad-mcp-someone"])
    assert lb.pipe_candidates("litecad-mcp-")[0].endswith("litecad-mcp-someone")
    assert all("litebim" not in n for n in lb.pipe_candidates("litecad-mcp-"))
    assert lb.pipe_present("litecad-mcp-") and not lb.pipe_present("nothing-")
    bridge = lb.LiteBimBridge(connect=lambda: (_ for _ in ()).throw(lb.LiteBimUnavailable("x")), product="litecad")
    reply = call(bridge, "tools/call", 1, {"name": "x"})
    assert "LiteCAD chưa mở" in reply["result"]["content"][0]["text"]
    assert call(bridge, "initialize", 2, {})["result"]["serverInfo"]["name"] == "litecad"


def test_the_shared_override_variable_only_applies_to_the_matching_product(monkeypatch):
    monkeypatch.setenv(lb.PIPE_ENV, "litebim-mcp-custom")
    monkeypatch.setattr(lb.os, "listdir", lambda _: [])
    assert lb.pipe_candidates("litebim-mcp-")[0].endswith("litebim-mcp-custom")
    assert not any("custom" in n for n in lb.pipe_candidates("litecad-mcp-"))


def test_gateway_routes_litecad_to_its_own_bridge(monkeypatch):
    seen = []
    litebim_stub, _ = bridge_with(FakePipe())
    litecad_pipe = FakePipe()
    litecad_stub, _ = bridge_with(litecad_pipe)
    monkeypatch.setattr(gateway, "litebim", litebim_stub)
    monkeypatch.setattr(gateway, "litecad", litecad_stub)
    request = FakeRequest("POST", json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}).encode())
    request.path_params = {"key": "litecad"}
    response = run(gateway.queued_mcp_route(request))
    assert json.loads(response.body)["result"]["tools"] == TOOLS + [gateway.PIPE_SKILLS_TOOL]
    assert litecad_pipe.seen and not seen


def test_litebim_route_offers_the_project_skills(monkeypatch):
    pipe = FakePipe()
    bridge, _ = bridge_with(pipe)
    monkeypatch.setattr(gateway, "litebim", bridge)
    init = json.loads(run(gateway.queued_mcp_route(post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                                         "params": {"protocolVersion": "2025-03-26"}}))).body)
    assert "`skills`" in init["result"]["instructions"]
    tools = json.loads(run(gateway.queued_mcp_route(post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))).body)
    assert [t["name"] for t in tools["result"]["tools"]].count("skills") == 1
    sent_before = len(pipe.seen)
    listed = json.loads(run(gateway.queued_mcp_route(post({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                                           "params": {"name": "skills", "arguments": {"operation": "list"}}}))).body)
    payload = json.loads(listed["result"]["content"][0]["text"])
    assert listed["id"] == 3 and payload["ok"] and any(s["name"] == "thiet-ke-phong-nha" for s in payload["skills"])
    assert len(pipe.seen) == sent_before   # skills trả lời ngay ở gateway, không gửi xuống LiteBIM


def test_status_line_wording():
    assert "Đang nối" in lb.describe("litebim", {"connected": True})
    assert "MCP bật" in lb.describe("litecad", {"available": True})
    assert "Chưa mở" in lb.describe("litecad", {})


def test_litecad_in_agent_config_remote_paths_and_bridge_choices(tmp_path):
    import remote_agent
    ctx = agentconfig.Context(home=tmp_path, appdata=tmp_path, localappdata=tmp_path, backup_dir=tmp_path / "b",
                              litebim=True, litecad=True)
    assert agentconfig.names(ctx)[-2:] == ["litebim", "litecad"]
    assert agentconfig.url("litecad") == "http://127.0.0.1:8764/litecad/mcp"
    assert remote_agent.PATH_RE.match("/litecad/mcp")
