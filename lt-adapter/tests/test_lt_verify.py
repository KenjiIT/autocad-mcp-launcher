from pathlib import Path

import pytest

from autocad_mcp.backends.base import CommandResult
from lt_adapter.lt_verify import (
    ProbeError,
    VerificationMismatch,
    assert_close,
    assert_test_document,
    diff,
    probe,
)


def test_diff_reports_handle_add_remove_modify_and_drawing_context():
    before = {
        "active_path": r"C:\Temp\Drawing1.dwg", "dbmod": 0,
        "entities": [
            {"handle": "1", "type": "LINE", "layer": "0"},
            {"handle": "2", "type": "CIRCLE", "layer": "A"},
        ],
    }
    after = {
        "active_path": r"C:\Temp\Drawing1.dwg", "dbmod": 1,
        "entities": [
            {"handle": "1", "type": "LINE", "layer": "A"},
            {"handle": "3", "type": "HATCH", "layer": "A"},
        ],
    }
    result = diff(before, after)
    assert [item["handle"] for item in result["added"]] == ["3"]
    assert [item["handle"] for item in result["removed"]] == ["2"]
    assert result["changed"][0]["handle"] == "1"
    assert result["context_changed"]["dbmod"] == {"before": 0, "after": 1}


def test_assert_close_includes_measurements_and_tolerance():
    evidence = assert_close("hatch area", 100.0, 100.0001, 0.001)
    assert evidence["passed"] is True
    assert evidence["delta"] == pytest.approx(0.0001)
    with pytest.raises(VerificationMismatch, match="exceeds tolerance"):
        assert_close("hatch area", 100.0, 101.0, 0.001)


@pytest.mark.asyncio
async def test_probe_uses_independent_dispatch_command():
    class Backend:
        async def _dispatch(self, command, params):
            assert command == "probe-entity"
            assert params == {"entity_id": "A1"}
            return CommandResult(ok=True, payload={"handle": "A1", "dxf": []})

    assert await probe(Backend(), "entity", entity_id="A1") == {"handle": "A1", "dxf": []}


@pytest.mark.asyncio
async def test_test_document_guard_allows_drawing_named_scratch_only():
    class Backend:
        def __init__(self, path):
            self.path = path

        async def document_context(self):
            return CommandResult(ok=True, payload={"active_path": self.path})

    context = await assert_test_document(Backend(r"C:\Temp\DrawingSmoke.dwg"))
    assert context["active_path"].endswith("DrawingSmoke.dwg")
    with pytest.raises(ProbeError, match="Refusing LT test"):
        await assert_test_document(Backend(r"C:\Projects\Architectural-A203.dwg"))
    test_dir = Path("C:/Temp/lt-tests")
    context = await assert_test_document(
        Backend(r"C:\Temp\lt-tests\suite-01.dwg"), test_root=test_dir
    )
    assert context["active_path"].endswith("suite-01.dwg")

