# AutoCAD MCP Multi-Session Launcher (experimental)

This launcher is isolated from `launcher/` and does not replace or edit the
existing launcher. It starts one Beiming MCP process per selected AutoCAD PID.

Each session gets its own HTTP port, IPC directory, output directory, and log.
Stopping a session terminates only its MCP process; it never terminates AutoCAD.

## Run

Run `Start Multi-Session Launcher.cmd`. Select an AutoCAD window, start its MCP,
then copy that session's URL into the chosen agent's MCP configuration.

This is an experiment. The current Beiming backend discovers AutoCAD by PID but
uses Windows `GetActiveObject` for COM. On systems with several AutoCAD instances,
that COM call can return another instance. The backend checks the PID and fails
closed if it does. A green process status means the MCP HTTP server started; use
the explicit **Test AutoCAD connection** button before sending drawing work.

The launcher uses a small per-session LISP wrapper. AutoLISP reads its IPC path
from the AutoCAD process environment, so setting `AUTOCAD_MCP_IPC_DIR` only in
the MCP process is not sufficient. The wrapper loads the Beiming dispatcher and
sets `*mcp-ipc-dir*` inside that AutoCAD process.

For configuring two separate Claude Code sessions, see
[`docs/claude-multi-session-autocad.md`](../docs/claude-multi-session-autocad.md).

## Test status — 2026-10-19

- Two isolated MCP HTTP processes can start at the same time and expose the
  Beiming tools.
- `system.ensure_ready` succeeded for AutoCAD PID 6280 after the per-session IPC
  wrapper was added.
- The same check for PID 37692 timed out. Multi-instance COM binding is still
  unresolved, so this build is not stable enough to replace the existing launcher.
- The original launcher continues to use port 8764. This experiment uses ports
  starting at 8800 and stops only its own MCP processes.

Session data is stored under `launcher_multi/runtime/` and logs under
`launcher_multi/logs/`.
