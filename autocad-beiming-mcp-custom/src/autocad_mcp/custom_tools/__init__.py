"""Additional AutoCAD tools maintained with this standalone MCP checkout."""


def register_tools(mcp) -> None:
    """Register the custom batch and region tools on the main MCP server."""
    from .batch_copy import register as register_batch_copy
    from .batch_delete import register as register_batch_delete
    from .region_copy import register as register_region_copy

    register_batch_copy(mcp)
    register_region_copy(mcp)
    register_batch_delete(mcp)
