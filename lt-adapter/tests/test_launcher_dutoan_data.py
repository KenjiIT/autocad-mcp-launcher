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


def gateway_opener(manifest, data, calls, fail=None):
    def opener(request, timeout=0):
        calls.append((request.full_url, request.get_header("X-team-key")))
        if fail:
            import urllib.error
            raise urllib.error.HTTPError(request.full_url, fail, "x", {}, None)
        if request.full_url.endswith("/dutoan/manifest"):
            return Response(manifest)
        return Response(data)
    return opener


def test_sync_downloads_when_missing_and_sends_key(tmp_path):
    data = make_db(tmp_path / "src.db")
    manifest = ('{"sha256":"%s"}' % hashlib.sha256(data).hexdigest()).encode()
    dest = tmp_path / "data" / "dutoan.db"
    calls = []
    result = dd.sync("https://gw.test/", "khoa", dest, opener=gateway_opener(manifest, data, calls))
    assert result["ok"] and result["changed"], result
    assert dest.read_bytes() == data
    assert [c[0] for c in calls] == ["https://gw.test/dutoan/manifest", "https://gw.test/dutoan/db"]
    assert all(c[1] == "khoa" for c in calls)


def test_sync_skips_when_hash_matches(tmp_path):
    data = make_db(tmp_path / "src.db")
    manifest = ('{"sha256":"%s"}' % hashlib.sha256(data).hexdigest()).encode()
    dest = tmp_path / "dutoan.db"
    dest.write_bytes(data)  # copied by hand, no cache file yet
    calls = []
    result = dd.sync("https://gw.test", "khoa", dest, opener=gateway_opener(manifest, data, calls))
    assert result["ok"] and not result["changed"]
    assert len(calls) == 1  # only the manifest


def test_sync_replaces_changed_file_and_keeps_old_on_bad_download(tmp_path):
    new = make_db(tmp_path / "src.db")
    dest = tmp_path / "dutoan.db"
    dest.write_bytes(b"old")
    good = ('{"sha256":"%s"}' % hashlib.sha256(new).hexdigest()).encode()
    bad = dd.sync("https://gw.test", "khoa", dest, opener=gateway_opener(good, b"x" * (dd.MIN_BYTES + 5), []))
    assert not bad["ok"] and dest.read_bytes() == b"old"
    ok = dd.sync("https://gw.test", "khoa", dest, opener=gateway_opener(good, new, []))
    assert ok["ok"] and ok["changed"] and dest.read_bytes() == new


def test_sync_reports_gateway_problems_without_touching_file(tmp_path):
    dest = tmp_path / "dutoan.db"
    dest.write_bytes(b"old")
    assert "Khóa nhóm" in dd.sync("https://gw.test", "sai", dest, opener=gateway_opener(b"", b"", [], fail=401))["message"]
    assert "chưa có dữ liệu" in dd.sync("https://gw.test", "k", dest, opener=gateway_opener(b"", b"", [], fail=404))["message"].lower()
    assert "khóa nhóm" in dd.sync("https://gw.test", "", dest)["message"].lower()
    assert "https" in dd.sync("http://gw.test", "k", dest)["message"]
    assert not dd.sync("https://gw.test", "k", dest, opener=gateway_opener(b'{"sha256":"zz"}', b"", []))["ok"]
    assert dest.read_bytes() == b"old"


def test_sync_key_prefers_own_key():
    assert dd.sync_key({"dutoan_data_key": " rieng "}, "chung") == "rieng"
    assert dd.sync_key({}, "chung") == "chung"


def test_import_plain_db_and_zip(tmp_path):
    import zipfile
    data = make_db(tmp_path / "src.db")
    dest = tmp_path / "data" / "dutoan.db"
    result = dd.import_file(tmp_path / "src.db", dest)
    assert result["ok"], result
    assert dest.read_bytes() == data and result["sha256"] == hashlib.sha256(data).hexdigest()
    assert dd.local_sha256(dest) == result["sha256"]
    archive = tmp_path / "gui.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_path / "src.db", "thu-muc/dutoan.db")
    other = tmp_path / "data2" / "dutoan.db"
    assert dd.import_file(archive, other)["ok"] and other.read_bytes() == data


def test_import_refuses_bad_files_and_keeps_current(tmp_path):
    import zipfile
    dest = tmp_path / "dutoan.db"
    dest.write_bytes(b"old")
    assert "Không tìm thấy" in dd.import_file(tmp_path / "khong-co.db", dest)["message"]
    small = tmp_path / "small.db"
    small.write_bytes(b"x" * 100)
    assert "quá nhỏ" in dd.import_file(small, dest)["message"]
    wrong = make_db(tmp_path / "w.db", tables=("don_gia",))
    assert "Thiếu bảng" in dd.import_file(tmp_path / "w.db", dest)["message"]
    two = tmp_path / "hai.zip"
    with zipfile.ZipFile(two, "w") as z:
        z.writestr("a.db", b"1")
        z.writestr("b.db", b"2")
    assert "đúng một" in dd.import_file(two, dest)["message"]
    empty = tmp_path / "rong.zip"
    with zipfile.ZipFile(empty, "w") as z:
        z.writestr("ghi-chu.txt", "khong co db")
    assert "đúng một" in dd.import_file(empty, dest)["message"]
    assert dest.read_bytes() == b"old" and not dest.with_name("dutoan.db.part").exists()
