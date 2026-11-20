"""Copy a reviewed model-space region between open AutoCAD DWG documents."""

from __future__ import annotations

import math
import os
import uuid
from pathlib import Path
from typing import Any


MAX_OBJECTS = 5_000
COM_TIMEOUT = 900.0


def _point(value: list[float] | None, label: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) not in (2, 3):
        raise ValueError(f"{label} must be [x, y] or [x, y, z]")
    point = tuple(float(part) for part in value)
    if not all(math.isfinite(part) for part in point):
        raise ValueError(f"{label} must contain finite numbers")
    return (point[0], point[1], point[2] if len(point) == 3 else 0.0)


def _dwg_path(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be an existing DWG path")
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != ".dwg":
        raise ValueError(f"{label} must be an existing DWG file")
    return str(path)


def _same_path(left: str, right: str) -> bool:
    return os.path.normcase(os.path.normpath(left)) == os.path.normcase(os.path.normpath(right))


def _region_operation(backend, request: dict[str, Any]):
    """All AutoCAD COM objects stay inside Beiming's STA worker."""
    import pythoncom
    import win32com.client

    from autocad_mcp.backends.base import CommandResult

    application = backend._get_autocad_application()
    source = application.ActiveDocument
    if not _same_path(str(source.FullName), request["source_path"]):
        return CommandResult(
            ok=False, error="The active DWG is not source_path",
            error_code="E_SOURCE_DOCUMENT_MISMATCH",
            payload={"active_path": str(source.FullName)},
        )

    target = None
    for index in range(int(application.Documents.Count)):
        candidate = application.Documents.Item(index)
        if _same_path(str(candidate.FullName), request["target_path"]):
            target = candidate
            break
    if target is None:
        return CommandResult(
            ok=False, error="Open target_path in the same AutoCAD instance first",
            error_code="E_TARGET_DOCUMENT_NOT_OPEN",
        )

    source_units = int(source.GetVariable("INSUNITS"))
    target_units = int(target.GetVariable("INSUNITS"))
    if (request["operation"] == "copy" and source_units and target_units
            and source_units != target_units and not request["allow_unit_mismatch"]):
        return CommandResult(
            ok=False, error="DWG insertion units differ; review units before copying",
            error_code="E_UNIT_MISMATCH",
            payload={"source_insunits": source_units, "target_insunits": target_units},
        )

    selection = source.SelectionSets.Add(f"MCP_REGION_{uuid.uuid4().hex[:12]}")
    copied = []
    stage = "select"
    try:
        point1 = win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8, request["corner1"]
        )
        point2 = win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8, request["corner2"]
        )
        selection.Select(0 if request["selection_mode"] == "window" else 1, point1, point2)
        if int(selection.Count) > MAX_OBJECTS:
            return CommandResult(
                ok=False, error=f"Region contains more than {MAX_OBJECTS} objects",
                error_code="E_SELECTION_TOO_LARGE",
                payload={"selected_count": int(selection.Count)},
            )

        model_owner_id = int(source.ModelSpace.ObjectID)
        source_objects = []
        skipped_other_space = 0
        for index in range(int(selection.Count)):
            entity = selection.Item(index)
            if int(entity.OwnerID) == model_owner_id:
                source_objects.append(entity)
            else:
                skipped_other_space += 1
        source_handles = [str(entity.Handle).upper() for entity in source_objects]
        evidence = {
            "source_path": request["source_path"],
            "target_path": request["target_path"],
            "selection_mode": request["selection_mode"],
            "selected_count": len(source_objects),
            "source_handles": source_handles,
            "skipped_other_space": skipped_other_space,
            "source_insunits": source_units,
            "target_insunits": target_units,
            "target_had_unsaved_changes": not bool(target.Saved),
        }
        if request["operation"] == "preview":
            return CommandResult(ok=True, payload=evidence)
        if not source_objects:
            return CommandResult(ok=False, error="Region contains no model-space objects",
                                 error_code="E_EMPTY_SELECTION", payload=evidence)
        expected = [str(handle).upper() for handle in request["expected_handles"]]
        if sorted(source_handles) != sorted(expected):
            return CommandResult(
                ok=False, error="Region selection changed since preview; preview again",
                error_code="E_SELECTION_CHANGED", payload=evidence,
            )

        # CopyObjects needs a SAFEARRAY of COM objects with one source owner.
        # Finish selection iteration before asking AutoCAD to write to target.
        stage = "copy"
        objects = win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, tuple(source_objects)
        )
        raw_copies = source.CopyObjects(objects, target.ModelSpace)
        # pywin32 returns (primary_objects, id_pairs) for this out-parameter
        # method. The COM objects inside are raw PyIDispatch pointers.
        primary_objects = (
            raw_copies[0]
            if isinstance(raw_copies, tuple) and len(raw_copies) == 2
            and isinstance(raw_copies[0], (tuple, list))
            else raw_copies
        )
        copied = [win32com.client.Dispatch(entity) for entity in primary_objects]
        if len(copied) != len(source_objects):
            raise RuntimeError("CopyObjects returned a different number of primary objects")
        if any(int(entity.OwnerID) != int(target.ModelSpace.ObjectID) for entity in copied):
            raise RuntimeError("A copied object is outside target Model Space")

        stage = "move"
        if any(request["offset"]):
            origin = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (0.0, 0.0, 0.0))
            destination = win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_R8, request["offset"]
            )
            for entity in copied:
                entity.Move(origin, destination)

        if request["save_target"]:
            stage = "save"
            target.Save()
        evidence.update(
            copied_count=len(copied),
            copied_handles=[str(entity.Handle).upper() for entity in copied],
            offset=list(request["offset"]),
            target_saved=bool(request["save_target"]),
        )
        return CommandResult(ok=True, payload=evidence)
    except Exception as exc:
        copied_handles = []
        for entity in copied:
            try:
                copied_handles.append(str(entity.Handle).upper())
            except Exception:
                pass
        # Once cloning begins, the result can be uncertain even if COM raises
        # before it returns the cloned objects. Never claim a safe retry.
        return CommandResult(
            ok=False,
            error=f"Region copy failed at {stage}: {exc}",
            error_code="E_REGION_COPY_OUTCOME_UNKNOWN" if stage != "select" else "E_REGION_SELECTION_FAILED",
            recoverable=False,
            recommended_action="inspect_target_dwg_before_retrying" if stage != "select" else None,
            payload={"stage": stage, "known_copied_handles": copied_handles,
                     "outcome_uncertain": stage != "select", "target_saved": False},
        )
    finally:
        try:
            selection.Delete()
        except Exception:
            pass


