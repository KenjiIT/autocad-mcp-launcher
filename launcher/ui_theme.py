"""Giao diện của launcher: theme ttk sáng/tối (theo Windows), DPI cao, màu chung với CAD Studio.

Không dùng thư viện ngoài: tự style theme "clam" của ttk. Màu và kiểu chữ dùng chung ở đây để app.py chỉ nói
"nút chính", "chữ phụ", "thẻ"... chứ không rải mã màu khắp nơi.
"""
import ctypes
import os
import tkinter as tk
from tkinter import ttk

try:
    import winreg
except ImportError:  # chỉ để test chạy được ngoài Windows
    winreg = None

FONT = "Segoe UI"
MONO = "Consolas"

LIGHT = {
    "bg": "#f4f6f8", "card": "#ffffff", "line": "#dde3ea", "ink": "#16212b", "mute": "#5f6b78",
    "accent": "#0e8f86", "accent_hover": "#0b776f", "accent_ink": "#ffffff", "accent_soft": "#e0f4f2",
    "ok": "#1f8a4c", "warn": "#b7791f", "err": "#c0392b", "off": "#9aa5b1",
    "field": "#ffffff", "btn": "#ffffff", "btn_hover": "#eef2f5", "code": "#f7f9fb",
}
DARK = {
    "bg": "#0f1720", "card": "#16212d", "line": "#273444", "ink": "#e6edf5", "mute": "#93a3b5",
    "accent": "#2bb3a8", "accent_hover": "#36c7bb", "accent_ink": "#04201e", "accent_soft": "#143330",
    "ok": "#3ed98f", "warn": "#e7a73b", "err": "#ff6b63", "off": "#66768a",
    "field": "#0f1924", "btn": "#1c2938", "btn_hover": "#243447", "code": "#101a25",
}


# Lựa chọn giao diện của người dùng (Cài đặt > Giao diện): "system" | "light" | "dark".
PREF = "system"
PREFS = (("system", "Theo hệ thống"), ("light", "Sáng"), ("dark", "Tối"))


def windows_dark():
    """App nên tối không? Thứ tự: biến LAUNCHER_THEME (ép, cho test/chụp ảnh) > lựa chọn trong Cài đặt > Windows."""
    forced = os.environ.get("LAUNCHER_THEME", "").strip().lower()
    if forced in ("light", "dark"):
        return forced == "dark"
    if PREF in ("light", "dark"):
        return PREF == "dark"
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


# PALETTE là MỘT dict dùng chung, đổi tại chỗ khi Windows đổi sáng/tối (set_mode) để mọi nơi đang giữ nó thấy màu mới.
PALETTE = dict(DARK if windows_dark() else LIGHT)
LEVEL_COLOR = {}


def is_dark():
    return PALETTE["bg"] == DARK["bg"]


def set_mode(dark):
    """Chọn bảng màu sáng/tối; trả True nếu có đổi."""
    target = DARK if dark else LIGHT
    changed = PALETTE != target
    PALETTE.clear(); PALETTE.update(target)
    # Màu chấm trạng thái theo mức: sẵn sàng / đang khởi động-đang nối / chưa chạy / lỗi.
    LEVEL_COLOR.clear()
    LEVEL_COLOR.update({"ok": PALETTE["ok"], "busy": PALETTE["warn"], "off": PALETTE["off"], "err": PALETTE["err"]})
    global OK, ERR, MUTED, WARN
    OK, ERR, MUTED, WARN = PALETTE["ok"], PALETTE["err"], PALETTE["mute"], PALETTE["warn"]
    return changed


OK = ERR = MUTED = WARN = ""
set_mode(is_dark())


def enable_dpi_awareness():
    """Gọi TRƯỚC khi tạo Tk: chữ nét trên màn hình DPI cao thay vì bị Windows phóng mờ."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


DWMWA_USE_IMMERSIVE_DARK_MODE = 20          # Windows 10 20H1+ và Windows 11
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19      # Windows 10 1809-1909
DWMWA_CAPTION_COLOR, DWMWA_TEXT_COLOR = 35, 36   # chỉ Windows 11 (build 22000+); Windows 10 trả lỗi, bỏ qua


def colorref(hex_color):
    """'#rrggbb' -> COLORREF 0x00BBGGRR."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r | (g << 8) | (b << 16)


