"""AutoCAD LT for Windows: AutoLISP file IPC, without Python COM automation."""

from __future__ import annotations

import asyncio
import ctypes
import faulthandler
import json
import logging
import math
import ntpath
import os
import re
import shutil
import sys
import threading
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
    "E_FILE_EXISTS": (False, "ask_the_user_before_replacing_then_retry_with_overwrite"),
}

_STALLED = object()
_log = logging.getLogger("lt_adapter")


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
        "drawing_create", "drawing_close", "drawing_copy_dwg",
        "drawing_save_as_dxf", "drawing_render_preview", "recover", "show_window",
        "apply_presentation_style", "prepare_recording_view",
        "product_render_view", "solid_create_box", "solid_create_cylinder", "solid_extrude",
        "solid_revolve", "solid_sweep", "solid_boolean", "product_create_feature",
        "drawing_plot_pdf", "drawing_audit", "entity_trim",
        "entity_extend", "entity_join", "create_dimension_linear",
        "create_dimension_aligned", "create_dimension_angular", "create_dimension_radius",
        "zoom_extents",
    })

    _LOAD_ATTEMPTS = 4
    _LOAD_PING_TIMEOUT = 8.0
    _TRIGGER_TIMEOUT = 20.0      # upstream waits up to 5 s + 2 s for idle, then types the trigger
    _SLOW_STEP_SECONDS = 2.0
    _QUICK_COMMANDS = frozenset({"document-context", "ping", "layer-exists-lt", "probe-layer",
                                 "probe-documents", "probe-vars", "layer-list"})
    _QUICK_TIMEOUT = 20.0        # answer cap for the quick reads above (heavy commands keep the long cap)
    _RETRIGGER_AFTER = 6.0       # seconds without an answer before the trigger is typed once more
    _STALL_DUMP_SECONDS = 25.0   # stack dump to C:/temp/lt_adapter_stall.log when a command outlives this
    _SAVE_TIMEOUT = 90.0         # large drawings take a while to write

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

    def _post_keys(self, target: int, command: str) -> bool:
        post = ctypes.windll.user32.PostMessageW
        sent = True
        for _ in range(2):  # cancel a pending command, nested ones need two
            sent &= bool(post(target, 0x0100, 0x1B, 0)) and bool(post(target, 0x0101, 0x1B, 0))
        time.sleep(0.05)
        for char in command:
            sent &= bool(post(target, 0x0102, ord(char), 0))
        sent &= bool(post(target, 0x0102, 0x0D, 0))
        time.sleep(0.05)
        return sent

    def _type_command(self, command: str) -> bool:
        """Post a command to LT and report whether the keys were really delivered.

        The upstream version ignores PostMessage failures and keeps the window
        found once at ensure_ready.  When that window goes stale the dispatcher
        is never triggered and the caller waits out the whole IPC timeout, so
        look the command window up again and retry once.
        """
        user32 = ctypes.windll.user32
        for attempt in range(2):
            target = self._command_hwnd
            if attempt or not target or not user32.IsWindow(target):
                target = self._find_command_line_hwnd() or self._hwnd
                self._command_hwnd = target
            if target and user32.IsWindow(target) and self._post_keys(target, command):
                return True
        return False

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
        try:
            from autocad_mcp.screenshot import Win32ScreenshotProvider

            self._screenshot_provider = Win32ScreenshotProvider(hwnd)  # view.get_screenshot
        except Exception:
            self._screenshot_provider = None
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
        # Right after a drawing is opened or activated LT may still be busy with it and
        # drop the typed keys.  A ping is harmless, so retry the load with a short wait
        # instead of waiting out the whole IPC timeout once.
        for attempt in range(self._LOAD_ATTEMPTS):
            for path in (upstream_runtime, overlay_runtime):
                expression = f'(load "{str(path.resolve()).replace(chr(92), "/")}")'
                if not self._type_command(expression):
                    return CommandResult(ok=False, error=f"Could not load dispatcher file in LT: {path.name}", error_code="E_DISPATCHER_NOT_LOADED")
                await asyncio.sleep(0.35)
            ping = await self._dispatch_unlocked("ping", {}, timeout=self._LOAD_PING_TIMEOUT)
            if ping.ok or ping.error_code != "E_IPC_TIMEOUT":
                break
            await asyncio.sleep(1.0)
        else:
            return CommandResult(
                ok=False, error="LT did not answer after the dispatcher was loaded; the drawing may still be opening",
                error_code="E_DISPATCHER_NOT_LOADED", recoverable=True,
                recommended_action="wait_for_the_drawing_to_finish_opening_and_retry")
        version = ping.payload.get("dispatcher_version") if ping.ok and isinstance(ping.payload, dict) else None
        if version != __version__:
            return CommandResult(ok=False, error=f"LT dispatcher ping/version failed: {ping.error or version}", error_code="E_DISPATCHER_NOT_LOADED")
        self._dispatcher_version = version
        self._dispatcher_key = self._window_key()
        return ping

    def _window_key(self) -> tuple:
        """Identify the LT window and drawing the dispatcher was loaded into.

        AutoLISP definitions are per drawing, so a different title (or window)
        means the dispatcher must be loaded again.
        """
        title = ""
        try:
            import win32gui
            title = win32gui.GetWindowText(self._hwnd)
        except Exception:
            pass
        return (self._hwnd, self._acad_process_id, title)

    async def _ensure_dispatcher_unlocked(self) -> CommandResult:
        """Load the dispatcher only when the window or drawing changed."""
        if getattr(self, "_dispatcher_key", None) == self._window_key():
            return CommandResult(ok=True)
        return await self._load_dispatcher_unlocked()

    async def _bounded_step(self, step: str, func, timeout: float):
        """Run a blocking step in a worker thread; return ``_STALLED`` if it outlives ``timeout``."""
        started = time.monotonic()
        try:
            value = await asyncio.wait_for(asyncio.to_thread(func), timeout)
        except asyncio.TimeoutError:
            _log.error("lt_step_stalled step=%s timeout=%.1fs", step, timeout)
            return _STALLED
        elapsed = time.monotonic() - started
        if elapsed > self._SLOW_STEP_SECONDS:
            _log.warning("lt_step_slow step=%s seconds=%.1f", step, elapsed)
        return value

    async def _dispatch_unlocked(self, command: str, params: dict, timeout: float | None = None) -> CommandResult:
        """Run the upstream IPC protocol, decoding LT's cp1252 Unicode escapes."""
        from autocad_mcp.backends import file_ipc as upstream

        request_id = uuid.uuid4().hex[:12]
        cmd_file = self._ipc_dir / f"autocad_mcp_cmd_{request_id}.json"
        result_file = self._ipc_dir / f"autocad_mcp_result_{request_id}.json"
        tmp_file = cmd_file.with_suffix(".tmp")
        dump = self._arm_stall_dump(command, request_id)
        try:
            clean_params = {key: value for key, value in params.items() if value is not None}
            payload = {"request_id": request_id, "command": command,
                       "params": clean_params, "ts": time.time()}
            tmp_file.write_text(json.dumps(payload), encoding="utf-8")
            tmp_file.rename(cmd_file)
            # The trigger is blocking (COM, window messages, waits); run it off the event loop under a
            # hard cap so a stalled step returns an error instead of freezing every queued request.
            triggered = await self._bounded_step(f"trigger:{command}", self._type_dispatch_trigger,
                                                 self._TRIGGER_TIMEOUT)
            if triggered is _STALLED:
                return CommandResult(
                    ok=False,
                    error=f"AutoCAD LT did not accept the dispatcher trigger within {self._TRIGGER_TIMEOUT:.0f} s "
                          f"(command={command}, request_id={request_id})",
                    error_code="E_LT_TRIGGER_STALLED", recoverable=True,
                    recommended_action="press_escape_in_autocad_then_retry")
            if not triggered:
                crash = upstream.detect_autocad_crash_state(self._hwnd, self._acad_process_id)
                if crash.get("crashed"):
                    return self._autocad_crashed_result(crash, command)
                return CommandResult(ok=False, error="LT command state remained blocked after cancellation",
                                     error_code="E_COMMAND_STATE_BLOCKED")
            # The launcher sets AUTOCAD_MCP_IPC_TIMEOUT=300 for heavy batches; a quick read that
            # AutoCAD never picked up must not hold the queue that long.
            quick = command in self._QUICK_COMMANDS
            limit = timeout or (min(upstream.TIMEOUT, self._QUICK_TIMEOUT) if quick else upstream.TIMEOUT)
            waiting_since = time.time()
            deadline = waiting_since + limit
            retriggered = False
            last_help_check = 0.0
            while time.time() < deadline:
                crash = upstream.detect_autocad_crash_state(self._hwnd, self._acad_process_id)
                if crash.get("crashed"):
                    return self._autocad_crashed_result(crash, command)
                if time.time() - last_help_check > 1.0:
                    last_help_check = time.time()
                    if self._close_stray_help() and quick and not retriggered and not result_file.exists():
                        # Keys that land in the wrong place open AutoCAD's Help: the trigger was lost.
                        retriggered = True
                        _log.warning("lt_trigger_retyped_after_help command=%s request_id=%s", command, request_id)
                        await self._bounded_step(f"retrigger:{command}", self._type_dispatch_trigger,
                                                 self._TRIGGER_TIMEOUT)
                if (quick and not retriggered and not result_file.exists()
                        and time.time() - waiting_since > self._RETRIGGER_AFTER):
                    # A quick read takes milliseconds, so no answer means the typed trigger was lost.
                    retriggered = True
                    _log.warning("lt_trigger_retyped command=%s request_id=%s", command, request_id)
                    await self._bounded_step(f"retrigger:{command}", self._type_dispatch_trigger,
                                             self._TRIGGER_TIMEOUT)
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
            self._disarm_stall_dump(dump)
            for file_path in (cmd_file, result_file, tmp_file):
                try:
                    file_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _close_stray_help(self) -> int:
        """Close a visible 'AutoCAD LT ... - Help' window of this AutoCAD process; return how many.

        The adapter never asks for Help, so one on screen means typed keys reached the wrong
        window (a 'p' is also the F1 virtual-key code). It would otherwise block the screen.
        """
        if sys.platform != "win32" or not self._acad_process_id:
            return 0
        try:
            import win32con
            import win32gui
            import win32process
        except Exception:
            return 0
        found: list[int] = []

        def visit(hwnd, _):
            try:
                if (win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd).endswith(" - Help")
                        and win32process.GetWindowThreadProcessId(hwnd)[1] == self._acad_process_id):
                    found.append(hwnd)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(visit, None)
            for hwnd in found:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception:
            return 0
        if found:
            _log.warning("lt_help_window_closed count=%d", len(found))
        return len(found)

    def _arm_stall_dump(self, command: str, request_id: str):
        """If one command outlives _STALL_DUMP_SECONDS, write every thread's stack to a file.

        The timer only fires for a command that is still running, so the file stays empty in
        normal use. It exists because a blocked COM or window call leaves the normal logs silent.
        """
        def dump() -> None:
            try:
                with open(self._ipc_dir / "lt_adapter_stall.log", "a", encoding="utf-8") as handle:
                    handle.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} command={command} "
                                 f"request_id={request_id} still running after {self._STALL_DUMP_SECONDS:.0f}s =====\n")
                    handle.flush()
                    faulthandler.dump_traceback(file=handle, all_threads=True)
            except Exception:
                pass

        timer = threading.Timer(self._STALL_DUMP_SECONDS, dump)
        timer.daemon = True
        timer.start()
        return timer

    @staticmethod
    def _disarm_stall_dump(timer) -> None:
        if timer is not None:
            timer.cancel()

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
            ready = await self._ensure_dispatcher_unlocked()
            return await self._context_unlocked() if ready.ok else ready

    async def drawing_activate(
        self,
        doc_id: str | None,
        expected_revision: int | None = None,
        lease_token: str | None = None,
        worker_generation: int | None = None,
    ) -> CommandResult:
        """Switch LT to another drawing that is already open, then rebind the dispatcher.

        ``doc_id`` is the id reported by ``drawing.context`` for that drawing, or
        its full path (a drawing the session has not seen yet has no id).  LT
        cannot open or close drawings from here; only drawings already open in
        this session qualify.
        """
        normalized, revision, validation = self._validate_activation_request(doc_id, expected_revision)
        if validation is not None:
            return validation
        known = self._session.documents_by_id.get(normalized)
        if known is not None and int(known.revision) != revision:
            return CommandResult(
                ok=False, error="The drawing changed since its context was read",
                error_code="E_DOCUMENT_REVISION_MISMATCH", recoverable=False,
                recommended_action="read_document_context_and_retry",
                payload={"expected_revision": revision, "actual_revision": int(known.revision)})
        wanted = os.path.normcase(os.path.normpath(known.path if known is not None else normalized))
        async with self._lock:
            if find_lt_window() != (self._hwnd, self._acad_process_id):
                return CommandResult(ok=False, error="LT instance changed; call system.ensure_ready",
                                     error_code="E_SESSION_GENERATION_MISMATCH")
            ready = await self._ensure_dispatcher_unlocked()
            if not ready.ok:
                return ready
            listing = await self._dispatch_unlocked("probe-documents", {})
            if not listing.ok or not isinstance(listing.payload, dict):
                return listing
            documents = listing.payload.get("documents", [])
            match = next((item for item in documents
                          if os.path.normcase(os.path.normpath(item["path"])) == wanted), None)
            if match is None:
                return CommandResult(
                    ok=False, error="doc_id is not a drawing open in this AutoCAD LT session",
                    error_code="E_PARAMETER_REJECTED", recoverable=False,
                    recommended_action="use_a_doc_id_from_open_documents",
                    payload={"open_documents": [
                        {"doc_id": self._session.doc_ids_by_key.get(os.path.normcase(item["path"])),
                         "path": item["path"], "name": item["name"], "active": item["active"]}
                        for item in documents]})
            if not match["active"]:
                result = await self._dispatch_unlocked("document-activate-lt", {"path": match["path"]})
                if not result.ok:
                    return result
                self._wait_for_autocad_idle(timeout=5.0)
            # The dispatcher lives per drawing: load it into the drawing that is now active.
            self._dispatcher_key = None
            ready = await self._load_dispatcher_unlocked()
            if not ready.ok:
                return ready
            context = await self._context_unlocked()
            if not context.ok:
                return context
            active = os.path.normcase(os.path.normpath(str(context.payload.get("active_path") or "")))
            if active and active != wanted:
                return CommandResult(
                    ok=False, error="LT did not switch to the requested drawing",
                    error_code="E_DOCUMENT_ID_MISMATCH", recoverable=False,
                    recommended_action="ask_user_to_click_the_drawing_tab",
                    payload={"requested": match["path"], "active": context.payload.get("active_path")})
            return context

    async def drawing_save(self, path: str | None = None, overwrite: bool = False) -> CommandResult:
        """Save the active drawing in place, or save a copy under ``path`` (an absolute .dwg path).

        Replacing an existing file needs ``overwrite=True``, which the caller sets only after
        the user has said so. Success is reported only when the drawing has no unsaved changes.
        """
        params: dict = {"replace": "1" if overwrite else "0"}
        if path:
            text = str(path).strip()
            if not ntpath.isabs(text) or not text.lower().endswith(".dwg"):
                return CommandResult(ok=False, error="Save path must be an absolute path ending in .dwg",
                                     error_code="E_PARAMETER_REJECTED", recoverable=False,
                                     recommended_action="ask_the_user_for_a_full_dwg_path")
            if not os.path.isdir(ntpath.dirname(text)):
                return CommandResult(ok=False, error=f"Save folder does not exist: {ntpath.dirname(text)}",
                                     error_code="E_PARAMETER_REJECTED", recoverable=False,
                                     recommended_action="ask_the_user_for_an_existing_folder")
            params["path"] = text.replace("\\", "/")
        result = await self._dispatch("drawing-save-lt", params, timeout=self._SAVE_TIMEOUT)
        if result.ok and isinstance(result.payload, dict) and result.payload.get("dbmod") not in (0, "0"):
            return CommandResult(ok=False, error="LT reported the save but the drawing still has unsaved changes",
                                 error_code="E_POSTCONDITION_MISMATCH", recoverable=False,
                                 recommended_action="stop_and_inspect_backend_state", payload=result.payload)
        return result

    async def _dispatch(self, command: str, params: dict, timeout: float | None = None) -> CommandResult:
        async with self._lock:
            selected = find_lt_window()
            if selected is None or selected != (self._hwnd, self._acad_process_id):
                return CommandResult(ok=False, error="LT instance changed; call system.ensure_ready", error_code="E_SESSION_GENERATION_MISMATCH")
            ready = await self._ensure_dispatcher_unlocked()
            if not ready.ok:
                return ready
            context = await self._context_unlocked()
            if not context.ok:
                # A read-only probe, so it is safe to reload once and retry.
                self._dispatcher_key = None
                ready = await self._load_dispatcher_unlocked()
                if not ready.ok:
                    return ready
                context = await self._context_unlocked()
                if not context.ok:
                    return context
            return await self._dispatch_unlocked(command, {
                **params, "_expected_document_path": context.payload["active_path"]
            }, timeout=timeout)

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

    _LIBRARY_BLOCK_NAME = re.compile(r"[A-Za-z0-9_-]{1,80}")
    _INSUNITS_NAMES = {0: "unitless", 1: "inches", 2: "feet", 4: "millimeters",
                       5: "centimeters", 6: "meters"}
    _INSUNITS_MM = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}

    @staticmethod
    def _block_library_folder() -> Path:
        configured = os.environ.get("AUTOCAD_MCP_BLOCK_LIBRARY", "").strip()
        return Path(configured) if configured else Path(__file__).resolve().parents[3] / "blocks"

    @staticmethod
    def _dxf_insunits(path: Path) -> int | None:
        """Read $INSUNITS from the header of an ASCII DXF; None for DWG or binary files."""
        try:
            with open(path, "rb") as handle:
                head = handle.read(65536).decode("ascii", errors="ignore")
        except OSError:
            return None
        lines = [line.strip() for line in head.splitlines()]
        for index, line in enumerate(lines[:-3]):
            if line == "$INSUNITS" and lines[index + 1] == "70":
                try:
                    return int(lines[index + 2])
                except ValueError:
                    return None
        return None

    @classmethod
    def _block_library_stores(cls) -> list[Path]:
        """Sub-folders of the library that hold an ``index.json``: one per "kho" (store)."""
        folder = cls._block_library_folder()
        try:
            return sorted(path for path in folder.iterdir()
                          if path.is_dir() and not path.name.startswith(".") and (path / "index.json").is_file())
        except OSError:
            return []

    @classmethod
    def _block_library_path(cls, name) -> str | None:
        """Return the library file for ``name`` (``<name>.dwg`` or ``.dxf``), if any.

        The folder comes from AUTOCAD_MCP_BLOCK_LIBRARY, else ``blocks`` at the
        repository root; its stores (sub-folders with an ``index.json``) are searched
        after it.  Names are limited to letters, digits, ``_`` and ``-``,
        so a name can never leave the folder.
        """
        if not isinstance(name, str) or not cls._LIBRARY_BLOCK_NAME.fullmatch(name):
            return None
        for folder in [cls._block_library_folder(), *cls._block_library_stores()]:
            for extension in (".dwg", ".dxf"):
                candidate = folder / f"{name}{extension}"
                if candidate.is_file():
                    return candidate.resolve().as_posix()
        return None

    def _block_library_entries(self, drawing_units: int | None, folder: Path | None = None) -> list[dict]:
        folder = folder or self._block_library_folder()
        try:
            index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            index = {}
        drawing_mm = self._INSUNITS_MM.get(drawing_units)
        entries: dict[str, dict] = {}
        try:
            files = sorted(folder.iterdir()) if folder.is_dir() else []
        except OSError:
            files = []
        for path in files:
            extension = path.suffix.lower()
            if extension not in (".dwg", ".dxf") or not self._LIBRARY_BLOCK_NAME.fullmatch(path.stem):
                continue
            if path.stem in entries and extension == ".dxf":
                continue  # insert prefers the .dwg of the same name
            known = index.get(path.stem) if isinstance(index.get(path.stem), dict) else {}
            if known.get("mm_per_unit"):
                units, file_mm = known.get("units"), float(known["mm_per_unit"])
            else:
                code = self._dxf_insunits(path) if extension == ".dxf" else None
                units = self._INSUNITS_NAMES.get(code, code) if code is not None else None
                file_mm = self._INSUNITS_MM.get(code)
            entry = {
                "name": path.stem, "file": path.name, "units": units,
                # AutoCAD multiplies the inserted size by this factor on its own.
                "scale_factor": round(file_mm / drawing_mm, 6) if file_mm and drawing_mm else None,
                "units_match": None if not file_mm or not drawing_mm else file_mm == drawing_mm,
            }
            for field in ("meaning", "view", "size_mm", "bbox_mm", "dynamic", "category"):
                if field in known:
                    entry[field] = known[field]
            if known.get("source_file"):
                entry["source"] = f"{known['source_file']} :: {known.get('source_block', '')}"
            entries[path.stem] = entry
        return list(entries.values())

    _STORE_LIMIT = 40

    def _store_listing(self, drawing_units: int | None, query: dict) -> dict:
        """Answer ``block list`` for the stores: a summary, or the entries of one store that match ``query``."""
        stores = {path.name: path for path in self._block_library_stores()}
        wanted = query.get("kho")
        if not wanted:
            summary = []
            for name, path in stores.items():
                entries = self._block_library_entries(drawing_units, path)
                categories: dict[str, int] = {}
                for entry in entries:
                    category = entry.get("category") or "-"
                    categories[category] = categories.get(category, 0) + 1
                summary.append({"kho": name, "count": len(entries), "categories": categories})
            return {"stores": summary}
        if wanted not in stores:
            return {"error": f"Không có kho '{wanted}'", "stores": sorted(stores)}
        entries = self._block_library_entries(drawing_units, stores[wanted])
        category = str(query["category"]).upper() if query.get("category") else None

        def side(entry: dict, position: int):
            size = entry.get("size_mm")
            return size[position] if isinstance(size, list) and len(size) == 2 else None

        def keep(entry: dict) -> bool:
            if category and entry.get("category") != category:
                return False
            for position, low, high in ((0, "min_width", "max_width"), (1, "min_depth", "max_depth")):
                value = side(entry, position)
                if value is None:
                    return False
                if query.get(low) is not None and value < float(query[low]):
                    return False
                if query.get(high) is not None and value > float(query[high]):
                    return False
            return True

        matching = [entry for entry in entries if keep(entry)]
        try:
            limit = max(1, min(200, int(query.get("limit", self._STORE_LIMIT))))
        except (TypeError, ValueError):
            limit = self._STORE_LIMIT
        return {"kho": wanted, "matching": len(matching), "shown": min(limit, len(matching)),
                "entries": matching[:limit]}

    async def block_list(self, query: dict | None = None) -> CommandResult:
        """List the drawing's blocks plus the library files that block.insert can load.

        Without ``query`` the root library is listed in full and each store only as a
        summary.  ``query = {"kho": name, "category": ..., "min_width": ..., "max_width": ...,
        "min_depth": ..., "max_depth": ..., "limit": n}`` lists one store, filtered by size in mm.
        """
        result = await super().block_list()
        if not result.ok or not isinstance(result.payload, dict):
            return result
        variables = await self.drawing_get_variables(["INSUNITS"])
        drawing_units = None
        if variables.ok and isinstance(variables.payload, dict):
            try:
                drawing_units = int(variables.payload.get("INSUNITS"))
            except (TypeError, ValueError):
                drawing_units = None
        result.payload["library"] = self._block_library_entries(drawing_units)
        result.payload["library_folder"] = str(self._block_library_folder())
        result.payload["drawing_units"] = (
            self._INSUNITS_NAMES.get(drawing_units, drawing_units) if drawing_units is not None else None)
        if isinstance(query, dict) and query.get("kho"):
            result.payload["store"] = self._store_listing(drawing_units, query)
            result.payload.pop("blocks", None)
            result.payload.pop("library", None)
        else:
            stores = self._store_listing(drawing_units, {})
            if stores.get("stores"):
                result.payload["stores"] = stores["stores"]
        return result

    async def block_export(self, name: str, library_name: str) -> CommandResult:
        """Write block ``name`` of the active drawing to ``<library>/<library_name>.dwg`` (maintenance use)."""
        if not isinstance(library_name, str) or not self._LIBRARY_BLOCK_NAME.fullmatch(library_name):
            return CommandResult(ok=False, error="Library names use letters, digits, _ and - only",
                                 error_code="E_PARAMETER_REJECTED", recoverable=False)
        folder = self._block_library_folder()
        folder.mkdir(parents=True, exist_ok=True)
        return await self._dispatch("block-export-lt", {
            "name": name, "target_path": (folder / f"{library_name}.dwg").resolve().as_posix(),
        })

    async def block_export_rebased(self, name: str, library_name: str, dx: float, dy: float) -> CommandResult:
        """Like block_export, but the file's base point moves: the block is inserted at (dx, dy), exploded and
        written with base point 0,0 (maintenance use, for blocks whose geometry is far from their base point)."""
        if not isinstance(library_name, str) or not self._LIBRARY_BLOCK_NAME.fullmatch(library_name):
            return CommandResult(ok=False, error="Library names use letters, digits, _ and - only",
                                 error_code="E_PARAMETER_REJECTED", recoverable=False)
        folder = self._block_library_folder()
        folder.mkdir(parents=True, exist_ok=True)
        return await self._dispatch("block-export-rebased-lt", {
            "name": name, "target_path": (folder / f"{library_name}.dwg").resolve().as_posix(),
            "dx": float(dx), "dy": float(dy),
        })

    async def block_catalog(self, start: int = 0, limit: int = 40) -> CommandResult:
        """Describe the active drawing's named blocks, one page at a time (maintenance use)."""
        return await self._dispatch("block-catalog-lt", {"start": int(start), "limit": int(limit)})

    async def block_insert(self, name, x, y, scale=1.0, rotation=0.0, block_id=None) -> CommandResult:
        """Insert a block already in the drawing, or load it from the block library."""
        return await self._dispatch("block-insert-lt", {
            "name": name, "x": x, "y": y, "scale": scale, "rotation": rotation,
            "library_path": self._block_library_path(name),
        })

    _LAYER_COLORS = frozenset({"red", "yellow", "green", "cyan", "blue", "magenta", "white"})

    @staticmethod
    def _true_color(text: str) -> str | None:
        """Return "r,g,b" for an "R,G,B" or "#RRGGBB" colour, else None."""
        if re.fullmatch(r"#[0-9a-f]{6}", text):
            return ",".join(str(int(text[i:i + 2], 16)) for i in (1, 3, 5))
        parts = [part.strip() for part in text.split(",")]
        if len(parts) == 3 and all(part.isdigit() and int(part) <= 255 for part in parts):
            return ",".join(str(int(part)) for part in parts)
        return None

    async def layer_set_properties(self, name, color=None, linetype=None, lineweight=None) -> CommandResult:
        """Set layer properties through the layer's ActiveX object; upstream uses COM and a LISP entmod LT rejects."""
        if color is not None:
            text = str(color).strip().lower()
            rgb = self._true_color(text)
            if rgb:
                color = rgb
            elif not ((text.isdigit() and 0 < int(text) < 256) or text in self._LAYER_COLORS):
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
        # Callers pad all-digit handles (" 400") so MCP clients keep them strings.
        entity_id = str(entity_id).strip().upper()
        if not re.fullmatch(r"[0-9A-F]+", entity_id):
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
            "entity_id": entity_id, "pattern": pattern,
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
        entity_id = str(entity_id).strip().upper()
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
