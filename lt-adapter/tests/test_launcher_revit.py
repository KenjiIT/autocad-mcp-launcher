import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "revit_mcp", Path(__file__).resolve().parents[2] / "launcher" / "revit_mcp.py")
revit_mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(revit_mcp)


def test_command_pins_packages_and_binds_loopback_only(monkeypatch):
    monkeypatch.setattr(revit_mcp, "local_server", lambda: None)
    command = revit_mcp.command("npx.cmd")
    assert command[:3] == ["npx.cmd", "-y", revit_mcp.GATEWAY_PACKAGE]
    assert "@" in revit_mcp.GATEWAY_PACKAGE and "@" in revit_mcp.SERVER_PACKAGE
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--port") + 1] == str(revit_mcp.PORT)
    assert revit_mcp.SERVER_PACKAGE in command[command.index("--stdio") + 1]


def test_command_prefers_local_server_install(monkeypatch):
    monkeypatch.setattr(revit_mcp, "local_server", lambda: '"node" "index.js"')
    command = revit_mcp.command("npx.cmd")
    assert command[command.index("--stdio") + 1] == '"node" "index.js"'


def test_local_server_needs_installed_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert revit_mcp.local_server() is None
    entry = tmp_path / "revit-mcp-server" / "node_modules" / "mcp-server-for-revit" / "build"
    entry.mkdir(parents=True)
    (entry / "index.js").write_text("x")
    monkeypatch.setattr(revit_mcp.shutil, "which", lambda name: "node.exe")
    assert revit_mcp.local_server() == f'"node.exe" "{entry / "index.js"}"'


def test_revit_detection_reads_program_files_and_addins(tmp_path, monkeypatch):
    (tmp_path / "pf" / "Autodesk" / "Revit 2025").mkdir(parents=True)
    (tmp_path / "pf" / "Autodesk" / "Revit 2025" / "Revit.exe").write_bytes(b"")
    (tmp_path / "pf" / "Autodesk" / "Revit Assistant 2027").mkdir()
    addins = tmp_path / "ad" / "Autodesk" / "Revit" / "Addins" / "2025"
    addins.mkdir(parents=True)
    (addins / "mcp-servers-for-revit.addin").write_text("x")
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "pf"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "ad"))
    assert revit_mcp.installed_revit_versions() == [2025]
    assert revit_mcp.addin_versions() == [2025]


def test_newer_revit_than_the_release_is_flagged(tmp_path, monkeypatch):
    (tmp_path / "Autodesk" / "Revit 2027").mkdir(parents=True)
    (tmp_path / "Autodesk" / "Revit 2027" / "Revit.exe").write_bytes(b"")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    line = [item for item in revit_mcp.readiness() if "Revit tìm thấy" in item[1]][0]
    assert line[0] is False and "2026" in line[1]
