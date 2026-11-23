"""Hộp thoại tự vẽ và giao diện cập nhật của launcher (dialogs.py)."""
import sys
import tkinter as tk
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"
sys.path.insert(0, str(LAUNCHER))

import dialogs  # noqa: E402
import ui_theme  # noqa: E402


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("không có màn hình")
    r.withdraw()
    ui_theme.apply(r)
    yield r
    r.destroy()


def test_gia_lap_ban_moi_va_tai(monkeypatch):
    monkeypatch.delenv("LAUNCHER_FAKE_UPDATE", raising=False)
    assert dialogs.fake_update() is None
    monkeypatch.setenv("LAUNCHER_FAKE_UPDATE", "0.4.9")
    up = dialogs.fake_update()
    assert up["version"] == "0.4.9" and up["fake"] and up["size"] > 0
    seen = []
    assert dialogs.fake_download(up, lambda r, t: seen.append((r, t)), delay=0) == "fake.zip"
    assert seen[-1] == (up["size"], up["size"]) and len(seen) == 20
    monkeypatch.setenv("LAUNCHER_FAKE_UPDATE_FAIL", "1")
    with pytest.raises(RuntimeError, match="Thử lại"):
        dialogs.fake_download(up, lambda r, t: None, delay=0)
    with pytest.raises(RuntimeError, match="huỷ"):
        dialogs.fake_download(up, lambda r, t: None, cancelled=lambda: True, delay=0)


def test_dung_luong_de_doc():
    assert dialogs.human_size(512) == "512 B"
    assert dialogs.human_size(38_600_000) == "36.8 MB"


def test_ghi_chu_phat_hanh_markdown_don_gian(root):
    t = tk.Text(root)
    dialogs.render_notes(t, "## Mới\n- **Đậm** và `mã`\nDòng thường")
    text = t.get("1.0", "end")
    assert "Mới\n" in text and "•  Đậm và mã" in text and "#" not in text and "**" not in text
    assert "h" in t.tag_names("1.0") and t.cget("state") == "disabled"
    dialogs.render_notes(t, "")
    assert "Không có ghi chú" in t.get("1.0", "end")


def _press(root, key):
    """Gọi đúng phím tắt đã gắn trên hộp đang mở (phím ảo cần focus thật nên gọi thẳng script của binding)."""
    def go():
        boxes = [w for w in root.winfo_children() if isinstance(w, dialogs.Dialog) and w.winfo_exists()]
        if boxes:
            box = boxes[0]
            assert box.bind(key), f"chưa gắn phím {key}"
            box.default() if key == "<Return>" else box.cancel()   # đúng việc mà binding Enter/Esc gọi
    root.after(300, go)
    root.after(3000, lambda: [w.cancel() for w in root.winfo_children() if isinstance(w, dialogs.Dialog) and w.winfo_exists()])


def test_hop_hoi_enter_dong_y_esc_huy(root):
    _press(root, "<Return>")
    assert dialogs.ask(root, "Ghi cấu hình?", "Tiếp tục?") is True
    _press(root, "<Escape>")
    assert dialogs.ask(root, "Ghi cấu hình?", "Tiếp tục?") is False


def test_hop_cap_nhat_cac_trang_thai(root, monkeypatch):
    monkeypatch.setenv("LAUNCHER_FAKE_UPDATE", "0.4.9")
    calls = []
    d = dialogs.UpdateDialog(root, "0.4.8", dialogs.fake_update(), {
        "start": lambda u: calls.append(("start", u["version"])), "cancel": lambda: calls.append(("cancel",)),
        "skip": lambda v: calls.append(("skip", v)), "restart": lambda: calls.append(("restart",))})
    d.show(wait=False)
    d.default()                                   # Enter = Cập nhật ngay
    assert calls == [("start", "0.4.9")] and d.bar.winfo_exists()
    d.progress(50, 100)
    assert d.bar.fraction == 0.5 and "50%" in d.progress_label.cget("text")
    d.state_error("Mất mạng")
    d.default()                                   # Thử lại
    assert calls[-1] == ("start", "0.4.9")
    d.state_done()
    d.default()                                   # Khởi động lại để hoàn tất
    assert calls[-1] == ("restart",)
