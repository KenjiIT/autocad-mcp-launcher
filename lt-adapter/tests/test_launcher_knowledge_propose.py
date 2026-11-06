import importlib.util
import io
import json
import urllib.error
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "knowledge_propose", Path(__file__).resolve().parents[2] / "launcher" / "knowledge_propose.py")
kp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kp)

GOOD = """---
title: Thử
type: pitfall
topics: [cad]
status: draft
source: Phiên thử
updated: 2026-11-05
reviewed_by:
---
Nội dung hợp lệ.
"""


class FakeResponse:
    def __init__(self, status, body):
        self.status, self._body = status, json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def settings(tmp_path, **extra):
    return {"knowledge_team_key": "khoa", "knowledge_dir": str(tmp_path), **extra}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("KNOWLEDGE_TEAM_KEY", "KNOWLEDGE_GATEWAY_URL"):
        monkeypatch.delenv(name, raising=False)


def recorder(status=201, body=None):
    calls = []

    def opener(request, timeout=None):
        calls.append(request)
        return FakeResponse(status, body or {"ok": True, "id": "ab12cd34", "path": "proposals/x.md"})

    return opener, calls


def test_sends_with_key_and_default_url(tmp_path):
    opener, calls = recorder()
    payload, error = kp.propose({"slug": "loi-lt", "content": GOOD, "sender": "may-A"}, settings(tmp_path), opener)
    assert (payload["ok"], payload["sent"], payload["id"], error) == (True, True, "ab12cd34", False)
    request = calls[0]
    assert request.full_url == kp.DEFAULT_GATEWAY_URL + "/propose"
    assert request.get_header("X-team-key") == "khoa"
    assert json.loads(request.data)["slug"] == "loi-lt"


def test_custom_url_from_settings(tmp_path):
    opener, calls = recorder()
    kp.propose({"slug": "a", "content": GOOD}, settings(tmp_path, knowledge_gateway_url="https://x.test/"), opener)
    assert calls[0].full_url == "https://x.test/propose"


def test_missing_key_sends_nothing(tmp_path):
    opener, calls = recorder()
    payload, error = kp.propose({"slug": "a", "content": GOOD}, {"knowledge_dir": str(tmp_path)}, opener)
    assert error and payload["code"] == "NO_TEAM_KEY" and not calls


@pytest.mark.parametrize("bad", ["mail a@b.com", "C:\\Users\\an\\x", "gọi 0912345678",
                                 "ghp_" + "x" * 30, "Lô MADUANX-3"])
def test_sensitive_content_never_leaves_machine(tmp_path, bad):
    (tmp_path / "sensitive-terms.local.txt").write_text("# ghi chú\nMADUANX\n", encoding="utf-8")
    opener, calls = recorder()
    payload, error = kp.propose({"slug": "a", "content": GOOD + bad}, settings(tmp_path), opener)
    assert error and payload["code"] == "REJECTED_LOCALLY" and payload["sent"] is False and not calls


def test_front_matter_rules(tmp_path):
    opener, calls = recorder()
    for content in ("chỉ có chữ", GOOD.replace("status: draft", "status: confirmed"),
                    GOOD.replace("reviewed_by:", "reviewed_by: ai"), GOOD.replace("type: pitfall", "type: la")):
        payload, error = kp.propose({"slug": "a", "content": content}, settings(tmp_path), opener)
        assert error and payload["code"] == "REJECTED_LOCALLY"
    assert not calls


@pytest.mark.parametrize("slug", ["../x", "Hoa", "a b", "", None, "x" * 81])
def test_bad_slug(tmp_path, slug):
    opener, calls = recorder()
    payload, error = kp.propose({"slug": slug, "content": GOOD}, settings(tmp_path), opener)
    assert error and not payload["ok"] and not calls


def test_too_large(tmp_path):
    opener, calls = recorder()
    payload, error = kp.propose({"slug": "a", "content": GOOD + "x" * 60000}, settings(tmp_path), opener)
    assert error and not calls


def test_gateway_rejection_is_reported(tmp_path):
    def opener(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 401, "no", {}, io.BytesIO(b'{"ok":false,"error":"Sai khoa."}'))

    payload, error = kp.propose({"slug": "a", "content": GOOD}, settings(tmp_path), opener)
    assert error and payload["status"] == 401 and payload["error"] == "Sai khoa."


def test_network_failure(tmp_path):
    def opener(request, timeout=None):
        raise urllib.error.URLError("không có mạng")

    payload, error = kp.propose({"slug": "a", "content": GOOD}, settings(tmp_path), opener)
    assert error and payload["sent"] is False


def test_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_TEAM_KEY", "tu-env")
    monkeypatch.setenv("KNOWLEDGE_GATEWAY_URL", "https://env.test")
    opener, calls = recorder()
    kp.propose({"slug": "a", "content": GOOD}, {"knowledge_dir": str(tmp_path)}, opener)
    assert calls[0].full_url == "https://env.test/propose" and calls[0].get_header("X-team-key") == "tu-env"


def test_embedded_key_roundtrip_and_precedence(tmp_path, monkeypatch):
    key = "Khoa-Nhom_123!"
    assert kp.decode_key(kp.encode_key(key)) == key
    assert key not in kp.encode_key(key)
    monkeypatch.delenv("KNOWLEDGE_TEAM_KEY", raising=False)
    monkeypatch.setattr(kp, "embedded_key", lambda: key)
    assert kp.team_key({}) == key
    assert kp.team_key({"knowledge_team_key": "typed"}) == "typed"
    monkeypatch.setenv("KNOWLEDGE_TEAM_KEY", "env")
    assert kp.team_key({"knowledge_team_key": "typed"}) == "env"


def test_missing_or_broken_embedded_file_means_no_key(tmp_path, monkeypatch):
    monkeypatch.setattr(kp, "__file__", str(tmp_path / "kp.py"))
    assert kp.embedded_key() == ""
    (tmp_path / kp.EMBEDDED_KEY_FILE).write_text("!!not base64!!", encoding="ascii")
    assert kp.embedded_key() == ""
