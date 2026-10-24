# AutoCAD LT adapter

This directory contains the AutoCAD LT transport and tool behavior kept outside the vendored Beiming source. `launcher/serve.py` installs it before importing `autocad_mcp.server` when serving `autocad-beiming-mcp-custom`.

## How it is loaded

1. The launcher adds `lt-adapter/py` to `sys.path` and calls `lt_adapter.bootstrap.install()`.
2. The bootstrap selects `file_ipc_lt` only when LT is present and full AutoCAD is not. If full AutoCAD is present, the original Beiming backend selection runs.
3. It maps the LT backend and LT-aware `delete_batching` and `copy_region_between_dwgs` modules into Beiming's import locations before the server imports its tools.
4. `LtFileIPCBackend` stages a runtime copy of the vendored dispatcher in the already-trusted `lisp-code` folder, renaming its dispatcher function to `mcp-dispatch-command-upstream`. It then stages and loads `lisp/mcp_dispatch_lt.lsp` from the same trusted folder. The overlay handles LT commands, forwards other commands to the renamed upstream function, and checks `_expected_document_path` before dispatch.
5. LT results are read through the inherited file IPC protocol with LT's cp1252 `\\U+XXXX` escapes decoded inside this adapter.
6. LT verification helpers live in `py/lt_adapter/lt_verify.py`; LT-only tests and the guarded live verifier live in `tests/`.
7. `contract.json` is the interface inventory and pins the expected upstream dispatcher hash. `bootstrap.install()` validates it before patching imports; a mismatch emits a warning and leaves the upstream server path untouched.

## Run adapter tests

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\lt-adapter\py;$PWD\autocad-beiming-mcp-custom\src"
& .\autocad-beiming-mcp-custom\.venv\Scripts\python.exe -m pytest .\lt-adapter\tests -q
```

The manual verifier is separate and refuses to run while the launcher server is listening on port 8876. Run it only with a disposable, empty `Drawing*.dwg` or a drawing under `AUTOCAD_MCP_LT_TEST_ROOT`.

## Upstream interfaces used

The adapter relies on these Beiming interfaces:

- `autocad_mcp.backends.file_ipc.FileIPCBackend`, including `_dispatch_unlocked` protocol helpers, `_type_dispatch_trigger`, `_autocad_crashed_result`, and window state fields.
- `autocad_mcp.backends.base.CommandResult` and `BackendCapabilities`.
- `autocad_mcp.config.LISP_DIR` and `detect_backend`.
- `autocad_mcp.client._backend`, `_init_lock`, `get_backend`, and `ensure_backend_ready`.
- FastMCP's server tool registration importing `autocad_mcp.custom_tools.batch_delete` and `region_copy` before serving requests.
- Dispatcher symbols `mcp-dispatch-command-upstream`, `c:mcp-dispatch`, JSON helpers, and the existing upstream command handlers.

The symbol list, overridden method signatures, LISP entry points, tool-module mappings, upstream commit, and dispatcher SHA-256 are recorded in `contract.json`. Review and update that file when intentionally changing the upstream baseline. Run the Python tests and LISP balance check after each upstream refresh, then verify the launcher against a disposable LT drawing. A successful import or unit test alone does not establish that a tool works in LT.

## Scope limits

The adapter intentionally uses AutoLISP IPC for LT. It does not add LT support for document lifecycle, solid modeling, or UI-only operations. Hatch creation and some verification probes use Visual LISP ActiveX functions inside AutoCAD LT; they do not use Python COM automation. Confirm those functions against the target LT release before relying on them.
