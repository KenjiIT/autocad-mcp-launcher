"""Extend Beiming's large-drawing read deadlines without editing its Git submodule."""

import os
from functools import wraps


READ_OPERATIONS = {"drawing.audit", "entity.collect"}


def apply():
    from autocad_mcp.com_sta import ComStaExecutor

    try:
        read_timeout = float(os.environ.get("AUTOCAD_MCP_READ_TIMEOUT", "600"))
    except ValueError:
        read_timeout = 600.0
    read_timeout = max(60.0, min(600.0, read_timeout))
    original_call = ComStaExecutor.call
    original_call_async = ComStaExecutor.call_async

    def extend(operation, kwargs):
        if operation in READ_OPERATIONS and kwargs.get("timeout") is not None:
            kwargs["timeout"] = max(float(kwargs.get("timeout", 30.0)), read_timeout)
        return kwargs

    @wraps(original_call)
    def call(self, operation, callback, **kwargs):
        return original_call(self, operation, callback, **extend(operation, kwargs))

    @wraps(original_call_async)
    async def call_async(self, operation, callback, **kwargs):
        return await original_call_async(self, operation, callback, **extend(operation, kwargs))

    ComStaExecutor.call = call
    ComStaExecutor.call_async = call_async
