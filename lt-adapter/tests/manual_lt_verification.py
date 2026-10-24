"""Manual, guarded integration verification against an open AutoCAD LT session.

Run with the custom MCP venv on Windows. The runner only mutates an empty
Drawing*.dwg or a drawing under AUTOCAD_MCP_LT_TEST_ROOT and removes every
test entity before returning. It never saves the drawing.
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lt-adapter" / "py"))
sys.path.insert(0, str(ROOT / "autocad-beiming-mcp-custom" / "src"))

from lt_adapter.lt_file_ipc import LtFileIPCBackend  # noqa: E402
from lt_adapter.lt_verify import (  # noqa: E402
    ProbeError,
    assert_test_document,
    diff,
    entity,
    probe,
    snapshot,
    write_report,
)


def _check(name: str, status: str, started: float, message: str = "", evidence: Any = None) -> dict[str, Any]:
    result = {"name": name, "status": status, "message": message,
              "duration_seconds": round(time.perf_counter() - started, 4)}
    if evidence is not None:
        result["evidence"] = evidence
    return result


async def run() -> int:
    # A second Python backend can inject commands into the same LT window while
    # the launcher server is active. Refuse that unsafe dual-dispatch setup.
    try:
        with socket.create_connection(("127.0.0.1", 8876), timeout=0.2):
            raise ProbeError("Stop the launcher Beiming MCP server before running this standalone verifier")
    except OSError:
        pass
    backend = LtFileIPCBackend()
    checks: list[dict[str, Any]] = []
    baseline: dict[str, Any] | None = None
    before_handles: set[str] = set()
    checks_failed = False
    test_root = os.environ.get("AUTOCAD_MCP_LT_TEST_ROOT")
    try:
        started = time.perf_counter()
        ready = await backend.ensure_ready()
        if not ready.ok:
            raise ProbeError(f"LT is not ready: {ready.error or ready.error_code}")
        context = await assert_test_document(backend, test_root=test_root)
        baseline = await snapshot(backend)
        if int(baseline.get("entity_count", -1)) != 0:
            raise ProbeError(
                f"Refusing to mutate non-empty test drawing: {baseline.get('entity_count')} entities"
            )
        before_handles = {str(item["handle"]) for item in baseline.get("entities", [])}
        checks.append(_check("LT dispatcher and test drawing guard", "passed", started,
                             evidence={"context": context, "snapshot": baseline}))

        started = time.perf_counter()
        var_data = await probe(backend, "vars", names_str="INSUNITS;OSMODE;CLAYER;DBMOD")
        checks.append(_check("Read-only system variable probe", "passed", started, evidence=var_data))

        started = time.perf_counter()
        rectangle = await backend.create_rectangle(1000, 1000, 2000, 2000, "0")
        if not rectangle.ok:
            raise ProbeError(f"Rectangle creation failed: {rectangle.error}")
        rectangle_handle = str((rectangle.payload or {}).get("handle", ""))
        if not rectangle_handle:
            raise ProbeError("Rectangle creation returned no handle")
        rectangle_readback = await entity(backend, rectangle_handle)
        rectangle_area = await probe(backend, "area", entity_id=rectangle_handle)
        expected_area = 1_000_000.0
        if rectangle_readback.get("type") != "LWPOLYLINE" or rectangle_readback.get("layer") != "0":
            raise ProbeError(f"Rectangle read-back mismatch: {rectangle_readback}")
        if abs(float(rectangle_area["area"]) - expected_area) > 0.01:
            raise ProbeError(f"Rectangle area mismatch: expected {expected_area}, got {rectangle_area}")
        rectangle_bbox = await probe(backend, "bbox", handles_str=rectangle_handle)
        if rectangle_bbox.get("min") != [1000.0, 1000.0, 0.0] or rectangle_bbox.get("max") != [2000.0, 2000.0, 0.0]:
            raise ProbeError(f"Rectangle bounding box mismatch: {rectangle_bbox}")
        layer_zero = await probe(backend, "layer", name="0")
        checks.append(_check("Rectangle and independent entity/area probes", "passed", started,
                             evidence={"handle": rectangle_handle, "entity": rectangle_readback,
                                       "area": rectangle_area, "expected_area": expected_area,
                                       "tolerance": 0.01, "bbox": rectangle_bbox,
                                       "layer_0": layer_zero}))

        started = time.perf_counter()
        created_hatch = await backend.create_hatch(rectangle_handle, "ANSI31", 0, 25, "0")
        verified_hatch = await backend.verify_created_hatch(
            created_hatch, entity_id=rectangle_handle, pattern="ANSI31", angle=0, scale=25,
            layer="0", boundary_area=expected_area,
        )
        if not verified_hatch.ok:
            raise ProbeError(f"Rectangle hatch verification failed: {verified_hatch.payload or verified_hatch.error}")
        checks.append(_check("Hatch on closed polyline", "passed", started,
                             evidence=verified_hatch.payload))

        started = time.perf_counter()
        circle = await backend.create_circle(3500, 1500, 100, "0")
        if not circle.ok:
            raise ProbeError(f"Circle creation failed: {circle.error}")
        circle_handle = str((circle.payload or {}).get("handle", ""))
        circle_area = await probe(backend, "area", entity_id=circle_handle)
        circle_bbox = await probe(backend, "bbox", handles_str=circle_handle)
        expected_circle_area = 3.141592653589793 * 100.0**2
        if abs(float(circle_area["area"]) - expected_circle_area) > 0.000001:
            raise ProbeError(f"Circle area mismatch: {circle_area}")
        if circle_bbox.get("min") != [3400.0, 1400.0, 0.0] or circle_bbox.get("max") != [3600.0, 1600.0, 0.0]:
            raise ProbeError(f"Circle bounding box mismatch: {circle_bbox}")
        circle_hatch = await backend.create_hatch(circle_handle, "ANSI31", 0, 25, "0")
        verified_circle_hatch = await backend.verify_created_hatch(
            circle_hatch, entity_id=circle_handle, pattern="ANSI31", angle=0, scale=25,
            layer="0", boundary_area=expected_circle_area,
        )
        if not verified_circle_hatch.ok:
            raise ProbeError(f"Circle hatch verification failed: {verified_circle_hatch.payload or verified_circle_hatch.error}")
        checks.append(_check("Hatch on circle", "passed", started,
                             evidence={"boundary": circle_area, "bbox": circle_bbox,
                                       "hatch": verified_circle_hatch.payload}))

        started = time.perf_counter()
        before_invalid = await snapshot(backend)
        no_such_handle = await backend.create_hatch("DEADBEEF", "ANSI31", 0, 1, "0")
        after_invalid = await snapshot(backend)
        invalid_diff = diff(before_invalid, after_invalid)
        if no_such_handle.ok or invalid_diff["added"] or invalid_diff["removed"] or invalid_diff["changed"]:
            raise ProbeError("Invalid hatch handle was not rejected without changing the drawing")
        checks.append(_check("Invalid hatch handle is rejected", "passed", started,
                             evidence={"error": no_such_handle.error, "diff": invalid_diff}))

        started = time.perf_counter()
        current = await snapshot(backend)
        handles = [str(item["handle"]) for item in current.get("entities", [])
                   if str(item["handle"]) not in before_handles]
        if handles:
            rejected_delete = await backend.delete_handles([handles[0], "DEADBEEF"])
            after_rejected_delete = await snapshot(backend)
            if rejected_delete.ok or diff(current, after_rejected_delete)["removed"]:
                raise ProbeError("Delete batch with one invalid handle changed the drawing")
            checks.append(_check("Delete batch validates all handles before mutation", "passed", started,
                                 evidence={"handles": handles, "error": rejected_delete.error}))
        else:
            checks.append(_check("Delete batch negative control", "blocked", started,
                                 "No test handles were available"))
    except Exception as exc:
        checks_failed = True
        checks.append({"name": "LT verification run", "status": "failed",
                       "message": f"{type(exc).__name__}: {exc}"})
    finally:
        # Remove only handles that did not exist in the baseline.
        if baseline is not None:
            try:
                after = await snapshot(backend)
                extras = [str(item["handle"]) for item in after.get("entities", [])
                          if str(item["handle"]) not in before_handles]
                started = time.perf_counter()
                cleanup = await backend.delete_handles(extras) if extras else None
                final = await snapshot(backend)
                remaining = diff(baseline, final)
                passed = not remaining["added"] and not remaining["removed"] and not remaining["changed"]
                if cleanup is not None and not cleanup.ok:
                    passed = False
                checks.append(_check("Cleanup and baseline entity restoration",
                                     "passed" if passed else "failed", started,
                                     evidence={"deleted_handles": extras,
                                               "cleanup": cleanup.to_dict() if cleanup else None,
                                               "final_diff": remaining,
                                               "drawing_saved": False}))
                checks_failed = checks_failed or not passed
            except Exception as exc:
                checks_failed = True
                checks.append({"name": "Cleanup", "status": "failed",
                               "message": f"{type(exc).__name__}: {exc}", "drawing_saved": False})
        await backend.shutdown()

        report = {
            "backend": "file_ipc_lt",
            "mode": "manual_live_lt",
            "checks": checks,
            "status": "failed" if checks_failed else "completed",
            "drawing_saved": False,
        }
        md, js = write_report(report, output_root=ROOT / "output" / "lt_verify")
        print(f"Report: {md}")
        print(f"JSON:   {js}")
        for check in checks:
            print(f"{check['status'].upper():7} {check['name']}: {check.get('message', '')}")
    return 1 if checks_failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

