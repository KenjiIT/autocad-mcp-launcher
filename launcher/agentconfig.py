"""Tự thêm hoặc gỡ cấu hình các MCP của launcher (autocad_puran, autocad_beiming, dutoan, và litebim, litecad khi máy có) trong agent.

Chỉ động vào đúng ba mục của launcher; mọi MCP khác của người dùng giữ nguyên. Trước khi ghi, tệp
cấu hình được sao lưu vào ``backup_dir`` (không để tệp .bak rải trong thư mục của agent).

Claude Code: gọi lệnh ``claude mcp`` (phạm vi user). Codex: sửa ~/.codex/config.toml theo khối có đánh dấu.
Claude Desktop và Cursor: gộp vào tệp JSON.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

try:  # Python 3.11 trở lên; trên 3.10 bỏ bước kiểm TOML sau khi sửa
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None

GATEWAY = "http://127.0.0.1:8764"
SERVERS = ("autocad_puran", "autocad_beiming", "dutoan", "litebim", "litecad")
KEYS = {"autocad_puran": "puran", "autocad_beiming": "beiming", "dutoan": "dutoan", "litebim": "litebim", "litecad": "litecad"}
AGENTS = ("OpenAI Codex", "Claude Code", "Claude Desktop", "Cursor")
BEGIN = "# >>> AutoCAD MCP Launcher (tự thêm; gỡ bằng nút Gỡ khỏi agent trong launcher)"
END = "# <<< AutoCAD MCP Launcher"
MARK_BEGIN = "# >>> AutoCAD MCP Launcher"
MARK_END = "# <<< AutoCAD MCP Launcher"


def url(name):
    return f"{GATEWAY}/{KEYS[name]}/mcp"


def _default_run(command):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=90, creationflags=flags)
    return done.returncode, ((done.stdout or "") + (done.stderr or "")).strip()


@dataclass
class Context:
    home: Path = field(default_factory=Path.home)
    appdata: Path = field(default_factory=lambda: Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"))
    localappdata: Path = field(default_factory=lambda: Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"))
    backup_dir: Path = field(default_factory=lambda: Path.home() / ".autocad-mcp-launcher-backups")
    bridge_python: str = sys.executable
    bridge_script: str = "stdio_bridge.py"
    dutoan: bool = True
    litebim: bool = False  # chỉ thêm khi máy có LiteBIM
    litecad: bool = False  # chỉ thêm khi máy có LiteCAD
    run: Callable = _default_run
    which: Callable = shutil.which
    stamp: Callable = lambda: time.strftime("%Y%m%d-%H%M%S")

    def claude(self) -> Optional[str]:
        found = self.which("claude")
        if found:
            return found
        fallback = self.home / ".local" / "bin" / "claude.exe"
        return str(fallback) if fallback.is_file() else None


def names(ctx):
    return [n for n in SERVERS if (n != "dutoan" or ctx.dutoan) and (n != "litebim" or ctx.litebim) and (n != "litecad" or ctx.litecad)]


# ---- đường dẫn tệp cấu hình ---------------------------------------------

def config_path(agent, ctx):
    if agent == "OpenAI Codex":
        return ctx.home / ".codex" / "config.toml"
    if agent == "Claude Code":
        return ctx.home / ".claude.json"
    if agent == "Cursor":
        return ctx.home / ".cursor" / "mcp.json"
    if agent == "Claude Desktop":
        # Bản cài thường dùng %APPDATA%\Claude; bản Store (MSIX) ghi vào thư mục gói riêng.
        name = "claude_desktop_config.json"
        normal = ctx.appdata / "Claude" / name
        packages = ctx.localappdata / "Packages"
        store_dirs = sorted(packages.glob("Claude_*/LocalCache/Roaming/Claude")) if packages.is_dir() else []
        existing = [p for p in [normal, *(d / name for d in store_dirs)] if p.is_file()]
        if existing:
            return max(existing, key=lambda p: p.stat().st_mtime)
        # Chưa có tệp nào: có thư mục dữ liệu của bản Store (và không có thư mục của bản thường) thì dùng bản Store.
        if store_dirs and not normal.parent.exists():
            return store_dirs[0] / name
        return normal
    raise ValueError(agent)


# ---- nội dung mong muốn / hiển thị --------------------------------------

def expected_entry(agent, name, ctx):
    if agent == "Claude Desktop":
        return {"command": ctx.bridge_python, "args": [ctx.bridge_script, KEYS[name]]}
    if agent == "Cursor":
        return {"url": url(name)}
    return {"type": "http", "url": url(name)}  # Claude Code


def codex_blocks(ctx):
    return "\n\n".join(f'[mcp_servers.{n}]\nurl = "{url(n)}"' for n in names(ctx))


def snippet(agent, ctx):
    if agent == "OpenAI Codex":
        return codex_blocks(ctx)
    if agent == "Claude Code":
        return "\n".join(f"claude mcp add --transport http --scope user {n} {url(n)}" for n in names(ctx))
    if agent in ("Claude Desktop", "Cursor"):
        servers = {n: ({"url": url(n)} if agent == "Cursor" else expected_entry(agent, n, ctx)) for n in names(ctx)}
        return json.dumps({"mcpServers": servers}, indent=2, ensure_ascii=False)
    raise ValueError(agent)


# ---- đọc trạng thái hiện tại --------------------------------------------

def _read_text(path):
    """Đọc nguyên văn (giữ CRLF/LF như trong tệp) và bỏ BOM nếu có."""
    if not path.is_file():
        return ""
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return handle.read()


def _read_json(path):
    """(dữ liệu, lỗi). Tệp chưa có hoặc rỗng thì dữ liệu là {}."""
    if not path.is_file():
        return {}, None
    raw = path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return {}, None
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, f"Tệp {path} không phải JSON hợp lệ ({exc}); launcher không sửa."
    if not isinstance(data, dict):
        return None, f"Tệp {path} không phải đối tượng JSON; launcher không sửa."
    return data, None


HEADER = re.compile(r"^\s*\[\[?\s*([^\[\]]+?)\s*\]\]?\s*(?:#.*)?$")


def _norm(key):
    return re.sub(r"\s*\.\s*", ".", key.replace('"', "").replace("'", "")).strip()


def _codex_tables(text):
    """Bảng mcp_servers.<tên> -> {khóa: chuỗi thô}; đủ để biết có url hay command."""
    tables, current = {}, None
    for line in text.splitlines():
        header = HEADER.match(line)
        if header:
            key = _norm(header.group(1))
            current = tables.setdefault(key.split(".")[1], {}) if key.startswith("mcp_servers.") and key.count(".") == 1 else None
            continue
        if current is not None:
            pair = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=\s*(.*?)\s*$", line)
            if pair:
                current[pair.group(1)] = pair.group(2).strip("\"'")
    return tables


def _json_servers(agent, data):
    block = data.get("mcpServers")
    return block if isinstance(block, dict) else {}


def status(agent, ctx):
    """{"path", "exists", "servers": {tên: missing|ok|different}, "problem"}."""
    path = config_path(agent, ctx)
    result = {"path": str(path), "exists": path.is_file(), "servers": {n: "missing" for n in names(ctx)}, "problem": None}
    if agent == "OpenAI Codex":
        text = _read_text(path)
        tables = _codex_tables(text)
        for n in names(ctx):
            table = tables.get(n)
            if table is None:
                continue
            result["servers"][n] = "ok" if table.get("url") == url(n) and "command" not in table else "different"
        return result
    data, problem = _read_json(path)
    if data is None:
        result["problem"] = problem
        return result
    present = _json_servers(agent, data)
    for n in names(ctx):
        entry = present.get(n)
        if entry is None:
            continue
        want = expected_entry(agent, n, ctx)
        if agent == "Claude Code":
            good = isinstance(entry, dict) and entry.get("url") == want["url"] and entry.get("type", "http") == "http" and "command" not in entry
        else:
            good = isinstance(entry, dict) and all(entry.get(k) == v for k, v in want.items())
        result["servers"][n] = "ok" if good else "different"
    return result


LABEL = {"missing": "thêm mới", "ok": "đã đúng, giữ nguyên", "different": "đang khác, sẽ thay bằng cấu hình của launcher"}
LABEL_REMOVE = {"missing": "không có, bỏ qua", "ok": "sẽ gỡ", "different": "sẽ gỡ"}


def describe_plan(agent, ctx, remove=False):
    """{"text", "changes", "problem"} để hiện hộp xác nhận trước khi ghi."""
    state = status(agent, ctx)
    if state["problem"]:
        return {"text": state["problem"], "changes": 0, "problem": state["problem"]}
    label = LABEL_REMOVE if remove else LABEL
    lines = [f"Agent: {agent}", f"Tệp cấu hình: {state['path']}" + ("" if state["exists"] else " (chưa có, sẽ tạo)")]
    if agent == "Claude Code":
        lines[1] = "Qua lệnh `claude mcp` (phạm vi user, ghi vào " + state["path"] + ")"
        if ctx.claude() is None:
            msg = "Không tìm thấy lệnh `claude` trên máy này. Dùng nút Sao chép cấu hình và chạy tay các lệnh hiện trong ô."
            return {"text": msg, "changes": 0, "problem": msg}
    changes = 0
    for n in names(ctx):
        st = state["servers"][n]
        if (remove and st != "missing") or (not remove and st != "ok"):
            changes += 1
        lines.append(f"  - {n}: {label[st]}")
    lines.append("Chỉ các mục trên bị đụng tới; các MCP khác của bạn giữ nguyên.")
    if changes:
        lines.append(f"Bản sao lưu trước khi ghi: {ctx.backup_dir}")
    return {"text": "\n".join(lines), "changes": changes, "problem": None}


# ---- ghi ----------------------------------------------------------------

def _backup(path, agent, ctx):
    if not path.is_file():
        return None
    ctx.backup_dir.mkdir(parents=True, exist_ok=True)
    target = ctx.backup_dir / f"{agent.replace(' ', '-')}-{ctx.stamp()}-{path.name}"
    shutil.copy2(path, target)
    return target


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".launcher-tmp")
    with open(temp, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    os.replace(temp, path)


NEXT = {
    "OpenAI Codex": "Mở lại Codex (phiên mới) để nhận cấu hình.",
    "Claude Code": "Mở phiên Claude Code mới để nhận cấu hình.",
    "Claude Desktop": "Thoát hẳn Claude Desktop (cả biểu tượng khay) rồi mở lại.",
    "Cursor": "Mở lại Cursor để nhận cấu hình.",
}


def _done(todo, remove):
    """Một câu ngắn: đã làm gì, bao nhiêu mục. Đường dẫn tệp đã có ở dòng "Tệp cấu hình" của launcher."""
    return f"Đã {'gỡ' if remove else 'cập nhật'} {len(todo)} mục: {', '.join(todo)}."


def _result(ok, message, changed=(), unchanged=(), backup=None, agent=None, remove=False):
    return {"ok": ok, "message": message, "changed": list(changed), "unchanged": list(unchanged),
            "backup": str(backup) if backup else None,
            "next": NEXT.get(agent, "") if ok and changed and not remove else ""}


def apply(agent, ctx, remove=False):
    """Thêm (hoặc gỡ) ba mục của launcher. Trả {"ok","message","changed","unchanged","backup","next"}."""
    state = status(agent, ctx)
    if state["problem"]:
        return _result(False, state["problem"], agent=agent)
    todo = [n for n in names(ctx) if (state["servers"][n] != "missing" if remove else state["servers"][n] != "ok")]
    same = [n for n in names(ctx) if n not in todo]
    if not todo:
        return _result(True, "Không có gì phải đổi: " + ("chưa có mục nào của launcher." if remove else "cấu hình đã đúng sẵn."),
                       unchanged=same, agent=agent, remove=remove)
    if agent == "Claude Code":
        return _apply_claude_code(ctx, state, todo, same, remove)
    path = config_path(agent, ctx)
    try:
        if agent == "OpenAI Codex":
            new_text, problem = _codex_text(path, ctx, remove)
            if problem:
                return _result(False, problem, agent=agent)
        else:
            new_text, problem = _json_text(agent, path, ctx, todo, remove)
            if problem:
                return _result(False, problem, agent=agent)
        backup = _backup(path, agent, ctx)
        _write(path, new_text)
    except OSError as exc:
        return _result(False, f"Không ghi được {path}: {exc}", agent=agent)
    return _result(True, _done(todo, remove), changed=todo, unchanged=same, backup=backup,
                   agent=agent, remove=remove)


def _json_text(agent, path, ctx, todo, remove):
    data, problem = _read_json(path)
    if data is None:
        return None, problem
    block = data.get("mcpServers")
    if block is not None and not isinstance(block, dict):
        return None, f"Mục mcpServers trong {path} không phải đối tượng; launcher không sửa."
    block = dict(block or {})
    for n in todo:
        if remove:
            block.pop(n, None)
        else:
            block[n] = expected_entry(agent, n, ctx)
    data["mcpServers"] = block
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n", None


def _segments(text):
    """Chia tệp TOML thành các đoạn: phần đầu, từng bảng (kèm dòng thuộc về nó), vùng đánh dấu của launcher."""
    segments = [{"kind": "pre", "key": None, "lines": []}]
    in_mark = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if not in_mark and stripped.startswith(MARK_BEGIN):
            in_mark = True
            segments.append({"kind": "marker", "key": None, "lines": [line]})
            continue
        if in_mark:
            segments[-1]["lines"].append(line)
            if stripped.startswith(MARK_END):
                in_mark = False
            continue
        header = HEADER.match(line)
        if header:
            segments.append({"kind": "table", "key": _norm(header.group(1)), "lines": [line]})
        else:
            segments[-1]["lines"].append(line)
    return segments


def _edit_codex(text, ctx, remove, eol):
    """Thêm/cập nhật: thay đúng bảng chính [mcp_servers.<tên>] (tại chỗ nếu đã có) và bảng con `.env` (chỉ dùng cho stdio);
    GIỮ các bảng con khác của người dùng (ví dụ `.tools.<tool>` với approval_mode). Gỡ: bỏ bảng chính và mọi bảng con,
    vì bảng con đứng một mình không hợp lệ. Vùng đánh dấu cũ của launcher luôn được dựng lại."""
    wanted = names(ctx)
    block = {n: eol.join([f"[mcp_servers.{n}]", f'url = "{url(n)}"']) + eol + eol for n in wanted}
    placed, out = set(), []
    for seg in _segments(text):
        if seg["kind"] == "marker":
            continue
        key = seg["key"]
        owner = next((n for n in wanted if key == f"mcp_servers.{n}" or (key or "").startswith(f"mcp_servers.{n}.")), None)
        if owner is None:
            out.extend(seg["lines"])
        elif remove:
            continue
        elif key == f"mcp_servers.{owner}":
            if owner not in placed:
                out.append(block[owner])
                placed.add(owner)
        elif key == f"mcp_servers.{owner}.env":
            continue
        else:
            out.extend(seg["lines"])
    result = "".join(out).rstrip()
    missing = [n for n in wanted if n not in placed]
    if not remove and missing:
        appended = eol.join([BEGIN, "".join(block[n] for n in missing).rstrip(), END])
        result = (result + eol + eol if result else "") + appended
    return (result + eol) if result else ""


def _codex_text(path, ctx, remove):
    original = _read_text(path)
    if re.search(r"^\s*mcp_servers\.(?:%s)\b" % "|".join(SERVERS), original, re.M):
        return None, f"{path} dùng kiểu viết khoá chấm (mcp_servers.<tên>.url = ...); launcher không sửa được tự động. Hãy sửa tay."
    if tomllib is not None and original.strip():
        try:
            tomllib.loads(original)
        except ValueError as exc:
            return None, f"{path} không phải TOML hợp lệ ({exc}); launcher không sửa."
    eol = "\r\n" if "\r\n" in original else "\n"
    new = _edit_codex(original, ctx, remove, eol)
    if tomllib is not None and new.strip():
        try:
            parsed = tomllib.loads(new)
        except ValueError as exc:
            return None, f"Kết quả sửa không hợp lệ ({exc}); không ghi gì."
        servers = parsed.get("mcp_servers", {})
        for n in names(ctx):
            ok = (n not in servers) if remove else (servers.get(n, {}).get("url") == url(n))
            if not ok:
                return None, f"Kiểm lại sau khi sửa thấy mục {n} chưa đúng; không ghi gì."
    return new, None


def _apply_claude_code(ctx, state, todo, same, remove):
    claude = ctx.claude()
    if claude is None:
        return _result(False, "Không tìm thấy lệnh `claude` trên máy này. Dùng nút Sao chép cấu hình và chạy tay các lệnh hiện trong ô.",
                       agent="Claude Code")
    path = config_path("Claude Code", ctx)
    backup = _backup(path, "Claude Code", ctx)
    for n in todo:
        if state["servers"][n] != "missing":
            code, out = ctx.run([claude, "mcp", "remove", "--scope", "user", n])
            if code != 0 and remove:
                return _result(False, f"`claude mcp remove {n}` lỗi: {out[:300]}", agent="Claude Code")
        if remove:
            continue
        code, out = ctx.run([claude, "mcp", "add", "--transport", "http", "--scope", "user", n, url(n)])
        if code != 0:
            return _result(False, f"`claude mcp add {n}` lỗi: {out[:300]}", agent="Claude Code")
    after = status("Claude Code", ctx)
    bad = [n for n in todo if (after["servers"][n] != "missing" if remove else after["servers"][n] != "ok")]
    if bad:
        return _result(False, "Lệnh `claude mcp` báo xong nhưng cấu hình chưa như mong muốn ở: " + ", ".join(bad)
                       + ". Kiểm tra bằng `claude mcp list`.", agent="Claude Code")
    return _result(True, _done(todo, remove), changed=todo, unchanged=same,
                   backup=backup, agent="Claude Code", remove=remove)
