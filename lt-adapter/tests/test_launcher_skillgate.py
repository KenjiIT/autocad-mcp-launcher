"""Gateway từ chối tool CAD cho tới khi phiên đã đọc skill điều phối."""
import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"
sys.path.insert(0, str(LAUNCHER))

import skillgate  # noqa: E402

gateway = pytest.importorskip("gateway")
COORDINATOR = {"operation": "get", "name": skillgate.REQUIRED_SKILL}
REAL_ROUTE = gateway.mcp_route  # `forwarded` thay gateway.mcp_route; các lệnh trực tiếp dùng bản thật


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.delenv(skillgate.ENV, raising=False)
    monkeypatch.setattr(gateway, "gate", skillgate.SkillGate())
    monkeypatch.setattr(gateway.knowledge_propose, "load_settings", lambda: {})


# ---- logic thuần ---------------------------------------------------------

def test_cad_tool_is_blocked_until_the_skill_is_read():
    g = skillgate.SkillGate()
    sid = g.new_session()
    assert g.blocks("drawing", sid)
    g.mark_read(sid)
    assert not g.blocks("drawing", sid)


@pytest.mark.parametrize("tool", sorted(skillgate.EXEMPT_TOOLS))
def test_exempt_tools_are_never_blocked(tool):
    assert not skillgate.SkillGate().blocks(tool, skillgate.SkillGate().new_session())


def test_sessions_are_independent():
    g = skillgate.SkillGate()
    a, b = g.new_session(), g.new_session()
    g.mark_read(a)
    assert not g.blocks("entity", a) and g.blocks("entity", b)


def test_unknown_session_id_is_blocked_then_can_read():
    # Sau khi gateway khởi động lại, mã phiên cũ không còn trong bộ nhớ.
    g = skillgate.SkillGate()
    assert g.blocks("entity", "from-before-restart")
    g.mark_read("from-before-restart")
    assert not g.blocks("entity", "from-before-restart")


def test_clients_without_a_session_id_share_a_time_window():
    now = [1000.0]
    g = skillgate.SkillGate(clock=lambda: now[0])
    assert g.blocks("entity", None)
    g.mark_read(None)
    assert not g.blocks("entity", None)
    now[0] += skillgate.ANON_WINDOW + 1
    assert g.blocks("entity", None)


def test_ended_session_must_read_again():
    g = skillgate.SkillGate()
    sid = g.new_session()
    g.mark_read(sid)
    g.end_session(sid)
    assert g.blocks("entity", sid)


def test_session_table_is_bounded():
    g = skillgate.SkillGate()
    for _ in range(skillgate.MAX_SESSIONS + 50):
        g.new_session()
    assert len(g.sessions) == skillgate.MAX_SESSIONS


def test_only_reading_the_coordinator_body_counts():
    assert skillgate.counts_as_read("skills", COORDINATOR)
    assert not skillgate.counts_as_read("skills", {"operation": "list"})
    assert not skillgate.counts_as_read("skills", {**COORDINATOR, "path": "references/catalog.md"})
    assert not skillgate.counts_as_read("skills", {"operation": "get", "name": "autocad-block-library"})
    assert not skillgate.counts_as_read("knowledge", COORDINATOR)


def test_refusal_names_the_next_step():
    r = skillgate.refusal("drawing")
    assert r["code"] == "SKILL_NOT_READ" and r["ok"] is False
    assert r["next_tool"] == "skills" and r["next_arguments"] == COORDINATOR


def test_enabled_by_default_and_by_setting_and_by_env(monkeypatch):
    assert skillgate.enabled({}) and skillgate.enabled(None)
    assert not skillgate.enabled({"skill_gate": False})
    monkeypatch.setenv(skillgate.ENV, "off")
    assert not skillgate.enabled({})
    monkeypatch.setenv(skillgate.ENV, "on")
    assert skillgate.enabled({"skill_gate": False})


# ---- nối vào gateway -----------------------------------------------------

class FakeRequest:
    def __init__(self, body, session=None, key="beiming", method="POST"):
        self.method = method
        self.path_params = {"key": key}
        self.headers = {"content-type": "application/json"}
        if session:
            self.headers[skillgate.HEADER] = session
        self._body = json.dumps(body).encode()

    async def json(self):
        return json.loads(self._body)

    async def body(self):
        return self._body


def call(tool, arguments=None, req_id=1):
    return {"jsonrpc": "2.0", "id": req_id, "method": "tools/call", "params": {"name": tool, "arguments": arguments or {}}}


def run(coro):
    return asyncio.run(coro)


def payload_of(response):
    result = json.loads(response.body)["result"]
    return json.loads(result["content"][0]["text"]), result["isError"]


