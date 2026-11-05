import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "knowledge_read", Path(__file__).resolve().parents[2] / "launcher" / "knowledge_read.py")
kr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kr)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("COMMON_KNOWLEDGE_DIR", raising=False)


@pytest.fixture
def folder(tmp_path):
    wiki = tmp_path / "wiki"
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "boc-khoi-luong").mkdir()
    (wiki / "index.md").write_text("# Mục lục\n- [Đọc mặt bằng](concepts/doc.md)\n", encoding="utf-8")
    (wiki / "concepts" / "doc.md").write_text("# Đọc mặt bằng kết cấu\n\nĐếm cột bằng hatch SOLID trên S-COLS.\n", encoding="utf-8")
    (wiki / "boc-khoi-luong" / "quy-trinh.md").write_text(
        "---\ntitle: Quy trình bóc khối lượng\ntype: howto\n---\nGom bản vẽ, đọc dầm sàn, lập bảng.\n", encoding="utf-8")
    (tmp_path / "proposals").mkdir()
    (tmp_path / "proposals" / "chua-duyet.md").write_text("dầm sàn chưa duyệt", encoding="utf-8")
    (tmp_path / "secret.md").write_text("ngoài wiki", encoding="utf-8")
    return {"knowledge_dir": str(tmp_path)}


def test_index_lists_pages_with_titles(folder):
    result = kr.index(folder)
    assert result["ok"] and "Mục lục" in result["index"]
    assert {p["path"]: p["title"] for p in result["pages"]} == {
        "concepts/doc.md": "Đọc mặt bằng kết cấu", "boc-khoi-luong/quy-trinh.md": "Quy trình bóc khối lượng"}


def test_get_reads_a_page(folder):
    assert "hatch SOLID" in kr.get("concepts/doc.md", folder)["content"]
    assert kr.get("concepts\\doc.md", folder)["ok"]


@pytest.mark.parametrize("path", ["../secret.md", "../proposals/chua-duyet.md", "concepts/../../secret.md",
                                  "concepts/khong-co.md", "", None, "index.md.exe", "C:/Windows/win.ini"])
def test_get_cannot_leave_the_wiki(folder, path):
    result = kr.get(path, folder)
    assert not result["ok"] and "content" not in result


def test_search_ignores_diacritics_and_case(folder):
    result = kr.search("KET CAU", folder)
    assert [h["path"] for h in result["results"]] == ["concepts/doc.md"]
    assert "hatch" in kr.search("hatch solid", folder)["results"][0]["snippet"]
    assert kr.search("dam san", folder)["results"][0]["path"] == "boc-khoi-luong/quy-trinh.md"


def test_search_never_returns_unreviewed_proposals(folder):
    paths = [h["path"] for h in kr.search("dầm sàn", folder)["results"]]
    assert paths and all(not p.startswith("..") and "chua-duyet" not in p for p in paths)


def test_missing_folder_tells_the_user_what_to_do(tmp_path):
    for payload in (kr.index({"knowledge_dir": str(tmp_path / "none")}), kr.get("a.md", {"knowledge_dir": str(tmp_path / "none")})):
        assert payload["code"] == "KNOWLEDGE_NOT_DOWNLOADED" and "Tải tri thức" in payload["error"]


def test_call_dispatch_and_errors(folder):
    assert kr.call({"operation": "index"}, folder)[1] is False
    assert kr.call({"operation": "search", "query": "cột"}, folder)[0]["total"] == 1
    assert kr.call({"operation": "get", "path": "x.md"}, folder)[1] is True
    assert kr.call({"operation": "xoa"}, folder)[1] is True
    assert kr.call({"operation": "search"}, folder)[1] is True


def test_env_overrides_the_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("COMMON_KNOWLEDGE_DIR", str(tmp_path))
    assert kr.knowledge_dir({"knowledge_dir": "C:/khac"}) == tmp_path


def test_index_reports_the_release_version(folder):
    assert kr.index(folder)["version"] is None
    (Path(folder["knowledge_dir"]) / "wiki" / ".version").write_text(
        '{"tag": "v0.1.0", "downloaded_at": 1793872416, "sha256": "x"}', encoding="utf-8")
    assert kr.index(folder)["version"] == {"tag": "v0.1.0", "downloaded_at": 1793872416}
    assert all(p["path"] != ".version" for p in kr.index(folder)["pages"])
