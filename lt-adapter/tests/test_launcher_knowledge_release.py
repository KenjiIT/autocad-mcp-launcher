import hashlib
import importlib.util
import io
import json
import urllib.error
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "knowledge", Path(__file__).resolve().parents[2] / "launcher" / "knowledge.py")
kn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kn)

DAY = 24 * 3600


def make_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for name, text in files.items():
            bundle.writestr(name, text)
    return buffer.getvalue()


PAGES_1 = {"wiki/index.md": "# Mục lục\n", "wiki/a/trang-a.md": "# A\n", "wiki/a/trang-cu.md": "# Cũ\n"}
PAGES_2 = {"wiki/index.md": "# Mục lục 2\n", "wiki/a/trang-a.md": "# A mới\n", "wiki/b/trang-b.md": "# B\n"}


class FakeGitHub:
    """Answers the two kinds of request the module makes and counts them."""

    def __init__(self, tag="v0.1.0", pages=PAGES_1, with_digest=True, corrupt=False, status=200):
        self.status = status
        self.etag = '"e1"'
        self.calls = []
        self.set_release(tag, pages, with_digest, corrupt)

    def set_release(self, tag, pages, with_digest=True, corrupt=False):
        self.zip = make_zip(pages)
        digest = hashlib.sha256(self.zip).hexdigest()
        sent = self.zip + b"x" if corrupt else self.zip
        self.sent = sent
        asset = {"name": kn.ASSET, "browser_download_url": "https://dl/asset.zip", "size": len(sent)}
        if with_digest:
            asset["digest"] = "sha256:" + digest
        assets = [asset]
        self.checksum_text = f"{digest}  {kn.ASSET}"
        if not with_digest:
            assets.append({"name": kn.ASSET + ".sha256", "browser_download_url": "https://dl/asset.sha256"})
        self.release = {"tag_name": tag, "body": "ghi chú", "assets": assets}

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.calls.append(url)
        if url.endswith("/releases/latest"):
            if self.status == 404:
                raise urllib.error.HTTPError(url, 404, "nf", {}, io.BytesIO(b""))
            if self.status == 500:
                raise urllib.error.HTTPError(url, 500, "err", {}, io.BytesIO(b""))
            if request.get_header("If-none-match") == self.etag:
                raise urllib.error.HTTPError(url, 304, "same", {}, io.BytesIO(b""))
            return Response(json.dumps(self.release).encode(), {"ETag": self.etag})
        if url.endswith("asset.zip"):
            return Response(self.sent)
        if url.endswith("asset.sha256"):
            return Response(self.checksum_text.encode())
        raise AssertionError(url)

    def downloads(self):
        return [c for c in self.calls if c.endswith("asset.zip")]


