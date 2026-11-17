"""dutoan is served over HTTP through the gateway (not stdio)."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"
sys.path.insert(0, str(LAUNCHER))

gateway = pytest.importorskip("gateway")


class FakeRequest:
    def __init__(self, method="POST", key="dutoan", body=b"{}", headers=None):
        self.method = method
        self.path_params = {"key": key}
        self.headers = headers or {"content-type": "application/json"}
        self._body = body

    async def body(self):
        return self._body

    async def json(self):
        return json.loads(self._body)


def run(coro):
    return asyncio.run(coro)


def test_get_and_delete_never_start_the_process(tmp_path):
    # A GET would open a never-ending event stream; the stateless server must not be asked for one.
    service = gateway.DutoanService(repo=tmp_path)
    assert run(service.proxy(FakeRequest("GET"))).status_code == 405
    assert run(service.proxy(FakeRequest("DELETE"))).status_code == 200
    assert service.process is None


def test_missing_environment_is_a_clear_503(tmp_path):
    service = gateway.DutoanService(repo=tmp_path)
    assert service.available() is False
    response = run(service.proxy(FakeRequest("POST")))
    assert response.status_code == 503
    assert "dutoan" in json.loads(response.body)["error"]


def test_dutoan_route_bypasses_the_cad_switchboard(monkeypatch):
    seen = []

    class Stub:
        async def proxy(self, request):
            seen.append(request.method)
            return "proxied"

    monkeypatch.setattr(gateway, "dutoan", Stub())
    monkeypatch.setattr(gateway.board, "select", lambda *_: (_ for _ in ()).throw(AssertionError("switchboard used")))
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_projects"}}).encode()
    assert run(gateway.queued_mcp_route(FakeRequest("POST", body=body))) == "proxied"
    assert seen == ["POST"]


def test_stop_route_stops_the_service(monkeypatch):
    calls = []

    class Stub:
        async def stop(self):
            calls.append("stop")

    monkeypatch.setattr(gateway, "dutoan", Stub())
    response = run(gateway.dutoan_stop_route(FakeRequest("POST")))
    assert json.loads(response.body) == {"stopped": True} and calls == ["stop"]


def test_status_reports_dutoan(monkeypatch):
    class Stub:
        def status(self):
            return {"available": True, "running": False, "error": None}

    monkeypatch.setattr(gateway, "dutoan", Stub())
    payload = json.loads(run(gateway.status_route(FakeRequest("GET"))).body)
    assert payload["dutoan"] == {"available": True, "running": False, "error": None}


def test_routes_are_registered():
    paths = {route.path for route in gateway.app.routes}
    assert {"/status", "/dutoan/stop", "/{key}/mcp", "/{key}/select"} <= paths


def test_agent_config_uses_http_for_dutoan():
    app = pytest.importorskip("app")
    url = "http://127.0.0.1:8764/dutoan/mcp"
    codex = app.config_for("OpenAI Codex")
    assert f'[mcp_servers.dutoan]\nurl = "{url}"' in codex and "dutoan_mcp.server" not in codex
    code = app.config_for("Claude Code")
    assert f"claude mcp add --transport http dutoan {url}" in code and "dutoan_mcp.server" not in code
    servers = json.loads(app.config_for("Claude Desktop"))["mcpServers"]
    assert set(servers) == {"autocad_puran", "autocad_beiming", "dutoan"}
    assert servers["dutoan"]["args"][-1] == "dutoan" and servers["dutoan"]["args"][0].endswith("stdio_bridge.py")
    assert servers["autocad_puran"]["args"][-1] == "puran"
