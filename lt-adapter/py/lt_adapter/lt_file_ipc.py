"""AutoCAD LT for Windows: AutoLISP file IPC, without Python COM automation."""

from __future__ import annotations

import asyncio
import ctypes
import json
import math
import os
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

from autocad_mcp import __version__
from autocad_mcp.backends.base import BackendCapabilities, CommandResult
from autocad_mcp.backends.file_ipc import FileIPCBackend
from autocad_mcp.config import LISP_DIR
from lt_adapter.lt_window import find_lt_window
from autocad_mcp.session import DocumentState, ProcessState, TransportState, UiState
from autocad_mcp.variables import validate_variable_updates


_LISP_UNICODE_ESCAPE = re.compile(r"\\\\|\\U\+([0-9A-Fa-f]{4})")
_UPSTREAM_DISPATCH_DEFINITION = b"(defun mcp-dispatch-command ("
_STAGED_DISPATCH_DEFINITION = b"(defun mcp-dispatch-command-upstream ("
_LT_ERROR_ACTIONS = {
    "E_PARAMETER_REJECTED": (False, "correct_request_fields"),
    "E_LAYER_NOT_FOUND": (False, "create_or_select_an_existing_layer"),
    "E_VARIABLE_REJECTED": (False, "use_whitelisted_variable_and_value"),
    "E_DOCUMENT_ID_MISMATCH": (False, "read_latest_document_context_and_retry"),
    "E_SOURCE_DOCUMENT_MISMATCH": (False, "activate_the_declared_source_drawing_and_retry"),
    "E_BATCH_ROLLED_BACK": (True, "correct_batch_and_retry"),
    "E_POSTCONDITION_MISMATCH": (False, "stop_and_inspect_backend_state"),
    "E_SYSTEM_CALL_FAILED": (True, "inspect_operation_inputs_and_system_error"),
}


def _decode_lisp_error(message: str | None) -> tuple[str | None, str | None]:
    """Read an adapter-owned ``E_CODE|message`` prefix, if present."""
    if not message:
        return message, None
    match = re.match(r"^(E_[A-Z0-9_]+)\|(.*)$", message, flags=re.DOTALL)
    if not match or match.group(1) not in _LT_ERROR_ACTIONS:
        return message, None
    return match.group(2), match.group(1)


def _lisp_unicode_to_json(text: str) -> str:
    """Translate LT's cp1252 ``\\U+XXXX`` text escapes into JSON escapes."""
    def convert(match: re.Match) -> str:
        return match.group(0) if match.group(1) is None else f"\\u{match.group(1)}"
    return _LISP_UNICODE_ESCAPE.sub(convert, text)


def _stage_upstream_dispatcher(source: Path, destination: Path) -> None:
    """Rename only the upstream dispatcher definition for the LT overlay hook."""
    contents = source.read_bytes()
    count = contents.count(_UPSTREAM_DISPATCH_DEFINITION)
    if count != 1:
        raise ValueError(f"Expected one upstream dispatcher definition in {source}; found {count}")
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(contents.replace(_UPSTREAM_DISPATCH_DEFINITION,
                                           _STAGED_DISPATCH_DEFINITION, 1))
    temporary.replace(destination)