class Response:
    def __init__(self, data, headers=None):
        self.data, self.headers = data, headers or {}

    def read(self, size=-1):
        return self.data if size < 0 else self.data[:size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def home(tmp_path):
    return tmp_path / "kho", tmp_path / "cache.json"


def run(home, github, **kw):
    folder, cache = home
    return kn.check(folder, opener=github, cache_file=cache, **kw)


def test_first_install_writes_pages_and_version(home):
    github = FakeGitHub()
    result = run(home, github)
    assert result["state"] == "updated" and result["tag"] == "v0.1.0" and result["files"] == 2
    folder = home[0]
    assert (folder / "wiki" / "a" / "trang-a.md").read_text(encoding="utf-8") == "# A\n"
    assert kn.read_version(folder)["tag"] == "v0.1.0"


def test_same_tag_is_current_and_downloads_nothing(home):
    github = FakeGitHub()
    run(home, github)
    github.calls.clear()
    result = run(home, github, last_check=0)
    assert result["state"] == "current" and result["checked"] is True
    assert github.downloads() == []


def test_unchanged_release_costs_a_304_and_uses_the_cache(home):
    github = FakeGitHub()
    run(home, github)
    github.calls.clear()
    assert run(home, github, last_check=0)["state"] == "current"
    assert github.calls == ["https://api.github.com/repos/KenjiIT/autocad-knowledge/releases/latest"]


def test_checked_within_a_day_is_skipped_without_contacting_github(home):
    github = FakeGitHub()
    run(home, github)
    github.calls.clear()
    result = run(home, github, last_check=1000, now=1000 + DAY - 1)
    assert result["state"] == "skipped" and result["checked"] is False and github.calls == []
    assert run(home, github, last_check=1000, now=1000 + DAY + 1)["state"] == "current"


def test_missing_folder_checks_immediately_even_if_recent(home):
    github = FakeGitHub()
    result = run(home, github, last_check=999, now=1000)
    assert result["state"] == "updated"


def test_newer_tag_replaces_pages_and_removes_retracted_ones(home):
    github = FakeGitHub()
    run(home, github)
    folder = home[0]
    (folder / "proposals").mkdir()
    (folder / "proposals" / "nhap.md").write_text("chưa duyệt", encoding="utf-8")
    (folder / "sensitive-terms.local.txt").write_text("MA-DU-AN\n", encoding="utf-8")
    github.set_release("v0.2.0", PAGES_2)
    github.etag = '"e2"'
    result = run(home, github, last_check=0)
    assert result["state"] == "updated" and result["tag"] == "v0.2.0"
    assert (folder / "wiki" / "a" / "trang-a.md").read_text(encoding="utf-8") == "# A mới\n"
    assert (folder / "wiki" / "b" / "trang-b.md").is_file()
    assert not (folder / "wiki" / "a" / "trang-cu.md").exists()
    assert (folder / "proposals" / "nhap.md").read_text(encoding="utf-8") == "chưa duyệt"
    assert (folder / "sensitive-terms.local.txt").is_file()


def test_older_tag_does_not_downgrade(home):
    github = FakeGitHub(tag="v0.2.0", pages=PAGES_2)
    run(home, github)
    github.set_release("v0.1.0", PAGES_1)
    github.etag = '"e2"'
    assert run(home, github, last_check=0)["state"] == "current"
    assert kn.read_version(home[0])["tag"] == "v0.2.0"


def test_force_reinstalls_the_same_tag(home):
    github = FakeGitHub()
    run(home, github)
    folder = home[0]
    (folder / "wiki" / "a" / "trang-a.md").unlink()
    result = run(home, github, force=True)
    assert result["state"] == "updated" and (folder / "wiki" / "a" / "trang-a.md").is_file()


def test_wiki_from_an_old_main_download_is_replaced_by_the_release(home):
    folder = home[0]
    (folder / "wiki").mkdir(parents=True)
    (folder / "wiki" / "index.md").write_text("cũ", encoding="utf-8")
    (folder / "wiki" / "tu-main.md").write_text("từ main", encoding="utf-8")
    assert run(home, FakeGitHub(), last_check=10**9, now=10**9 + 1)["state"] == "updated"
    assert not (folder / "wiki" / "tu-main.md").exists()


def test_sha256_mismatch_leaves_existing_pages_untouched(home):
    github = FakeGitHub()
    run(home, github)
    github.set_release("v0.2.0", PAGES_2, corrupt=True)
    github.etag = '"e2"'
    result = run(home, github, last_check=0)
    assert result["state"] == "error"
    assert kn.read_version(home[0])["tag"] == "v0.1.0"
    assert (home[0] / "wiki" / "a" / "trang-cu.md").is_file()


def test_checksum_asset_is_used_when_the_release_has_no_digest(home):
    assert run(home, FakeGitHub(with_digest=False))["state"] == "updated"


def test_wrong_checksum_asset_is_rejected(home):
    github = FakeGitHub(with_digest=False)
    github.checksum_text = "0" * 64 + "  x"
    result = run(home, github)
    assert result["state"] == "error" and not (home[0] / "wiki").exists()


def test_entries_outside_wiki_are_ignored_never_written(home):
    pages = {"wiki/index.md": "# x" + chr(10), "/wiki/a.md": "tuyệt đối", "ngoai/b.md": "ngoài wiki", "../c.md": "lên trên"}
    result = run(home, FakeGitHub(pages=pages))
    assert result["state"] == "updated" and result["files"] == 0
    assert sorted(p.name for p in (home[0] / "wiki").rglob("*") if p.is_file()) == [".version", "index.md"]
    assert not (home[0].parent / "c.md").exists()


@pytest.mark.parametrize("bad", ["wiki/../escape.md", "wiki/C:/x.md"])
def test_path_traversal_entries_are_rejected_and_nothing_is_written(home, bad):
    pages = {"wiki/index.md": "# x\n", bad: "mal"}
    result = run(home, FakeGitHub(pages=pages))
    assert result["state"] == "error"
    assert not (home[0] / "wiki").exists() and not (home[0].parent / "escape.md").exists()


def test_archive_without_index_is_rejected(home):
    assert run(home, FakeGitHub(pages={"wiki/a.md": "x"}))["state"] == "error"


def test_no_published_release_is_reported_not_raised(home):
    result = run(home, FakeGitHub(status=404))
    assert result["state"] == "unavailable" and not (home[0] / "wiki").exists()


def test_network_failure_is_reported_not_raised(home):
    def offline(request, timeout=None):
        raise urllib.error.URLError("không có mạng")

    assert kn.check(home[0], opener=offline, cache_file=home[1])["state"] == "error"
    assert run(home, FakeGitHub(status=500))["state"] == "error"


def test_rate_limited_keeps_the_cached_answer(home):
    github = FakeGitHub()
    run(home, github)

    def limited(request, timeout=None):
        if request.full_url.endswith("/releases/latest"):
            raise urllib.error.HTTPError(request.full_url, 403, "rate", {}, io.BytesIO(b""))
        return github(request, timeout)

    assert kn.check(home[0], last_check=0, opener=limited, cache_file=home[1])["state"] == "current"


def test_release_without_the_asset_or_with_a_bad_tag_is_refused(home):
    github = FakeGitHub()
    github.release["assets"] = []
    assert run(home, github)["state"] == "error"
    github = FakeGitHub(tag="nightly")
    assert run(home, github)["state"] == "error"


@pytest.mark.parametrize("value,expected", [("v1.2.3", (1, 2, 3)), ("0.10.0", (0, 10, 0)), ("main", None), ("v1.2", None)])
def test_version_key(value, expected):
    assert kn.version_key(value) == expected
