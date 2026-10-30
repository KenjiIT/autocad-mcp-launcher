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


def test_drawing_save_uses_activex_and_never_replaces_without_permission():
    saver = _definition("mcp-cmd-drawing-save-lt")
    assert "vla-SaveAs" in saver and "vla-Save" in saver and "(command" not in saver
    assert "E_FILE_EXISTS" in saver and '(/= replace "1")' in saver
    # Same-path check after SaveAs, and the dirty flag is reported back for verification.
    assert "E_POSTCONDITION_MISMATCH" in saver
    assert "DBMOD" in _definition("mcp-lt-save-result")
    assert '(= cmd-name "drawing-save-lt") (mcp-cmd-drawing-save-lt params-json)' in LISP.read_text(encoding="utf-8")
