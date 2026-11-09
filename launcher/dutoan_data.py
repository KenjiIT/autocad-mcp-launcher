"""Download the estimating database (dutoan.db) from a link the user supplies.

The database is compiled from a commercial estimating package, so it is never
bundled with the launcher or published in a public release. The user points the
launcher at a private link (SharePoint, Drive, a private release) and, optionally,
the expected SHA-256; the file is checked and only then put in place.
"""

import hashlib
import json
import os
import sqlite3
import urllib.error
import urllib.request
import zipfile
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "du-toan-mcp" / "data" / "dutoan.db"
REQUIRED_TABLES = ("don_gia", "dinh_muc", "tu_dien_vat_tu")
CHUNK = 1024 * 256
MIN_BYTES = 1024 * 1024


def db_path():
    override = os.environ.get("DUTOAN_DB_PATH")
    return Path(override) if override else DB_PATH


def describe(path=None):
    """Short status line for the settings tab."""
    path = Path(path) if path else db_path()
    if not path.is_file():
        return {"present": False, "message": f"Chưa có dữ liệu dự toán ({path})."}
    size = path.stat().st_size / (1024 * 1024)
    return {"present": True, "message": f"Đã có dữ liệu dự toán ({size:.0f} MB)."}


def check_database(path):
    """Return None when the file is a usable estimating database, else a reason."""
    try:
        with closing(sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)) as conn:
            tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
    except sqlite3.Error as exc:
        return f"Không phải tệp SQLite hợp lệ: {exc}"
    missing = [name for name in REQUIRED_TABLES if name not in tables]
    if missing:
        return "Thiếu bảng dữ liệu: " + ", ".join(missing)
    return None


def download(url, expected_sha256="", dest=None, progress=None, opener=urllib.request.urlopen, headers=None):
    """Download to a temporary file, verify, then replace dest. Returns {"ok", "message"}."""
    dest = Path(dest) if dest else db_path()
    url = (url or "").strip()
    if not url.startswith("https://"):
        return {"ok": False, "message": "Địa chỉ tải phải bắt đầu bằng https://"}
    expected = (expected_sha256 or "").strip().lower()
    if expected and (len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected)):
        return {"ok": False, "message": "SHA-256 phải gồm 64 ký tự thập lục phân."}
    part = dest.with_name(dest.name + ".part")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        done = 0
        request = urllib.request.Request(url, headers={"user-agent": "autocad-mcp-launcher", **(headers or {})})
        with opener(request, timeout=60) as response, part.open("wb") as out:
            total = int(response.headers.get("content-length") or 0)
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                out.write(block)
                digest.update(block)
                done += len(block)
                if progress:
                    progress(done, total)
        if done < MIN_BYTES:
            return _fail(part, "Tệp tải về quá nhỏ; có thể link trả về trang đăng nhập thay vì dữ liệu.")
        if expected and digest.hexdigest() != expected:
            return _fail(part, "SHA-256 không khớp; không dùng tệp này.")
        reason = check_database(part)
        if reason:
            return _fail(part, reason)
        os.replace(part, dest)
    except (OSError, ValueError) as exc:
        part.unlink(missing_ok=True)
        return {"ok": False, "message": f"Không tải được: {exc}"}
    _remember(dest, digest.hexdigest())
    return {"ok": True, "message": f"Đã tải dữ liệu dự toán ({done / (1024 * 1024):.0f} MB).", "sha256": digest.hexdigest()}


def _fail(part, message):
    Path(part).unlink(missing_ok=True)
    return {"ok": False, "message": message}


def _sidecar(dest):
    return Path(dest).with_name(Path(dest).name + ".sha256")


def _remember(dest, sha):
    try:
        _sidecar(dest).write_text(sha, encoding="ascii")
    except OSError:
        pass  # only a cache; the next sync re-hashes the file


def local_sha256(dest=None):
    """SHA-256 of the installed database, or '' when absent. Cached beside the file."""
    dest = Path(dest) if dest else db_path()
    if not dest.is_file():
        return ""
    side = _sidecar(dest)
    try:
        cached = side.read_text(encoding="ascii").strip().lower()
        if len(cached) == 64 and side.stat().st_mtime >= dest.stat().st_mtime:
            return cached
    except OSError:
        pass
    digest = hashlib.sha256()
    with dest.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    _remember(dest, digest.hexdigest())
    return digest.hexdigest()


