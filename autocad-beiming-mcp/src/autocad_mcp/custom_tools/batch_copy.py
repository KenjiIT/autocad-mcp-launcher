"""Register a bounded batch-copy tool on the Beiming MCP server."""

from __future__ import annotations

import math
from typing import Any


MAX_COPIES = 100


def register(mcp) -> None:
    from autocad_mcp.backends.base import CommandResult
    from autocad_mcp.client import _safe, add_screenshot_if_available, get_backend, tool_error
    from autocad_mcp.server import (
        _attach_document_context,
        _begin_journaled_mutation,
        _finish_journaled_mutation,
        _guard_mutation,
    )

    @mcp.tool(name="copy_batching", annotations={"title": "Copy AutoCAD Entities in Batches", "readOnlyHint": False})
    @_safe("copy_batching")
    async def copy_batching(
        entity_ids: list[str],
        offsets: list[list[float]],
        doc_id: str | None = None,
        expected_revision: int | None = None,
        lease_token: str | None = None,
        worker_generation: int | None = None,
        idempotency_key: str | None = None,
        continue_on_error: bool = False,
        rollback_on_error: bool = True,
    ) -> Any:
        """Copy each source entity at each [dx, dy] offset from its original position.

        Examples: many entity_ids with one offset; one entity_id with many
        offsets. At most 100 copies per call. On failure, successful copies are
        erased by default; rollback errors are returned explicitly.
        """
        if not entity_ids or not offsets or len(entity_ids) * len(offsets) > MAX_COPIES:
            return tool_error(
                f"Provide source handles and offsets for 1 to {MAX_COPIES} copies",
                code="E_PARAMETER_REJECTED",
            )
        if continue_on_error and rollback_on_error:
            return tool_error(
                "Set rollback_on_error=false when continue_on_error=true",
                code="E_PARAMETER_REJECTED",
            )
        if any(not isinstance(handle, str) or not handle.strip() or handle.lower() == "last"
               for handle in entity_ids):
            return tool_error("Every entity_id must be an explicit handle", code="E_PARAMETER_REJECTED")
        try:
            displacements = []
            for pair in offsets:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    raise ValueError("Each offset must be [dx, dy]")
                dx, dy = float(pair[0]), float(pair[1])
                if not math.isfinite(dx) or not math.isfinite(dy):
                    raise ValueError("Offsets must be finite numbers")
                displacements.append((dx, dy))
        except (TypeError, ValueError) as exc:
            return tool_error(str(exc), code="E_PARAMETER_REJECTED")

        backend = await get_backend()
        guard = await _guard_mutation(
            backend, doc_id, expected_revision, lease_token, worker_generation
        )
        if not guard.ok:
            return await add_screenshot_if_available(guard, False)
        replay = _begin_journaled_mutation(
            idempotency_key,
            operation="copy_batching",
            request={
                "entity_ids": entity_ids,
                "offsets": displacements,
                "doc_id": doc_id,
                "expected_revision": expected_revision,
                "continue_on_error": continue_on_error,
                "rollback_on_error": rollback_on_error,
            },
            context=guard.payload,
        )
        if replay is not None:
            return await add_screenshot_if_available(replay, False)

        results: list[dict[str, Any]] = []
        created_handles: list[str] = []
        failures = 0
        suspended_fit = hasattr(backend, "_suspend_auto_fit")
        if suspended_fit:
            backend._suspend_auto_fit += 1
        try:
            for entity_id in entity_ids:
                for dx, dy in displacements:
                    try:
                        copied = await backend.entity_copy(entity_id, dx, dy)
                    except Exception as exc:
                        copied = CommandResult(
                            ok=False,
                            error=f"Copy outcome is uncertain: {exc}",
                            error_code="E_COPY_OUTCOME_UNKNOWN",
                            recoverable=False,
                        )
                    if copied.ok and not (
                        isinstance(copied.payload, dict) and copied.payload.get("handle")
                    ):
                        copied = CommandResult(
                            ok=False,
                            error="Copy returned no handle; inspect the drawing before retrying",
                            error_code="E_COPY_HANDLE_MISSING",
                            recoverable=False,
                        )
                    entry = {
                        "source_handle": entity_id,
                        "offset": [dx, dy],
                        **copied.to_dict(),
                    }
                    results.append(entry)
                    if copied.ok and isinstance(copied.payload, dict) and copied.payload.get("handle"):
                        created_handles.append(str(copied.payload["handle"]))
                    else:
                        failures += 1
                        if not continue_on_error:
                            break
                if failures and not continue_on_error:
                    break
        finally:
            if suspended_fit:
                backend._suspend_auto_fit = max(0, backend._suspend_auto_fit - 1)

        rolled_back: list[str] = []
        rollback_errors: list[dict[str, str]] = []
        if failures and rollback_on_error:
            for handle in reversed(created_handles):
                try:
                    erased = await backend.entity_erase(handle)
                    if erased.ok:
                        rolled_back.append(handle)
                    else:
                        rollback_errors.append({"handle": handle, "error": erased.error or "unknown"})
                except Exception as exc:
                    rollback_errors.append({"handle": handle, "error": str(exc)})

        payload: dict[str, Any] = {
            "requested": len(entity_ids) * len(displacements),
            "processed": len(results),
            "failures": failures,
            "results": results,
            "created_handles": created_handles,
            "rolled_back": rolled_back,
            "rollback_errors": rollback_errors,
            "remaining_handles": [handle for handle in created_handles if handle not in rolled_back],
            "outcome_uncertain": any(
                entry.get("error", {}).get("code") in {"E_COPY_OUTCOME_UNKNOWN", "E_COPY_HANDLE_MISSING"}
                for entry in results
            ) or bool(rollback_errors),
        }
        result = CommandResult(
            ok=failures == 0,
            payload=payload,
            error=f"Copy batch failed after {len(results)} attempts" if failures else None,
            error_code="E_BATCH_FAILED" if failures else None,
        )
        if result.ok:
            result = await _attach_document_context(backend, result, doc_id=doc_id, mutated=True)
        elif created_handles and doc_id:
            context = await backend.record_document_mutation(doc_id)
            payload["document_context"] = context.to_dict()
        result = _finish_journaled_mutation(idempotency_key, result)
        return await add_screenshot_if_available(result, False)
