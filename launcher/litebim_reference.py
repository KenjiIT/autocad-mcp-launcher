"""Lưu tài liệu API của LiteBIM / LiteCAD (kết quả tool ``get_reference``) thành file markdown trong thư mục của launcher.

Agent đọc thẳng file này (Read, từng đoạn bằng offset/limit) thay vì gọi get_reference mỗi phiên rồi phải mò vào
thư mục tool-results của CLI. Nội dung là của hãng và đổi theo phiên bản nên chỉ là bộ đệm (launcher/state/ không vào git).

Bố cục, mỗi sản phẩm một thư mục:
    launcher/state/<product>/reference/<product>-reference.md          tài liệu (tool không có tham số)
    launcher/state/<product>/reference/<product>-reference-<giá trị>.md  thêm mỗi chủ đề nếu tool có tham số enum
    launcher/state/<product>/reference/meta.json                       phiên bản, ngày lấy, danh sách file
Làm mới khi phiên bản ứng dụng (serverInfo.version lúc initialize) khác bản đã lưu, hoặc khi được yêu cầu (refresh).
"""
import datetime
import json
import os
import re
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get("LAUNCHER_STATE_DIR") or (ROOT / "launcher" / "state"))
TOOL = "get_reference"
_locks = {}


def ref_dir(product, state=None):
    return Path(state or STATE) / product / "reference"


def main_file(product, state=None):
    return ref_dir(product, state) / f"{product}-reference.md"


def read_meta(product, state=None):
    try:
        return json.loads((ref_dir(product, state) / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def info(product, state=None):
    """Đường dẫn + phiên bản + ngày lấy của tài liệu đã lưu (None nếu chưa có), cho /status và CAD Studio."""
    meta = read_meta(product, state)
    path = main_file(product, state)
    if not meta or not path.exists():
        return {"path": str(path), "available": False}
    return {"path": str(path), "dir": str(ref_dir(product, state)), "available": True, "version": meta.get("version"),
            "fetched_at": meta.get("fetched_at"), "files": meta.get("files", []), "bytes": meta.get("bytes")}


def _text_of(result):
    """Ghép mọi khối text của kết quả tools/call."""
    if not isinstance(result, dict) or result.get("isError"):
        return None
    parts = [c.get("text", "") for c in result.get("content") or [] if isinstance(c, dict) and c.get("type") == "text"]
    text = "\n".join(p for p in parts if p).strip()
    return text or None


def _header(title, version, fetched_at, topic=None):
    what = f" — chủ đề {topic}" if topic else ""
    return (f"<!-- Tài liệu API {title}{what}, phiên bản {version}, lấy lúc {fetched_at} bằng tool {TOOL}. "
            f"Bộ đệm do AutoCAD MCP Launcher tự lưu; tự làm mới khi {title} đổi phiên bản. -->\n\n")


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _slug(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-")[:60] or "x"


def _topics(tool):
    """Nếu get_reference có tham số enum (chủ đề), trả (tên tham số, các giá trị); không thì (None, [None])."""
    props = ((tool or {}).get("inputSchema") or {}).get("properties") or {}
    for name, spec in props.items():
        if isinstance(spec, dict) and isinstance(spec.get("enum"), list) and spec["enum"]:
            return name, list(spec["enum"])
    return None, [None]


def store(product, title, version, text, topic=None, state=None, now=None):
    """Ghi một kết quả get_reference (dùng cả khi agent tự gọi tool qua launcher)."""
    fetched = (now or datetime.datetime.now()).isoformat(timespec="seconds")
    base = main_file(product, state)
    path = base if topic is None else base.with_name(f"{product}-reference-{_slug(topic)}.md")
    _write(path, _header(title, version, fetched, topic) + text + "\n")
    meta = read_meta(product, state) or {}
    if meta.get("version") != version:
        meta = {}
    files = sorted(set(meta.get("files", [])) | {path.name})
    total = sum((ref_dir(product, state) / f).stat().st_size for f in files if (ref_dir(product, state) / f).exists())
    _write(ref_dir(product, state) / "meta.json", json.dumps(
        {"product": product, "title": title, "version": version, "fetched_at": fetched, "tool": TOOL, "files": files, "bytes": total},
        ensure_ascii=False, indent=2))
    return path


def refresh(bridge, force=False, state=None):
    """Lấy lại tài liệu qua cầu nối nếu phiên bản đổi (hoặc force). Trả dict kết quả; không ném lỗi."""
    product, title = bridge.product, bridge.title
    lock = _locks.setdefault(product, threading.Lock())
    if not lock.acquire(blocking=False):
        return {"state": "busy"}
    try:
        hello = bridge.handle({"jsonrpc": "2.0", "id": "ref-init", "method": "initialize", "params": {}}) or {}
        server = ((hello.get("result") or {}).get("serverInfo") or {})
        version = str(server.get("version") or "")
        if not version or version == "launcher":
            return {"state": "unavailable", "message": f"{title} chưa mở."}
        meta = read_meta(product, state)
        if not force and meta and meta.get("version") == version and main_file(product, state).exists():
            return {"state": "current", "version": version}
        tools = (((bridge.handle({"jsonrpc": "2.0", "id": "ref-list", "method": "tools/list"}) or {}).get("result") or {}).get("tools")) or []
        tool = next((t for t in tools if isinstance(t, dict) and t.get("name") == TOOL), None)
        if not tool:
            return {"state": "no-tool", "version": version}
        arg, values = _topics(tool)
        written = []
        for value in values:
            args = {} if value is None else {arg: value}
            reply = bridge.handle({"jsonrpc": "2.0", "id": "ref-call", "method": "tools/call", "params": {"name": TOOL, "arguments": args}}) or {}
            text = _text_of(reply.get("result"))
            if text:
                written.append(str(store(product, title, version, text, topic=value, state=state)))
        if not written:
            return {"state": "error", "message": f"{title} không trả tài liệu."}
        if arg:  # nhiều chủ đề: file chính là mục lục trỏ tới từng file
            index = "\n".join(f"- {Path(w).name}" for w in written)
            written.insert(0, str(store(product, title, version, f"# Tài liệu {title} theo chủ đề ({arg})\n\nĐọc file tương ứng cùng thư mục:\n{index}", state=state)))
        return {"state": "updated", "version": version, "files": written}
    except Exception as exc:  # cầu nối tự xử lý lỗi pipe; đây chỉ chặn lỗi ghi file
        return {"state": "error", "message": str(exc)}
    finally:
        lock.release()


def refresh_async(bridge, force=False, state=None):
    threading.Thread(target=refresh, args=(bridge, force, state), daemon=True, name=f"ref-{bridge.product}").start()
