"""Giao diện launcher: chế độ sáng/tối, mức trạng thái dịch vụ (chấm màu), trạng thái LiteBIM/LiteCAD."""
import importlib
import sys
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"
sys.path.insert(0, str(LAUNCHER))

import litebim_bridge as lb  # noqa: E402
import ui_theme  # noqa: E402


def test_theme_ep_sang_toi_bang_bien_moi_truong(monkeypatch):
    monkeypatch.setenv("LAUNCHER_THEME", "dark")
    assert ui_theme.windows_dark() is True
    monkeypatch.setenv("LAUNCHER_THEME", "light")
    assert ui_theme.windows_dark() is False
    light = importlib.reload(ui_theme)
    assert light.PALETTE == light.LIGHT and not light.is_dark()
    monkeypatch.setenv("LAUNCHER_THEME", "dark")
    dark = importlib.reload(ui_theme)
    assert dark.PALETTE == dark.DARK and dark.is_dark()
    monkeypatch.delenv("LAUNCHER_THEME")
    importlib.reload(ui_theme)


def test_moi_muc_trang_thai_co_mau_rieng_va_hai_bang_mau_cung_khoa():
    assert set(ui_theme.LEVEL_COLOR) == {"ok", "busy", "off", "err"}
    assert len(set(ui_theme.LEVEL_COLOR.values())) == 4
    assert set(ui_theme.LIGHT) == set(ui_theme.DARK)
    assert ui_theme.LIGHT["accent"] == "#0e8f86"   # cùng màu nhấn với CAD Studio


def test_trang_thai_litebim_cho_dong_dich_vu():
    assert lb.status("litebim", {"connected": True}) == ("ok", "Đã nối qua gateway")
    assert lb.status("litebim", {"available": True})[0] == "ok"
    assert lb.status("litecad", None) == ("off", "Chưa mở hoặc MCP đang tắt")
    assert lb.describe("litebim", None).startswith("○  LiteBIM")   # dòng cũ vẫn giữ cho nơi khác dùng


def test_doi_che_do_luc_chay_doi_tai_cho_bang_mau_dung_chung():
    palette, levels = ui_theme.PALETTE, ui_theme.LEVEL_COLOR
    ui_theme.set_mode(True)
    assert palette == ui_theme.DARK and levels["ok"] == ui_theme.DARK["ok"]
    assert ui_theme.set_mode(False) is True and palette == ui_theme.LIGHT and levels["ok"] == ui_theme.LIGHT["ok"]
    assert ui_theme.set_mode(False) is False
    assert ui_theme.PALETTE is palette and ui_theme.OK == ui_theme.LIGHT["ok"]


def test_colorref_cho_mau_thanh_tieu_de():
    assert ui_theme.colorref("#0e8f86") == 0x868F0E
    assert ui_theme.colorref("#ffffff") == 0xFFFFFF


def test_bo_chuyen_trang_segmented_chon_bang_chuot_va_ban_phim():
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError:
        import pytest
        pytest.skip("không có màn hình")
    root.withdraw()
    picked = []
    seg = ui_theme.Segmented(root, ["Điều khiển", "Cài đặt"], picked.append)
    xs, _, total = seg._layout()
    assert seg._hit(xs[1][0] + 5) == 1 and seg._hit(total + 50) is None
    seg._click(xs[1][0] + 5)
    assert seg.index == 1 and picked == [1]
    seg.select(1, notify=True)            # chọn lại trang đang mở: không gọi lại
    assert picked == [1]
    seg.event_generate("<Right>")         # bàn phím: vòng sang trang kế
    seg.update()
    seg.select((seg.index + 1) % 2, notify=True)
    assert seg.index == 0 and picked[-1] == 0
    root.destroy()


def test_o_chon_tu_ve_menu_theo_theme_dau_tick_trang_thai_va_ban_phim():
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError:
        import pytest
        pytest.skip("không có màn hình")
    ui_theme.apply(root)
    var = tk.StringVar(value="B")
    changed = []
    dd = ui_theme.Dropdown(root, var, ["A", "B", "C"], command=changed.append, status=lambda v: f"st-{v}")
    dd.pack(); root.update()
    assert dd.cget("text").startswith("B") and dd.cget("text").endswith("▾")
    dd.open(); root.update()
    rows = dd.rows
    assert [r[1].cget("text") for r in rows] == ["", "✓", ""]          # mục đang chọn có dấu ✓
    assert rows[0][0].cget("bg") == ui_theme.PALETTE["card"]            # nền menu theo theme
    dd.menu.event_generate("<Down>"); root.update()
    assert dd.active == 2
    dd.choose(dd.active); root.update()
    assert var.get() == "C" and changed == ["C"] and dd.menu is None and dd.cget("text").startswith("C")
    root.after(300, root.quit); root.mainloop()
    assert dd.statuses.get("A") == "st-A"                               # trạng thái lấy ở luồng nền
    root.destroy()


def test_lua_chon_giao_dien_trong_cai_dat(monkeypatch):
    """Cài đặt > Giao diện: Sáng/Tối thắng Windows; Theo hệ thống thì theo Windows; LAUNCHER_THEME vẫn ép được."""
    monkeypatch.delenv("LAUNCHER_THEME", raising=False)
    old = ui_theme.PREF
    try:
        ui_theme.PREF = "dark"
        assert ui_theme.windows_dark() is True
        ui_theme.PREF = "light"
        assert ui_theme.windows_dark() is False
        monkeypatch.setenv("LAUNCHER_THEME", "dark")
        assert ui_theme.windows_dark() is True
        monkeypatch.delenv("LAUNCHER_THEME")
        ui_theme.PREF = "system"
        assert isinstance(ui_theme.windows_dark(), bool)
        assert [k for k, _ in ui_theme.PREFS] == ["system", "light", "dark"]
    finally:
        ui_theme.PREF = old
