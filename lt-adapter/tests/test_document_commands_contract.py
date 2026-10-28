from test_region_selection_contract import LISP, _definition


def test_drawing_open_decodes_path_checks_file_and_activates_the_result():
    opener = _definition("mcp-cmd-drawing-open-lt")
    assert "findfile" in opener and "mcp-lt-decode-json-u" in opener
    assert "E_PARAMETER_REJECTED|DWG file not found" in opener
    assert "vla-Open" in opener
    # Documents.Open leaves the old drawing active; both the already-open and the new branch must switch.
    assert opener.count("vla-put-ActiveDocument") == 2
    # Success is only reported after the drawing is found in the document list.
    assert opener.index("E_POSTCONDITION_MISMATCH") < opener.rindex("vla-put-ActiveDocument")


def test_document_commands_are_routed_by_the_dispatcher():
    text = LISP.read_text(encoding="utf-8")
    assert '(= cmd-name "drawing-open") (mcp-cmd-drawing-open-lt params-json)' in text
    assert '(= cmd-name "document-activate-lt") (mcp-cmd-document-activate-lt params-json)' in text
    assert "vla-put-ActiveDocument" in _definition("mcp-cmd-document-activate-lt")
