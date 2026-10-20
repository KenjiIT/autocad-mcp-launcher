AutoCAD MCP Launcher v0.1.3

Added:

- Added `cad_batch` to Beiming custom MCP. It groups up to 100 supported entity operations into one MCP request, supports references to handles returned by earlier steps, and uses an AutoCAD undo transaction for rollback on failure.

Known limitations:

- `cad_batch` has passed Python syntax and diff checks, but has not yet been exercised against a live AutoCAD drawing. Restart the Beiming custom MCP server to load the new tool.
- Batch support is limited to the operations documented in the custom MCP README. It currently requires the AutoCAD `file_ipc` backend.
- The Windows installer is unsigned; SmartScreen may show an unknown publisher warning.
