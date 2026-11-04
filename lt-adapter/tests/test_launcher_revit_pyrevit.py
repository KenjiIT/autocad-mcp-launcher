import importlib.util
import sys
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"
sys.path.insert(0, str(LAUNCHER))  # revit_pyrevit_mcp imports revit_mcp
SPEC = importlib.util.spec_from_file_location("revit_pyrevit_mcp", LAUNCHER / "revit_pyrevit_mcp.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_command_runs_main_over_http():
    assert mod.command("uv.exe") == ["uv.exe", "run", "main.py", "--http"]
    assert mod.URL == f"http://127.0.0.1:{mod.PORT}/mcp"


def test_entry_needs_cloned_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("REVIT_PYREVIT_MCP_DIR", str(tmp_path))
    assert mod.entry() is None
    (tmp_path / "main.py").write_text("x")
    assert mod.entry() == tmp_path / "main.py"


def test_readiness_reports_missing_uv_and_source(tmp_path, monkeypatch):
    monkeypatch.setenv("REVIT_PYREVIT_MCP_DIR", str(tmp_path))
    monkeypatch.setattr(mod, "find_uv", lambda: None)
    monkeypatch.setattr(mod.revit_mcp, "installed_revit_versions", lambda: [2026])
    lines = mod.readiness()
    assert [ok for ok, _ in lines] == [False, False, True]
