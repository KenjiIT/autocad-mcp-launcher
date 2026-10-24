AutoCAD MCP Launcher v0.2.0

Added:

- Added an AutoCAD LT adapter (`lt-adapter/`) that runs the Beiming MCP on AutoCAD LT without COM. It drives LT through its window and an AutoLISP dispatcher, and reports `E_NOT_SUPPORTED_ON_LT` for tools that need COM.
- Added LT versions of batch delete and region copy between drawings, entity listing with bounding boxes, and `layer set_properties` (colour, linetype, lineweight).
- Added structured error codes for LT failures, and an upstream contract check that falls back to the unmodified server if the Beiming source changes.
- The launcher now remembers which AutoCAD process a session is bound to, and the skill installer reads a single skill source.
- Fixed AutoCAD LT window detection that picked the floating Quick Properties panel instead of the main window.

Known limitations:

- Not yet verified on a live AutoCAD LT drawing: region selection with an extremely zoomed-out view, `layer set_properties` after the last syntax fix, and `drawing_audit` (currently blocked on LT).
- `entity_list` on LT always returns coordinates, and `create_*` commands still depend on the OSNAP setting.
- On LT, the folder `autocad-beiming-mcp-custom/lisp-code` must be in AutoCAD's `TRUSTEDPATHS`. The launcher does not set it for LT yet.
- One launcher drives one AutoCAD process at a time.
- The Windows installer is unsigned; SmartScreen may show an unknown publisher warning.
