# Upstream provenance

This standalone project is derived from Beiming's AutoCAD-MCP repository:

- Repository: https://github.com/beiming183-cloud/AutoCAD-MCP
- Upstream commit copied as the baseline: `11f7c47e5038796a20451b38b23032e625b5aa26`
- License: MIT; the upstream `LICENSE` file is retained.

The project preserves upstream notices and records local changes in `LOCAL_CHANGES.md`. The three modules under `src/autocad_mcp/custom_tools/` provide locally integrated batch copy, region copy between drawings, and batch delete tools. This folder intentionally excludes upstream Git metadata so it can later be initialized and published as an independent repository.

## Refreshing the vendored upstream

AutoCAD LT support, LT verification helpers, and LT-only tests live in the sibling `lt-adapter/` directory. The vendored source contains no LT backend modules or LT-specific tests. When refreshing Beiming, do not copy adapter code into `src/autocad_mcp/` or `lisp-code/`. Use this sequence:

1. Save the current working diff and list locally maintained custom tools.
2. Replace only the vendored Beiming files from a reviewed upstream revision, retaining `LICENSE` and provenance.
3. Reapply changes documented in `LOCAL_CHANGES.md` and preserve the local custom tool modules that are not part of upstream.
4. Review the adapter contract in `lt-adapter/contract.json` and its explanation in `lt-adapter/README.md`, especially the dispatcher hash, `FileIPCBackend`, and client backend lifecycle hooks.
5. From the repository root, set `PYTHONPATH` to `lt-adapter/py` and `autocad-beiming-mcp-custom/src`, then run `pytest lt-adapter/tests -q`. This suite includes the overlay/upstream LISP balance checks.
6. Start the launcher with a disposable LT drawing and verify backend selection and each LT operation before using the refreshed checkout.

The adapter overlays the upstream LISP dispatcher at runtime; it depends on upstream helper and command symbols remaining available. A successful merge or import is not proof of LT runtime compatibility.
