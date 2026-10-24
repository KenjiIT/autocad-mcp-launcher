"""Install the AutoCAD LT adapter before importing Beiming's MCP server."""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
import warnings


ADAPTER_ROOT = Path(__file__).resolve().parents[2]
PY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ADAPTER_ROOT.parent


def _load_as(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load adapter module {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def install() -> None:
    """Hook backend selection and substitute LT-aware tool implementations."""
    if str(PY_ROOT) not in sys.path:
        sys.path.insert(0, str(PY_ROOT))

    from lt_adapter.contract import validate_contract

    problems = validate_contract()
    if problems:
        warnings.warn(
            "AutoCAD LT adapter not installed because its Beiming contract changed: "
            + "; ".join(problems),
            RuntimeWarning,
            stacklevel=2,
        )
        return

    from autocad_mcp import config
    from autocad_mcp import client
    from autocad_mcp.backends.file_ipc import FileIPCBackend

    backend_module = _load_as(
        "lt_adapter.lt_file_ipc", PY_ROOT / "lt_adapter" / "lt_file_ipc.py"
    )
    sys.modules["autocad_mcp.backends.lt_file_ipc"] = backend_module
    import autocad_mcp.backends as backends
    backends.lt_file_ipc = backend_module
    for tool_name in ("batch_delete", "region_copy"):
        _load_as(
            f"autocad_mcp.custom_tools.{tool_name}",
            PY_ROOT / "lt_adapter" / "custom_tools" / f"{tool_name}.py",
        )

    original_detect = config.detect_backend
    original_get = client.get_backend
    original_ensure = client.ensure_backend_ready

    def detect_backend() -> str:
        requested = os.environ.get("AUTOCAD_MCP_BACKEND", "auto").strip().lower()
        if requested == "file_ipc_lt":
            return "file_ipc_lt"
        if requested in {"auto", "file_ipc"} and sys.platform == "win32":
            selected = backend_module.find_lt_window()
            if selected is not None:
                from autocad_mcp.backends.file_ipc import find_autocad_window
                if find_autocad_window() is None:
                    return "file_ipc_lt"
        return original_detect()

    async def _retire_backend(previous) -> None:
        if previous is None:
            return
        shutdown = getattr(previous, "shutdown", None)
        if shutdown is None:
            return
        result = shutdown()
        if hasattr(result, "__await__"):
            await result

    async def get_backend():
        selected = detect_backend()
        current = client._backend
        if selected != "file_ipc_lt":
            if isinstance(current, backend_module.LtFileIPCBackend):
                async with client._init_lock:
                    if client._backend is current:
                        client._backend = None
                        await _retire_backend(current)
            return await original_get()
        if isinstance(current, backend_module.LtFileIPCBackend):
            return current
        async with client._init_lock:
            current = client._backend
            if isinstance(current, backend_module.LtFileIPCBackend):
                return current
            await _retire_backend(current)
            backend = backend_module.LtFileIPCBackend()
            result = await backend.initialize()
            if not result.ok:
                raise RuntimeError(f"AutoCAD LT backend init failed: {result.error}")
            client._backend = backend
            return backend

    async def ensure_backend_ready():
        selected = detect_backend()
        current = client._backend
        if selected != "file_ipc_lt":
            if isinstance(current, backend_module.LtFileIPCBackend):
                async with client._init_lock:
                    if client._backend is current:
                        client._backend = None
                        await _retire_backend(current)
            return await original_ensure()
        async with client._init_lock:
            current = client._backend
            backend = current if isinstance(current, backend_module.LtFileIPCBackend) else backend_module.LtFileIPCBackend()
            result = await backend.ensure_ready()
            if result.ok:
                if current is not backend:
                    await _retire_backend(current)
                client._backend = backend
            return result

    config.detect_backend = detect_backend
    client.detect_backend = detect_backend
    client.get_backend = get_backend
    client.ensure_backend_ready = ensure_backend_ready