class LtFileIPCBackend(FileIPCBackend):
    """Keep Beiming's tool surface but bind the dispatcher through LT AutoLISP."""

    _UNSUPPORTED = frozenset({
        "drawing_activate", "drawing_create", "drawing_close", "drawing_copy_dwg",
        "drawing_save_as_dxf", "drawing_render_preview", "recover", "show_window",
        "apply_presentation_style", "prepare_recording_view",
        "product_render_view", "solid_create_box", "solid_create_cylinder", "solid_extrude",
        "solid_revolve", "solid_sweep", "solid_boolean", "product_create_feature",
        "drawing_save", "drawing_plot_pdf", "drawing_audit", "entity_trim",
        "entity_extend", "entity_join", "create_dimension_linear",
        "create_dimension_aligned", "create_dimension_angular", "create_dimension_radius",
        "zoom_extents",
    })

    def __getattribute__(self, name):
        if name in type(self)._UNSUPPORTED:
            async def unavailable(*_args, **_kwargs):
                return CommandResult(
                    ok=False,
                    error=f"{name} is not supported by the AutoCAD LT backend",
                    error_code="E_NOT_SUPPORTED_ON_LT",
                    recoverable=False,
                    recommended_action="use_a_supported_LT_tool_or_switch_to_full_autocad",
                )
            return unavailable
        return super().__getattribute__(name)

    @property
    def name(self) -> str:
        return "file_ipc_lt"

    @property
    def capabilities(self) -> BackendCapabilities:
        base = super().capabilities.__dict__.copy()
        base.update(can_create_solids=False, can_boolean_solids=False,
                    can_product_features=False)
        return BackendCapabilities(**base)

    def _send_command_via_com(self, command: str) -> bool:
        return False

    def _get_autocad_application(self):
        raise RuntimeError("Python COM automation is unavailable for the AutoCAD LT backend")

    def _active_document_dispatch_key(self) -> str:
        return getattr(self, "_lt_active_document_key", "")

    def _cancel_active_command(self) -> str:
        target = self._command_hwnd or self._hwnd
        if not target:
            return "no-window"
        user32 = ctypes.windll.user32
        for _ in range(2):
            user32.PostMessageW(target, 0x0100, 0x1B, 0)
            user32.PostMessageW(target, 0x0101, 0x1B, 0)
        return "win32-message"

    def _wait_for_autocad_idle(self, timeout: float = 2.0) -> bool:
        # The inherited COM CMDACTIVE probe is unavailable in LT.  The IPC
        # result file is written after the LISP command finishes instead.
        return bool(self._hwnd and ctypes.windll.user32.IsWindow(self._hwnd))

    @staticmethod
    def _should_auto_fit(command: str) -> bool:
        return False

    async def ensure_ready(self) -> CommandResult:
        selected = find_lt_window()
        if selected is None:
            return CommandResult(
                ok=False,
                error="Open AutoCAD LT 2024+ with a drawing; set AUTOCAD_MCP_ACAD_PID if multiple LT windows are open",
                error_code="E_AUTOCAD_LT_WINDOW_UNAVAILABLE",
                recoverable=True,
            )
        hwnd, pid = selected
        self._hwnd, self._acad_process_id = hwnd, pid
        self._command_hwnd = self._find_command_line_hwnd()
        self._ipc_dir.mkdir(parents=True, exist_ok=True)
        self._session.bind_worker(process_id=pid, hwnd=hwnd, owned=False, generation=pid)
        self._session.process_state = ProcessState.READY
        async with self._lock:
            ready = await self._load_dispatcher_unlocked()
            if not ready.ok:
                return ready
            context = await self._context_unlocked()
        if not context.ok:
            return context
        self._session.transport_state = TransportState.COM_READY
        self._session.document_state = DocumentState.READY
        self._session.ui_state = UiState.IDLE
        return CommandResult(ok=True, payload={
            "ready": True, "transport": "file_ipc_lt", "autocad": {
                "product": "AutoCAD LT", "running": True, "hwnd": hwnd,
                "process_id": pid, "active_document": context.payload["document_name"],
                "active_document_path": context.payload["active_path"],
            }, "document_context": context.payload,
            "dispatcher": {"loaded": True, "version": self._dispatcher_version},
        })

    async def _load_dispatcher_unlocked(self) -> CommandResult:
        repo_root = Path(__file__).resolve().parents[3]
        upstream = Path(os.environ.get("AUTOCAD_MCP_LISP_PATH", "") or LISP_DIR / "mcp_dispatch.lsp")
        overlay_source = repo_root / "lt-adapter" / "lisp" / "mcp_dispatch_lt.lsp"
        overlay_runtime = upstream.parent / f".mcp_dispatch_lt_runtime_{os.getpid()}.lsp"
        upstream_runtime = upstream.parent / f".mcp_dispatch_upstream_runtime_{os.getpid()}.lsp"
        if not overlay_source.is_file():
            return CommandResult(ok=False, error=f"LT adapter overlay missing: {overlay_source}", error_code="E_DISPATCHER_NOT_FOUND")
        try:
            _stage_upstream_dispatcher(upstream, upstream_runtime)
            temporary = overlay_runtime.with_suffix(overlay_runtime.suffix + ".tmp")
            shutil.copyfile(overlay_source, temporary)
            temporary.replace(overlay_runtime)
        except OSError as exc:
            return CommandResult(ok=False, error=f"Cannot stage LT adapter in the trusted LISP folder: {exc}", error_code="E_DISPATCHER_NOT_LOADED")
        for path in (upstream_runtime, overlay_runtime):
            if not path.is_file():
                return CommandResult(ok=False, error=f"Dispatcher file missing: {path}", error_code="E_DISPATCHER_NOT_FOUND")
            expression = f'(load "{str(path.resolve()).replace(chr(92), "/")}")'
            if not self._type_command(expression):
                return CommandResult(ok=False, error=f"Could not load dispatcher file in LT: {path.name}", error_code="E_DISPATCHER_NOT_LOADED")
            await asyncio.sleep(0.35)
        ping = await self._dispatch_unlocked("ping", {})
        version = ping.payload.get("dispatcher_version") if ping.ok and isinstance(ping.payload, dict) else None
        if version != __version__:
            return CommandResult(ok=False, error=f"LT dispatcher ping/version failed: {ping.error or version}", error_code="E_DISPATCHER_NOT_LOADED")
        self._dispatcher_version = version
        return ping

    async def _dispatch_unlocked(self, command: str, params: dict) -> CommandResult:
        """Run the upstream IPC protocol, decoding LT's cp1252 Unicode escapes."""
        from autocad_mcp.backends import file_ipc as upstream

        request_id = uuid.uuid4().hex[:12]
        cmd_file = self._ipc_dir / f"autocad_mcp_cmd_{request_id}.json"
        result_file = self._ipc_dir / f"autocad_mcp_result_{request_id}.json"
        tmp_file = cmd_file.with_suffix(".tmp")
        try:
            clean_params = {key: value for key, value in params.items() if value is not None}
            payload = {"request_id": request_id, "command": command,
                       "params": clean_params, "ts": time.time()}
            tmp_file.write_text(json.dumps(payload), encoding="utf-8")
            tmp_file.rename(cmd_file)
            if not self._type_dispatch_trigger():
                crash = upstream.detect_autocad_crash_state(self._hwnd, self._acad_process_id)
                if crash.get("crashed"):
                    return self._autocad_crashed_result(crash, command)
                return CommandResult(ok=False, error="LT command state remained blocked after cancellation",
                                     error_code="E_COMMAND_STATE_BLOCKED")
            deadline = time.time() + upstream.TIMEOUT
            while time.time() < deadline:
                crash = upstream.detect_autocad_crash_state(self._hwnd, self._acad_process_id)
                if crash.get("crashed"):
                    return self._autocad_crashed_result(crash, command)
                if result_file.exists():
                    try:
                        try:
                            result_text = result_file.read_text(encoding="utf-8")
                        except UnicodeDecodeError:
                            result_text = result_file.read_text(encoding="cp1252")
                        data = json.loads(_lisp_unicode_to_json(result_text))
                        if data.get("request_id") == request_id:
                            self._wait_for_autocad_idle(timeout=2.0)
                            error, error_code = _decode_lisp_error(data.get("error"))
                            error_options = _LT_ERROR_ACTIONS.get(error_code, (None, None))
                            result = CommandResult(
                                ok=data.get("ok", False), payload=data.get("payload"),
                                error=error, error_code=error_code,
                                recoverable=error_options[0],
                                recommended_action=error_options[1],
                            )
                            if result.ok and self._should_auto_fit(command):
                                self._auto_fit_view()
                            return result
                    except (json.JSONDecodeError, OSError):
                        pass
                await asyncio.sleep(upstream.POLL_INTERVAL)
            self._cancel_active_command()
            crash = upstream.detect_autocad_crash_state(self._hwnd, self._acad_process_id)
            if crash.get("crashed"):
                return self._autocad_crashed_result(crash, command)
            return CommandResult(ok=False,
                                 error=f"Timeout waiting for LT result (request_id={request_id})",
                                 error_code="E_IPC_TIMEOUT")
        finally:
            for file_path in (cmd_file, result_file, tmp_file):
                try:
                    file_path.unlink(missing_ok=True)
                except OSError:
                    pass

    async def _context_unlocked(self) -> CommandResult:
        result = await self._dispatch_unlocked("document-context", {})
        if not result.ok or not isinstance(result.payload, dict):
            return result
        path = str(result.payload.get("active_path") or "")
        name = str(result.payload.get("document_name") or "")
        key = os.path.normcase(path or name)
        self._lt_active_document_key = key
        lease = self._session.bind_document(key, path=path, name=name)
        return CommandResult(ok=True, payload={
            **self._session.context(lease), "backend": self.name,
            "transport": "file_ipc_lt", "dbmod": result.payload.get("dbmod"),
        })

    async def document_context(self) -> CommandResult:
        async with self._lock:
            if find_lt_window() != (self._hwnd, self._acad_process_id):
                return CommandResult(ok=False, error="LT instance changed; call system.ensure_ready",
                                     error_code="E_SESSION_GENERATION_MISMATCH")
            ready = await self._load_dispatcher_unlocked()
            return await self._context_unlocked() if ready.ok else ready

    async def _dispatch(self, command: str, params: dict) -> CommandResult:
        async with self._lock:
            selected = find_lt_window()
            if selected is None or selected != (self._hwnd, self._acad_process_id):
                return CommandResult(ok=False, error="LT instance changed; call system.ensure_ready", error_code="E_SESSION_GENERATION_MISMATCH")
            ready = await self._load_dispatcher_unlocked()
            if not ready.ok:
                return ready
            context = await self._context_unlocked()
            if not context.ok:
                return context
            return await self._dispatch_unlocked(command, {
                **params, "_expected_document_path": context.payload["active_path"]
            })

    async def status(self) -> CommandResult:
        selected = find_lt_window()
        return CommandResult(ok=True, payload={
            "backend": self.name, "transport": "file_ipc_lt",
            "ready": bool(selected and selected == (self._hwnd, self._acad_process_id)
                          and self._dispatcher_version == __version__),
            "hwnd": self._hwnd, "process_id": self._acad_process_id,
            "dispatcher_version": self._dispatcher_version,
            "session": self._session.snapshot(),
        })

    async def _create_with_com_fallback(
        self, kind: str, params: dict, layer: str | None, command: str, dispatch_params: dict
    ) -> CommandResult:
        """Create supported entities through AutoLISP without probing Python COM."""
        result = await self._dispatch(command, dispatch_params)
        if result.ok and isinstance(result.payload, dict):
            result.payload.setdefault("renderer", "autolisp")
        return result

    async def entity_get(self, entity_id) -> CommandResult:
        """Read entity data through IPC; LT has no Python COM fallback."""
        result = await self._dispatch("entity-get", {"entity_id": entity_id})
        if result.ok and isinstance(result.payload, dict):
            semantics = self._semantic_store().get(str(entity_id))
            if semantics:
                result.payload["semantics"] = dict(semantics)
        return result

    _LAYER_COLORS = frozenset({"red", "yellow", "green", "cyan", "blue", "magenta", "white"})

    async def layer_set_properties(self, name, color=None, linetype=None, lineweight=None) -> CommandResult:
        """Set layer properties through the layer's ActiveX object; upstream uses COM and a LISP entmod LT rejects."""
        if color is not None:
            text = str(color).strip().lower()
            if not ((text.isdigit() and 0 < int(text) < 256) or text in self._LAYER_COLORS):
                return CommandResult(ok=False, error=f"Unsupported layer colour: {color}",
                                     error_code="E_PARAMETER_REJECTED")
        check = await self.layer_exists(str(name))
        if not check.ok or not isinstance(check.payload, dict) or not check.payload.get("exists"):
            return CommandResult(ok=False, error=f"Layer does not exist: {name}",
                                 error_code="E_LAYER_NOT_FOUND")
        return await self._dispatch("layer-set-properties", {
            "name": name,
            "color": str(color) if color is not None else None,
            "linetype": linetype,
            "lineweight": str(lineweight) if lineweight is not None else None,
        })

    async def create_hatch(self, entity_id, pattern="ANSI31", angle=0.0, scale=1.0, layer=None) -> CommandResult:
        if not re.fullmatch(r"[0-9A-Fa-f]+", str(entity_id)):
            return CommandResult(ok=False, error="LT hatch requires an explicit boundary handle",
                                 error_code="E_PARAMETER_REJECTED")
        if not isinstance(pattern, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", pattern):
            return CommandResult(ok=False, error="Invalid hatch pattern", error_code="E_PARAMETER_REJECTED")
        try:
            numeric_scale, numeric_angle = float(scale), float(angle)
        except (TypeError, ValueError):
            return CommandResult(ok=False, error="Invalid hatch scale or angle", error_code="E_PARAMETER_REJECTED")
        if not math.isfinite(numeric_scale) or numeric_scale <= 0 or not math.isfinite(numeric_angle):
            return CommandResult(ok=False, error="Hatch scale must be positive", error_code="E_PARAMETER_REJECTED")
        if layer:
            check = await self.layer_exists(str(layer))
            if not check.ok or not isinstance(check.payload, dict) or not check.payload.get("exists"):
                return CommandResult(ok=False, error=f"Hatch layer does not exist: {layer}", error_code="E_LAYER_NOT_FOUND")
        return await self._dispatch("create-hatch-lt", {
            "entity_id": str(entity_id), "pattern": pattern,
            "angle": numeric_angle, "scale": numeric_scale, "layer": layer,
        })

    async def verify_created_hatch(
        self, result: CommandResult, *, entity_id: str, pattern: str,
        angle: float, scale: float, layer: str | None = None,
        boundary_area: float | None = None,
        boundary_bounds: dict | None = None,
        tolerance: float = 0.000001,
    ) -> CommandResult:
        """Verify LT hatch state through an independent read-only LISP probe.

        The generic FileIPC verifier reads entities through Python COM first.
        LT must instead query the hatch and its boundary via the dispatcher.
        """
        if not result.ok or not isinstance(result.payload, dict):
            return result
        handle = str(result.payload.get("handle") or "")
        requested = {
            "type": "HATCH", "layer": str(layer or "0"),
            "pattern": str(pattern), "angle": float(angle),
            "scale": float(scale), "boundary_entity_id": str(entity_id),
        }
        differences: list[dict] = []
        actual = None
        if not handle:
            differences.append({"path": "handle", "requested": "created handle", "actual": None})
        else:
            readback = await self._dispatch("probe-hatch", {"entity_id": handle})
            actual = readback.payload if readback.ok and isinstance(readback.payload, dict) else None
            if actual is None:
                differences.append({"path": "probe-hatch", "requested": "readable HATCH", "actual": readback.error})
            else:
                for field, expected in (("type", "HATCH"), ("layer", requested["layer"]), ("pattern", str(pattern))):
                    value = actual.get(field)
                    if str(value).casefold() != expected.casefold():
                        differences.append({"path": field, "requested": expected, "actual": value})
                for field, expected in (("angle", float(angle)), ("scale", float(scale))):
                    try:
                        value = float(actual[field])
                    except (KeyError, TypeError, ValueError):
                        differences.append({"path": field, "requested": expected, "actual": actual.get(field)})
                        continue
                    delta = (value - expected + 180.0) % 360.0 - 180.0 if field == "angle" else value - expected
                    if not math.isfinite(value) or abs(delta) > tolerance:
                        differences.append({"path": field, "requested": expected, "actual": value, "tolerance": tolerance})

                # Measure the boundary independently from the hatch command result.
                boundary = await self._dispatch("probe-area", {"entity_id": str(entity_id)})
                boundary_payload = boundary.payload if boundary.ok and isinstance(boundary.payload, dict) else None
                measured_boundary_area = boundary_payload.get("area") if boundary_payload else None
                try:
                    expected_area = float(measured_boundary_area)
                    measured_hatch_area = float(actual.get("area"))
                except (TypeError, ValueError):
                    expected_area = math.nan
                    measured_hatch_area = math.nan
                if not math.isfinite(expected_area) or not math.isfinite(measured_hatch_area):
                    differences.append({"path": "area", "requested": measured_boundary_area, "actual": actual.get("area")})
                else:
                    area_tolerance = max(tolerance, abs(expected_area) * 1e-8)
                    if abs(measured_hatch_area - expected_area) > area_tolerance:
                        differences.append({"path": "area", "requested": expected_area, "actual": measured_hatch_area, "tolerance": area_tolerance})

        if differences:
            deletion = await self.entity_erase(handle) if handle else CommandResult(ok=False, error="No hatch handle to clean up")
            return CommandResult(
                ok=False, error=f"Created HATCH {handle or '<no handle>'} failed LT read-back verification",
                error_code="E_POSTCONDITION_MISMATCH", recoverable=False,
                recommended_action="inspect_the_LT_probe_result",
                payload={"handle": handle or None, "requested": requested, "actual": actual,
                         "diff": differences, "deleted": deletion.ok, "delete_error": deletion.error},
            )
        return CommandResult(ok=True, payload={
            **result.payload, "verified": True,
            "actual": actual, "boundary_area_verified": expected_area,
            "hatch_area_verified": measured_hatch_area, "diff": [],
        })

    async def delete_handles(self, handles: list[str]) -> CommandResult:
        return await self._dispatch("entity-delete-batch", {"handles_str": ";".join(handles)})

    async def layer_exists(self, name: str) -> CommandResult:
        return await self._dispatch("layer-exists-lt", {"name": str(name)})

    async def drawing_set_variables(self, values: dict) -> CommandResult:
        try:
            updates = validate_variable_updates(values)
        except ValueError as exc:
            return CommandResult(ok=False, error=str(exc), error_code="E_VARIABLE_REJECTED")
        encoded = ";".join(f"{key}={format(float(value), '.12g')}" for key, value in updates.items())
        return await self._dispatch("drawing-set-variables-lt", {"updates_str": encoded})

    async def entity_set_layer(self, entity_ids, layer) -> CommandResult:
        if not isinstance(entity_ids, (list, tuple)) or not entity_ids:
            return CommandResult(ok=False, error="Provide entity handles", error_code="E_PARAMETER_REJECTED")
        handles = [str(handle).strip().upper() for handle in entity_ids]
        if any(not re.fullmatch(r"[0-9A-F]+", handle) for handle in handles) or len(set(handles)) != len(handles):
            return CommandResult(ok=False, error="Entity handles must be unique hexadecimal handles", error_code="E_PARAMETER_REJECTED")
        exists = await self.layer_exists(str(layer))
        if not exists.ok or not isinstance(exists.payload, dict) or not exists.payload.get("exists"):
            return CommandResult(ok=False, error=f"Layer does not exist: {layer}", error_code="E_LAYER_NOT_FOUND")
        return await self._dispatch("entity-set-layer-lt", {
            "handles_str": ";".join(handles), "layer": str(layer),
        })

    async def entity_erase_layers(self, layers) -> CommandResult:
        names = [str(item).strip() for item in layers if str(item).strip()]
        if not names or any(name.casefold() == "0" for name in names):
            return CommandResult(ok=False, error="Refusing to erase layer 0 or an empty layer list", error_code="E_PARAMETER_REJECTED")
        return await self._dispatch("entity-erase-layers-lt", {"layers_str": ";".join(names)})

    async def entity_set_hatch_pattern(self, entity_ids, pattern="SOLID") -> CommandResult:
        handles = [str(handle).strip().upper() for handle in entity_ids]
        if not handles or any(not re.fullmatch(r"[0-9A-F]+", h) for h in handles):
            return CommandResult(ok=False, error="Provide valid hatch handles", error_code="E_PARAMETER_REJECTED")
        if not isinstance(pattern, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", pattern):
            return CommandResult(ok=False, error="Invalid hatch pattern", error_code="E_PARAMETER_REJECTED")
        return await self._dispatch("entity-set-hatch-pattern-lt", {
            "handles_str": ";".join(handles), "pattern": pattern,
        })

    async def entity_create_lines_file(self, path) -> CommandResult:
        try:
            with open(str(path), "r", encoding="utf-8") as handle:
                rows = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return CommandResult(ok=False, error=f"Cannot read line input file: {exc}", error_code="E_PARAMETER_REJECTED")
        if not isinstance(rows, list) or not rows or len(rows) > 5000:
            return CommandResult(ok=False, error="Line file must contain 1 to 5000 rows", error_code="E_PARAMETER_REJECTED")
        encoded = []
        for row in rows:
            if not isinstance(row, dict) or str(row.get("type", "line")).lower() != "line":
                return CommandResult(ok=False, error="AutoCAD LT line files accept LINE rows only", error_code="E_PARAMETER_REJECTED")
            layer = str(row.get("layer", "")).strip()
            if not layer or any(char in layer for char in ",;\"\\"):
                return CommandResult(ok=False, error="Line layer name is empty or contains a reserved separator", error_code="E_PARAMETER_REJECTED")
            try:
                coords = [float(row[key]) for key in ("x1", "y1", "x2", "y2")]
            except (KeyError, TypeError, ValueError):
                return CommandResult(ok=False, error="Each line requires numeric x1, y1, x2, y2", error_code="E_PARAMETER_REJECTED")
            if not all(math.isfinite(value) for value in coords):
                return CommandResult(ok=False, error="Line coordinates must be finite", error_code="E_PARAMETER_REJECTED")
            encoded.append(",".join([*(format(value, ".12g") for value in coords), layer]))
        return await self._dispatch("entity-create-lines-lt", {"lines_str": ";".join(encoded)})

    async def block_define(self, name, entities) -> CommandResult:
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", name):
            return CommandResult(ok=False, error="Invalid block name", error_code="E_PARAMETER_REJECTED")
        if not isinstance(entities, list) or not entities or len(entities) > 500:
            return CommandResult(ok=False, error="Provide 1 to 500 block entities", error_code="E_PARAMETER_REJECTED")
        rows = []
        for entity in entities:
            if not isinstance(entity, dict):
                return CommandResult(ok=False, error="Invalid block entity", error_code="E_PARAMETER_REJECTED")
            kind = str(entity.get("type", "LINE")).upper()
            keys = (("x1", "y1", "x2", "y2") if kind == "LINE" else
                    ("cx", "cy", "radius") if kind == "CIRCLE" else
                    ("x", "y", "height") if kind == "ATTDEF" else None)
            if keys is None:
                return CommandResult(ok=False, error=f"Unsupported LT block entity: {kind}", error_code="E_PARAMETER_REJECTED")
            try:
                numbers = [float(entity.get(key, 1 if key == "radius" else 2.5 if key == "height" else 0)) for key in keys]
            except (ValueError, TypeError):
                return CommandResult(ok=False, error="Block coordinates must be numbers", error_code="E_PARAMETER_REJECTED")
            if not all(math.isfinite(value) for value in numbers) or (kind in ("CIRCLE", "ATTDEF") and numbers[-1] <= 0):
                return CommandResult(ok=False, error="Invalid block geometry", error_code="E_PARAMETER_REJECTED")
            if kind == "ATTDEF":
                tag = str(entity.get("tag", "TAG"))
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", tag):
                    return CommandResult(ok=False, error="Invalid attribute tag", error_code="E_PARAMETER_REJECTED")
                rows.append(",".join([kind, tag, *(format(value, ".12g") for value in numbers)]))
            else:
                rows.append(",".join([kind, *(format(value, ".12g") for value in numbers)]))
        return await self._dispatch("block-define", {"name": name, "entities_str": ";".join(rows)})

    async def region_operation(self, request: dict) -> CommandResult:
        source_context = await self.document_context()
        if not source_context.ok:
            return source_context
        if os.path.normcase(os.path.normpath(source_context.payload["active_path"])) != os.path.normcase(os.path.normpath(request["source_path"])):
            return CommandResult(ok=False, error="The active LT drawing is not source_path", error_code="E_SOURCE_DOCUMENT_MISMATCH")
        params = {
            "source_path": request["source_path"],
            "target_path": request["target_path"],
            "x1": request["corner1"][0], "y1": request["corner1"][1],
            "x2": request["corner2"][0], "y2": request["corner2"][1],
            "selection_mode": request["selection_mode"],
        }
        if request["operation"] == "preview":
            result = await self._dispatch("region-preview-lt", params)
            if result.ok and isinstance(result.payload, dict):
                result.payload.update(source_path=request["source_path"], target_path=request["target_path"],
                                      selection_mode=request["selection_mode"])
            return result
        params.update({
            "expected_handles_str": ";".join(str(h).upper() for h in request["expected_handles"]),
            "offset_x": request["offset"][0], "offset_y": request["offset"][1],
            "offset_z": request["offset"][2],
            "allow_unit_mismatch": "1" if request["allow_unit_mismatch"] else "0",
            "save_target": "1" if request["save_target"] else "0",
        })
        result = await self._dispatch("region-copy-lt", params)
        if result.ok and isinstance(result.payload, dict):
            result.payload.update(source_path=request["source_path"], target_path=request["target_path"],
                                  source_handles=request["expected_handles"], offset=list(request["offset"]))
        return result
