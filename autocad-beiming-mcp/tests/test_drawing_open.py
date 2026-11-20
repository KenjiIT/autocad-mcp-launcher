"""drawing.open must verify the result instead of trusting the AutoLISP "opened" reply."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from autocad_mcp.backends.base import CommandResult
from autocad_mcp.backends.file_ipc import FileIPCBackend


def make_backend():
    backend = object.__new__(FileIPCBackend)
    backend._audit_cache_by_document = {"doc": 1}
    backend._entity_semantics_by_document = {"doc": 1}
    backend._active_document_dispatch_key = lambda: "doc"
    backend.document_context = AsyncMock(return_value=CommandResult(ok=True, payload={"active_path": "x"}))
    return backend


@pytest.fixture
def dwg(tmp_path):
    path = tmp_path / "ban ve.dwg"
    path.write_bytes(b"0")
    return str(path)


def run(coro):
    return asyncio.run(coro)


def test_opens_through_com_and_never_uses_lisp(dwg):
    backend = make_backend()
    backend._open_via_com = lambda path: {"opened": path, "already_open": False, "renderer": "autocad-com-open"}
    backend._dispatch = AsyncMock()
    result = run(backend.drawing_open(dwg))
    assert result.ok and result.payload["opened"] == dwg and result.payload["renderer"] == "autocad-com-open"
    assert result.payload["requested_path"] == str(Path(dwg).resolve())
    backend._dispatch.assert_not_called()
    assert backend._audit_cache_by_document == {} and backend._entity_semantics_by_document == {}


def test_missing_file_is_rejected_without_touching_autocad(dwg):
    backend = make_backend()

    def boom(path):
        raise FileNotFoundError(f"Drawing file not found: {path}")

    backend._open_via_com = boom
    backend._dispatch = AsyncMock()
    result = run(backend.drawing_open(dwg + ".missing"))
    assert not result.ok and result.error_code == "E_PARAMETER_REJECTED"
    backend._dispatch.assert_not_called()


def test_lisp_false_success_is_reported_as_failure(dwg):
    """The reported bug: LISP says "opened" while the file never opened."""
    backend = make_backend()

    def no_com(path):
        raise RuntimeError("COM unavailable")

    backend._open_via_com = no_com
    backend._dispatch = AsyncMock(return_value=CommandResult(ok=True, payload="opened: " + dwg))
    backend.document_context = AsyncMock(
        return_value=CommandResult(ok=True, payload={"active_path": r"C:\other\a-303.dwg"}))
    original = backend._wait_until_active
    backend._wait_until_active = lambda path, timeout=0.0: original(path, timeout=0.0)
    result = run(backend.drawing_open(dwg))
    assert not result.ok
    assert result.error_code == "E_POSTCONDITION_MISMATCH"
    assert "COM unavailable" in result.error and "a-303" in result.error


def test_lisp_fallback_succeeds_when_the_drawing_really_became_active(dwg):
    backend = make_backend()

    def no_com(path):
        raise RuntimeError("COM unavailable")

    backend._open_via_com = no_com
    backend._dispatch = AsyncMock(return_value=CommandResult(ok=True, payload={"opened": dwg}))
    backend.document_context = AsyncMock(return_value=CommandResult(ok=True, payload={"active_path": dwg}))
    result = run(backend.drawing_open(dwg))
    assert result.ok and result.payload["opened"] == dwg and result.payload["requested_path"]


def test_lisp_failure_passes_through(dwg):
    backend = make_backend()

    def no_com(path):
        raise RuntimeError("COM unavailable")

    backend._open_via_com = no_com
    backend._dispatch = AsyncMock(return_value=CommandResult(ok=False, error="Path required", error_code="E_PARAMETER_REJECTED"))
    result = run(backend.drawing_open(dwg))
    assert not result.ok and result.error == "Path required"


def test_same_file_ignores_case_and_relative_parts(tmp_path):
    path = tmp_path / "A.dwg"
    path.write_bytes(b"0")
    assert FileIPCBackend._same_file(str(path), str(path).upper())
    assert FileIPCBackend._same_file(str(tmp_path / "x" / ".." / "A.dwg"), str(path))
    assert not FileIPCBackend._same_file(str(path), str(tmp_path / "B.dwg"))
