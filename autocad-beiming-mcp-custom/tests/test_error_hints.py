"""A few expensive-to-diagnose errors carry a hint that points the agent at the shared knowledge."""

import pytest

from autocad_mcp.backends.base import CommandResult
from autocad_mcp.com_sta import ComStaTimeoutError, ComStaUnavailableError
from autocad_mcp.errors import ERROR_ACTIONS, ERROR_HINTS, error_payload


@pytest.mark.parametrize("code", sorted(ERROR_HINTS))
def test_hinted_codes_point_at_the_knowledge_tool_and_the_recovery(code):
    hint = error_payload("x", code=code)["hint"]
    assert "`knowledge`" in hint and "`knowledge_propose`" in hint
    assert "hỏi người dùng" in hint  # the agent must ask, never record on its own


def test_com_lock_hint_names_the_recovery_step():
    for error in (ComStaTimeoutError("drawing.audit", 60.0), ComStaUnavailableError(poisoned=True)):
        hint = error_payload(str(error), code=error.error_code)["hint"]
        assert "operation=init" in hint and "từng layer" in hint


@pytest.mark.parametrize("code", sorted(set(ERROR_ACTIONS) - set(ERROR_HINTS)))
def test_other_errors_stay_quiet(code):
    assert "hint" not in error_payload("x", code=code)


def test_the_hint_reaches_the_command_result_envelope():
    result = CommandResult(ok=False, error="opened but not active", error_code="E_POSTCONDITION_MISMATCH")
    assert "hint" in result.to_dict()["error"]
    assert "hint" not in CommandResult(ok=False, error="x", error_code="E_LAYER_NOT_FOUND").to_dict()["error"]
