import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "skillserve", Path(__file__).resolve().parents[2] / "launcher" / "skillserve.py")
skillserve = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skillserve)


@pytest.fixture
def root(tmp_path):
    skill = tmp_path / "demo-skill"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo-skill\ndescription: Mô tả thử\n---\nNội dung", encoding="utf-8")
    (skill / "references" / "a.md").write_text("tham chiếu", encoding="utf-8")
    (skill / "references" / "big.pdf").write_bytes(b"0")
    (tmp_path / "secret.md").write_text("no", encoding="utf-8")
    return tmp_path


def test_list_and_read(root):
    assert skillserve.list_skills(root) == [{"name": "demo-skill", "description": "Mô tả thử"}]
    main = skillserve.read_skill(root, "demo-skill")
    assert main["content"].endswith("Nội dung") and main["other_files"] == ["references/a.md"]
    assert skillserve.read_skill(root, "demo-skill", "references/a.md")["content"] == "tham chiếu"


@pytest.mark.parametrize("name,path", [
    ("nope", None), ("../x", None), ("demo-skill", "../secret.md"), ("demo-skill", r"..\secret.md"),
    ("demo-skill", "references/big.pdf"), ("demo-skill", "references"), ("demo-skill", 5), (None, None),
])
def test_bad_requests_are_rejected(root, name, path):
    with pytest.raises(ValueError):
        skillserve.read_skill(root, name, path)


def test_real_coordinator_is_served():
    real = Path(__file__).resolve().parents[2] / ".claude" / "skills"
    text = skillserve.read_skill(real, "autocad-agent-coordinator")["content"]
    assert "Quy tắc 1" in text
    assert any(s["name"] == "autocad-agent-coordinator" for s in skillserve.list_skills(real))
