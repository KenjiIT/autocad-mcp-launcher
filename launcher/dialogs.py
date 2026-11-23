"""Hộp thoại và giao diện cập nhật của launcher, cùng theme với ui_theme (teal, sáng/tối, thanh tiêu đề theo theme).

Thay tkinter.messagebox mặc định: ``ask`` / ``info`` / ``error`` (Enter = nút chính, Esc = huỷ) và ``UpdateDialog``
(có bản mới → đang tải → lỗi/xong). Logic tải, kiểm SHA-256 và cài vẫn ở updater.py; ở đây chỉ là giao diện.

Giả lập bản mới để chụp ảnh / thử: LAUNCHER_FAKE_UPDATE=0.4.9 (thêm LAUNCHER_FAKE_UPDATE_FAIL=1 để tải lỗi).
"""
import os
import re
import threading
import time
import tkinter as tk
from tkinter import ttk

import ui_theme


# ---- hộp thoại chung ------------------------------------------------------

class Dialog(tk.Toplevel):
    """Cửa sổ con có theme: tiêu đề, nội dung, hàng nút ở dưới (nút chính bên phải). Modal với cửa sổ cha."""

    def __init__(self, parent, title, width=460):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        p = ui_theme.PALETTE
        self.configure(bg=p["bg"])
        self.result = None
        self.width = width
        self.body = ttk.Frame(self, padding=(22, 18, 22, 6))
        self.body.pack(fill="both", expand=True)
        self.buttons = ttk.Frame(self, padding=(22, 8, 22, 18))
        self.buttons.pack(fill="x")
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<Return>", lambda e: self.default())
        self._default = None

    def heading(self, text, sub=None):
        ttk.Label(self.body, text=text, style="H2.TLabel", wraplength=self.width - 44, justify="left").pack(anchor="w")
        if sub:
            ttk.Label(self.body, text=sub, style="Muted.TLabel", wraplength=self.width - 44, justify="left").pack(anchor="w", pady=(6, 0))

    def clear_buttons(self):
        for w in self.buttons.winfo_children():
            w.destroy()
        self._default = None

    def button(self, text, command, primary=False, danger=False, side="right"):
        style = "Accent.TButton" if primary and not danger else ("Danger.TButton" if danger else "TButton")
        b = ttk.Button(self.buttons, text=text, style=style, command=command)
        b.pack(side=side, padx=(8, 0) if side == "right" else (0, 8))
        if primary:
            self._default = command
            b.focus_set()
        return b

    def default(self):
        if self._default:
            self._default()

    def done(self, value):
        self.result = value
        self.close()

    def cancel(self):
        self.done(None)

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def show(self, wait=True):
        """Đặt giữa cửa sổ cha, theme thanh tiêu đề, giữ focus (modal)."""
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        w = max(self.width, self.winfo_reqwidth())
        h = self.winfo_reqheight()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
            y = parent.winfo_rooty() + max(20, (parent.winfo_height() - h) // 3)
        except tk.TclError:
            x, y = 200, 200
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        self.deiconify()
        ui_theme.title_bar(self)
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_force()
        if wait:
            self.wait_window()
        return self.result


def ask(parent, title, message, ok="Đồng ý", cancel="Huỷ", danger=False, detail=None):
    """Thay messagebox.askyesno: True khi bấm nút chính (Enter), False khi huỷ (Esc)."""
    d = Dialog(parent, title)
    d.heading(title, message)
    if detail:
        box = ui_theme.text_widget(d.body, height=min(12, detail.count("\n") + 2))
        box.insert("1.0", detail)
        box.configure(state="disabled", wrap="word")
        box.pack(fill="both", expand=True, pady=(10, 0))
    d.button(ok, lambda: d.done(True), primary=True, danger=danger)
    d.button(cancel, lambda: d.done(False))
    return bool(d.show())


def info(parent, title, message):
    d = Dialog(parent, title)
    d.heading(title, message)
    d.button("Đóng", lambda: d.done(True), primary=True)
    d.show()


def error(parent, title, message):
    d = Dialog(parent, title)
    ttk.Label(d.body, text="●  " + title, style="H2.TLabel", foreground=ui_theme.PALETTE["err"]).pack(anchor="w")
    ttk.Label(d.body, text=message, style="Muted.TLabel", wraplength=d.width - 44, justify="left").pack(anchor="w", pady=(6, 0))
    d.button("Đóng", lambda: d.done(True), primary=True)
    d.show()


# ---- thanh tiến độ, ghi chú phát hành -------------------------------------

class ProgressBar(tk.Canvas):
    """Thanh tiến độ bo tròn, màu nhấn; ``set(fraction)`` 0..1, None = chưa biết tổng (chạy qua lại)."""

    def __init__(self, parent, height=10):
        super().__init__(parent, height=height, highlightthickness=0, borderwidth=0, bg=ui_theme.PALETTE["bg"])
        self.fraction = 0.0
        self.bind("<Configure>", lambda e: self.redraw())

    def set(self, fraction):
        self.fraction = fraction
        self.redraw()

    def redraw(self):
        p = ui_theme.PALETTE
        w, h = max(self.winfo_width(), 10), int(self["height"])
        self.delete("all")
        self.configure(bg=p["bg"])
        r = h // 2
        self.create_line(r, r, w - r, r, width=h, capstyle="round", fill=p["line"])
        if self.fraction is None:
            x = (time.monotonic() * 120) % (w + 80) - 80
            self.create_line(max(r, x), r, min(w - r, x + 80), r, width=h, capstyle="round", fill=p["accent"])
        elif self.fraction > 0:
            self.create_line(r, r, r + (w - 2 * r) * min(1.0, self.fraction), r, width=h, capstyle="round", fill=p["accent"])


def render_notes(text_widget, notes):
    """Ghi chú phát hành dạng markdown đơn giản: # tiêu đề đậm, - gạch đầu dòng, **đậm**, `mã`."""
    p = ui_theme.PALETTE
    t = text_widget
    t.configure(state="normal", wrap="word")
    t.delete("1.0", "end")
    t.tag_configure("h", font=(ui_theme.FONT, 11, "bold"), spacing1=6, spacing3=2)
    t.tag_configure("b", font=(ui_theme.FONT, 10, "bold"))
    t.tag_configure("code", font=(ui_theme.MONO, 9), background=p["line"])
    t.tag_configure("li", lmargin1=8, lmargin2=22)
    t.configure(font=(ui_theme.FONT, 10))
    for line in (notes or "Không có ghi chú phát hành.").splitlines():
        tags = ()
        m = re.match(r"^\s*#{1,6}\s+(.*)", line)
        if m:
            t.insert("end", m.group(1) + "\n", ("h",))
            continue
        m = re.match(r"^\s*[-*+]\s+(.*)", line)
        if m:
            line, tags = "•  " + m.group(1), ("li",)
        for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", line):
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                t.insert("end", part[2:-2], tags + ("b",))
            elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                t.insert("end", part[1:-1], tags + ("code",))
            else:
                t.insert("end", part, tags)
        t.insert("end", "\n", tags)
    t.configure(state="disabled")


def human_size(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024


# ---- hộp cập nhật ---------------------------------------------------------

class UpdateDialog(Dialog):
    """Có bản mới → đang tải (tiến độ, Huỷ) → lỗi (Thử lại) / xong (Khởi động lại để hoàn tất).

    ``actions``: dict với các hàm do app cung cấp: start(update), cancel(), skip(version), restart()."""

    def __init__(self, parent, current, update, actions):
        super().__init__(parent, "Cập nhật AutoCAD MCP Launcher", width=520)
        self.update_info, self.actions, self.current = update, actions, current
        self.bind("<Return>", lambda e: self.default())
        self.state_offer()

    def _reset_body(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.clear_buttons()

    def _versions(self):
        row = ttk.Frame(self.body)
        row.pack(anchor="w", pady=(8, 0))
        ttk.Label(row, text=f"v{self.current}", style="Muted.TLabel").pack(side="left")
        ttk.Label(row, text="  →  ", style="Muted.TLabel").pack(side="left")
        ttk.Label(row, text=f"v{self.update_info['version']}", style="H3.TLabel", foreground=ui_theme.PALETTE["accent"]).pack(side="left")
        size = self.update_info.get("size")
        if size:
            ttk.Label(row, text=f"   ·   {human_size(size)}", style="Muted.TLabel").pack(side="left")

    def state_offer(self):
        self._reset_body()
        self.heading("Có bản mới của launcher", "Cập nhật sẽ tải gói, kiểm tra SHA-256 rồi khởi động lại launcher và các kết nối MCP.")
        self._versions()
        ttk.Label(self.body, text="Có gì mới", style="H3.TLabel").pack(anchor="w", pady=(14, 4))
        frame = ttk.Frame(self.body)
        frame.pack(fill="both", expand=True)
        notes = ui_theme.text_widget(frame, height=9)
        bar = ttk.Scrollbar(frame, orient="vertical", command=notes.yview)
        notes.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        notes.pack(side="left", fill="both", expand=True)
        render_notes(notes, self.update_info.get("notes"))
        self.button("Cập nhật ngay", self._start, primary=True)
        self.button("Để sau", self.cancel)
        self.button("Bỏ qua bản này", self._skip, side="left")

    def _start(self):
        self.state_downloading()
        self.actions["start"](self.update_info)

    def _skip(self):
        self.actions["skip"](self.update_info["version"])
        self.done("skip")

    def state_downloading(self):
        self._reset_body()
        self.heading(f"Đang tải bản v{self.update_info['version']}…", "Có thể tiếp tục làm việc; launcher chỉ khởi động lại khi bạn đồng ý.")
        self.bar = ProgressBar(self.body)
        self.bar.pack(fill="x", pady=(18, 6))
        self.progress_label = ttk.Label(self.body, text="Đang bắt đầu…", style="Muted.TLabel")
        self.progress_label.pack(anchor="w")
        self.button("Huỷ", self._cancel_download)
        self._default = None
        self.unbind("<Return>")
        self._relayout()

    def progress(self, received, total):
        if not getattr(self, "bar", None) or not self.bar.winfo_exists():
            return
        if total:
            self.bar.set(received / total)
            self.progress_label.configure(text=f"{received * 100 // total}%  ·  {human_size(received)} / {human_size(total)}")
        else:
            self.bar.set(None)
            self.progress_label.configure(text=human_size(received))

    def _cancel_download(self):
        self.actions["cancel"]()
        self.done("cancel")

    def state_error(self, message):
        self._reset_body()
        ttk.Label(self.body, text="●  Không tải được bản cập nhật", style="H2.TLabel", foreground=ui_theme.PALETTE["err"]).pack(anchor="w")
        ttk.Label(self.body, text=message, style="Muted.TLabel", wraplength=self.width - 44, justify="left").pack(anchor="w", pady=(8, 0))
        ttk.Label(self.body, text="Launcher vẫn chạy bình thường với bản hiện tại.", style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
        self.button("Thử lại", self._start, primary=True)
        self.button("Đóng", self.cancel)
        self.bind("<Return>", lambda e: self.default())
        self._relayout()

    def state_done(self):
        self._reset_body()
        ttk.Label(self.body, text="●  Đã tải và kiểm tra xong", style="H2.TLabel", foreground=ui_theme.PALETTE["ok"]).pack(anchor="w")
        ttk.Label(self.body, text=f"Bản v{self.update_info['version']} đã sẵn sàng. Launcher sẽ đợi các yêu cầu AutoCAD đang chạy xong, "
                                  "cài bản mới rồi tự mở lại.", style="Muted.TLabel", wraplength=self.width - 44, justify="left").pack(anchor="w", pady=(8, 0))
        self.button("Khởi động lại để hoàn tất", lambda: (self.actions["restart"](), self.done("restart")), primary=True)
        self.button("Để sau", self.cancel)
        self.bind("<Return>", lambda e: self.default())
        self._relayout()

    def _relayout(self):
        self.update_idletasks()
        self.geometry(f"{max(self.width, self.winfo_reqwidth())}x{self.winfo_reqheight()}")


# ---- thẻ thông báo trên tab Điều khiển ------------------------------------

class Banner(ttk.Frame):
    """Dải 'Có bản mới vX' + 'Xem & cập nhật' + 'Để sau'; ẩn cho tới khi ``show`` được gọi."""

    def __init__(self, parent, on_open, on_dismiss):
        super().__init__(parent, style="Card.TFrame", padding=1)
        inner = ttk.Frame(self, style="Inner.TFrame", padding=(14, 10))
        inner.pack(fill="x")
        self.dot = ttk.Label(inner, text="●", style="Dot.TLabel", foreground=ui_theme.PALETTE["accent"])
        self.dot.pack(side="left", padx=(0, 8))
        self.text = ttk.Label(inner, text="", style="Card.H3.TLabel")
        self.text.pack(side="left")
        self.sub = ttk.Label(inner, text="", style="Card.Muted.TLabel")
        self.sub.pack(side="left", padx=(10, 0))
        ttk.Button(inner, text="Để sau", style="Link.TButton", command=on_dismiss).pack(side="right")
        ttk.Button(inner, text="Xem & cập nhật", style="Accent.TButton", command=on_open).pack(side="right", padx=(0, 10))

    def show(self, version, before=None):
        self.text.configure(text=f"Có bản mới v{version}")
        self.sub.configure(text="Cập nhật khi bạn sẵn sàng.")
        if not self.winfo_ismapped():
            self.pack(fill="x", pady=(0, 12))

    def hide(self):
        self.pack_forget()


# ---- giả lập bản mới ------------------------------------------------------

def fake_update():
    """Bản mới giả lập khi đặt LAUNCHER_FAKE_UPDATE (để chụp ảnh/test), None nếu không đặt."""
    version = os.environ.get("LAUNCHER_FAKE_UPDATE", "").strip()
    if not version:
        return None
    return {"version": version, "tag": "v" + version, "fake": True, "size": 38_600_000, "sha256": "0" * 64,
            "url": "", "checksum_url": None,
            "notes": "## Có gì mới\n- Giao diện launcher mới: **theme sáng/tối**, thanh tiêu đề theo theme\n"
                     "- Ô chọn agent tự vẽ, hiện trạng thái MCP của từng agent\n- Sửa `Thêm vào agent` cho Claude Code\n"
                     "## Sửa lỗi\n- Thẻ CAD Studio báo đúng Đang chạy\n- Nhiều cải tiến nhỏ khác"}


def fake_download(release, progress, cancelled=lambda: False, steps=20, delay=None):
    """Giả lập tải về (không ghi file); LAUNCHER_FAKE_UPDATE_FAIL=1 thì lỗi giữa chừng."""
    total = int(release.get("size") or 1)
    delay = float(os.environ.get("LAUNCHER_FAKE_UPDATE_DELAY", "0.08")) if delay is None else delay
    for i in range(1, steps + 1):
        if cancelled():
            raise RuntimeError("Đã huỷ")
        time.sleep(delay)
        progress(total * i // steps, total)
        if os.environ.get("LAUNCHER_FAKE_UPDATE_FAIL") and i == steps // 2:
            raise RuntimeError("Mất kết nối tới GitHub khi đang tải (giả lập). Kiểm tra mạng rồi bấm Thử lại.")
    return "fake.zip"
