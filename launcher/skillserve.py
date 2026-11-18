"""Serve the project's skills over MCP for clients that cannot load skill folders."""
import re
from pathlib import Path

NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".csv", ".json"}
MAX_BYTES = 200_000

INSTRUCTIONS = (
    "Dự án AutoCAD này có bộ skill hướng dẫn quy trình và quy tắc. Trước khi gọi bất kỳ tool CAD nào, "
    "gọi tool `skills` với operation=get, name=autocad-agent-coordinator và làm theo; skill đó có bảng chọn "
    "skill chuyên biệt theo yêu cầu (operation=list liệt kê tất cả). Đọc xong skill điều phối, tự gọi "
    "operation=list, chọn rồi nạp (operation=get) mọi skill chuyên biệt khớp yêu cầu trước khi vẽ hoặc sửa; "
    "không tự bỏ skill vì lý do như vẽ sơ bộ hay việc nhỏ. Skill dài có tệp tham chiếu: đọc bằng "
    "operation=get, name, path. Kho skill riêng của agent (thư mục skills của tài khoản: Claude Code dùng ~/.claude/skills, "
    "Codex CLI dùng ~/.codex/skills; agent khác dùng thư mục skills theo tài liệu của chính nó, "
    "không rõ thì ~/.agents/skills và báo người dùng đã chọn đâu; ghi vào kho của chính agent đang chạy) chưa có hoặc đang thiếu skill nào trong operation=list thì hỏi người dùng một lần "
    "có muốn thêm không; đồng ý thì với từng skill thiếu, lấy SKILL.md và mọi tệp tham chiếu bằng operation=get "
    "rồi ghi vào <kho skill>/<tên skill>/ giữ nguyên cấu trúc thư mục, không ghi đè skill người dùng đã sửa."
)


def _description(text):
    for line in text.replace("\r\n", "\n").split("\n")[:8]:
        if line.startswith("description:"):
            return line[len("description:"):].strip()
    return ""


def list_skills(root):
    root = Path(root)
    if not root.is_dir():
        return []
    return [{"name": p.name, "description": _description((p / "SKILL.md").read_text(encoding="utf-8"))}
            for p in sorted(root.iterdir()) if (p / "SKILL.md").is_file()]


def read_skill(root, name, path=None):
    """Return SKILL.md, or one text file inside the skill folder; raise ValueError on a bad request."""
    root = Path(root)
    if not isinstance(name, str) or not NAME.fullmatch(name) or not (root / name / "SKILL.md").is_file():
        raise ValueError(f"Không có skill tên {name!r}")
    folder = (root / name).resolve()
    if path in (None, "", "SKILL.md"):
        target = folder / "SKILL.md"
    else:
        if not isinstance(path, str):
            raise ValueError("path phải là chuỗi")
        target = (folder / path).resolve()
        if folder not in target.parents or target.suffix.lower() not in TEXT_SUFFIXES or not target.is_file():
            raise ValueError(f"Không đọc được tệp {path!r} trong skill {name}")
    if target.stat().st_size > MAX_BYTES:
        raise ValueError("Tệp quá lớn")
    files = sorted(f.relative_to(folder).as_posix() for f in folder.rglob("*")
                   if f.is_file() and f.suffix.lower() in TEXT_SUFFIXES and f.name != "SKILL.md"
                   and "__pycache__" not in f.parts)
    return {"name": name, "path": target.relative_to(folder).as_posix(),
            "content": target.read_text(encoding="utf-8"), "other_files": files}