def register(mcp) -> None:
    from autocad_mcp.backends.base import CommandResult
    from autocad_mcp.backends.file_ipc import FileIPCBackend
    from autocad_mcp.client import _safe, add_screenshot_if_available, get_backend, tool_error
    from autocad_mcp.server import (
        _begin_journaled_mutation,
        _finish_journaled_mutation,
        _guard_mutation,
    )

    @mcp.tool(name="copy_region_between_dwgs", annotations={"title": "Copy DWG Region to Another DWG", "readOnlyHint": False})
    @_safe("copy_region_between_dwgs")
    async def copy_region_between_dwgs(
        operation: str,
        source_path: str,
        target_path: str,
        corner1: list[float],
        corner2: list[float],
        selection_mode: str = "window",
        offset: list[float] | None = None,
        expected_handles: list[str] | None = None,
        doc_id: str | None = None,
        expected_revision: int | None = None,
        lease_token: str | None = None,
        worker_generation: int | None = None,
        idempotency_key: str | None = None,
        allow_unit_mismatch: bool = False,
        save_target: bool = False,
    ) -> Any:
        """Preview or copy a rectangular Model Space region between open DWGs.

        The source DWG must be active; the target DWG must be open in the same
        AutoCAD instance. Use operation=preview first. Then pass its exact
        source_handles as expected_handles to operation=copy, together with
        the current source document context and a unique idempotency_key.
        Coordinates and optional offset are in WCS drawing units. Window
        selects fully enclosed objects; crossing also selects touched objects.
        Set save_target=true to save the destination DWG after copying.
        """
        if operation not in {"preview", "copy"}:
            return tool_error("operation must be preview or copy", code="E_PARAMETER_REJECTED")
        if selection_mode not in {"window", "crossing"}:
            return tool_error("selection_mode must be window or crossing", code="E_PARAMETER_REJECTED")
        try:
            source = _dwg_path(source_path, "source_path")
            target = _dwg_path(target_path, "target_path")
            if _same_path(source, target):
                raise ValueError("source_path and target_path must differ")
            first = _point(corner1, "corner1")
            second = _point(corner2, "corner2")
            displacement = _point(offset or [0.0, 0.0], "offset")
            if first[0] == second[0] or first[1] == second[1]:
                raise ValueError("Selection rectangle must have nonzero width and height")
        except (OSError, TypeError, ValueError) as exc:
            return tool_error(str(exc), code="E_PARAMETER_REJECTED")
        if operation == "copy":
            if not expected_handles or len(expected_handles) > MAX_OBJECTS:
                return tool_error("Copy requires source_handles from preview as expected_handles",
                                  code="E_PARAMETER_REJECTED")
            if not doc_id or expected_revision is None or not idempotency_key:
                return tool_error("Copy requires source doc_id, expected_revision and idempotency_key",
                                  code="E_PARAMETER_REJECTED")

        backend = await get_backend()
        if not isinstance(backend, FileIPCBackend):
            return tool_error("Copy between DWGs requires the AutoCAD backend",
                              code="E_BACKEND_UNSUPPORTED")
        guard = None
        if operation == "copy":
            guard = await _guard_mutation(
                backend, doc_id, expected_revision, lease_token, worker_generation
            )
            if not guard.ok:
                return await add_screenshot_if_available(guard, False)

        request = {
            "operation": operation,
            "source_path": source,
            "target_path": target,
            "corner1": first,
            "corner2": second,
            "selection_mode": selection_mode,
            "offset": displacement,
            "expected_handles": expected_handles or [],
            "allow_unit_mismatch": bool(allow_unit_mismatch),
            "save_target": bool(save_target),
        }
        if operation == "copy":
            replay = _begin_journaled_mutation(
                idempotency_key,
                operation="copy_region_between_dwgs.copy",
                request={**request, "doc_id": doc_id, "expected_revision": expected_revision},
                context=guard.payload,
            )
            if replay is not None:
                return await add_screenshot_if_available(replay, False)

        try:
            result = await backend._com_executor.call_async(
                f"drawing.copy_region_{operation}",
                lambda: _region_operation(backend, request),
                idempotent=operation == "preview",
                timeout=COM_TIMEOUT,
            )
        except Exception as exc:
            result = CommandResult(
                ok=False,
                error=f"AutoCAD region {operation} did not complete: {exc}",
                error_code="E_REGION_COPY_OUTCOME_UNKNOWN" if operation == "copy" else "E_REGION_SELECTION_FAILED",
                recoverable=False,
                recommended_action="inspect_target_dwg_before_retrying" if operation == "copy" else None,
                payload={"outcome_uncertain": operation == "copy"},
            )
        if operation == "copy":
            result = _finish_journaled_mutation(idempotency_key, result)
        return await add_screenshot_if_available(result, False)
