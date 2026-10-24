AutoCAD MCP Launcher v0.2.1

Added:

- Added a Settings option, "Tự bật MCP khi mở launcher" (start MCP when the launcher opens). When enabled, the gateway starts as soon as the launcher opens, without pressing Start. It is off by default and is independent of the "start with Windows" option. AutoCAD is still only connected when an agent calls a tool.

Known limitations:

- The option was checked for settings load/save and syntax only. It has not been exercised in the launcher window.
- Carried over from v0.2.0: region selection with a zoomed-out view, `layer set_properties` after the last syntax fix and `drawing_audit` are not verified on live AutoCAD LT; on LT, `autocad-beiming-mcp-custom/lisp-code` must be in `TRUSTEDPATHS`.
- The Windows installer is unsigned; SmartScreen may show an unknown publisher warning.
