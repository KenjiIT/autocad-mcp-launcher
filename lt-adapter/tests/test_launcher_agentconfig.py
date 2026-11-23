"""Nút tự thêm/gỡ cấu hình MCP vào agent (Codex, Claude Code, Claude Desktop, Cursor)."""
import json
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "launcher"))
import agentconfig as ac  # noqa: E402

NAMES = ["autocad_puran", "autocad_beiming", "dutoan"]


def make_ctx(tmp_path, run=None, claude="claude", dutoan=True):
    return ac.Context(
        home=tmp_path / "home", appdata=tmp_path / "appdata", localappdata=tmp_path / "local",
        backup_dir=tmp_path / "backups", bridge_python=r"C:\L\python.exe", bridge_script=r"C:\L\stdio_bridge.py",
        dutoan=dutoan, run=run or (lambda command: (0, "")),
        which=lambda name: claude if name == "claude" else None, stamp=lambda: "T1", claude_config_dir=None)


def states(agent, ctx):
    return ac.status(agent, ctx)["servers"]


# ---- Codex ---------------------------------------------------------------

def codex_file(ctx):
    path = ac.config_path("OpenAI Codex", ctx)
    return path


def test_codex_creates_the_file_and_is_idempotent(tmp_path):
    ctx = make_ctx(tmp_path)
    result = ac.apply("OpenAI Codex", ctx)
    assert result["ok"] and result["changed"] == NAMES and result["backup"] is None
    parsed = tomllib.loads(codex_file(ctx).read_text(encoding="utf-8"))
    assert {n: parsed["mcp_servers"][n]["url"] for n in NAMES} == {n: ac.url(n) for n in NAMES}
    assert set(states("OpenAI Codex", ctx).values()) == {"ok"}
    again = ac.apply("OpenAI Codex", ctx)
    assert again["ok"] and again["changed"] == [] and again["backup"] is None


def test_codex_replaces_old_stdio_entries_and_keeps_everything_else(tmp_path):
    ctx = make_ctx(tmp_path)
    path = codex_file(ctx)
    path.parent.mkdir(parents=True)
    original = (
        'model = "gpt-5"\r\n\r\n'
        "[mcp_servers.other]\r\nurl = \"https://example.test/mcp\"\r\n\r\n"
        "[mcp_servers.dutoan]\r\ncommand = 'du-toan-mcp/.venv/Scripts/python.exe'\r\nargs = [\r\n    \"-m\",\r\n    \"dutoan_mcp.server\",\r\n]\r\n\r\n"
        "[mcp_servers.dutoan.env]\r\nX = \"1\"\r\n\r\n"
        "[mcp_servers.autocad_puran]\r\ncommand = 'old'\r\n\r\n"
        "[profiles.fast]\r\nmodel = \"x\"\r\n")
    path.write_bytes(original.encode("utf-8"))
    assert states("OpenAI Codex", ctx) == {"autocad_puran": "different", "autocad_beiming": "missing", "dutoan": "different"}
    result = ac.apply("OpenAI Codex", ctx)
    assert result["ok"] and set(result["changed"]) == set(NAMES)
    raw = path.read_bytes().decode("utf-8")
    parsed = tomllib.loads(raw)
    assert parsed["model"] == "gpt-5" and parsed["profiles"]["fast"]["model"] == "x"
    assert parsed["mcp_servers"]["other"]["url"] == "https://example.test/mcp"
    assert "command" not in parsed["mcp_servers"]["dutoan"] and "env" not in parsed["mcp_servers"]["dutoan"]
    assert "\n" in raw and raw.count("\r\n") == raw.count("\n")  # giữ kiểu xuống dòng CRLF
    backup = Path(result["backup"])
    assert backup.parent == tmp_path / "backups" and backup.read_bytes().decode("utf-8") == original


def test_codex_keeps_the_users_per_tool_settings_when_updating(tmp_path):
    # Tệp thật có `[mcp_servers.<tên>.tools.<tool>] approval_mode = "approve"`; cập nhật không được làm mất.
    ctx = make_ctx(tmp_path)
    path = codex_file(ctx)
    path.parent.mkdir(parents=True)
    path.write_text(
        '[mcp_servers.autocad_beiming]\ncommand = "old"\n\n'
        '[mcp_servers.autocad_beiming.tools.entity]\napproval_mode = "approve"\n\n'
        '[mcp_servers.autocad_puran]\nurl = "http://127.0.0.1:8764/puran/mcp"\n\n'
        '[mcp_servers.autocad_puran.tools.drawing]\napproval_mode = "approve"\n', encoding="utf-8")
    result = ac.apply("OpenAI Codex", ctx)
    assert result["ok"] and result["changed"] == ["autocad_beiming", "dutoan"]
    parsed = tomllib.loads(path.read_text("utf-8"))
    beiming = parsed["mcp_servers"]["autocad_beiming"]
    assert beiming["url"] == ac.url("autocad_beiming") and "command" not in beiming
    assert beiming["tools"]["entity"]["approval_mode"] == "approve"
    assert parsed["mcp_servers"]["autocad_puran"]["tools"]["drawing"]["approval_mode"] == "approve"
    assert parsed["mcp_servers"]["dutoan"]["url"] == ac.url("dutoan")
    again = ac.apply("OpenAI Codex", ctx)
    assert again["changed"] == []
    assert tomllib.loads(path.read_text("utf-8")) == parsed


