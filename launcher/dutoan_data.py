"""Download the estimating database (dutoan.db) from a link the user supplies.

The database is compiled from a commercial estimating package, so it is never
bundled with the launcher or published in a public release. The user points the
launcher at a private link (SharePoint, Drive, a private release) and, optionally,
the expected SHA-256; the file is checked and only then put in place.
"""

import hashlib
import os
import sqlite3
import urllib.request
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


def download(url, expected_sha256="", dest=None, progress=None, opener=urllib.request.urlopen):
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
        request = urllib.request.Request(url, headers={"user-agent": "autocad-mcp-launcher"})
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
    return {"ok": True, "message": f"Đã tải dữ liệu dự toán ({done / (1024 * 1024):.0f} MB).", "sha256": digest.hexdigest()}


def _fail(part, message):
    Path(part).unlink(missing_ok=True)
    return {"ok": False, "message": message}
