# AutoCAD LT live verification

The live verifier talks to LT through file IPC and AutoLISP. It does not use Python COM. The `probe-*` commands return evidence read independently from the active drawing and do not mutate it.

## Safe manual run

The standalone runner refuses to run while the launcher Beiming server is listening on port `8876`, because two Python backends must not inject commands into the same LT window. Stop Beiming in the launcher first; keep AutoCAD LT open.

The active drawing must be empty and either named `Drawing*.dwg` or located under `AUTOCAD_MCP_LT_TEST_ROOT`. The runner never saves. It creates a rectangle, circle, and hatches, probes the resulting entities and areas, tests invalid handles, deletes its own test entities, then confirms the model-space handle set matches the initial snapshot.

From PowerShell in `autocad-beiming-mcp-custom`:

```powershell
$env:AUTOCAD_MCP_LISP_PATH = (Join-Path (Get-Location).Path 'lisp-code\mcp_dispatch.lsp')
$env:AUTOCAD_MCP_LT_TEST_ROOT = Join-Path $env:TEMP 'autocad-mcp-lt-verify-live'
$env:PYTHONPATH = Join-Path (Get-Location).Path 'src'
.\.venv\Scripts\python.exe tests\manual_lt_verification.py
```

Do not set a private `AUTOCAD_MCP_IPC_DIR` for this runner unless the same value is also configured inside AutoCAD LT. By default, both use `C:\temp`.

JSON and Markdown reports are written to `output/lt_verify/`.

## Current live coverage

- LT dispatcher readiness and test-document guard.
- Read-only snapshot, entity DXF data, system variables, layer properties, bounding boxes, and area probes.
- Hatch verification on a closed polyline and a circle, including independent area comparison.
- Invalid hatch handle rejection without drawing changes.
- Delete-batch invalid-handle control and cleanup back to the baseline entity set.

Other `LT_VERIFY_PLAN.md` scenarios such as block definitions, cross-DWG region copying, and dispatcher reload/Unicode-path rounds require their own guarded fixtures and are not part of this smoke runner yet.