def test_codex_remove_drops_orphan_subtables_too(tmp_path):
    # Bảng con đứng một mình (không có url/command) làm Codex báo lỗi, nên gỡ phải bỏ cả chúng.
    ctx = make_ctx(tmp_path)
    path = codex_file(ctx)
    path.parent.mkdir(parents=True)
    path.write_text(
        '[mcp_servers.autocad_beiming]\nurl = "http://127.0.0.1:8764/beiming/mcp"\n\n'
        '[mcp_servers.autocad_beiming.tools.entity]\napproval_mode = "approve"\n\n'
        '[mcp_servers.other]\nurl = "https://x.test"\n', encoding="utf-8")
    ac.apply("OpenAI Codex", ctx, remove=True)
    parsed = tomllib.loads(path.read_text("utf-8"))
    assert list(parsed["mcp_servers"]) == ["other"]


def test_codex_remove_only_touches_launcher_entries(tmp_path):
    ctx = make_ctx(tmp_path)
    path = codex_file(ctx)
    path.parent.mkdir(parents=True)
    path.write_text('[mcp_servers.other]\nurl = "https://x.test"\n', encoding="utf-8")
    ac.apply("OpenAI Codex", ctx)
    result = ac.apply("OpenAI Codex", ctx, remove=True)
    assert result["ok"] and result["changed"] == NAMES
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert list(parsed["mcp_servers"]) == ["other"]
    assert ac.apply("OpenAI Codex", ctx, remove=True)["changed"] == []


def test_codex_refuses_invalid_toml_and_dotted_keys(tmp_path):
    ctx = make_ctx(tmp_path)
    path = codex_file(ctx)
    path.parent.mkdir(parents=True)
    path.write_text("this is = = not toml", encoding="utf-8")
    result = ac.apply("OpenAI Codex", ctx)
    assert not result["ok"] and "TOML" in result["message"]
    assert path.read_text(encoding="utf-8") == "this is = = not toml" and not (tmp_path / "backups").exists()
    path.write_text('mcp_servers.dutoan.url = "x"\n', encoding="utf-8")
    result = ac.apply("OpenAI Codex", ctx)
    assert not result["ok"] and "kiểu viết" in result["message"]


# ---- Cursor và Claude Desktop (JSON) -------------------------------------

def test_cursor_creates_then_merges_without_losing_other_servers(tmp_path):
    ctx = make_ctx(tmp_path)
    path = ac.config_path("Cursor", ctx)
    result = ac.apply("Cursor", ctx)
    assert result["ok"] and json.loads(path.read_text("utf-8"))["mcpServers"]["dutoan"] == {"url": ac.url("dutoan")}
    path.write_text(json.dumps({"theme": "dark", "mcpServers": {"mine": {"url": "https://m.test"},
                                                                   "dutoan": {"command": "old"}}}), encoding="utf-8")
    assert states("Cursor", ctx)["dutoan"] == "different"
    result = ac.apply("Cursor", ctx)
    data = json.loads(path.read_text("utf-8"))
    assert data["theme"] == "dark" and data["mcpServers"]["mine"] == {"url": "https://m.test"}
    assert data["mcpServers"]["dutoan"] == {"url": ac.url("dutoan")} and Path(result["backup"]).is_file()


def test_json_remove_keeps_other_servers(tmp_path):
    ctx = make_ctx(tmp_path)
    path = ac.config_path("Cursor", ctx)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"mcpServers": {"mine": {"url": "https://m.test"}}}), encoding="utf-8")
    ac.apply("Cursor", ctx)
    result = ac.apply("Cursor", ctx, remove=True)
    assert result["ok"] and json.loads(path.read_text("utf-8"))["mcpServers"] == {"mine": {"url": "https://m.test"}}


