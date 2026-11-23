"""Tab Cài đặt chia nhóm: menu nhóm (ui_theme.NavList), tìm nhanh, nhớ nhóm mở lần cuối."""
import sys
import tkinter as tk
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "launcher"
sys.path.insert(0, str(LAUNCHER))

import ui_theme  # noqa: E402


def test_fold_bo_dau_de_tim():
    assert ui_theme.fold("Khởi động cùng Windows") == "khoi dong cung windows"
    assert ui_theme.fold("Đặt lại") == "dat lai"


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("không có màn hình")
    r.withdraw()
    yield r
    r.destroy()


def test_menu_nhom_chon_bang_chuot_ban_phim_va_dem_ket_qua(root):
    picked = []
    nav = ui_theme.NavList(root, [("a", "Chung"), ("b", "Dữ liệu"), ("c", "Nâng cao")], picked.append)
    nav.pack(); root.update()
    nav.select("b", notify=True)
    assert nav.current == "b" and picked == ["b"]
    nav.event_generate("<Down>"); nav.focus_force(); root.update()
    nav.select("c", notify=True); nav.select("c", notify=True)     # chọn lại nhóm đang mở: không gọi lại
    assert picked == ["b", "c"]
    nav.set_counts({"a": 2}); root.update()
    assert nav.rows["a"]["badge"].cget("text") == "2" and nav.rows["b"]["badge"].cget("text") == ""
    nav.set_compact(True); root.update()
    assert nav.rows["b"]["text"].cget("text") == "Dữ"                # cửa sổ hẹp: nhãn thu gọn
    nav.set_counts(None); root.update()
    assert nav.rows["a"]["badge"].cget("text") == ""


def test_tab_cai_dat_nhom_tim_kiem_va_nho_nhom(monkeypatch):
    try:
        tk.Tk().destroy()
    except tk.TclError:
        pytest.skip("không có màn hình")
    monkeypatch.setattr(sys, "argv", ["app"])
    import tray
    monkeypatch.setattr(tray, "TrayIcon", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    import app as appmod
    saved = {}
    monkeypatch.setattr(appmod, "load_settings", lambda: {"settings_group": "dulieu"})
    monkeypatch.setattr(appmod, "save_setting", lambda k, v: saved.__setitem__(k, v))
    for n in ("tick", "check_for_updates", "knowledge_tick", "dutoan_tick", "start"):
        monkeypatch.setattr(appmod.App, n, lambda self, *a, **k: None)
    monkeypatch.setattr(appmod.App, "TrayIcon", None, raising=False)
    app = appmod.App()
    try:
        app.withdraw()
        assert app.current_group == "dulieu"                         # nhớ nhóm mở lần cuối
        keys = [k for k, _, _ in app.SETTINGS_GROUPS]
        assert keys == ["chung", "ketnoi", "agent", "dulieu", "capnhat", "nangcao"]
        app.show_group("capnhat")
        assert saved.get("settings_group") == "capnhat" and app.groups["capnhat"].winfo_manager() == "pack"
        assert app.groups["dulieu"].winfo_manager() == ""            # chỉ hiện một nhóm
        app.settings_search_var.set("khoi dong cung windows")          # tìm không dấu
        app.update()
        assert app.current_group == "chung" and app.settings_nav.counts.get("chung")
        app.settings_search_var.set("token")
        assert app.current_group == "ketnoi"
        app.settings_search_var.set("")
        assert app.settings_nav.counts is None
        # mọi tuỳ chọn cũ vẫn còn trong một nhóm nào đó
        texts = " | ".join(t for _, _, t in app.settings_index)
        for must in ("buoc agent doc skill", "tu kiem tra ban moi", "du lieu du toan", "ket noi ra server", "thu vien block",
                     "cai skill cho agent", "tri thuc autocad", "dat lai cai dat", "nhat ky"):
            assert must in texts, must
    finally:
        app.destroy()
