import hashlib
import json
import warnings

from autocad_mcp import client, config
from lt_adapter.contract import ADAPTER_ROOT, REPO_ROOT, validate_contract
from lt_adapter import bootstrap


def test_current_upstream_matches_adapter_contract():
    assert validate_contract() == []


def test_dispatcher_hash_drift_is_reported(tmp_path):
    source = REPO_ROOT / "autocad-beiming-mcp-custom" / "lisp-code" / "mcp_dispatch.lsp"
    destination = tmp_path / "autocad-beiming-mcp-custom" / "lisp-code" / "mcp_dispatch.lsp"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(source.read_bytes().replace(
        b"(defun mcp-dispatch-command (",
        b"(defun mcp-dispatch-command-renamed (",
        1,
    ))

    problems = validate_contract(tmp_path)

    assert any("upstream dispatcher hash changed" in problem for problem in problems)
    assert any("missing upstream LISP defun mcp-dispatch-command" in problem for problem in problems)


def test_contract_hash_is_the_pinned_dispatcher_hash():
    contract = json.loads((ADAPTER_ROOT / "contract.json").read_text(encoding="utf-8"))
    dispatcher = REPO_ROOT / "autocad-beiming-mcp-custom" / "lisp-code" / "mcp_dispatch.lsp"
    actual = hashlib.sha256(dispatcher.read_bytes()).hexdigest().upper()
    assert actual == contract["dispatcher_sha256"]


def test_contract_drift_warns_and_leaves_upstream_hooks_untouched(monkeypatch):
    original_get = client.get_backend
    original_ensure = client.ensure_backend_ready
    original_detect = config.detect_backend
    monkeypatch.setattr("lt_adapter.contract.validate_contract", lambda: ["symbol renamed"])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        bootstrap.install()

    assert client.get_backend is original_get
    assert client.ensure_backend_ready is original_ensure
    assert config.detect_backend is original_detect
    assert any("symbol renamed" in str(item.message) for item in caught)
