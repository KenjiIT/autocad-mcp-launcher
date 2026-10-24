from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

from lt_adapter.lt_file_ipc import (  # noqa: E402
    _lisp_unicode_to_json,
    _stage_upstream_dispatcher,
)


def test_lisp_unicode_escape_decoder_preserves_json_backslashes():
    assert _lisp_unicode_to_json(r'{"text":"vi\U+1EC7c"}') == r'{"text":"vi\u1EC7c"}'
    assert _lisp_unicode_to_json(r'{"path":"C:\\temp"}') == r'{"path":"C:\\temp"}'


def test_staged_upstream_dispatcher_renames_only_the_function_definition(tmp_path):
    source = ROOT / "autocad-beiming-mcp-custom" / "lisp-code" / "mcp_dispatch.lsp"
    destination = tmp_path / "mcp_dispatch_upstream_runtime.lsp"
    _stage_upstream_dispatcher(source, destination)

    staged = destination.read_bytes()
    assert b"(defun mcp-dispatch-command-upstream (" in staged
    assert b"'mcp-dispatch-command" in staged  # c:mcp-dispatch still resolves the overlay wrapper
    assert staged.count(b"(defun mcp-dispatch-command (") == 0


def test_staging_rejects_unexpected_upstream_dispatcher_shape(tmp_path):
    source = tmp_path / "dispatcher.lsp"
    source.write_bytes(b"(defun unrelated-command () T)")
    destination = tmp_path / "staged.lsp"

    try:
        _stage_upstream_dispatcher(source, destination)
    except ValueError as exc:
        assert "Expected one upstream dispatcher definition" in str(exc)
    else:
        raise AssertionError("Unexpected upstream shape should fail closed")
