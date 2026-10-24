from autocad_mcp.backends.base import CommandResult
from lt_adapter.lt_file_ipc import _decode_lisp_error


def test_adapter_error_prefix_becomes_nonrecoverable_parameter_error():
    message, code = _decode_lisp_error("E_PARAMETER_REJECTED|Block name already exists")
    result = CommandResult(ok=False, error=message, error_code=code,
                           recoverable=False, recommended_action="correct_request_fields")

    assert result.to_dict()["error"] == {
        "code": "E_PARAMETER_REJECTED",
        "message": "Block name already exists",
        "recoverable": False,
        "recommended_action": "correct_request_fields",
    }


def test_document_and_rollback_prefixes_are_preserved():
    assert _decode_lisp_error("E_DOCUMENT_ID_MISMATCH|Drawing changed") == (
        "Drawing changed", "E_DOCUMENT_ID_MISMATCH"
    )
    assert _decode_lisp_error("E_BATCH_ROLLED_BACK|Operation rolled back") == (
        "Operation rolled back", "E_BATCH_ROLLED_BACK"
    )


def test_unprefixed_and_unknown_errors_keep_upstream_inference_behavior():
    plain = "No more specific diagnostic"
    assert _decode_lisp_error(plain) == (plain, None)
    unknown = "E_UNKNOWN|Message"
    assert _decode_lisp_error(unknown) == (unknown, None)