def test_desktop_uses_the_stdio_bridge_for_every_server(tmp_path):
    ctx = make_ctx(tmp_path)
    ac.apply("Claude Desktop", ctx)
    servers = json.loads(ac.config_path("Claude Desktop", ctx).read_text("utf-8"))["mcpServers"]
    assert servers["dutoan"] == {"command": r"C:\L\python.exe", "args": [r"C:\L\stdio_bridge.py", "dutoan"]}
    assert servers["autocad_puran"]["args"][-1] == "puran" and servers["autocad_beiming"]["args"][-1] == "beiming"
    assert ac.apply("Claude Desktop", ctx)["changed"] == []


def test_desktop_path_prefers_an_existing_file_then_the_store_build(tmp_path):
    ctx = make_ctx(tmp_path)
    normal = ctx.appdata / "Claude" / "claude_desktop_config.json"
    store_dir = ctx.localappdata / "Packages" / "Claude_abc" / "LocalCache" / "Roaming" / "Claude"
    assert ac.config_path("Claude Desktop", ctx) == normal  # không có gì: đường dẫn thường
    store_dir.mkdir(parents=True)
    assert ac.config_path("Claude Desktop", ctx) == store_dir / "claude_desktop_config.json"  # chỉ có bản Store
    normal.parent.mkdir(parents=True)
    normal.write_text("{}", encoding="utf-8")
    assert ac.config_path("Claude Desktop", ctx) == normal  # tệp đã có được ưu tiên


def test_invalid_json_is_never_touched(tmp_path):
    ctx = make_ctx(tmp_path)
    path = ac.config_path("Cursor", ctx)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    result = ac.apply("Cursor", ctx)
    assert not result["ok"] and "JSON" in result["message"]
    assert path.read_text(encoding="utf-8") == "{not json" and not (tmp_path / "backups").exists()
    assert ac.describe_plan("Cursor", ctx)["problem"]


# ---- Claude Code (lệnh `claude mcp`) --------------------------------------

class FakeClaude:
    """Bắt chước lệnh claude: ghi vào ~/.claude.json như CLI thật."""

    def __init__(self, path, fail_on=None, noop=False):
        self.path, self.calls, self.fail_on, self.noop = path, [], fail_on, noop

    def __call__(self, command):
        self.calls.append(command[1:])
        if self.fail_on and self.fail_on in command:
            return 1, "boom"
        if self.noop:
            return 0, ""
        data = json.loads(self.path.read_text("utf-8")) if self.path.is_file() else {}
        servers = data.setdefault("mcpServers", {})
        if command[2] == "add":
            servers[command[-2]] = {"type": "http", "url": command[-1]}
        elif command[2] == "remove":
            servers.pop(command[-1], None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data), encoding="utf-8")
        return 0, ""


def claude_ctx(tmp_path, **kw):
    ctx = make_ctx(tmp_path)
    ctx.run = FakeClaude(ctx.home / ".claude.json", **kw)
    return ctx


def test_claude_code_adds_with_user_scope_and_http(tmp_path):
    ctx = claude_ctx(tmp_path)
    result = ac.apply("Claude Code", ctx)
    assert result["ok"] and result["changed"] == NAMES
    adds = [c for c in ctx.run.calls if c[1] == "add"]
    assert [c[-2] for c in adds] == NAMES
    assert all(c[:6] == ["mcp", "add", "--transport", "http", "--scope", "user"] or c[1:6] == ["add", "--transport", "http", "--scope", "user"] for c in adds)
    assert set(states("Claude Code", ctx).values()) == {"ok"}
    assert ac.apply("Claude Code", ctx)["changed"] == []


def test_claude_code_replaces_a_different_entry_by_remove_then_add(tmp_path):
    ctx = claude_ctx(tmp_path)
    path = ctx.home / ".claude.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"mcpServers": {"dutoan": {"type": "stdio", "command": "py"},
                                               "mine": {"type": "http", "url": "https://m.test"}}}), encoding="utf-8")
    result = ac.apply("Claude Code", ctx)
    assert result["ok"]
    ops = [(c[1], c[-1] if c[1] == "remove" else c[-2]) for c in ctx.run.calls]
    assert ops.index(("remove", "dutoan")) < ops.index(("add", "dutoan"))
    assert not any(op == ("remove", "mine") for op in ops)
    assert json.loads(path.read_text("utf-8"))["mcpServers"]["mine"]["url"] == "https://m.test"
    assert Path(result["backup"]).parent == tmp_path / "backups"


def test_claude_code_remove(tmp_path):
    ctx = claude_ctx(tmp_path)
    ac.apply("Claude Code", ctx)
    result = ac.apply("Claude Code", ctx, remove=True)
    assert result["ok"] and result["changed"] == NAMES
    assert set(states("Claude Code", ctx).values()) == {"missing"}