def title_bar(root):
    """Thanh tiêu đề Windows theo theme của app: tối/sáng (Windows 10 1809+), cùng màu nền app (Windows 11).
    Không tự vẽ thanh tiêu đề (overrideredirect) để giữ snap, kéo cửa sổ, nút taskbar. Lỗi thì bỏ qua."""
    try:
        dwm = ctypes.windll.dwmapi
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
    except (AttributeError, OSError, tk.TclError):
        return False
    def set_int(attr, value):
        v = ctypes.c_int(value)
        return dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v)) == 0
    dark = 1 if is_dark() else 0
    ok = set_int(DWMWA_USE_IMMERSIVE_DARK_MODE, dark) or set_int(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, dark)
    set_int(DWMWA_CAPTION_COLOR, colorref(PALETTE["bg"]))     # Windows 11: thanh tiêu đề cùng màu nền app
    set_int(DWMWA_TEXT_COLOR, colorref(PALETTE["ink"]))
    # Windows 10 chỉ vẽ lại khung khi khung "đổi": báo SWP_FRAMECHANGED để thấy ngay, không cần thu nhỏ/phóng to.
    try:
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
    except (AttributeError, OSError):
        pass
    return ok


dark_title_bar = title_bar   # tên cũ


def apply(root):
    """Style toàn bộ ttk của cửa sổ ``root``."""
    p = PALETTE
    root.configure(bg=p["bg"])
    # Không đặt "*Font" trong option database: nó đè font của style ttk (tiêu đề sẽ mất chữ đậm).
    root.option_add("*TCombobox*Listbox.font", (FONT, 10))
    root.option_add("*TCombobox*Listbox.background", p["field"])
    root.option_add("*TCombobox*Listbox.foreground", p["ink"])
    root.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["accent_ink"])
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=p["bg"], foreground=p["ink"], font=(FONT, 10), bordercolor=p["line"],
                lightcolor=p["bg"], darkcolor=p["bg"], troughcolor=p["bg"], focuscolor=p["accent"],
                selectbackground=p["accent"], selectforeground=p["accent_ink"], insertcolor=p["ink"])
    s.configure("TFrame", background=p["bg"])
    s.configure("Card.TFrame", background=p["card"], relief="solid", borderwidth=1, bordercolor=p["line"])
    s.configure("Inner.TFrame", background=p["card"])
    s.configure("Hl.Card.TFrame", background=p["card"], relief="solid", borderwidth=1, bordercolor=p["accent"],
                lightcolor=p["accent"], darkcolor=p["accent"])   # thẻ vừa được tìm thấy (ô tìm nhanh)
    s.configure("TLabel", background=p["bg"], foreground=p["ink"])
    for base, bg in (("", p["bg"]), ("Card.", p["card"])):
        s.configure(f"{base}TLabel", background=bg, foreground=p["ink"])
        s.configure(f"{base}Muted.TLabel", background=bg, foreground=p["mute"])
        s.configure(f"{base}Title.TLabel", background=bg, foreground=p["ink"], font=(FONT, 15, "bold"))
        s.configure(f"{base}H2.TLabel", background=bg, foreground=p["ink"], font=(FONT, 12, "bold"))
        s.configure(f"{base}H3.TLabel", background=bg, foreground=p["ink"], font=(FONT, 10, "bold"))
        s.configure(f"{base}Small.TLabel", background=bg, foreground=p["mute"], font=(FONT, 9))
        s.configure(f"{base}Ok.TLabel", background=bg, foreground=p["ok"])
    s.configure("Dot.TLabel", background=p["card"], font=(FONT, 12))
    s.configure("Pill.TLabel", font=(FONT, 9, "bold"), padding=(10, 3))

    # Nút: thường (viền nhạt), chính (teal), phụ dạng chữ
    s.configure("TButton", background=p["btn"], foreground=p["ink"], bordercolor=p["line"], padding=(12, 6),
                borderwidth=1, lightcolor=p["btn"], darkcolor=p["btn"], focusthickness=1)
    s.map("TButton", background=[("disabled", p["bg"]), ("pressed", p["btn_hover"]), ("active", p["btn_hover"])],
          foreground=[("disabled", p["off"])], bordercolor=[("focus", p["accent"])])
    s.configure("Accent.TButton", background=p["accent"], foreground=p["accent_ink"], bordercolor=p["accent"],
                lightcolor=p["accent"], darkcolor=p["accent"], font=(FONT, 10, "bold"), padding=(14, 7))
    s.map("Accent.TButton", background=[("disabled", p["off"]), ("pressed", p["accent_hover"]), ("active", p["accent_hover"])],
          foreground=[("disabled", p["card"])], bordercolor=[("active", p["accent_hover"])])
    # Ô chọn (Dropdown): cao bằng nút chính, chữ trái, mũi tên phải
    s.configure("Select.TButton", background=p["field"], foreground=p["ink"], bordercolor=p["line"], padding=(12, 7),
                lightcolor=p["field"], darkcolor=p["field"], anchor="w", font=(FONT, 10))
    s.map("Select.TButton", background=[("pressed", p["btn_hover"]), ("active", p["btn_hover"])],
          bordercolor=[("focus", p["accent"]), ("active", p["accent"])])
    s.configure("Big.Accent.TButton", font=(FONT, 11, "bold"), padding=(20, 10))
    s.configure("Danger.TButton", foreground=p["err"])
    s.configure("Link.TButton", background=p["card"], foreground=p["accent"], borderwidth=0, padding=(2, 2),
                lightcolor=p["card"], darkcolor=p["card"], bordercolor=p["card"])
    s.map("Link.TButton", background=[("active", p["card"])], foreground=[("active", p["accent_hover"])])

    # Theme clam vẽ ô tick bằng indicatorbackground (nền ô) + indicatorforeground (dấu tick) + upper/lowerbordercolor (viền).
    # Trước đây dấu tick để mặc định màu đen: ở chế độ tối nền ô gần đen nên tick không thấy, tưởng bấm không được.
    s.configure("TCheckbutton", background=p["card"], foreground=p["ink"], indicatorbackground=p["field"],
                indicatorforeground=p["accent_ink"], upperbordercolor=p["mute"], lowerbordercolor=p["mute"],
                indicatorrelief="flat", indicatormargin=(0, 0, 8, 0), padding=(0, 2), focuscolor=p["card"])
    s.map("TCheckbutton", background=[("active", p["card"])],
          indicatorbackground=[("selected", p["accent"]), ("active", p["btn_hover"]), ("!selected", p["field"])],
          indicatorforeground=[("selected", p["accent_ink"])],
          upperbordercolor=[("selected", p["accent"]), ("active", p["accent"])],
          lowerbordercolor=[("selected", p["accent"]), ("active", p["accent"])])
    s.configure("TEntry", fieldbackground=p["field"], foreground=p["ink"], bordercolor=p["line"],
                lightcolor=p["field"], darkcolor=p["field"], padding=(6, 4))
    s.map("TEntry", bordercolor=[("focus", p["accent"])], fieldbackground=[("readonly", p["code"])])
    s.configure("TCombobox", fieldbackground=p["field"], background=p["btn"], foreground=p["ink"],
                arrowcolor=p["ink"], bordercolor=p["line"], lightcolor=p["field"], darkcolor=p["field"], padding=(6, 4))
    s.map("TCombobox", fieldbackground=[("readonly", p["field"])], selectbackground=[("readonly", p["field"])],
          selectforeground=[("readonly", p["ink"])], bordercolor=[("focus", p["accent"])])
    s.configure("TNotebook", background=p["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    s.configure("TNotebook.Tab", background=p["bg"], foreground=p["mute"], padding=(16, 8), borderwidth=0,
                font=(FONT, 10, "bold"), lightcolor=p["bg"], bordercolor=p["bg"])
    s.map("TNotebook.Tab", background=[("selected", p["bg"])], foreground=[("selected", p["accent"])],
          lightcolor=[("selected", p["accent"])], expand=[("selected", (0, 0, 0, 0))])
    s.configure("TSeparator", background=p["line"])
    s.configure("Vertical.TScrollbar", background=p["btn"], troughcolor=p["bg"], bordercolor=p["bg"],
                arrowcolor=p["mute"], lightcolor=p["btn"], darkcolor=p["btn"], gripcount=0)
    return s


def card(parent, padding=16):
    """Khung nền trắng (tối: xám đậm) có viền mảnh; nội dung đặt trong khung con trả về."""
    outer = ttk.Frame(parent, style="Card.TFrame", padding=1)
    inner = ttk.Frame(outer, style="Inner.TFrame", padding=padding)
    inner.pack(fill="both", expand=True)
    return outer, inner


def pill(parent, text, level):
    """Nhãn trạng thái bo màu: level ok / busy / off / err."""
    label = ttk.Label(parent, text=text, style="Pill.TLabel")
    set_pill(label, text, level)
    return label


def set_pill(label, text, level):
    color = LEVEL_COLOR.get(level, PALETTE["off"])
    label.configure(text=text, background=color, foreground=PALETTE["bg"] if is_dark() else PALETTE["card"])


def autowrap(label, margin=40, minimum=200):
    """Chữ dài tự xuống dòng theo bề rộng khung chứa (cửa sổ co giãn được)."""
    master = label.master

    def fit(event):
        try:
            offset = label.winfo_x()   # nhãn thụt vào (padx) thì trừ phần thụt
        except tk.TclError:
            return
        label.configure(wraplength=max(minimum, event.width - offset - margin))

    master.bind("<Configure>", fit, add="+")


def style_cards(root):
    """Sau khi dựng xong: mọi Frame/Label nằm trong thẻ lấy nền của thẻ; chữ dài tự xuống dòng; Listbox theo màu theme."""
    p = PALETTE

    def walk(widget, in_card):
        for child in widget.winfo_children():
            cls = child.winfo_class()
            inside = in_card
            if cls == "TFrame":
                style = str(child.cget("style"))
                if style in ("Card.TFrame", "Inner.TFrame"):
                    inside = True
                elif in_card and not style:
                    child.configure(style="Inner.TFrame")
            elif cls == "TLabel":
                style = str(child.cget("style"))
                if in_card and not style:
                    child.configure(style="Card.TLabel")
                try:
                    if int(str(child.cget("wraplength")) or 0) > 0:
                        autowrap(child)
                except (ValueError, tk.TclError):
                    pass
            elif cls == "Listbox":
                child.configure(bg=p["field"], fg=p["ink"], selectbackground=p["accent"], selectforeground=p["accent_ink"],
                                highlightthickness=1, highlightbackground=p["line"], highlightcolor=p["accent"],
                                relief="flat", borderwidth=0)
            walk(child, inside)

    walk(root, False)


class Segmented(tk.Canvas):
    """Bộ chuyển trang kiểu "segmented control" như đầu trang CAD Studio: các nút trong một khung bo tròn,
    nút đang chọn có nền nổi và chữ đậm, nút khác chữ mờ; hover nhẹ. Bàn phím: Tab để tới, mũi tên/Space/Enter để chuyển;
    khi có focus thì viền mảnh màu nhấn quanh nút đang chọn (không có viền chấm kiểu cũ)."""

    PAD, GAP, RADIUS = 4, 2, 9

    def __init__(self, parent, labels, command, bg_key="bg"):
        super().__init__(parent, highlightthickness=0, borderwidth=0, takefocus=1, cursor="hand2")
        self.labels, self.command, self.bg_key = list(labels), command, bg_key
        self.index, self.hover, self.focused = 0, None, False
        self.bind("<Button-1>", lambda e: self._click(e.x))
        self.bind("<Motion>", lambda e: self._set_hover(self._hit(e.x)))
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<FocusIn>", lambda e: self._focus(True))
        self.bind("<FocusOut>", lambda e: self._focus(False))
        for key in ("<Left>", "<Up>"):
            self.bind(key, lambda e: self.select((self.index - 1) % len(self.labels), notify=True))
        for key in ("<Right>", "<Down>", "<space>", "<Return>"):
            self.bind(key, lambda e: self.select((self.index + 1) % len(self.labels), notify=True))
        self.redraw()

    def _fonts(self):
        from tkinter import font as tkfont
        return tkfont.Font(family=FONT, size=10, weight="bold"), tkfont.Font(family=FONT, size=10)

    def _layout(self):
        bold, _ = self._fonts()
        widths = [bold.measure(t) + 32 for t in self.labels]
        h = bold.metrics("linespace") + 14
        xs, x = [], self.PAD
        for w in widths:
            xs.append((x, x + w)); x += w + self.GAP
        return xs, h, x - self.GAP + self.PAD

    def _hit(self, x):
        for i, (a, b) in enumerate(self._layout()[0]):
            if a <= x <= b:
                return i
        return None

    def _click(self, x):
        i = self._hit(x)
        self.focus_set()
        if i is not None:
            self.select(i, notify=True)

    def _set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self.redraw()

    def _focus(self, on):
        self.focused = on
        self.redraw()

    def select(self, i, notify=False):
        changed = i != self.index
        self.index = i
        self.redraw()
        if notify and changed:
            self.command(i)

    def _round(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pts, smooth=True, splinesteps=12, **kw)

    def redraw(self):
        p = PALETTE
        xs, h, total = self._layout()
        H = h + 2 * self.PAD
        self.configure(width=total, height=H, bg=p[self.bg_key])
        self.delete("all")
        track = p["btn_hover"] if is_dark() else "#e6ebf0"
        self._round(0, 0, total, H, self.RADIUS + 3, fill=track, outline=track)
        bold, normal = self._fonts()
        for i, (a, b) in enumerate(xs):
            on = i == self.index
            if on:
                self._round(a, self.PAD, b, self.PAD + h, self.RADIUS, fill=p["card"],
                            outline=p["accent"] if self.focused else p["line"], width=1)
            color = p["ink"] if on else (p["accent"] if i == self.hover else p["mute"])
            self.create_text((a + b) / 2, self.PAD + h / 2, text=self.labels[i], fill=color, font=bold if on else normal)


class Dropdown(ttk.Button):
    """Ô chọn tự vẽ thay ttk.Combobox: nút cao bằng nút bên cạnh, có mũi tên; bấm mở menu thả xuống theo theme
    (nền sáng/tối, có padding, hàng ~32px, hover nhạt, mục đang chọn có dấu ✓, cột trạng thái mờ bên phải).
    Đóng khi bấm ra ngoài hoặc Esc; bàn phím: Space/Enter/↓ mở, ↑↓ chọn, Enter xác nhận.

    ``status(value)`` (tùy chọn) trả chữ trạng thái của từng mục; gọi ở luồng nền nên được phép chậm."""

    ROW = 32

    def __init__(self, parent, variable, values, command=None, status=None, icons=None, width=22):
        super().__init__(parent, style="Select.TButton", width=width, command=self.open)
        self.var, self.values, self.on_change = variable, list(values), command
        self.status_fn, self.icons, self.statuses = status, icons or {}, {}
        self.menu = None
        self.var.trace_add("write", lambda *_: self._sync())
        self.bind("<Down>", lambda e: self.open())
        self._sync()

    def _sync(self):
        value = self.var.get()
        icon = self.icons.get(value, "")
        label = f"{icon + '  ' if icon else ''}{value}"
        self.configure(text=label.ljust(int(str(self.cget("width")) or 20) + 2) + "▾")

    def open(self):
        import time
        if self.menu:
            self.close()
            return
        if time.monotonic() - getattr(self, "_closed_at", 0) < 0.3:
            return   # cú bấm vào chính nút vừa đóng menu: không mở lại
        p = PALETTE
        top = tk.Toplevel(self)
        top.overrideredirect(True)
        top.attributes("-topmost", True)   # menu thả xuống luôn nằm trên cửa sổ app
        top.configure(bg=p["line"])
        frame = tk.Frame(top, bg=p["card"], padx=6, pady=6)
        frame.pack(fill="both", expand=True, padx=1, pady=1)   # viền 1px màu line
        self.menu, self.rows, self.active = top, [], max(0, self.values.index(self.var.get()) if self.var.get() in self.values else 0)
        for i, value in enumerate(self.values):
            row = tk.Frame(frame, bg=p["card"], height=self.ROW, cursor="hand2")
            row.pack(fill="x")
            row.pack_propagate(False)
            check = tk.Label(row, text="✓" if value == self.var.get() else "", width=2, bg=p["card"], fg=p["accent"],
                             font=(FONT, 10, "bold"))
            check.pack(side="left", padx=(6, 2))
            icon = self.icons.get(value, "")
            name = tk.Label(row, text=(icon + "  " if icon else "") + value, bg=p["card"], fg=p["ink"], font=(FONT, 10), anchor="w")
            name.pack(side="left", fill="x", expand=True)
            state = tk.Label(row, text=self.statuses.get(value, "…" if self.status_fn else ""), bg=p["card"],
                             fg=p["mute"], font=(FONT, 9))
            state.pack(side="right", padx=(12, 10))
            self.rows.append((row, check, name, state))
            for w in (row, check, name, state):
                w.bind("<Enter>", lambda e, k=i: self._hover(k))
                w.bind("<Button-1>", lambda e, k=i: self.choose(k))
        top.update_idletasks()
        width = max(self.winfo_width(), frame.winfo_reqwidth() + 2, 300)
        height = frame.winfo_reqheight() + 2
        x, y = self.winfo_rootx(), self.winfo_rooty() + self.winfo_height() + 4
        if y + height > self.winfo_screenheight() - 8:   # sát đáy màn hình: mở lên trên
            y = self.winfo_rooty() - height - 4
        top.geometry(f"{width}x{height}+{x}+{y}")
        self._hover(self.active)
        top.bind("<Escape>", lambda e: self.close())
        top.bind("<Up>", lambda e: self._hover((self.active - 1) % len(self.values)))
        top.bind("<Down>", lambda e: self._hover((self.active + 1) % len(self.values)))
        top.bind("<Return>", lambda e: self.choose(self.active))
        top.bind("<space>", lambda e: self.choose(self.active))
        top.bind("<FocusOut>", lambda e: self.after(80, self._maybe_close))
        top.focus_force()
        # Bấm ra ngoài menu (trong cửa sổ app) thì đóng
        self._outside = self.winfo_toplevel().bind("<Button-1>", lambda e: self.close(), add="+")
        if self.status_fn:
            import threading
            def work():
                for value in self.values:
                    try:
                        text = self.status_fn(value)
                    except Exception:
                        text = ""
                    self.statuses[value] = text
                    self.after(0, lambda v=value, t=text: self._set_status(v, t))
            threading.Thread(target=work, daemon=True).start()

    def _set_status(self, value, text):
        if self.menu and value in self.values:
            try:
                self.rows[self.values.index(value)][3].configure(text=text)
            except tk.TclError:
                pass

    def _hover(self, k):
        p = PALETTE
        self.active = k
        hover = p["btn_hover"]
        for i, widgets in enumerate(self.rows):
            for w in widgets:
                w.configure(bg=hover if i == k else p["card"])

    def _maybe_close(self):
        try:
            if self.menu and self.menu.focus_get() is None:
                self.close()
        except (tk.TclError, KeyError):
            self.close()

    def choose(self, k):
        value = self.values[k]
        self.close()
        if value != self.var.get():
            self.var.set(value)
            if self.on_change:
                self.on_change(value)

    def close(self):
        if self.menu:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._outside)
            except tk.TclError:
                pass
            self.menu.destroy()
            self.menu = None
            import time
            self._closed_at = time.monotonic()
            self.focus_set()


