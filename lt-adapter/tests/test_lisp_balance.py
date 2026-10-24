from pathlib import Path


def _balance(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    depth = 0
    in_string = False
    escaped = False
    in_comment = False
    for char in text:
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == ";":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            assert depth >= 0, f"Unexpected closing parenthesis in {path}"
    assert not in_string, f"Unclosed string in {path}"
    return depth


def test_mcp_dispatch_lisp_balanced():
    root = Path(__file__).resolve().parents[2]
    dispatchers = (
        root / "autocad-beiming-mcp-custom" / "lisp-code" / "mcp_dispatch.lsp",
        root / "lt-adapter" / "lisp" / "mcp_dispatch_lt.lsp",
    )
    for dispatcher in dispatchers:
        assert dispatcher.is_file(), f"Missing dispatcher: {dispatcher}"
        assert not dispatcher.read_bytes().startswith(b"\xef\xbb\xbf"), f"AutoLISP file has a UTF-8 BOM: {dispatcher}"
        assert _balance(dispatcher) == 0
