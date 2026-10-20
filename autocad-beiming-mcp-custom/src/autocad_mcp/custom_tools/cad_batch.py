"""Bounded multi-operation CAD batch for the standard AutoCAD backend."""

from __future__ import annotations

from typing import Any


MAX_OPERATIONS = 100


def register(mcp) -> None:
    from autocad_mcp.backends.file_ipc import FileIPCBackend
    from autocad_mcp.backends.base import CommandResult
    from autocad_mcp.client import _safe, add_screenshot_if_available, get_backend, tool_error
    from autocad_mcp.server import (
        _begin_journaled_mutation,
        _finish_journaled_mutation,
        _guard_mutation,
        _require_existing_layer,
    )

    @mcp.tool(name="cad_batch", annotations={"title": "Run a Bounded CAD Operation Batch", "readOnlyHint": False})
    @_safe("cad_batch")
    async def cad_batch(
        operations: list[dict[str, Any]],
        doc_id: str,
        expected_revision: int,
        lease_token: str | None = None,
        worker_generation: int | None = None,
        idempotency_key: str | None = None,
        verbose: bool = False,
    ) -> Any:
        """Run up to 100 entity operations in one MCP request.

        Supported ops: create_line, create_circle, create_polyline,
        create_rectangle, create_arc, create_ellipse, create_text,
        create_mtext, copy, move, rotate, scale, erase, get, count, list.
        An entity_id may use "$<step>.handle" to reference a handle returned
        by an earlier step (for example "$0.handle"). Mutating batches use
        an AutoCAD undo transaction and roll back on the first failure.
        """
        if not isinstance(operations, list) or not operations or len(operations) > MAX_OPERATIONS:
            return tool_error(f"Provide 1 to {MAX_OPERATIONS} operations", code="E_PARAMETER_REJECTED")
        if not doc_id or expected_revision is None:
            return tool_error("doc_id and expected_revision are required", code="E_PARAMETER_REJECTED")

        allowed = {
            "create_line", "create_circle", "create_polyline", "create_rectangle",
            "create_arc", "create_ellipse", "create_text", "create_mtext",
            "copy", "move", "rotate", "scale", "erase", "get", "count", "list",
        }
        validated: list[dict[str, Any]] = []
        for index, item in enumerate(operations):
            if not isinstance(item, dict) or item.get("op") not in allowed:
                return tool_error(f"Operation {index} has an unsupported op", code="E_PARAMETER_REJECTED")
            params = item.get("params", {})
            if not isinstance(params, dict):
                return tool_error(f"Operation {index} params must be an object", code="E_PARAMETER_REJECTED")
            validated.append({"op": item["op"], "params": params})

        backend = await get_backend()
        if not isinstance(backend, FileIPCBackend):
            return tool_error("cad_batch currently requires the AutoCAD file_ipc backend", code="E_BACKEND_UNSUPPORTED")
        guard = await _guard_mutation(backend, doc_id, expected_revision, lease_token, worker_generation)
        if not guard.ok:
            return await add_screenshot_if_available(guard, False)
        replay = _begin_journaled_mutation(
            idempotency_key,
            operation="cad_batch",
            request={"operations": validated, "doc_id": doc_id, "expected_revision": expected_revision},
            context=guard.payload,
        )
        if replay is not None:
            return await add_screenshot_if_available(replay, False)

        mutating = any(item["op"] not in {"get", "count", "list"} for item in validated)
        transaction_id = None
        if mutating:
            begin = await backend.transaction_begin(doc_id, expected_revision)
            if not begin.ok:
                result = CommandResult(ok=False, error=begin.error or "Could not begin CAD batch transaction", error_code=begin.error_code or "E_TRANSACTION_BEGIN", payload={"transaction": begin.to_dict()})
                result = _finish_journaled_mutation(idempotency_key, result)
                return await add_screenshot_if_available(result, False)
            transaction_id = (begin.payload or {}).get("transaction_id")

        results: list[dict[str, Any]] = []
        failed = False

        def resolve(value: Any) -> Any:
            if isinstance(value, str) and value.startswith("$") and "." in value:
                head, path = value[1:].split(".", 1)
                source = results[int(head)]["result"]
                if not path.startswith("payload.") and "payload" in source and path.split(".", 1)[0] not in source:
                    source = source["payload"]
                elif path.startswith("payload."):
                    path = path.removeprefix("payload.")
                for part in path.split("."):
                    source = source[part]
                return source
            if isinstance(value, list):
                return [resolve(part) for part in value]
            if isinstance(value, dict):
                return {key: resolve(part) for key, part in value.items()}
            return value

        for index, item in enumerate(validated):
            op = item["op"]
            try:
                p = resolve(item["params"])
                if op.startswith("create_") and p.get("layer"):
                    layer_check = await _require_existing_layer(backend, p["layer"])
                    if not layer_check.ok:
                        payload = layer_check.to_dict()
                        results.append({"index": index, "op": op, "result": payload})
                        failed = True
                        break
                if op == "create_line":
                    call = backend.create_line(p["x1"], p["y1"], p["x2"], p["y2"], p.get("layer"))
                elif op == "create_circle":
                    call = backend.create_circle(p["cx"], p["cy"], p["radius"], p.get("layer"))
                elif op == "create_polyline":
                    call = backend.create_polyline(p["points"], p.get("closed", False), p.get("layer"))
                elif op == "create_rectangle":
                    call = backend.create_rectangle(p["x1"], p["y1"], p["x2"], p["y2"], p.get("layer"))
                elif op == "create_arc":
                    call = backend.create_arc(p["cx"], p["cy"], p["radius"], p["start_angle"], p["end_angle"], p.get("layer"))
                elif op == "create_ellipse":
                    call = backend.create_ellipse(p["cx"], p["cy"], p["major_x"], p["major_y"], p["ratio"], p.get("layer"))
                elif op == "create_text":
                    call = backend.create_text(p["x"], p["y"], p["text"], p.get("height", 2.5), p.get("rotation", 0), p.get("layer"))
                elif op == "create_mtext":
                    call = backend.create_mtext(p["x"], p["y"], p["width"], p["text"], p.get("height", 2.5), p.get("layer"))
                elif op == "copy":
                    call = backend.entity_copy(p["entity_id"], p["dx"], p["dy"])
                elif op == "move":
                    call = backend.entity_move(p["entity_id"], p["dx"], p["dy"])
                elif op == "rotate":
                    call = backend.entity_rotate(p["entity_id"], p["cx"], p["cy"], p["angle"])
                elif op == "scale":
                    call = backend.entity_scale(p["entity_id"], p["cx"], p["cy"], p["factor"])
                elif op == "erase":
                    call = backend.entity_erase(p["entity_id"])
                elif op == "get":
                    call = backend.entity_get_with_semantics(p["entity_id"])
                elif op == "count":
                    call = backend.entity_count(p.get("layer"))
                else:
                    call = backend.entity_list(p.get("layer"))
                response = await call
                payload = response.to_dict()
            except Exception as exc:
                payload = {"ok": False, "error": str(exc), "error_code": "E_BATCH_OPERATION_FAILED"}
            entry = {"index": index, "op": op, "result": payload}
            results.append(entry)
            if not payload.get("ok"):
                failed = True
                break

        transaction_result = None
        if transaction_id:
            finish = (
                backend.transaction_rollback(transaction_id, doc_id, expected_revision)
                if failed else backend.transaction_commit(transaction_id, doc_id, expected_revision)
            )
            transaction_result = (await finish).to_dict()
            if not transaction_result.get("ok"):
                failed = True

        if not verbose:
            for entry in results:
                raw = entry["result"]
                payload = raw.get("payload") or {}
                if isinstance(payload, dict):
                    keep = {key: payload[key] for key in ("handle", "handles", "count", "entity_count", "doc_id", "revision") if key in payload}
                    raw["payload"] = keep
        result = CommandResult(
            ok=not failed,
            error="CAD batch failed; inspect per-step results and transaction status" if failed else None,
            error_code="E_CAD_BATCH_FAILED" if failed else None,
            payload={"requested": len(validated), "processed": len(results), "atomic": bool(transaction_id), "results": results, "transaction": transaction_result},
        )
        if transaction_id and not failed:
            context = await backend.record_document_mutation(doc_id)
            if context.ok:
                result.payload["document_context"] = context.to_dict()
            else:
                result = CommandResult(ok=False, error="Batch committed but document context readback failed", error_code="E_MUTATION_CONTEXT_UNAVAILABLE", payload={**result.payload, "mutation_committed": True, "context_error": context.to_dict()})
        result = _finish_journaled_mutation(idempotency_key, result)
        return await add_screenshot_if_available(result, False)
