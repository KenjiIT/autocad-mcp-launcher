"""Fail-closed checks for the Beiming interfaces used by this adapter."""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import re
from pathlib import Path


ADAPTER_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ADAPTER_ROOT.parent
CONTRACT_PATH = ADAPTER_ROOT / "contract.json"


def validate_contract(repo_root: Path = REPO_ROOT) -> list[str]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []

    def resolve(dotted_name: str):
        parts = dotted_name.split(".")
        for split in range(len(parts), 0, -1):
            try:
                obj = importlib.import_module(".".join(parts[:split]))
            except ImportError:
                continue
            for part in parts[split:]:
                obj = getattr(obj, part, None)
                if obj is None:
                    break
            else:
                return obj
        return None

    for dotted_name, required in contract["python_symbols"].items():
        obj = resolve(dotted_name)
        for symbol in required:
            if obj is None or not hasattr(obj, symbol):
                problems.append(f"missing Python symbol {dotted_name}.{symbol}")

    for dotted_name, expected in contract["python_signatures"].items():
        function = resolve(dotted_name)
        if function is None:
            continue
        actual = list(inspect.signature(function).parameters)
        if actual != expected:
            problems.append(
                f"signature changed for {dotted_name}: expected {expected}, found {actual}"
            )

    dispatcher = repo_root / "autocad-beiming-mcp-custom" / "lisp-code" / "mcp_dispatch.lsp"
    if not dispatcher.is_file():
        problems.append(f"missing upstream dispatcher {dispatcher}")
    else:
        digest = hashlib.sha256(dispatcher.read_bytes()).hexdigest().upper()
        expected_digest = contract["dispatcher_sha256"].upper()
        if digest != expected_digest:
            problems.append(
                f"upstream dispatcher hash changed: expected {expected_digest}, found {digest}"
            )
        text = dispatcher.read_text(encoding="utf-8")
        for symbol in contract["lisp_defuns"]:
            if not re.search(r"\(defun\s+" + re.escape(symbol) + r"(?:\s|\))", text, re.I):
                problems.append(f"missing upstream LISP defun {symbol}")

    for tool_name, module_name in contract["replacement_tools"].items():
        path = ADAPTER_ROOT / "py" / "lt_adapter" / "custom_tools" / f"{module_name}.py"
        if not path.is_file():
            problems.append(f"missing adapter tool module for {tool_name}: {path}")
    return problems
