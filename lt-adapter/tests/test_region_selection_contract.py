from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
LISP = ROOT / "lt-adapter" / "lisp" / "mcp_dispatch_lt.lsp"


def _definition(name: str) -> str:
    text = LISP.read_text(encoding="utf-8")
    match = re.search(r"\(defun\s+" + re.escape(name) + r"\b", text)
    assert match, f"Missing LISP function {name}"
    depth = 0
    in_string = escaped = in_comment = False
    for index in range(match.start(), len(text)):
        char = text[index]
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
            if depth == 0:
                return text[match.start():index + 1]
    raise AssertionError(f"Unbalanced LISP definition {name}")


def test_region_selector_scans_model_space_and_uses_wcs_bounding_boxes():
    selector = _definition("mcp-region-select")
    bounds = _definition("mcp-region-entity-bounds")
    matches = _definition("mcp-region-bounds-match-p")

    assert '(ssget "_X"' in selector
    assert "mcp-region-entity-bounds" in selector
    assert "vla-GetBoundingBox" in bounds
    assert '(= mode "crossing")' in matches
    assert '(ssget "_W"' not in _definition("mcp-cmd-region-preview-lt")
    assert '(ssget "_C"' not in _definition("mcp-cmd-region-preview-lt")
    assert "mcp-region-select" in _definition("mcp-cmd-region-preview-lt")
    assert "mcp-region-select" in _definition("mcp-cmd-region-copy-lt")