def fold(text):
    """Bỏ dấu tiếng Việt + chữ thường, để tìm 'khoi dong' khớp 'Khởi động'."""
    import unicodedata
    t = unicodedata.normalize("NFD", str(text)).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


class NavList(tk.Frame):
    """Menu nhóm dọc (cột trái tab Cài đặt): mục đang chọn có nền nổi + vạch nhấn teal bên trái, hover nhạt.
    Bàn phím: ↑↓ Home End chuyển nhóm. ``set_counts`` hiện số kết quả tìm kiếm cạnh mỗi nhóm (0 thì làm mờ)."""

    def __init__(self, parent, items, command):
        super().__init__(parent, takefocus=1, highlightthickness=0, bd=0)
        self.items, self.command = list(items), command   # [(key, label)]
        self.current, self.counts, self.compact = self.items[0][0], None, False
        self.rows = {}
        for key, label in self.items:
            row = tk.Frame(self, cursor="hand2", height=36)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            bar = tk.Frame(row, width=3)
            bar.pack(side="left", fill="y", pady=7)
            text = tk.Label(row, text=label, anchor="w", padx=12)
            text.pack(side="left", fill="both", expand=True)
            badge = tk.Label(row, text="", padx=8)
            badge.pack(side="right")
            for w in (row, bar, text, badge):
                w.bind("<Button-1>", lambda e, k=key: (self.focus_set(), self.select(k, notify=True)))
                w.bind("<Enter>", lambda e, k=key: self._hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self._hover(k, False))
            self.rows[key] = {"row": row, "bar": bar, "text": text, "badge": badge, "label": label, "hover": False}
        keys = [k for k, _ in self.items]
        step = lambda d: self.select(keys[(keys.index(self.current) + d) % len(keys)], notify=True)
        self.bind("<Up>", lambda e: step(-1))
        self.bind("<Down>", lambda e: step(1))
        self.bind("<Home>", lambda e: self.select(keys[0], notify=True))
        self.bind("<End>", lambda e: self.select(keys[-1], notify=True))
        self.bind("<FocusIn>", lambda e: self.redraw())
        self.bind("<FocusOut>", lambda e: self.redraw())
        self.redraw()

    def _hover(self, key, on):
        self.rows[key]["hover"] = on
        self.redraw()

    def select(self, key, notify=False):
        changed = key != self.current
        self.current = key
        self.redraw()
        if notify and changed:
            self.command(key)

    def set_counts(self, counts):
        """{key: số kết quả} khi đang tìm; None khi ô tìm trống."""
        self.counts = counts
        self.redraw()

    def set_compact(self, compact):
        if compact != self.compact:
            self.compact = compact
            self.redraw()

    def redraw(self):
        p = PALETTE
        self.configure(bg=p["bg"])
        focused = self.focus_get() is self
        for key, r in self.rows.items():
            on = key == self.current
            bg = p["card"] if on else (p["btn_hover"] if r["hover"] else p["bg"])
            n = None if self.counts is None else self.counts.get(key, 0)
            fg = p["ink"] if on else (p["off"] if n == 0 else p["mute"])
            label = r["label"].split(" ")[0] if self.compact else r["label"]
            r["row"].configure(bg=bg, highlightthickness=1 if on else 0,
                               highlightbackground=p["accent"] if (on and focused) else p["line"])
            r["bar"].configure(bg=p["accent"] if on else bg)
            r["text"].configure(bg=bg, fg=fg, text=label, font=(FONT, 10, "bold" if on else "normal"))
            r["badge"].configure(bg=bg, fg=p["accent"], font=(FONT, 9, "bold"), text="" if not n else str(n))


def text_widget(parent, height=6):
    """Ô chữ đơn cách (cấu hình thủ công) theo màu theme."""
    p = PALETTE
    return tk.Text(parent, height=height, wrap="none", font=(MONO, 10), bg=p["code"], fg=p["ink"],
                   insertbackground=p["ink"], relief="flat", padx=12, pady=10, highlightthickness=1,
                   highlightbackground=p["line"], highlightcolor=p["accent"])
