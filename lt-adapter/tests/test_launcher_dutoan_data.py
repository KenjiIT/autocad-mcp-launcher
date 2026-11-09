import hashlib
import importlib.util
import io
import sqlite3
from contextlib import closing
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "dutoan_data", Path(__file__).resolve().parents[2] / "launcher" / "dutoan_data.py")
dd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dd)


def make_db(path, tables=("don_gia", "dinh_muc", "tu_dien_vat_tu"), pad=dd.MIN_BYTES + 10):
    with closing(sqlite3.connect(path)) as conn:
        for name in tables:
            conn.execute(f"create table {name} (id integer)")
        conn.execute("create table pad (x blob)")
        conn.execute("insert into pad values (?)", (b"0" * pad,))
        conn.commit()
    return Path(path).read_bytes()


class Response(io.BytesIO):
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def opener_for(data):
    return lambda request, timeout=0: Response(data)


def test_good_download_is_verified_and_installed(tmp_path):
    data = make_db(tmp_path / "src.db")
    dest = tmp_path / "data" / "dutoan.db"
    seen = []
    result = dd.download("https://example.test/dutoan.db", hashlib.sha256(data).hexdigest(), dest,
                         progress=lambda d, t: seen.append(d), opener=opener_for(data))
    assert result["ok"], result
    assert dest.read_bytes() == data and seen and not dest.with_name("dutoan.db.part").exists()


def test_hash_mismatch_keeps_existing_file(tmp_path):
    data = make_db(tmp_path / "src.db")
    dest = tmp_path / "dutoan.db"
    dest.write_bytes(b"old")
    result = dd.download("https://example.test/x", "0" * 64, dest, opener=opener_for(data))
    assert not result["ok"] and "SHA-256" in result["message"]
    assert dest.read_bytes() == b"old" and not dest.with_name("dutoan.db.part").exists()


def test_login_page_and_wrong_database_are_refused(tmp_path):
    dest = tmp_path / "dutoan.db"
    assert "quá nhỏ" in dd.download("https://x.test/a", "", dest, opener=opener_for(b"<html>login</html>"))["message"]
    wrong = make_db(tmp_path / "w.db", tables=("don_gia",))
    assert "Thiếu bảng" in dd.download("https://x.test/a", "", dest, opener=opener_for(wrong))["message"]
    assert not dest.exists()


def test_rejects_non_https_and_bad_hash_format(tmp_path):
    assert not dd.download("http://x.test/a", "", tmp_path / "d.db")["ok"]
    assert not dd.download("https://x.test/a", "zz", tmp_path / "d.db")["ok"]


def test_describe_reports_presence(tmp_path):
    assert not dd.describe(tmp_path / "none.db")["present"]
    path = tmp_path / "dutoan.db"
    make_db(path)
    assert dd.describe(path)["present"]
