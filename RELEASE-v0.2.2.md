AutoCAD MCP Launcher v0.2.2

Added:

- Block library for AutoCAD LT. `block insert` now loads a block from the `blocks` folder when the drawing does not have it yet, and `block list` also lists the library files with their meaning, size in mm, bounding box and unit scale factor. The Settings tab has a button that opens the library folder.
- Skill `autocad-block-library`: look blocks up and insert them instead of drawing furniture, sanitary ware, doors, windows, plants and drawing symbols by hand. It ships a catalogue of all 432 blocks in the sample drawings that come with AutoCAD LT. The block files themselves are Autodesk content and are not part of the package; `lt-adapter/tools/extract_sample_blocks.py` rebuilds them on a machine with AutoCAD LT.
- Settings: "Tải tri thức" downloads the public knowledge pages (download only, nothing is uploaded).

Changed:

- The skills `autocad-identify-boundaries` and `autocad-identify-and-measure` are merged into `autocad-identify-and-measure` (boundaries and objects/measuring as two reference pages). Skill packages in `dist` now include the whole skill folder.
- AutoCAD LT: the dispatcher is loaded once per window and drawing instead of before every command. `cad_batch` is 6 to 8 times faster (30 lines in 7 s instead of 45 s).
- The launcher reuses a gateway that an earlier launcher left running on port 8764 instead of reporting that the port is in use.
- The Settings tab scrolls.

Known limitations:

- Blocks were checked on a blank drawing for scale, rotation, inch to mm conversion and layers. The colour of strokes inside a block and dynamic block states were not checked. `SYMB-DETAIL-GRID` and `SYMB-GRAPHIC-SCALE` insert slowly and can report a timeout even though the object was created.
- The new Settings buttons and the gateway reuse were exercised in the launcher window once; the 0.2.2 installer was not run.
- Carried over from v0.2.0: region selection with a zoomed-out view and `drawing_audit` are not verified on live AutoCAD LT; on LT, `autocad-beiming-mcp-custom/lisp-code` must be in `TRUSTEDPATHS`.
- The Windows installer is unsigned; SmartScreen may show an unknown publisher warning.