def sync(gateway_url, team_key, dest=None, progress=None, opener=urllib.request.urlopen):
    """Bring the database up to date from the team gateway.

    Returns {"ok", "message", "changed"}. Nothing is replaced unless the gateway's
    manifest differs from the local file and the new file passes every check.
    """
    dest = Path(dest) if dest else db_path()
    base = (gateway_url or "").strip().rstrip("/")
    if not base.startswith("https://"):
        return {"ok": False, "changed": False, "message": "Địa chỉ cổng phải bắt đầu bằng https://"}
    if not team_key:
        return {"ok": False, "changed": False, "message": "Chưa có khóa nhóm nên chưa tự tải được dữ liệu dự toán."}
    headers = {"x-team-key": team_key}
    try:
        request = urllib.request.Request(base + "/dutoan/manifest", headers={"user-agent": "autocad-mcp-launcher", **headers})
        with opener(request, timeout=30) as response:
            manifest = json.loads(response.read(65536).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        reasons = {401: "Khóa nhóm không đúng.", 404: "Cổng chưa có dữ liệu dự toán.", 503: "Cổng chưa cấu hình kho dữ liệu dự toán."}
        return {"ok": False, "changed": False, "message": reasons.get(exc.code, f"Cổng trả lỗi {exc.code}.")}
    except (OSError, ValueError) as exc:
        return {"ok": False, "changed": False, "message": f"Không hỏi được cổng: {exc}"}
    sha = str(manifest.get("sha256") or "").lower() if isinstance(manifest, dict) else ""
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        return {"ok": False, "changed": False, "message": "Cổng trả thông tin dữ liệu không hợp lệ."}
    if local_sha256(dest) == sha:
        return {"ok": True, "changed": False, "message": "Dữ liệu dự toán đã là bản mới nhất."}
    result = download(base + "/dutoan/db", sha, dest=dest, progress=progress, opener=opener, headers=headers)
    result["changed"] = bool(result["ok"])
    return result


def sync_key(settings, team_key):
    """Key for the estimating data: its own key when set, else the shared team key."""
    return str((settings or {}).get("dutoan_data_key") or os.environ.get("DUTOAN_DATA_KEY") or team_key or "").strip()


MAX_UNPACKED = 2 * 1024 ** 3  # refuse a zip that expands past 2 GiB


def import_file(source, dest=None):
    """Install a database the user was handed: a .db file or a .zip holding one.

    The file is copied to a temporary name beside ``dest``, checked, and only then
    replaces the current database; on any problem the current file is untouched.
    Returns {"ok", "message", "sha256"?}.
    """
    source = Path(source)
    dest = Path(dest) if dest else db_path()
    if not source.is_file():
        return {"ok": False, "message": "Không tìm thấy tệp đã chọn."}
    part = dest.with_name(dest.name + ".part")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        done = 0
        if zipfile.is_zipfile(source):
            with zipfile.ZipFile(source) as archive:
                members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith(".db")]
                named = [m for m in members if Path(m.filename).name.lower() == "dutoan.db"]
                chosen = named or members
                if len(chosen) != 1:
                    return {"ok": False, "message": "Tệp zip phải chứa đúng một tệp dutoan.db."}
                if chosen[0].file_size > MAX_UNPACKED:
                    return {"ok": False, "message": "Tệp trong zip quá lớn; không dùng."}
                with archive.open(chosen[0]) as reader, part.open("wb") as out:
                    for block in iter(lambda: reader.read(CHUNK), b""):
                        done += len(block)
                        if done > MAX_UNPACKED:
                            return _fail(part, "Tệp trong zip quá lớn; không dùng.")
                        out.write(block)
                        digest.update(block)
        else:
            with source.open("rb") as reader, part.open("wb") as out:
                for block in iter(lambda: reader.read(CHUNK), b""):
                    out.write(block)
                    digest.update(block)
                    done += len(block)
        if done < MIN_BYTES:
            return _fail(part, "Tệp quá nhỏ nên không phải dữ liệu dự toán.")
        reason = check_database(part)
        if reason:
            return _fail(part, reason)
        os.replace(part, dest)
    except PermissionError:
        part.unlink(missing_ok=True)
        return {"ok": False, "message": "Tệp dữ liệu đang được dùng. Đóng các phiên agent (Claude, Codex) đang mở công cụ dutoan rồi nhập lại."}
    except (OSError, zipfile.BadZipFile) as exc:
        part.unlink(missing_ok=True)
        return {"ok": False, "message": f"Không nhập được: {exc}"}
    _remember(dest, digest.hexdigest())
    return {"ok": True, "message": f"Đã nhập dữ liệu dự toán ({done / (1024 * 1024):.0f} MB).", "sha256": digest.hexdigest()}
