# Upstream provenance

This standalone project is derived from Beiming's AutoCAD-MCP repository:

- Repository: https://github.com/beiming183-cloud/AutoCAD-MCP
- Upstream commit copied as the baseline: `11f7c47e5038796a20451b38b23032e625b5aa26`
- License: MIT; the upstream `LICENSE` file is retained.

The project preserves upstream notices and records local changes in `LOCAL_CHANGES.md`. The three modules under `src/autocad_mcp/custom_tools/` provide locally integrated batch copy, region copy between drawings, and batch delete tools. This folder intentionally excludes upstream Git metadata so it can later be initialized and published as an independent repository.
