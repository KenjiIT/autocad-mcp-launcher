"""COM-free, read-only AutoCAD LT probes and verification helpers.

The probes are independent dispatcher commands. They deliberately do not use
the result returned by the mutating tool being verified.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autocad_mcp.backends.base import CommandResult


PROBE_COMMANDS = {
    "snapshot": "probe-snapshot",
    "entity": "probe-entity",
    "vars": "probe-vars",
    "area": "probe-area",
    "hatch": "probe-hatch",
    "bbox": "probe-bbox",
    "layer": "probe-layer",
    "block": "probe-block",
}


class ProbeError(RuntimeError):
    """A read-only LT probe could not return trustworthy data."""


class VerificationMismatch(AssertionError):
    """An observed value differs from the requested contract."""


async def probe(backend: Any, kind: str, **params: Any) -> dict[str, Any]:
    """Run one independent AutoLISP/IPC probe and return its payload."""
    try:
        command = PROBE_COMMANDS[kind]
    except KeyError as exc:
        raise ValueError(f"Unknown LT probe: {kind}") from exc
    result: CommandResult = await backend._dispatch(command, params)
    if not result.ok or not isinstance(result.payload, dict):
        raise ProbeError(f"LT probe {kind!r} failed: {result.error or result.error_code}")
    return result.payload


async def snapshot(backend: Any) -> dict[str, Any]:
    """Capture model-space entity handles, types, layers, and drawing state."""
    return await probe(backend, "snapshot")


async def entity(backend: Any, handle: str) -> dict[str, Any]:
    return await probe(backend, "entity", entity_id=handle)


async def area(backend: Any, handle: str) -> dict[str, Any]:
    return await probe(backend, "area", entity_id=handle)


async def hatch(backend: Any, handle: str) -> dict[str, Any]:
    return await probe(backend, "hatch", entity_id=handle)


async def variables(backend: Any, names: list[str]) -> dict[str, Any]:
    if not names or any(";" in name or not name for name in names):
        raise ValueError("Provide system variable names without semicolons")
    return await probe(backend, "vars", names_str=";".join(names))


async def bbox(backend: Any, handles: list[str]) -> dict[str, Any]:
    if not handles or any(";" in handle or not handle for handle in handles):
        raise ValueError("Provide entity handles without semicolons")
    return await probe(backend, "bbox", handles_str=";".join(handles))


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare snapshots by handle; report added, removed, and changed entities."""
    old = {str(e["handle"]): e for e in before.get("entities", [])}
    new = {str(e["handle"]): e for e in after.get("entities", [])}
    added = [{"handle": key, **new[key]} for key in sorted(new.keys() - old.keys())]
    removed = [{"handle": key, **old[key]} for key in sorted(old.keys() - new.keys())]
    changed = []
    for key in sorted(old.keys() & new.keys()):
        if old[key] != new[key]:
            changed.append({"handle": key, "before": old[key], "after": new[key]})
    context_fields = ("active_path", "document_name", "dbmod")
    context = {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in context_fields if before.get(key) != after.get(key)
    }
    return {"added": added, "removed": removed, "changed": changed, "context_changed": context}


def assert_close(label: str, expected: float, actual: float, tolerance: float) -> dict[str, Any]:
    """Assert a numeric measurement and return the evidence for reports."""
    values = (expected, actual, tolerance)
    if not all(math.isfinite(float(value)) for value in values) or tolerance < 0:
        raise VerificationMismatch(
            f"{label}: invalid measurement; expected={expected!r}, actual={actual!r}, tolerance={tolerance!r}"
        )
    delta = abs(float(expected) - float(actual))
    evidence = {"label": label, "expected": expected, "actual": actual,
                "delta": delta, "tolerance": tolerance, "passed": delta <= tolerance}
    if delta > tolerance:
        raise VerificationMismatch(
            f"{label}: expected {expected}, observed {actual}, delta {delta} exceeds tolerance {tolerance}"
        )
    return evidence


async def assert_test_document(backend: Any, *, test_root: str | Path | None = None) -> dict[str, Any]:
    """Refuse mutations unless the active document meets the plan's test guard."""
    result: CommandResult = await backend.document_context()
    if not result.ok or not isinstance(result.payload, dict):
        raise ProbeError(f"Cannot verify active LT document: {result.error or result.error_code}")
    context = result.payload
    path = Path(str(context.get("active_path") or "")).resolve()
    is_named_test = path.name.casefold().startswith("drawing") and path.suffix.casefold() == ".dwg"
    is_under_root = False
    if test_root is not None:
        root = Path(test_root).resolve()
        try:
            path.relative_to(root)
            is_under_root = True
        except ValueError:
            pass
    if not (is_named_test or is_under_root):
        raise ProbeError(f"Refusing LT test on non-test drawing: {path}")
    return context


def write_report(report: dict[str, Any], *, output_root: str | Path = "output/lt_verify") -> tuple[Path, Path]:
    """Write matching JSON and Markdown evidence files and return their paths."""
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    json_path, markdown_path = root / f"{stamp}.json", root / f"{stamp}.md"
    serializable = {"created_at": datetime.now(timezone.utc).isoformat(), **report}
    json_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# AutoCAD LT verification report", "", f"Created: {serializable['created_at']}", ""]
    for item in serializable.get("checks", []):
        state = item.get("status", "unknown").upper()
        lines.append(f"- **{state}** {item.get('name', 'unnamed')}: {item.get('message', '')}")
        if "evidence" in item:
            lines.append(f"  - Evidence: `{json.dumps(item['evidence'], ensure_ascii=False)}`")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return markdown_path, json_path

