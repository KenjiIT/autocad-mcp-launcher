AutoCAD MCP Launcher v0.2.3

Added:

- Skills over MCP. The gateway has a read-only `skills` tool (`list` and `get`, with `path` for a skill's reference files), sends an `instructions` text on connect that tells the agent to read `autocad-agent-coordinator` before any CAD tool, and lists every skill as an MCP prompt. `stdio_bridge.py` passes the instructions and prompts on, so Claude Desktop gets the skills without uploading them. Checked over HTTP and over the stdio bridge; confirmed in Claude Desktop that the agent can fetch a skill this way.
- Settings, "Cài skill cho agent": new target "Claude Desktop (tải zip lên)". It builds one zip per selected skill in `%USERPROFILE%\AutoCAD-MCP-Skills-Claude-Desktop`, writes a short guide and opens the folder, because Claude Desktop only accepts skills uploaded as zip files.

Fixed:

- AutoCAD LT: `drawing open` no longer reports "opened" for a file it did not find. The path is decoded (Vietnamese names work), the drawing is opened through the Documents collection, success is reported only when the drawing is in the open-document list, and the opened drawing becomes the active one. A file that is already open is just activated.

Changed:

- Skill `autocad-agent-coordinator`: agents may open existing DWG files themselves with `drawing open`; the reference to the optional skill `mechanical-drafting-gbt` is removed.
- README: how to add skills to Claude Desktop.

Known limitations:

- The skills tool and instructions are a reminder, not a lock: an agent can still call CAD tools without reading the skill. Whether a client acts on the `instructions` text depends on the client.
- AutoCAD LT cannot create a new drawing or close one from the MCP; a new file has to be created by the user (or a template copied and then opened).
- `drawing open` was tested on small test files only; the 0.2.3 installer was not run.
- Carried over from v0.2.2: region selection with a zoomed-out view and `drawing_audit` are not verified on live AutoCAD LT; on LT, `autocad-beiming-mcp-custom/lisp-code` must be in `TRUSTEDPATHS`. The Windows installer is unsigned; SmartScreen may show an unknown publisher warning.
