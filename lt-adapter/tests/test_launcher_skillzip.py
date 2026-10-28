import importlib.util
from pathlib import Path
from zipfile import ZipFile

import pytest

SPEC = importlib.util.spec_from_file_location(
    "skillzip", Path(__file__).resolve().parents[2] / "launcher" / "skillzip.py")
skillzip = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skillzip)


def test_zip_keeps_the_skill_folder_and_references(tmp_path):
    skill = tmp_path / "src" / "demo"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
    (skill / "references" / "a.md").write_text("x", encoding="utf-8")
    (skill / "__pycache__").mkdir()
    (skill / "__pycache__" / "junk.pyc").write_bytes(b"0")
    out = tmp_path / "out"
    written = skillzip.build_skill_zips(tmp_path / "src", ["demo"], out)
    assert written == [out / "demo.zip"]
    assert sorted(ZipFile(written[0]).namelist()) == ["demo/SKILL.md", "demo/references/a.md"]
    assert (out / "HUONG-DAN.txt").read_text(encoding="utf-8").startswith("Cách thêm skill")


def test_missing_skill_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        skillzip.build_skill_zips(tmp_path, ["nope"], tmp_path / "out")
