import asyncio
import importlib.util
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"


def load(name):
    spec = importlib.util.spec_from_file_location(name, LAUNCHER / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_serve_extends_the_read_timeout_for_the_renamed_checkout():
    """Regression: matching only the old 'beiming183' name dropped the extension, so a 60 s audit poisoned COM."""
    serve = load("serve")
    assert serve.extends_read_timeout(Path("C:/x/autocad-beiming-mcp-custom"))
    assert serve.extends_read_timeout(Path("C:/x/beiming183-cloud-AutoCAD-MCP"))
    assert not serve.extends_read_timeout(Path("C:/x/puran-water-autocad-mcp"))


def test_apply_extends_only_the_large_read_operations(monkeypatch):
    from autocad_mcp.com_sta import ComStaExecutor

    seen = []

    def call(self, operation, callback, **kwargs):
        seen.append((operation, kwargs.get("timeout")))

    async def call_async(self, operation, callback, **kwargs):
        seen.append((operation, kwargs.get("timeout")))

    monkeypatch.setattr(ComStaExecutor, "call", call)
    monkeypatch.setattr(ComStaExecutor, "call_async", call_async)
    monkeypatch.setenv("AUTOCAD_MCP_READ_TIMEOUT", "600")
    load("beiming_timeout").apply()

    executor = object.__new__(ComStaExecutor)
    executor.call("drawing.audit", None, timeout=60.0)
    executor.call("entity.collect", None, timeout=30.0)
    executor.call("drawing.save", None, timeout=60.0)
    executor.call("drawing.audit", None, timeout=None)
    asyncio.run(executor.call_async("drawing.audit", None, timeout=60.0))
    assert seen == [
        ("drawing.audit", 600.0),
        ("entity.collect", 600.0),
        ("drawing.save", 60.0),
        ("drawing.audit", None),
        ("drawing.audit", 600.0),
    ]
