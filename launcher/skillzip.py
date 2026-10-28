"""Zip skills for Claude Desktop, which only accepts skills uploaded as .zip files."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

GUIDE = """Cách thêm skill vào Claude Desktop (Chat / Cowork)

1. Mở Claude Desktop, vào Customize (hoặc Settings), mục Skills.
2. Tải từng file .zip trong thư mục này lên (Upload skill), rồi bật skill.
3. Tải trước autocad-agent-coordinator.zip, sau đó các skill còn lại.
4. Skill trùng tên thì thay bản cũ. Mở cuộc trò chuyện mới để skill có hiệu lực.

Chép skill vào Claude Desktop không thay cho việc thêm hai MCP (autocad_beiming, autocad_puran).
"""


def build_skill_zips(source_root, names, target_dir):
    """Write ``<name>.zip`` (folder ``<name>/`` at its root) for each skill; return the paths."""
    source_root, target_dir = Path(source_root), Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in names:
        skill_dir = source_root / name
        if not (skill_dir / "SKILL.md").is_file():
            raise FileNotFoundError(f"Không tìm thấy nội dung skill: {skill_dir}")
        target = target_dir / f"{name}.zip"
        with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
            for file in sorted(skill_dir.rglob("*")):
                if file.is_file() and "__pycache__" not in file.parts:
                    archive.write(file, f"{name}/{file.relative_to(skill_dir).as_posix()}")
        written.append(target)
    (target_dir / "HUONG-DAN.txt").write_text(GUIDE, encoding="utf-8")
    return written
