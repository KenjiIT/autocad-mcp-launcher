"""Cổng chặn ở gateway: tool CAD chỉ chạy sau khi phiên đã đọc skill điều phối.

Lời dặn trong hướng dẫn MCP và trong CLAUDE.md/AGENTS.md chỉ là nhắc; agent vẫn có thể
bỏ qua. Ở đây gateway từ chối lệnh gọi tool CAD cho tới khi phiên đó đã gọi tool `skills`
với operation=get, name=autocad-agent-coordinator. Lời từ chối ghi sẵn bước kế tiếp.

Phiên được nhận biết bằng Mcp-Session-Id mà gateway phát lúc initialize. Máy khách không
gửi lại mã phiên thì dùng chung một cửa sổ thời gian (ANON_WINDOW).
"""
import os
import time
import uuid
from collections import OrderedDict

REQUIRED_SKILL = "autocad-agent-coordinator"
# Không dính tới AutoCAD; không bao giờ bị chặn (và là đường để đọc skill).
EXEMPT_TOOLS = frozenset({"skills", "knowledge", "knowledge_propose", "launcher_set_backend"})
ANON_WINDOW = 30 * 60
MAX_SESSIONS = 1000
HEADER = "mcp-session-id"
SETTING = "skill_gate"
ENV = "AUTOCAD_MCP_SKILL_GATE"


NOTE = (
    "Gateway chặn: tool CAD trả lỗi SKILL_NOT_READ cho tới khi phiên này đã gọi `skills` với operation=get, "
    f"name={REQUIRED_SKILL} (đọc tệp SKILL.md bằng công cụ khác không được tính); gặp lỗi đó thì đọc skill "
    "rồi gọi lại tool vừa bị chặn."
)


def enabled(settings=None):
    """Bật theo mặc định. Biến môi trường ghi đè cài đặt trong app."""
    forced = os.environ.get(ENV, "").strip().lower()
    if forced in ("0", "off", "false", "no"):
        return False
    if forced in ("1", "on", "true", "yes"):
        return True
    return (settings or {}).get(SETTING, True) is not False


def counts_as_read(tool, arguments):
    """Chỉ việc đọc thân skill điều phối mới tính (không tính list hay tệp tham chiếu)."""
    arguments = arguments or {}
    return (tool == "skills" and arguments.get("operation") == "get"
            and arguments.get("name") == REQUIRED_SKILL and not arguments.get("path"))


def refusal(tool):
    return {
        "ok": False,
        "code": "SKILL_NOT_READ",
        "error": (f"Chưa đọc skill điều phối `{REQUIRED_SKILL}` trong phiên này nên chưa chạy `{tool}`. "
                  "Đọc skill, làm theo bảng chọn skill chuyên biệt trong đó, rồi gọi lại tool vừa bị chặn."),
        "next_tool": "skills",
        "next_arguments": {"operation": "get", "name": REQUIRED_SKILL},
        "then": f"Gọi lại `{tool}` sau khi đã đọc skill.",
    }


class SkillGate:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.sessions = OrderedDict()  # mã phiên -> đã đọc skill hay chưa
        self.anon_read_at = None

    def new_session(self):
        session_id = uuid.uuid4().hex
        self._remember(session_id, False)
        return session_id

    def end_session(self, session_id):
        self.sessions.pop(session_id, None)

    def mark_read(self, session_id):
        if session_id:
            self._remember(session_id, True)
        else:
            self.anon_read_at = self.clock()

    def satisfied(self, session_id):
        if session_id:
            if session_id in self.sessions:
                self.sessions.move_to_end(session_id)
            return self.sessions.get(session_id, False)
        return self.anon_read_at is not None and self.clock() - self.anon_read_at <= ANON_WINDOW

    def blocks(self, tool, session_id):
        return tool not in EXEMPT_TOOLS and not self.satisfied(session_id)

    def _remember(self, session_id, read):
        self.sessions[session_id] = read or self.sessions.get(session_id, False)
        self.sessions.move_to_end(session_id)
        while len(self.sessions) > MAX_SESSIONS:
            self.sessions.popitem(last=False)
