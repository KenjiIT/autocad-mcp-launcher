"""Register a guarded batch-delete tool on the Beiming AutoCAD MCP server."""

from __future__ import annotations

import re
from typing import Any


MAX_DELETE = 500
COM_TIMEOUT = 900.0


def _delete_operation(backend, doc_id: str, handles: list[str], continue_on_error: bool,
                     progress: list[str]):
    """Resolve and erase explicit handles inside AutoCAD's COM STA thread."""
    from autocad_mcp.backends.base import CommandResult

    application = backend._get_autocad_application()
    document = application.ActiveDocument
    context = backend._bind_document(document)
    if str(context.get("active_doc_id")) != str(doc_id):
        return CommandResult(
            ok=False, error="The active drawing changed before deletion began",
            error_code="E_DOCUMENT_ID_MISMATCH",
            payload={"active_doc_id": context.get("active_doc_id")},
        )

    # Resolve every handle before the first mutation, so stale or invalid input
    # cannot cause an avoidable partial deletion.
    objects = []
    try:
        space_ids = {int(document.ModelSpace.ObjectID), int(document.PaperSpace.ObjectID)}
        layouts = document.Layouts
        for index in range(int(layouts.Count)):
            try:
                space_ids.add(int(layouts.Item(index).Block.ObjectID))
            except Exception:
                continue
        for handle in handles:
            entity = document.HandleToObject(handle)
            if int(entity.OwnerID) not in space_ids:
                return CommandResult(
                    ok=False,
                    error=f"Handle {handle} is not an entity in Model Space or a layout; nothing was deleted",
                    error_code="E_UNSUPPORTED_OBJECT",
                    payload={"deleted_handles": [], "failed_handle": handle},
                )
            objects.append((handle, entity))
    except Exception as exc:
        return CommandResult(
            ok=False, error=f"Could not resolve every handle; nothing was deleted: {exc}",
            error_code="E_HANDLE_NOT_FOUND",
            payload={"deleted_handles": [], "failed_handle": handles[len(objects)]},
        )

    deleted: list[str] = []
    errors: list[dict[str, str]] = []
    for handle, entity in objects:
        try:
            entity.Delete()
            deleted.append(handle)
            progress.append(handle)
        except Exception as exc:
            errors.append({"handle": handle, "error": str(exc)})
            if not continue_on_error:
                break

    payload = {
        "requested": len(handles),
        "deleted_count": len(deleted),
        "deleted_handles": deleted,
        "errors": errors,
        "outcome_uncertain": False,
    }
    return CommandResult(
        ok=not errors,
        payload=payload,
        error=f"Batch delete failed after deleting {len(deleted)} object(s)" if errors else None,
        error_code="E_BATCH_FAILED" if errors else None,
    )


def register(mcp) -> None:
    from autocad_mcp.backends.file_ipc import FileIPCBackend
    from autocad_mcp.backends.base import CommandResult
    from autocad_mcp.client import _safe, add_screenshot_if_available, get_backend, tool_error
    from autocad_mcp.product_design import mark_feature_handles_invalid
    from autocad_mcp.server import (
        _begin_journaled_mutation,
        _finish_journaled_mutation,
        _guard_mutation,
    )

    @mcp.tool(name="delete_batching", annotations={"title": "Delete AutoCAD Entities in Batches", "readOnlyHint": False})
    @_safe("delete_batching")
    async def delete_batching(
        entity_ids: list[str],
        doc_id: str,
        expected_revision: int,
        lease_token: str | None = None,
        worker_generation: int | None = None,
        idempotency_key: str | None = None,
        continue_on_error: bool = False,
    ) -> Any:
        """Delete up to 500 explicit entity handles in the active DWG.

        All handles are checked before deletion starts. Deletion cannot be
        rolled back; if AutoCAD rejects a deletion, the response lists objects
        already deleted and the remaining failure details.
        """
        if not isinstance(entity_ids, list) or not entity_ids or len(entity_ids) > MAX_DELETE:
            return tool_error(f"Provide 1 to {MAX_DELETE} entity handles", code="E_PARAMETER_REJECTED")
        handles = [item.strip().upper() if isinstance(item, str) else "" for item in entity_ids]
        if any(not re.fullmatch(r"[0-9A-F]+", handle) for handle in handles):
            return tool_error("Every entity_id must be an explicit hexadecimal handle", code="E_PARAMETER_REJECTED")
        if len(set(handles)) != len(handles):
            return tool_error("Duplicate handles are not allowed", code="E_PARAMETER_REJECTED")
        if not doc_id or expected_revision is None:
            return tool_error("doc_id and expected_revision are required", code="E_PARAMETER_REJECTED")

        backend = await get_backend()
        if not isinstance(backend, FileIPCBackend):
            return tool_error("Batch deletion requires the AutoCAD backend", code="E_BACKEND_UNSUPPORTED")
        from autocad_mcp.backends.lt_file_ipc import LtFileIPCBackend
        if isinstance(backend, LtFileIPCBackend) and continue_on_error:
            return tool_error("AutoCAD LT batch deletion is atomic; set continue_on_error=false",
                              code="E_PARAMETER_REJECTED")
        guard = await _guard_mutation(backend, doc_id, expected_revision, lease_token, worker_generation)
        if not guard.ok:
            return await add_screenshot_if_available(guard, False)
        replay = _begin_journaled_mutation(
            idempotency_key,
            operation="delete_batching",
            request={"entity_ids": handles, "doc_id": doc_id,
                     "expected_revision": expected_revision, "continue_on_error": continue_on_error},
            context=guard.payload,
        )
        if replay is not None:
            return await add_screenshot_if_available(replay, False)

        deleted_progress: list[str] = []
        try:
            if isinstance(backend, LtFileIPCBackend):
                result = await backend.delete_handles(handles)
            else:
                result = await backend._com_executor.call_async(
                    "drawing.delete_batch",
                    lambda: _delete_operation(backend, doc_id, handles, continue_on_error, deleted_progress),
                    idempotent=False,
                    timeout=COM_TIMEOUT,
                )
        except Exception as exc:
            result = CommandResult(
                ok=False,
                error=f"AutoCAD batch delete did not complete; inspect the drawing before retrying: {exc}",
                error_code="E_DELETE_BATCH_OUTCOME_UNKNOWN",
                recoverable=False,
                payload={"deleted_handles": deleted_progress, "outcome_uncertain": True},
            )

        payload = result.payload if isinstance(result.payload, dict) else {}
        deleted = payload.get("deleted_handles", [])
        if deleted:
            mark_feature_handles_invalid(backend, doc_id, deleted, reason="native_entity_erased")
            for handle in deleted:
                try:
                    backend._semantic_store().pop(str(handle), None)
                except Exception:
                    pass
            context = await backend.record_document_mutation(doc_id)
            if context.ok:
                payload["document_context"] = context.to_dict()
            else:
                payload["context_error"] = context.to_dict()
        result = _finish_journaled_mutation(idempotency_key, result)
        return await add_screenshot_if_available(result, False)