def test_claude_code_reports_a_failing_command(tmp_path):
    ctx = claude_ctx(tmp_path, fail_on="dutoan")
    result = ac.apply("Claude Code", ctx)
    assert not result["ok"] and "dutoan" in result["message"] and "boom" in result["message"]


def test_claude_code_checks_the_result_instead_of_trusting_the_exit_code(tmp_path):
    result = ac.apply("Claude Code", claude_ctx(tmp_path, noop=True))
    assert not result["ok"] and "chưa đúng" in result["message"] and ".claude.json" in result["message"]


def test_claude_code_without_the_cli_explains_what_to_do(tmp_path):
    ctx = make_ctx(tmp_path, claude=None)
    plan = ac.describe_plan("Claude Code", ctx)
    assert plan["problem"] and "claude" in plan["problem"]
    assert not ac.apply("Claude Code", ctx)["ok"]


# ---- hiển thị -------------------------------------------------------------

def test_plan_counts_only_real_changes(tmp_path):
    ctx = make_ctx(tmp_path)
    plan = ac.describe_plan("Cursor", ctx)
    assert plan["changes"] == 3 and "thêm mới" in plan["text"] and "các MCP khác của bạn giữ nguyên" in plan["text"]
    ac.apply("Cursor", ctx)
    plan = ac.describe_plan("Cursor", ctx)
    assert plan["changes"] == 0 and "đã đúng" in plan["text"]
    assert ac.describe_plan("Cursor", ctx, remove=True)["changes"] == 3


def test_without_dutoan_only_the_cad_servers_are_managed(tmp_path):
    ctx = make_ctx(tmp_path, dutoan=False)
    assert ac.names(ctx) == ["autocad_puran", "autocad_beiming"]
    ac.apply("Cursor", ctx)
    assert "dutoan" not in json.loads(ac.config_path("Cursor", ctx).read_text("utf-8"))["mcpServers"]


def test_snippets(tmp_path):
    ctx = make_ctx(tmp_path)
    assert "claude mcp add --transport http --scope user dutoan http://127.0.0.1:8764/dutoan/mcp" in ac.snippet("Claude Code", ctx)
    assert '[mcp_servers.dutoan]\nurl = "http://127.0.0.1:8764/dutoan/mcp"' in ac.snippet("OpenAI Codex", ctx)
    assert json.loads(ac.snippet("Cursor", ctx))["mcpServers"]["dutoan"] == {"url": ac.url("dutoan")}
    assert json.loads(ac.snippet("Claude Desktop", ctx))["mcpServers"]["dutoan"]["args"][-1] == "dutoan"
    with pytest.raises(ValueError):
        ac.snippet("Nobody", ctx)


def test_claude_code_theo_claude_config_dir_ghi_va_kiem_cung_mot_tep(tmp_path):
    """Launcher chạy với CLAUDE_CONFIG_DIR: `claude mcp add` ghi vào <dir>/.claude.json, launcher phải kiểm đúng tệp đó."""
    ctx = make_ctx(tmp_path)
    ctx.claude_config_dir = str(tmp_path / "profile")
    ctx.run = FakeClaude(tmp_path / "profile" / ".claude.json")
    assert ac.config_path("Claude Code", ctx) == tmp_path / "profile" / ".claude.json"
    result = ac.apply("Claude Code", ctx)
    assert result["ok"] and set(states("Claude Code", ctx).values()) == {"ok"}
    assert not (ctx.home / ".claude.json").exists()
    assert ac.apply("Claude Code", ctx, remove=True)["ok"] and set(states("Claude Code", ctx).values()) == {"missing"}


def test_claude_code_ghi_cho_khac_thi_bao_ro_tep_va_bien_moi_truong(tmp_path):
    """Lệnh claude ghi vào hồ sơ khác (ví dụ CLAUDE_CONFIG_DIR của môi trường khác): báo rõ tệp đã kiểm và lý do."""
    ctx = make_ctx(tmp_path)
    ctx.claude_config_dir = str(tmp_path / "profile")
    ctx.run = FakeClaude(tmp_path / "noi-khac" / ".claude.json")
    result = ac.apply("Claude Code", ctx)
    assert not result["ok"]
    assert str(tmp_path / "profile" / ".claude.json") in result["message"]
    assert "CLAUDE_CONFIG_DIR" in result["message"] and "autocad_puran" in result["message"]


def test_context_mac_dinh_lay_claude_config_dir_tu_moi_truong(monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", r"D:\cfg")
    assert ac.Context().claude_config_dir == r"D:\cfg"
    monkeypatch.delenv("CLAUDE_CONFIG_DIR")
    assert ac.Context().claude_config_dir is None