@pytest.fixture
def forwarded(monkeypatch):
    """Thay phần chuyển tiếp thật bằng một dấu hiệu, để thấy tool CAD có qua cổng hay không."""
    seen = []

    async def fake_mcp_route(request):
        seen.append(request)
        return "forwarded"

    @asynccontextmanager
    async def free_slot(key, tool):
        yield

    monkeypatch.setattr(gateway, "mcp_route", fake_mcp_route)
    monkeypatch.setattr(gateway.board, "request_slot", free_slot)
    return seen


def initialize(key="beiming"):
    body = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}}
    return run(REAL_ROUTE(FakeRequest(body, key=key)))


def test_initialize_hands_out_a_session_id_and_explains_the_gate():
    response = initialize()
    assert response.headers["Mcp-Session-Id"] in gateway.gate.sessions
    text = json.loads(response.body)["result"]["instructions"]
    assert "SKILL_NOT_READ" in text


def test_initialize_when_disabled_is_unchanged(monkeypatch):
    monkeypatch.setattr(gateway.knowledge_propose, "load_settings", lambda: {"skill_gate": False})
    response = initialize()
    assert "Mcp-Session-Id" not in response.headers
    assert "SKILL_NOT_READ" not in json.loads(response.body)["result"]["instructions"]


def test_cad_call_without_reading_is_refused_before_queueing(monkeypatch):
    def boom(key, tool):
        raise AssertionError("a refused call must not enter the CAD queue")

    monkeypatch.setattr(gateway.board, "request_slot", boom)
    sid = initialize().headers["Mcp-Session-Id"]
    payload, is_error = payload_of(run(gateway.queued_mcp_route(FakeRequest(call("drawing", {"operation": "info"}), sid))))
    assert is_error and payload["code"] == "SKILL_NOT_READ"
    assert payload["next_tool"] == "skills" and payload["next_arguments"] == COORDINATOR


def test_skills_tool_call_marks_the_session_read():
    sid = initialize().headers["Mcp-Session-Id"]
    assert gateway.gate.blocks("drawing", sid)
    payload, is_error = payload_of(run(REAL_ROUTE(FakeRequest(call("skills", COORDINATOR), sid))))
    assert not is_error and payload["ok"]
    assert not gateway.gate.blocks("drawing", sid)


def test_listing_or_other_skills_do_not_unlock():
    sid = initialize().headers["Mcp-Session-Id"]
    run(REAL_ROUTE(FakeRequest(call("skills", {"operation": "list"}), sid)))
    run(REAL_ROUTE(FakeRequest(call("skills", {"operation": "get", "name": "autocad-block-library"}), sid)))
    assert gateway.gate.blocks("drawing", sid)


def test_another_session_is_still_refused(forwarded):
    a, b = initialize().headers["Mcp-Session-Id"], initialize().headers["Mcp-Session-Id"]
    gateway.gate.mark_read(a)
    assert run(gateway.queued_mcp_route(FakeRequest(call("drawing"), a))) == "forwarded"
    payload, is_error = payload_of(run(gateway.queued_mcp_route(FakeRequest(call("drawing"), b))))
    assert is_error and payload["code"] == "SKILL_NOT_READ"


@pytest.mark.parametrize("tool", ["skills", "knowledge", "knowledge_propose", "launcher_set_backend"])
def test_exempt_tools_pass_without_reading(forwarded, tool):
    sid = initialize().headers["Mcp-Session-Id"]
    assert run(gateway.queued_mcp_route(FakeRequest(call(tool), sid))) == "forwarded"


def test_disabled_gate_lets_everything_through(forwarded, monkeypatch):
    monkeypatch.setattr(gateway.knowledge_propose, "load_settings", lambda: {"skill_gate": False})
    assert run(gateway.queued_mcp_route(FakeRequest(call("drawing"), "any"))) == "forwarded"


def test_gate_opens_when_the_coordinator_skill_is_not_installed(forwarded, monkeypatch, tmp_path):
    # Không có skill thì agent không thể mở khóa; chặn lúc đó sẽ khóa vĩnh viễn.
    monkeypatch.setattr(gateway, "SKILLS_ROOT", tmp_path)
    assert not gateway.gate_active()
    assert "Mcp-Session-Id" not in initialize().headers
    assert run(gateway.queued_mcp_route(FakeRequest(call("drawing"), "any"))) == "forwarded"


def test_gate_is_active_with_the_real_skills():
    assert gateway.gate_active()


def test_dutoan_is_never_gated(monkeypatch):
    class Stub:
        async def proxy(self, request):
            return "dutoan"

    monkeypatch.setattr(gateway, "dutoan", Stub())
    assert run(gateway.queued_mcp_route(FakeRequest(call("search_don_gia"), key="dutoan"))) == "dutoan"


def test_delete_ends_the_session():
    sid = initialize().headers["Mcp-Session-Id"]
    gateway.gate.mark_read(sid)
    run(REAL_ROUTE(FakeRequest({}, sid, method="DELETE")))
    assert gateway.gate.blocks("drawing", sid)


def test_session_header_is_not_forwarded_to_the_cad_servers():
    assert skillgate.HEADER in gateway.HOP_HEADERS
