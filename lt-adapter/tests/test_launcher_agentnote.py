import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "agentnote", Path(__file__).resolve().parents[2] / "launcher" / "agentnote.py")
agentnote = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agentnote)


def test_creates_missing_file(tmp_path):
    target = tmp_path / ".claude" / "CLAUDE.md"
    assert agentnote.install_note(target) == "added"
    text = target.read_text(encoding="utf-8")
    assert "autocad-agent-coordinator" in text and text.count(agentnote.BEGIN) == 1


def test_keeps_user_text_and_is_idempotent(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text("# Của tôi\nđừng xóa", encoding="utf-8")
    agentnote.install_note(target)
    first = target.read_text(encoding="utf-8")
    assert first.startswith("# Của tôi\nđừng xóa")
    assert agentnote.install_note(target) == "same"
    assert target.read_text(encoding="utf-8") == first


def test_updates_old_block_in_place(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text(f"trước\n\n{agentnote.BEGIN}\ncũ\n{agentnote.END}\nsau\n", encoding="utf-8")
    assert agentnote.install_note(target) == "updated"
    text = target.read_text(encoding="utf-8")
    assert "cũ" not in text and text.startswith("trước\n\n") and text.endswith("sau\n")
    assert text.count(agentnote.BEGIN) == 1
