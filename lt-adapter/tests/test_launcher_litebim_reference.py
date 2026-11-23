"""Tài liệu get_reference của LiteBIM/LiteCAD được lưu thành markdown trong launcher/state/<sản phẩm>/reference/."""
import json
import sys
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"
sys.path.insert(0, str(LAUNCHER))

import litebim_reference as ref  # noqa: E402

DOC = "# Rules of a script\n\nfrom litebim import *\n"


class FakeBridge:
    def __init__(self, version="27.4.19", schema=None, text=DOC):
        self.product, self.title, self.version, self.schema, self.text, self.calls = "litebim", "LiteBIM", version, schema, text, []

    def handle(self, m):
        self.calls.append(m)
        if m["method"] == "initialize":
            return {"id": m["id"], "result": {"serverInfo": {"name": "litebim", "version": self.version}}}
        if m["method"] == "tools/list":
            return {"id": m["id"], "result": {"tools": [{"name": "run_script"}, {"name": "get_reference", "inputSchema": self.schema or {"type": "object", "properties": {}}}]}}
        args = m["params"]["arguments"]
        return {"id": m["id"], "result": {"content": [{"type": "text", "text": self.text + json.dumps(args)}]}}


def test_luu_file_kem_phien_ban_va_khong_lay_lai_khi_cung_phien_ban(tmp_path):
    b = FakeBridge()
    r = ref.refresh(b, state=tmp_path)
    assert r["state"] == "updated"
    path = ref.main_file("litebim", tmp_path)
    assert path == tmp_path / "litebim" / "reference" / "litebim-reference.md"
    body = path.read_text(encoding="utf-8")
    assert "phiên bản 27.4.19" in body.splitlines()[0] and "# Rules of a script" in body
    info = ref.info("litebim", tmp_path)
    assert info["available"] and info["version"] == "27.4.19" and info["files"] == ["litebim-reference.md"]
    calls = len(b.calls)
    assert ref.refresh(b, state=tmp_path)["state"] == "current"
    assert not any(c["method"] == "tools/call" for c in b.calls[calls:]), "cùng phiên bản thì không gọi lại get_reference"


def test_doi_phien_ban_hoac_force_thi_lay_lai(tmp_path):
    ref.refresh(FakeBridge(), state=tmp_path)
    assert ref.refresh(FakeBridge(version="27.5.0"), state=tmp_path)["state"] == "updated"
    assert ref.info("litebim", tmp_path)["version"] == "27.5.0"
    assert ref.refresh(FakeBridge(version="27.5.0"), force=True, state=tmp_path)["state"] == "updated"


def test_chua_mo_hoac_khong_co_tool_thi_khong_ghi_gi(tmp_path):
    assert ref.refresh(FakeBridge(version="launcher"), state=tmp_path)["state"] == "unavailable"
    b = FakeBridge(); b.handle_orig = b.handle
    b.handle = lambda m: {"result": {"tools": []}} if m["method"] == "tools/list" else b.handle_orig(m)
    assert ref.refresh(b, state=tmp_path)["state"] == "no-tool"
    assert not ref.info("litebim", tmp_path)["available"]


def test_tool_co_tham_so_enum_thi_luu_moi_chu_de_va_file_muc_luc(tmp_path):
    schema = {"type": "object", "properties": {"topic": {"type": "string", "enum": ["walls", "doors/windows"]}}}
    r = ref.refresh(FakeBridge(schema=schema), state=tmp_path)
    names = sorted(Path(f).name for f in r["files"])
    assert names == ["litebim-reference-doors-windows.md", "litebim-reference-walls.md", "litebim-reference.md"]
    assert "litebim-reference-walls.md" in ref.main_file("litebim", tmp_path).read_text(encoding="utf-8")
    assert '"topic": "walls"' in (tmp_path / "litebim" / "reference" / "litebim-reference-walls.md").read_text(encoding="utf-8")


def test_ket_qua_loi_khong_ghi_de_tai_lieu_cu(tmp_path):
    ref.refresh(FakeBridge(), state=tmp_path)
    assert ref._text_of({"isError": True, "content": [{"type": "text", "text": "x"}]}) is None
    assert ref._text_of({"content": []}) is None
