"""Windows desktop controller for the exclusive AutoCAD MCP gateway."""
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
import winreg
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import agentconfig
import agentnote
import cadweb_local
import dutoan_data
import install_ui
import ui_theme
import dialogs
import remote_agent
import knowledge
import litebim_bridge
import knowledge_propose
from logfile import RotatingLog, start_logged
from skillzip import build_skill_zips
from tray import TrayIcon

ROOT = Path(__file__).resolve().parent.parent
SKILLS_SOURCE = ROOT / ".codex" / "skills"
CLAUDE_DESKTOP = "Claude Desktop (tải zip lên)"
LOG_DIR = ROOT / "launcher" / "logs"
SETTINGS_FILE = ROOT / "launcher" / "state" / "settings.json"
REPOS = {
    "puran": ROOT / "puran-water-autocad-mcp",
    "beiming": ROOT / "autocad-beiming-mcp",
}
NAMES = {"puran": "autocad_puran", "beiming": "autocad_beiming"}
UPDATE_REPO = "KenjiIT/autocad-mcp-launcher"
DUTOAN_DIR = ROOT / "du-toan-mcp"
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE = "AutoCADMcpLauncher"


def startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY) as key:
            winreg.QueryValueEx(key, STARTUP_VALUE)
        return True
    except FileNotFoundError:
        return False


def set_startup_enabled(enabled):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0,
                        winreg.KEY_SET_VALUE) as key:
        if enabled:
            wscript = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "wscript.exe"
            launcher = ROOT / "Start AutoCAD MCP.vbs"
            command = f'"{wscript}" "{launcher}"'
            winreg.SetValueEx(key, STARTUP_VALUE, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, STARTUP_VALUE)
            except FileNotFoundError:
                pass


def load_settings():
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_setting(name, value):
    settings = load_settings()
    settings[name] = value
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(SETTINGS_FILE)
    if settings.get("remote_machine_token"):
        # Tệp có token của chế độ agent: chỉ chủ tài khoản đọc được (cố gắng, không bắt buộc).
        remote_agent.restrict_to_owner(SETTINGS_FILE)


def app_version():
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def python_in(repo):
    return repo / ".venv" / "Scripts" / "python.exe"


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def block_library_dir():
    """Folder block.insert reads library files from; keep in step with lt_file_ipc."""
    configured = os.environ.get("AUTOCAD_MCP_BLOCK_LIBRARY", "").strip()
    return Path(configured) if configured else ROOT / "blocks"


def listener_pid(port):
    """PID that listens on the loopback ``port``, or None."""
    try:
        output = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                                timeout=10, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[3] == "LISTENING" and fields[1] == f"127.0.0.1:{port}":
            try:
                return int(fields[4])
            except ValueError:
                return None
    return None


def is_launcher_gateway(port=8764):
    """True when the listener on ``port`` answers /status like this launcher's gateway."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/status", timeout=2) as response:
            state = json.load(response)
    except (OSError, ValueError):
        return False
    return isinstance(state, dict) and {"mode", "queued_requests"} <= state.keys()


class AdoptedGateway:
    """A gateway left running by an earlier launcher; the app reuses and later stops it."""

    def __init__(self, pid, port=8764):
        self.pid = pid
        self.port = port

    def poll(self):
        return None if listening(self.port) else 0

    def wait(self, timeout=None):
        deadline = time.time() + (timeout if timeout is not None else 5)
        while listening(self.port) and time.time() < deadline:
            time.sleep(0.1)


def kill_tree(process):
    if process and process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def agent_context():
    """Đường dẫn và lựa chọn của máy này, dùng cho cấu hình agent (xem agentconfig.py)."""
    return agentconfig.Context(
        backup_dir=ROOT / "launcher" / "state" / "config-backups",
        bridge_python=str(python_in(REPOS["puran"])),
        bridge_script=str(ROOT / "launcher" / "stdio_bridge.py"),
        # dutoan cũng qua gateway (HTTP) nhưng không dùng AutoCAD.
        dutoan=(DUTOAN_DIR / "src" / "dutoan_mcp" / "server.py").is_file(),
        litebim=litebim_bridge.installed("litebim"),
        litecad=litebim_bridge.installed("litecad"))


def agent_mcp_status(agent):
    """Trạng thái ngắn của một agent cho menu chọn agent: đã thêm MCP / thêm x/y / chưa thêm / chưa cài."""
    try:
        ctx = agent_context()
        state = agentconfig.status(agent, ctx)
    except Exception:
        return ""
    if state.get("problem"):
        return "chưa cài" if "Không tìm thấy" in state["problem"] or "chưa cài" in state["problem"].lower() else "không đọc được"
    if agent == "Claude Code" and ctx.claude() is None:
        return "chưa cài"
    if not state.get("exists") and not Path(state["path"]).parent.exists():
        return "chưa cài"   # chưa có cả thư mục cấu hình: agent chưa cài trên máy này
    wanted = agentconfig.names(ctx)
    ok = sum(1 for n in wanted if state["servers"].get(n) == "ok")
    if ok == len(wanted):
        return "đã thêm MCP"
    return "chưa thêm" if ok == 0 else f"đã thêm {ok}/{len(wanted)}"


def config_for(agent):
    return agentconfig.snippet(agent, agent_context())

SERVICE_TITLES = {"puran": "AutoCAD – Puran", "beiming": "AutoCAD – Beiming", "dutoan": "Dự toán",
                  "litebim": "LiteBIM", "litecad": "LiteCAD"}


class ServiceRow:
    """Một dòng ở khối Dịch vụ: chấm màu theo mức, tên dễ hiểu, trạng thái ngắn, nút hành động (nếu có)."""

    def __init__(self, grid, row, title, action=None, hide_when_ok=False):
        self.hide_when_ok = hide_when_ok
        self.dot = ttk.Label(grid, text="●", style="Dot.TLabel")
        self.dot.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Label(grid, text=title, style="Card.H3.TLabel", width=18).grid(row=row, column=1, sticky="w", pady=4)
        self.text = ttk.Label(grid, text="", style="Card.Muted.TLabel")
        self.text.grid(row=row, column=2, sticky="w", padx=(8, 0), pady=4)
        self.button = None
        if action:
            self.button = ttk.Button(grid, text=action[0], style="Link.TButton", command=action[1])
            self.button.grid(row=row, column=3, sticky="e", padx=(8, 0))
        self.level = "off"

    def set(self, level, text):
        self.level = level
        self.dot.configure(foreground=ui_theme.LEVEL_COLOR.get(level, ui_theme.LEVEL_COLOR["off"]))
        self.text.configure(text=text)
        if self.button is not None and self.hide_when_ok:   # vd. LiteBIM đã nối: không cần "Hướng dẫn bật MCP"
            if level == "ok":
                self.button.grid_remove()
            else:
                self.button.grid()


class App(tk.Tk):
    def __init__(self):
        ui_theme.enable_dpi_awareness()
        ui_theme.PREF = str(load_settings().get("theme") or "system")   # giao diện đã chọn trong Cài đặt
        ui_theme.set_mode(ui_theme.windows_dark())
        super().__init__()
        self.title("AutoCAD MCP Launcher")
        self.iconbitmap(default=str(Path(__file__).with_name("launcher-plan-flat-v3.ico")))
        self.canvases = []
        self.dropdowns = []
        self.gateway = None
        self.log = None
        self.events = queue.Queue()
        self.busy = False
        self.closing = False
        self.updating = False
        self.update_archive = None
        self.update_wait_started = None
        self.update_busy_notice_shown = False
        self.agent = tk.StringVar(value="OpenAI Codex")
        self.startup_var = tk.BooleanVar(value=startup_enabled())
        self.autostart_mcp_var = tk.BooleanVar(value=bool(load_settings().get("autostart_mcp")))
        self.skill_gate_var = tk.BooleanVar(value=load_settings().get("skill_gate", True) is not False)
        saved = load_settings()
        self.remote_enabled_var = tk.BooleanVar(value=saved.get("remote_agent_enabled") is True)
        self.remote_url_var = tk.StringVar(value=str(saved.get("remote_server_url") or ""))
        self.remote_id_var = tk.StringVar(value=str(saved.get("remote_machine_id") or ""))
        self.remote_token_var = tk.StringVar(value="")  # không bao giờ điền lại token đã lưu
        self.status = tk.StringVar(value="Sẵn sàng")
        self.knowledge_checking = False
        self.knowledge_auto_var = tk.BooleanVar(value=load_settings().get("knowledge_auto_update", True) is not False)
        self.dutoan_auto_var = tk.BooleanVar(value=load_settings().get("dutoan_auto_update", True) is not False)
        self.dutoan_busy = False
        self.cadweb = cadweb_local.CadWebLocal(ROOT, LOG_DIR)
        self.cadweb_auto_var = tk.BooleanVar(value=load_settings().get("cadweb_local_auto", True) is not False)
        self.cadweb_busy = False
        self.build()
        ui_theme.style_cards(self)
        self.fit_to_content()
        self.after(50, lambda: ui_theme.title_bar(self))
        self.theme_dark = ui_theme.is_dark()
        self.refresh_knowledge_status()
        self.refresh_config()
        self.tray_menu = tk.Menu(self, tearoff=False)
        self.tray_menu.add_command(label="Mở ứng dụng", command=self.restore)
        self.tray_menu.add_separator()
        self.tray_menu.add_command(label="Thoát hẳn", command=self.close)
        try:
            self.tray = TrayIcon(self, self.restore, self.show_tray_menu)
        except OSError:
            self.tray = None
        self.bind("<Unmap>", self.on_unmap)
        self.after(500, self.tick)
        self.after(1600, self.check_for_updates)
        self.after(4000, self.knowledge_tick)
        self.after(9000, self.dutoan_tick)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        if "--start" in sys.argv[1:] or self.autostart_mcp_var.get():
            self.after(300, self.start)

    def build(self):
        ui_theme.apply(self)
        # Bộ chuyển trang kiểu segmented (như đầu trang CAD Studio) thay cho ttk.Notebook
        top = ttk.Frame(self)
        top.pack(fill="x", padx=18, pady=(12, 2))
        self.switcher = ui_theme.Segmented(top, ["Điều khiển", "Cài đặt"], self.select_page)
        self.switcher.pack(side="left")
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=14, pady=(4, 14))
        main_page = ttk.Frame(body)
        settings_page = ttk.Frame(body)
        self.page_list = [main_page, settings_page]
        main_page.pack(fill="both", expand=True)
        self.bind("<Control-Tab>", lambda _: self.select_page((self.current_page + 1) % 2, sync=True))
        self.bind("<Control-Shift-Tab>", lambda _: self.select_page((self.current_page - 1) % 2, sync=True))
        self.current_page = 0
        self.scale = max(1.0, self.winfo_fpixels("1i") / 96)   # màn hình DPI cao
        main = self.scrollable(main_page)
        self.main_inner, self.main_page = main, main_page
        settings = self.build_settings_shell(settings_page)
        self.settings_page = settings_page
        self.build_settings(settings)
        self.finish_settings()

        # (1) Đầu trang: tên + phiên bản, nhãn trạng thái tổng, một nút bật/tắt duy nhất ở bên phải
        head = ttk.Frame(main)
        head.pack(fill="x")
        head.columnconfigure(1, weight=1)
        ttk.Label(head, text="AutoCAD MCP Launcher", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(head, text=f"v{app_version()}", style="Small.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        self.state_pill = ui_theme.pill(head, "Đã dừng", "off")
        self.state_pill.grid(row=0, column=2, sticky="e", padx=(0, 10))
        self.power_btn = ttk.Button(head, text="▶  Bật kết nối", style="Accent.TButton", command=self.toggle_power, width=16)
        self.power_btn.grid(row=0, column=3, sticky="e")
        self.start_btn = self.stop_btn = self.power_btn   # mã cũ bật/tắt trạng thái hai nút: nay là một nút
        sub = ttk.Label(main, text="Agent ưu tiên AutoCAD; nếu AutoCAD không chạy, agent sẽ hỏi trước khi dùng DXF.",
                        style="Muted.TLabel")
        sub.pack(anchor="w", fill="x", pady=(2, 14))
        ui_theme.autowrap(sub)
        # Thẻ "Có bản mới" (ẩn tới khi kiểm tra thấy bản mới; không bật hộp chặn lúc mở app)
        slot = ttk.Frame(main)
        slot.pack(fill="x")
        self.update_banner = dialogs.Banner(slot, self.open_update_dialog, self.dismiss_update_banner)
        self.banner_anchor = None
        self.last_error = None

        # (2) Thẻ CAD Studio: trạng thái + nút chính lớn
        self.cadweb_row = None
        self.cadweb_level = "off"
        if cadweb_local.project_dir(ROOT):   # chỉ hiện nếu máy này có clone cad-web-local cạnh mcp/
            outer, box = ui_theme.card(main, padding=(18, 14))
            outer.pack(fill="x", pady=(0, 12))
            box.columnconfigure(1, weight=1)
            self.cadweb_row = box
            self.cadweb_dot = ttk.Label(box, text="●", style="Dot.TLabel", foreground=ui_theme.LEVEL_COLOR["off"])
            self.cadweb_dot.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 10), pady=(2, 0))
            ttk.Label(box, text="CAD Studio", style="Card.H2.TLabel").grid(row=0, column=1, sticky="w")
            self.cadweb_label = ttk.Label(box, text="Chưa mở. Web chat dùng các MCP ngay trên máy này.", style="Card.Muted.TLabel")
            self.cadweb_label.grid(row=1, column=1, sticky="ew")
            ui_theme.autowrap(self.cadweb_label, margin=260)
            self.cadweb_open_btn = ttk.Button(box, text="Mở CAD Studio", style="Big.Accent.TButton", command=self.open_cadweb_local)
            self.cadweb_open_btn.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))

        # (3) Dịch vụ: mỗi dòng chấm màu + tên dễ hiểu + trạng thái ngắn + nút hành động khi cần
        outer, box = ui_theme.card(main, padding=(18, 12))
        outer.pack(fill="x", pady=(0, 12))
        ttk.Label(box, text="Dịch vụ", style="Card.H2.TLabel").pack(anchor="w", pady=(0, 6))
        grid = ttk.Frame(box, style="Inner.TFrame")
        grid.pack(fill="x")
        grid.columnconfigure(2, weight=1)
        self.services = {}
        for key in REPOS:
            self.services[key] = ServiceRow(grid, len(self.services), SERVICE_TITLES[key])
            self.services[key].set("off", "Chưa khởi chạy")
        self.labels = self.services   # tên cũ
        dutoan_ok = dutoan_data.describe()["present"]
        self.services["dutoan"] = ServiceRow(grid, len(self.services), SERVICE_TITLES["dutoan"],
                                             None if dutoan_ok else ("Thêm dữ liệu", self.show_settings))
        self.services["dutoan"].set("ok" if dutoan_ok else "off",
                                    "Sẵn sàng (qua gateway)" if dutoan_ok else "Chưa có dữ liệu (xem Cài đặt › Dữ liệu dự toán)")
        self.dutoan_label = self.services["dutoan"]
        self.pipe_labels = {}
        for key in ("litebim", "litecad"):
            if litebim_bridge.installed(key):  # chỉ hiện sản phẩm có cài trên máy này
                row = ServiceRow(grid, len(self.services), SERVICE_TITLES[key],
                                 ("Hướng dẫn bật MCP", lambda k=key: self.show_pipe_help(k)), hide_when_ok=True)
                row.set("off", "Chưa kiểm tra")
                self.services[key] = row
                self.pipe_labels[key] = row
        status = ttk.Label(box, textvariable=self.status, style="Card.Muted.TLabel")
        status.pack(anchor="w", fill="x", pady=(10, 0))
        ui_theme.autowrap(status)

        # (4) Kết nối với agent: chọn agent + Thêm (chính) / Gỡ (phụ) một hàng; cấu hình thủ công gập lại
        outer, box = ui_theme.card(main, padding=(18, 14))
        outer.pack(fill="x", pady=(0, 6))
        ttk.Label(box, text="Kết nối với agent", style="Card.H2.TLabel").pack(anchor="w")
        note = ttk.Label(box, text="Thêm các MCP của launcher vào Codex, Claude Code, Claude Desktop hoặc Cursor. "
                                   "Launcher hỏi trước khi ghi và sao lưu cấu hình cũ.", style="Card.Muted.TLabel")
        note.pack(anchor="w", fill="x", pady=(2, 10))
        ui_theme.autowrap(note)
        row = ttk.Frame(box, style="Inner.TFrame")
        row.pack(fill="x")
        self.agent_select = ui_theme.Dropdown(row, self.agent, agentconfig.AGENTS, command=lambda _: self.refresh_config(),
                                              status=agent_mcp_status, width=20)
        self.agent_select.pack(side="left")
        self.dropdowns.append(self.agent_select)
        self.auto_btn = ttk.Button(row, text="Thêm vào agent", style="Accent.TButton", command=self.auto_configure)
        self.auto_btn.pack(side="left", padx=(10, 0))
        self.unauto_btn = ttk.Button(row, text="Gỡ", command=lambda: self.auto_configure(remove=True))
        self.unauto_btn.pack(side="left", padx=(8, 0))
        self.agentcfg_status = ttk.Label(box, text="", style="Card.Ok.TLabel", justify="left")
        self.agentcfg_status.pack(anchor="w", fill="x", pady=(8, 0))
        ui_theme.autowrap(self.agentcfg_status)
        self.manual_open = tk.BooleanVar(value=False)
        self.manual_btn = ttk.Button(box, text="▸  Cấu hình thủ công", style="Link.TButton", command=self.toggle_manual)
        self.manual_btn.pack(anchor="w", pady=(8, 0))
        self.manual = ttk.Frame(box, style="Inner.TFrame")
        manual_head = ttk.Frame(self.manual, style="Inner.TFrame")
        manual_head.pack(fill="x", pady=(4, 6))
        self.hint = ttk.Label(manual_head, style="Card.Muted.TLabel", justify="left")
        self.hint.pack(side="left", fill="x", expand=True)
        ui_theme.autowrap(self.hint, margin=150)
        ttk.Button(manual_head, text="Sao chép", command=self.copy).pack(side="right")
        self.config_box = ui_theme.text_widget(self.manual, height=8)
        self.config_box.pack(fill="both", expand=True)

    def fit_to_content(self, tries=0):
        """Cửa sổ mặc định và tối thiểu vừa đủ toàn bộ tab Điều khiển (đo nội dung thật sau khi vẽ, đã theo DPI):
        không có thanh cuộn ở kích thước mặc định; người dùng thu nhỏ hơn nội dung thì thanh cuộn mới hiện."""
        self.update_idletasks()
        canvas = self.canvases[0]
        need_h = self.main_inner.winfo_reqheight() - canvas.winfo_height()
        width = int(820 * self.scale)   # bề rộng cố định theo DPI; chữ dài tự xuống dòng nên không đo theo nội dung
        height = min(self.winfo_height() + need_h, int(self.winfo_screenheight() * 0.9))
        if tries == 0 or need_h != 0:
            self.geometry(f"{width}x{height}")
            self.minsize(int(620 * self.scale), height)
        if tries < 3 and (tries == 0 or need_h != 0):
            self.after(30, lambda: self.fit_to_content(tries + 1))   # lặp vài lần: đổi bề rộng làm chữ xuống dòng khác đi

    def retheme(self):
        """Windows vừa đổi sáng/tối: tô lại toàn bộ theo bảng màu mới."""
        ui_theme.apply(self)
        ui_theme.style_cards(self)
        p = ui_theme.PALETTE
        for canvas in self.canvases:
            canvas.configure(bg=p["bg"])
        self.config_box.configure(bg=p["code"], fg=p["ink"], insertbackground=p["ink"], highlightbackground=p["line"],
                                  highlightcolor=p["accent"])
        for row in self.services.values():
            row.set(row.level, row.text.cget("text"))
        if self.cadweb_row:
            self.set_cadweb(self.cadweb_level, self.cadweb_label.cget("text"))
        self.refresh_power()
        self.switcher.redraw()
        if getattr(self, "theme_switch", None):
            self.theme_switch.redraw()
        ui_theme.title_bar(self)

    def choose_theme(self, index):
        """Cài đặt > Giao diện: Theo hệ thống / Sáng / Tối; đổi ngay, lưu lại cho lần mở sau."""
        ui_theme.PREF = ui_theme.PREFS[index][0]
        try:
            save_setting("theme", ui_theme.PREF)
        except OSError as exc:
            dialogs.error(self, "Không lưu được cài đặt", str(exc))
        self.check_theme()

    def check_theme(self):
        dark = ui_theme.windows_dark()
        if dark != self.theme_dark:
            self.theme_dark = dark
            ui_theme.set_mode(dark)
            self.retheme()

    def toggle_manual(self):
        """Mở/gập mục Cấu hình thủ công."""
        opened = not self.manual_open.get()
        self.manual_open.set(opened)
        self.manual_btn.configure(text=("▾" if opened else "▸") + "  Cấu hình thủ công")
        if opened:
            self.manual.pack(fill="both", expand=True)
        else:
            self.manual.pack_forget()

    def show_settings(self):
        self.select_page(1, sync=True)

    def select_page(self, index, sync=False):
        """Hiện trang thứ ``index`` (0: Điều khiển, 1: Cài đặt)."""
        if index == self.current_page:
            return
        for dropdown in self.dropdowns:
            dropdown.close()   # menu thả xuống của trang cũ không được treo lại
        self.page_list[self.current_page].pack_forget()
        self.page_list[index].pack(fill="both", expand=True)
        self.current_page = index
        if sync:
            self.switcher.select(index)

    def show_pipe_help(self, key):
        title = litebim_bridge.PRODUCTS[key][0]
        dialogs.info(
            self, f"Bật MCP trong {title}",
            f"1. Mở {title}.\n2. Vào Tùy chọn > AI (hoặc gõ lệnh MCP) và chọn MCP: On.\n"
            f"3. Bật kết nối cho agent ở launcher (nút trên cùng).\n\n"
            f"Launcher tự nối tới {title} khi agent gọi tool; không cần mở lại launcher.")

    def running(self):
        return bool(self.gateway and self.gateway.poll() is None)

    def toggle_power(self):
        if self.running():
            self.stop()
        else:
            self.start()
        self.refresh_power()

    def refresh_power(self):
        """Nút bật/tắt và nhãn trạng thái tổng theo tình trạng gateway."""
        if self.busy:
            text, level, button = "Đang khởi động…", "busy", "Đang mở…"
        elif self.updating:
            text, level, button = "Đang cập nhật…", "busy", "Đang cập nhật…"
        elif self.running():
            text, level, button = "Đang chạy", "ok", "■  Dừng"
        elif self.last_error:
            text, level, button = "Lỗi", "err", "▶  Bật kết nối"
        else:
            text, level, button = "Đã dừng", "off", "▶  Bật kết nối"
        ui_theme.set_pill(self.state_pill, text, level)
        self.power_btn.configure(text=button, style="TButton" if self.running() and not self.busy else "Accent.TButton")

    def section(self, root, title, desc=None):
        """Một thẻ trong nhóm Cài đặt: tiêu đề + (tuỳ chọn) một dòng giải thích ngắn; trả khung để đặt nội dung."""
        outer, box = ui_theme.card(root, padding=(18, 14))
        outer.pack(fill="x", pady=(0, 12))
        ttk.Label(box, text=title, style="Card.H2.TLabel").pack(anchor="w", pady=(0, 2 if desc else 4))
        if desc:
            ttk.Label(box, text=desc, style="Card.Muted.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=(0, 8))
        return box

    SETTINGS_GROUPS = (
        ("chung", "Chung", "Giao diện và cách launcher khởi động."),
        ("ketnoi", "Kết nối & dịch vụ", "Gateway MCP, các dịch vụ CAD/BIM, CAD Studio và kết nối ra server."),
        ("agent", "Agent & Skill", "Đưa MCP vào agent, cài skill và cổng bắt đọc skill."),
        ("dulieu", "Dữ liệu", "Dữ liệu dự toán, tri thức, tài liệu LiteBIM và thư viện block."),
        ("capnhat", "Cập nhật", "Phiên bản launcher và kiểm tra bản mới."),
        ("nangcao", "Nâng cao", "Nhật ký, thư mục cấu hình và đặt lại cài đặt."),
    )

    def build_settings_shell(self, page):
        """Tab Cài đặt 2 cột: trái là ô tìm nhanh + menu nhóm, phải là nội dung MỘT nhóm (không cuộn cả trang dài)."""
        left = ttk.Frame(page, padding=(16, 14, 6, 14))
        left.pack(side="left", fill="y")
        self.settings_left = left
        self.settings_search_var = tk.StringVar()
        self.settings_search = ttk.Entry(left, textvariable=self.settings_search_var, width=24)
        self.settings_search.pack(fill="x", pady=(0, 4))
        self.settings_search_hint = ttk.Label(left, text="Tìm tuỳ chọn…  (Enter: kết quả kế)", style="Small.TLabel")
        self.settings_search_hint.pack(anchor="w", pady=(0, 10))
        self.settings_search_var.trace_add("write", lambda *_: self.search_settings())
        self.settings_search.bind("<Return>", lambda e: self.search_settings(step=1))
        self.settings_search.bind("<Escape>", lambda e: self.settings_search_var.set(""))
        self.settings_nav = ui_theme.NavList(left, [(k, label) for k, label, _ in self.SETTINGS_GROUPS], self.show_group)
        self.settings_nav.pack(fill="x")
        right = ttk.Frame(page)
        right.pack(side="left", fill="both", expand=True)
        inner = self.scrollable(right)
        self.settings_canvas, self.settings_inner = self.canvases[-1], inner
        self.groups = {}
        for key, label, desc in self.SETTINGS_GROUPS:
            g = ttk.Frame(inner)
            ttk.Label(g, text=label, style="Title.TLabel").pack(anchor="w")
            ttk.Label(g, text=desc, style="Muted.TLabel").pack(anchor="w", pady=(2, 14))
            self.groups[key] = g
        self.current_group = None
        page.bind("<Configure>", lambda e: self.settings_nav.set_compact(e.width < int(700 * self.scale)), add="+")
        return inner

    def show_group(self, key, remember=True):
        """Hiện nhóm ``key`` ở cột phải, cuộn lên đầu; nhớ nhóm mở lần cuối."""
        if key not in self.groups:
            key = self.SETTINGS_GROUPS[0][0]
        if self.current_group == key:
            return
        if self.current_group:
            self.groups[self.current_group].pack_forget()
        self.groups[key].pack(fill="both", expand=True)
        self.current_group = key
        self.settings_nav.select(key)
        self.settings_canvas.yview_moveto(0)
        if remember:
            try:
                save_setting("settings_group", key)
            except OSError:
                pass

    def finish_settings(self):
        """Lập chỉ mục cho ô tìm nhanh (chữ của mọi nhãn/ô tick/nút trong từng nhóm) và mở nhóm lần trước."""
        self.settings_index = []
        def walk(w, key):
            for c in w.winfo_children():
                try:
                    text = c.cget("text") if c.winfo_class() in ("TLabel", "TCheckbutton", "TButton", "TRadiobutton") else ""
                except tk.TclError:
                    text = ""
                if text and len(str(text)) < 400:
                    self.settings_index.append((key, c, ui_theme.fold(text)))
                walk(c, key)
        for key, g in self.groups.items():
            walk(g, key)
        self.search_hits, self.search_pos = [], 0
        self.show_group(str(load_settings().get("settings_group") or "chung"), remember=False)

    def search_settings(self, step=0):
        """Gõ để lọc: đếm kết quả mỗi nhóm trên menu, nhảy tới tuỳ chọn khớp đầu tiên và tô sáng thẻ chứa nó."""
        q = ui_theme.fold(self.settings_search_var.get().strip())
        if not q:
            self.settings_nav.set_counts(None)
            self.search_hits = []
            return
        words = q.split()
        hits = [(k, w) for k, w, t in self.settings_index if all(x in t for x in words)]
        counts = {}
        for k, _ in hits:
            counts[k] = counts.get(k, 0) + 1
        self.settings_nav.set_counts(counts)
        if not hits:
            self.search_hits = []
            return
        self.search_pos = (self.search_pos + step) % len(hits) if step and hits == self.search_hits else 0
        self.search_hits = hits
        key, widget = hits[self.search_pos]
        self.show_group(key, remember=False)
        self.reveal(widget)

    def reveal(self, widget):
        """Cuộn cột phải tới ``widget`` và tô viền teal thẻ chứa nó trong 1,6 giây."""
        self.update_idletasks()
        inner, canvas = self.settings_inner, self.settings_canvas
        y = widget.winfo_rooty() - inner.winfo_rooty()
        total = max(1, inner.winfo_height())
        canvas.yview_moveto(max(0.0, (y - 40) / total))
        card = widget
        while card is not None and str(card.cget("style") if card.winfo_class() == "TFrame" else "") != "Card.TFrame":
            card = card.master if card.master is not self else None
        if card is not None:
            card.configure(style="Hl.Card.TFrame")
            self.after(1600, lambda: card.winfo_exists() and card.configure(style="Card.TFrame"))

    def scrollable(self, page):
        """Return a padded frame inside ``page`` that scrolls when it grows taller than the window."""
        canvas = tk.Canvas(page, highlightthickness=0, borderwidth=0, bg=ui_theme.PALETTE["bg"])
        bar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas, padding=(20, 14, 20, 14))
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        self.canvases.append(canvas)

        def fit_bar(_=None):
            """Thanh cuộn chỉ hiện (và chỉ chiếm chỗ) khi nội dung cao hơn khung nhìn."""
            canvas.configure(scrollregion=canvas.bbox("all"))
            need = inner.winfo_reqheight() > canvas.winfo_height() + 1
            if need and not bar.winfo_ismapped():
                bar.pack(side="right", fill="y", before=canvas)
            elif not need and bar.winfo_ismapped():
                bar.pack_forget()
                canvas.yview_moveto(0)

        inner.bind("<Configure>", fit_bar, add="+")
        canvas.bind("<Configure>", lambda event: (canvas.itemconfigure(window, width=event.width), fit_bar()), add="+")

        def wheel(event):
            if isinstance(event.widget, tk.Listbox):
                return
            if inner.winfo_reqheight() > canvas.winfo_height():
                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

        canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))
        return inner

    def build_settings(self, root):
        G = self.groups
        frame = self.section(G["chung"], "Giao diện & khởi động", "Sáng/tối, mở cùng Windows và tự bật MCP.")
        theme_row = ttk.Frame(frame)
        theme_row.pack(fill="x", pady=(2, 12))
        ttk.Label(theme_row, text="Giao diện").pack(side="left", padx=(0, 12))
        keys = [k for k, _ in ui_theme.PREFS]
        self.theme_switch = ui_theme.Segmented(theme_row, [label for _, label in ui_theme.PREFS], self.choose_theme, bg_key="card")
        self.theme_switch.select(keys.index(ui_theme.PREF) if ui_theme.PREF in keys else 0)
        self.theme_switch.pack(side="left")
        ttk.Checkbutton(frame, text="Khởi động AutoCAD MCP Launcher cùng Windows",
                        variable=self.startup_var,
                        command=self.save_startup_setting).pack(anchor="w")
        ttk.Label(frame,
                  text="Khi bật, launcher sẽ mở sau khi bạn đăng nhập Windows. Bạn có thể tắt lựa chọn này bất cứ lúc nào.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", padx=(24, 0), pady=(6, 12))
        ttk.Checkbutton(frame, text="Tự bật MCP khi mở launcher",
                        variable=self.autostart_mcp_var,
                        command=self.save_autostart_mcp_setting).pack(anchor="w", pady=(4, 0))
        ttk.Label(frame,
                  text="Khi bật, gateway MCP tự chạy ngay khi launcher mở, không cần bấm Bắt đầu. AutoCAD vẫn chỉ được kết nối khi agent gọi tool.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", padx=(24, 0), pady=(6, 12))
        ttk.Label(frame, text="Đóng cửa sổ (nút X) thì launcher thu xuống khay hệ thống và vẫn chạy; thoát hẳn bằng menu chuột phải ở biểu tượng khay.",
                  style="Card.Muted.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=(4, 0))
        frame = self.section(G["agent"], "Cổng skill", "Bắt agent đọc skill điều phối trước khi dùng tool CAD.")
        ttk.Checkbutton(frame, text="Buộc agent đọc skill điều phối trước khi dùng tool CAD",
                        variable=self.skill_gate_var,
                        command=self.save_skill_gate_setting).pack(anchor="w", pady=(4, 0))
        ttk.Label(frame,
                  text="Khi bật (khuyên bật), gateway từ chối tool CAD cho tới khi phiên agent đã đọc skill autocad-agent-coordinator qua tool skills; lời từ chối nói rõ phải làm gì. Có hiệu lực ngay, không cần mở lại launcher. Các tool skills, knowledge, knowledge_propose và dutoan không bị chặn.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", padx=(24, 0), pady=(6, 12))
        self.settings_status = ttk.Label(frame, text="")
        self.settings_status.pack(anchor="w", padx=(24, 0))
        frame = self.section(G["capnhat"], "Cập nhật", "Phiên bản đang dùng và kiểm tra bản mới.")
        self.update_auto_var = tk.BooleanVar(value=load_settings().get("update_auto_check", True) is not False)
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(2, 0))
        self.update_info_label = ttk.Label(row, text="")
        self.update_info_label.pack(side="left")
        ttk.Button(row, text="Kiểm tra cập nhật", command=lambda: self.check_for_updates(manual=True)).pack(side="right")
        self.update_check_status = ttk.Label(frame, text="")
        self.update_check_status.pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(frame, text="Tự kiểm tra bản mới khi mở launcher", variable=self.update_auto_var,
                        command=self.save_update_auto_setting).pack(anchor="w", pady=(6, 0))
        self.refresh_update_settings()
        frame = self.section(G["dulieu"], "Tri thức AutoCAD", "Trang tri thức công khai tải về máy và gửi đề xuất.")
        ttk.Label(frame,
                  text="Tải các trang tri thức công khai (cách đọc bản vẽ, bóc khối lượng, lỗi hay gặp) về máy. Launcher chỉ nhận bản phát hành đã được người duyệt đóng tag, kiểm tra SHA-256, và kiểm tra bản mới mỗi 24 giờ. Trang nào bản mới không còn sẽ bị xóa khỏi wiki/; thư mục proposals/ và sensitive-terms.local.txt không bị đụng. Nút bên phải tải lại ngay. Chỉ tải về, không tải lên gì. Việc gửi đề xuất do agent làm bằng tool knowledge_propose, ở mục bên dưới.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(5, 6))
        ttk.Checkbutton(frame, text="Tự kiểm tra và cập nhật tri thức mỗi 24 giờ",
                        variable=self.knowledge_auto_var,
                        command=self.save_knowledge_auto_setting).pack(anchor="w", pady=(0, 6))
        self.knowledge_dir_var = tk.StringVar(value=self.knowledge_dir())
        knowledge_row = ttk.Frame(frame)
        knowledge_row.pack(fill="x")
        ttk.Entry(knowledge_row, textvariable=self.knowledge_dir_var, state="readonly").pack(
            side="left", fill="x", expand=True)
        ttk.Button(knowledge_row, text="Đổi thư mục…", command=self.choose_knowledge_dir).pack(side="left", padx=(6, 0))
        self.knowledge_btn = ttk.Button(knowledge_row, text="Tải tri thức", command=lambda: self.run_knowledge_check(force=True))
        self.knowledge_btn.pack(side="left", padx=(6, 0))
        self.knowledge_status = ttk.Label(frame, text="")
        self.knowledge_status.pack(anchor="w", pady=(6, 0))
        ttk.Label(frame, text="Gửi đề xuất tri thức", style="Card.H3.TLabel").pack(anchor="w", pady=(14, 0))
        ttk.Label(frame,
                  text="Agent gửi trang đề xuất (đã gỡ tên dự án, số liệu thật) vào hàng chờ duyệt; chỉ sau khi người duyệt chấp nhận mới công khai. Khóa nhóm đã có sẵn trong launcher (bản phát hành chính thức). Nội dung được kiểm tra trên máy trước khi gửi: email, số điện thoại, đường dẫn máy, khóa và các thuật ngữ trong sensitive-terms.local.txt (đặt trong thư mục tri thức) sẽ bị chặn. Bản tự dựng không có khóa sẽ hiện thêm ô nhập; khóa nhập tay lưu trong launcher/state/settings.json.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(4, 6))
        settings_now = knowledge_propose.load_settings()
        self.propose_url_var = tk.StringVar(value=knowledge_propose.gateway_url(settings_now))
        self.propose_key_var = tk.StringVar(value=str(settings_now.get("knowledge_team_key") or ""))
        # A key shipped in the package is never shown or editable; the field appears only when none is embedded.
        has_embedded_key = bool(knowledge_propose.embedded_key())
        fields = [("Địa chỉ cổng", self.propose_url_var, False)]
        if not has_embedded_key:
            fields.append(("Khóa nhóm", self.propose_key_var, True))
        for caption, variable, hidden in fields:
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=caption, width=14).pack(side="left")
            ttk.Entry(row, textvariable=variable, show="•" if hidden else "").pack(side="left", fill="x", expand=True)
        if has_embedded_key:
            ttk.Label(frame, text="Khóa nhóm đã được tích hợp sẵn trong launcher; không cần nhập.",
                      foreground=ui_theme.OK).pack(anchor="w", pady=(2, 0))
        ttk.Button(frame, text="Lưu cấu hình gửi đề xuất", command=self.save_propose_settings).pack(
            anchor="w", pady=(6, 0))
        self.propose_status = ttk.Label(frame, text="")
        self.propose_status.pack(anchor="w", pady=(6, 0))
        frame = self.section(G["dulieu"], "Dữ liệu dự toán", "Tệp dutoan.db (đơn giá, định mức) cho công cụ dutoan.")
        ttk.Label(frame,
                  text="Công cụ dutoan cần tệp dutoan.db (đơn giá, định mức). Tệp này không đi kèm launcher và không được đưa lên chỗ công khai. Nhập khóa dữ liệu do người quản lý cấp (khóa riêng, không nhúng sẵn trong launcher), launcher sẽ tự tải và cập nhật tệp từ cổng của nhóm; tệp được kiểm tra (SHA-256, đủ bảng) rồi mới thay bản cũ. Cách đơn giản nhất: bấm Nhập từ tệp và chọn tệp dutoan.db (hoặc zip chứa nó) do người quản lý gửi. Nếu có cổng nhóm hoặc địa chỉ tải riêng thì dùng các ô bên dưới.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(5, 6))
        settings_dutoan = knowledge_propose.load_settings()
        self.dutoan_url_var = tk.StringVar(value=str(settings_dutoan.get("dutoan_db_url") or ""))
        self.dutoan_sha_var = tk.StringVar(value=str(settings_dutoan.get("dutoan_db_sha256") or ""))
        self.dutoan_key_var = tk.StringVar(value=str(settings_dutoan.get("dutoan_data_key") or ""))
        for caption, variable, hidden in (("Khóa dữ liệu", self.dutoan_key_var, True), ("Địa chỉ tải", self.dutoan_url_var, False),
                                          ("SHA-256", self.dutoan_sha_var, False)):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=caption, width=14).pack(side="left")
            ttk.Entry(row, textvariable=variable, show="•" if hidden else "").pack(side="left", fill="x", expand=True)
        buttons = ttk.Frame(frame)
        buttons.pack(anchor="w", pady=(6, 0))
        self.dutoan_sync_button = ttk.Button(buttons, text="Cập nhật từ cổng nhóm", command=lambda: self.run_dutoan_sync(manual=True))
        self.dutoan_sync_button.pack(side="left")
        self.dutoan_button = ttk.Button(buttons, text="Tải theo địa chỉ", command=self.run_dutoan_download)
        self.dutoan_button.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Nhập từ tệp…", command=self.import_dutoan_file).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Mở thư mục dữ liệu", command=self.open_dutoan_folder).pack(side="left", padx=(8, 0))
        self.dutoan_status = ttk.Label(frame, text=dutoan_data.describe()["message"])
        self.dutoan_status.pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(frame, text="Tự cập nhật dữ liệu dự toán từ cổng nhóm khi mở launcher",
                        variable=self.dutoan_auto_var, command=self.save_dutoan_auto_setting).pack(anchor="w", pady=(4, 0))
        if cadweb_local.project_dir(ROOT):   # chỉ hiện nếu máy này có clone cad-web-local cạnh mcp/
            frame = self.section(G["ketnoi"], "CAD Studio (local)", "Web chat dùng MCP ngay trên máy này.")
            ttk.Label(frame,
                      text="Web chat gọi MCP ngay trên máy này (không đăng nhập, không máy CAD từ xa) — chạy ngay trong launcher, không cần cài thêm.",
                      foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(5, 6))
            ttk.Checkbutton(frame, text="Tự mở CAD Studio (local) khi bật kết nối cho agent",
                            variable=self.cadweb_auto_var, command=self.save_cadweb_auto_setting).pack(anchor="w", pady=(4, 0))
        frame = self.section(G["ketnoi"], "Kết nối ra server (agent từ xa)", "Cho web/server ở máy khác gọi MCP của máy này.")
        ttk.Label(frame,
                  text="Dùng khi web hoặc server nằm ở máy khác: launcher chủ động kết nối ra server (wss://), server gọi MCP của máy này qua kết nối đó. Không mở cổng nào ở máy này. Tắt mặc định; tắt thì mọi thứ chạy như cũ. Token là bí mật và sẽ không hiện lại sau khi lưu. Tool launcher_set_backend bị chặn với server. Cần gateway đang chạy (Bật kết nối cho agent); máy dùng lâu dài nên bật Tự bật MCP khi mở launcher.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(5, 6))
        ttk.Checkbutton(frame, text="Bật kết nối ra server", variable=self.remote_enabled_var).pack(anchor="w", pady=(0, 4))
        for caption, variable, hidden in (("Địa chỉ server", self.remote_url_var, False), ("Mã máy", self.remote_id_var, False),
                                          ("Token", self.remote_token_var, True)):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=caption, width=14).pack(side="left")
            ttk.Entry(row, textvariable=variable, show="•" if hidden else "").pack(side="left", fill="x", expand=True)
        self.remote_token_note = ttk.Label(frame, text="", foreground=ui_theme.MUTED)
        self.remote_token_note.pack(anchor="w", pady=(2, 0))
        self.refresh_remote_token_note()
        ttk.Button(frame, text="Lưu cấu hình kết nối ra server", command=self.save_remote_settings).pack(anchor="w", pady=(6, 0))
        self.remote_status = ttk.Label(frame, text="", wraplength=650, justify="left")
        self.remote_status.pack(anchor="w", pady=(6, 0))
        self.remote_live = ttk.Label(frame, text="Trạng thái: đang tắt.", foreground=ui_theme.OK, wraplength=650, justify="left")
        self.remote_live.pack(anchor="w", pady=(2, 0))
        frame = self.section(G["dulieu"], "Thư viện block", "Block dựng sẵn (.dwg/.dxf) agent chèn theo tên.")
        ttk.Label(frame,
                  text="Nơi lưu các block dựng sẵn (nội thất, cây cối, thiết bị vệ sinh) dạng .dwg hoặc .dxf. Agent chèn chúng bằng tên file; đơn vị mỗi file phải là mm. Thư mục con có file index.json là một kho riêng (ví dụ dwgshare), agent tra theo loại và kích thước. Quy ước đặt tên có trong README.md của thư mục.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(5, 6))
        library_row = ttk.Frame(frame)
        library_row.pack(fill="x")
        self.block_library_var = tk.StringVar(value=str(block_library_dir()))
        ttk.Entry(library_row, textvariable=self.block_library_var, state="readonly").pack(
            side="left", fill="x", expand=True)
        ttk.Button(library_row, text="Mở thư mục thư viện", command=self.open_block_library).pack(
            side="left", padx=(6, 0))
        self.block_library_status = ttk.Label(frame, text=self.block_library_summary())
        self.block_library_status.pack(anchor="w", pady=(6, 0))
        frame = self.section(G["agent"], "Cài skill cho agent", "Chép skill AutoCAD vào thư mục skill của agent.")
        ttk.Label(frame,
                  text="Chọn agent và các skill AutoCAD muốn cài hoặc cập nhật. Skill được chép vào thư mục dùng chung của tài khoản Windows.",
                  foreground=ui_theme.MUTED, wraplength=650, justify="left").pack(anchor="w", pady=(5, 10))
        self.skill_agent = tk.StringVar(value="OpenAI Codex")
        self.skill_agents = {
            "OpenAI Codex": Path.home() / ".codex" / "skills",
            "Claude Code": Path.home() / ".claude" / "skills",
            CLAUDE_DESKTOP: Path.home() / "AutoCAD-MCP-Skills-Claude-Desktop",
        }
        self.agent_notes = {
            "OpenAI Codex": Path.home() / ".codex" / "AGENTS.md",
            "Claude Code": Path.home() / ".claude" / "CLAUDE.md",
        }
        skill_select = ui_theme.Dropdown(frame, self.skill_agent, tuple(self.skill_agents), width=26)
        skill_select.pack(anchor="w", pady=(0, 8))
        self.dropdowns.append(skill_select)
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)
        self.skill_list = tk.Listbox(list_frame, selectmode="extended", height=8,
                                     exportselection=False, font=("Segoe UI", 9))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.skill_list.yview)
        self.skill_list.configure(yscrollcommand=scrollbar.set)
        self.skill_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.skill_names = self.available_skills()
        for name in self.skill_names:
            self.skill_list.insert("end", name)
        skill_actions = ttk.Frame(frame)
        skill_actions.pack(fill="x", pady=(8, 0))
        ttk.Button(skill_actions, text="Chọn tất cả", command=self.select_all_skills).pack(side="left")
        ttk.Button(skill_actions, text="Cài / cập nhật skill đã chọn",
                   command=self.install_selected_skills).pack(side="right")
        self.skill_status = ttk.Label(frame, text=f"Có {len(self.skill_names)} skill trong bản này.",
                                      foreground=ui_theme.OK)
        self.skill_status.pack(anchor="w", pady=(8, 0))
        self.build_extra_settings(G)

    def build_extra_settings(self, G):
        """Các thẻ thêm cho bố cục nhóm: gateway & dịch vụ, thêm MCP vào agent, tài liệu LiteBIM, nâng cao."""
        frame = self.section(G["ketnoi"], "Gateway MCP & dịch vụ", "Agent gọi MCP qua gateway của launcher trên máy này.")
        frame.master.pack_configure(before=frame.master.master.winfo_children()[2])   # đứng đầu nhóm, sau tiêu đề nhóm
        ttk.Label(frame, text="Địa chỉ gateway: http://127.0.0.1:8764 (cổng cố định, chỉ nghe trên máy này)").pack(anchor="w")
        ttk.Label(frame, text="Dịch vụ: AutoCAD – Puran, AutoCAD – Beiming, Dự toán" +
                  "".join(f", {litebim_bridge.PRODUCTS[k][0]}" for k in ("litebim", "litecad") if litebim_bridge.installed(k)) +
                  ". Trạng thái từng dịch vụ xem ở tab Điều khiển.", style="Card.Muted.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=(4, 8))
        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Button(row, text="Mở tab Điều khiển", command=lambda: self.select_page(0, sync=True)).pack(side="left")
        for k in ("litebim", "litecad"):
            if litebim_bridge.installed(k):
                ttk.Button(row, text=f"Bật MCP {litebim_bridge.PRODUCTS[k][0]}?", style="Link.TButton",
                           command=lambda k=k: self.show_pipe_help(k)).pack(side="left", padx=(14, 0))
        frame = self.section(G["agent"], "Thêm MCP vào agent", "Ghi các MCP của launcher vào Codex, Claude Code, Claude Desktop, Cursor.")
        frame.master.pack_configure(before=frame.master.master.winfo_children()[2])
        ttk.Label(frame, text="Chọn agent và bấm Thêm vào agent ở mục Kết nối với agent (tab Điều khiển); có cấu hình thủ công để sao chép.",
                  style="Card.Muted.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=(0, 8))
        ttk.Button(frame, text="Mở mục Kết nối với agent", command=lambda: self.select_page(0, sync=True)).pack(anchor="w")
        frame = self.section(G["dulieu"], "Tài liệu LiteBIM / LiteCAD đã lưu", "Tài liệu API (get_reference) launcher lưu sẵn cho agent đọc.")
        self.reference_label = ttk.Label(frame, text="", style="Card.Muted.TLabel", wraplength=600, justify="left")
        self.reference_label.pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Button(row, text="Làm mới tài liệu", command=self.refresh_reference).pack(side="left")
        ttk.Button(row, text="Mở thư mục", command=lambda: self.open_folder(ROOT / "launcher" / "state" / "litebim" / "reference")).pack(side="left", padx=(8, 0))
        self.show_reference_info()
        frame = self.section(G["nangcao"], "Nhật ký", "Log của gateway, CAD Studio và trình cập nhật.")
        ttk.Button(frame, text="Mở thư mục nhật ký", command=lambda: self.open_folder(LOG_DIR)).pack(anchor="w")
        frame = self.section(G["nangcao"], "Thư mục cấu hình", "settings.json, sao lưu cấu hình agent, bộ đệm tài liệu.")
        ttk.Label(frame, text=str(ROOT / "launcher" / "state"), style="Card.Muted.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Button(frame, text="Mở thư mục cấu hình", command=lambda: self.open_folder(ROOT / "launcher" / "state")).pack(anchor="w")
        frame = self.section(G["nangcao"], "Đặt lại cài đặt", "Đưa mọi tuỳ chọn của launcher về mặc định (có sao lưu).")
        ttk.Button(frame, text="Đặt lại cài đặt…", style="Danger.TButton", command=self.reset_settings).pack(anchor="w")

    def open_folder(self, path):
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            os.startfile(str(path))
        except OSError as exc:
            dialogs.error(self, "Không mở được thư mục", str(exc))

    def show_reference_info(self):
        import litebim_reference
        lines = []
        for key in ("litebim", "litecad"):
            info = litebim_reference.info(key)
            title = litebim_bridge.PRODUCTS[key][0]
            lines.append(f"{title}: phiên bản {info['version']}, lấy lúc {info['fetched_at']}" if info.get("available")
                         else f"{title}: chưa có (lưu tự động khi {title} mở và nối qua gateway)")
        self.reference_label.configure(text="\n".join(lines))

    def refresh_reference(self):
        """Lấy lại tài liệu ngay (gateway phải đang chạy và ứng dụng đang mở)."""
        def worker():
            msgs = []
            for key in ("litebim", "litecad"):
                try:
                    req = urllib.request.Request(f"http://127.0.0.1:8764/{key}/reference/refresh", method="POST")
                    with urllib.request.urlopen(req, timeout=60) as r:
                        msgs.append(f"{key}: {json.load(r).get('state')}")
                except Exception as exc:
                    msgs.append(f"{key}: {getattr(exc, 'code', '') or 'gateway chưa chạy / ứng dụng chưa mở'}")
            self.after(0, self.show_reference_info)
        threading.Thread(target=worker, daemon=True).start()
        self.reference_label.configure(text="Đang làm mới…")

    def reset_settings(self):
        if not dialogs.ask(self, "Đặt lại cài đặt?", "Mọi tuỳ chọn của launcher về mặc định. Tệp settings.json cũ được giữ lại "
                           "thành bản sao lưu cạnh nó. Cấu hình của agent và dữ liệu không bị đụng.", ok="Đặt lại", danger=True):
            return
        try:
            if SETTINGS_FILE.exists():
                SETTINGS_FILE.replace(SETTINGS_FILE.with_name(f"settings.backup-{time.strftime('%Y%m%d-%H%M%S')}.json"))
        except OSError as exc:
            dialogs.error(self, "Không đặt lại được", str(exc))
            return
        dialogs.info(self, "Đã đặt lại", "Đã đưa cài đặt về mặc định. Đóng hẳn và mở lại launcher để áp dụng hết.")

    @staticmethod
    def available_skills():
        skills_dir = SKILLS_SOURCE
        return sorted(path.name for path in skills_dir.iterdir()
                      if path.is_dir() and (path / "SKILL.md").is_file()) if skills_dir.is_dir() else []

    @staticmethod
    def missing_skills():
        """Skills that the other agent folders carry but the installer source lacks."""
        names = set(App.available_skills())
        extra = set()
        for folder in (".claude", ".agents"):
            root = ROOT / folder / "skills"
            if root.is_dir():
                extra |= {p.name for p in root.iterdir() if (p / "SKILL.md").is_file()}
        return sorted(extra - names)

    def select_all_skills(self):
        self.skill_list.selection_set(0, "end")

    def install_selected_skills(self):
        selected = [self.skill_names[index] for index in self.skill_list.curselection()]
        if not selected:
            self.skill_status.configure(text="Hãy chọn ít nhất một skill.", foreground=ui_theme.WARN)
            return
        target_root = self.skill_agents[self.skill_agent.get()]
        source_root = SKILLS_SOURCE
        if self.skill_agent.get() == CLAUDE_DESKTOP:
            self.package_skills_for_claude_desktop(selected, target_root)
            return
        missing = self.missing_skills()
        if missing:
            self.skill_status.configure(
                text=f"Nguồn skill thiếu: {', '.join(missing)}. Đồng bộ {SKILLS_SOURCE} trước khi cài.",
                foreground=ui_theme.ERR)
            return
        try:
            target_root.mkdir(parents=True, exist_ok=True)
            for name in selected:
                source = source_root / name
                target = target_root / name
                if not (source / "SKILL.md").is_file():
                    raise FileNotFoundError(f"Không tìm thấy nội dung skill: {source}")
                shutil.copytree(source, target, dirs_exist_ok=True)
            note_path = self.agent_notes.get(self.skill_agent.get())
            if note_path:
                agentnote.install_note(note_path)
            self.skill_status.configure(
                text=f"Đã cài / cập nhật {len(selected)} skill cho {self.skill_agent.get()} tại {target_root}."
                     + (f" Đã ghi chỉ dẫn tự dùng skill vào {note_path}." if note_path else ""),
                foreground=ui_theme.OK)
        except OSError as exc:
            self.skill_status.configure(text=f"Không cài được skill: {exc}", foreground=ui_theme.ERR)

    def package_skills_for_claude_desktop(self, selected, target_dir):
        """Claude Desktop keeps its own skill store and only accepts uploaded zips."""
        try:
            build_skill_zips(SKILLS_SOURCE, selected, target_dir)
            os.startfile(str(target_dir))
        except OSError as exc:
            self.skill_status.configure(text=f"Không tạo được file zip: {exc}", foreground=ui_theme.ERR)
            return
        self.skill_status.configure(
            text=f"Đã tạo {len(selected)} file zip tại {target_dir}. Trong Claude Desktop: Customize, Skills, "
                 "tải từng file lên (xem HUONG-DAN.txt).",
            foreground=ui_theme.OK)

    def save_startup_setting(self):
        enabled = self.startup_var.get()
        try:
            set_startup_enabled(enabled)
            self.settings_status.configure(
                text="Đã bật khởi động cùng Windows." if enabled else "Đã tắt khởi động cùng Windows."
            )
        except OSError as exc:
            self.startup_var.set(not enabled)
            self.settings_status.configure(text=f"Không lưu được cài đặt: {exc}")

    def save_autostart_mcp_setting(self):
        enabled = self.autostart_mcp_var.get()
        try:
            save_setting("autostart_mcp", enabled)
            self.settings_status.configure(
                text="Đã bật tự chạy MCP khi mở launcher." if enabled else "Đã tắt tự chạy MCP khi mở launcher."
            )
        except OSError as exc:
            self.autostart_mcp_var.set(not enabled)
            self.settings_status.configure(text=f"Không lưu được cài đặt: {exc}")

    def refresh_remote_token_note(self):
        saved = bool(load_settings().get("remote_machine_token"))
        self.remote_token_note.configure(
            text="Token đã lưu (ẩn). Để trống ô Token nếu không muốn đổi." if saved else "Chưa có token.")

    def save_remote_settings(self):
        enabled = self.remote_enabled_var.get()
        entered = self.remote_token_var.get().strip()
        values = {
            "remote_agent_enabled": enabled,
            "remote_server_url": self.remote_url_var.get().strip(),
            "remote_machine_id": self.remote_id_var.get().strip(),
            "remote_machine_token": entered or str(load_settings().get("remote_machine_token") or ""),
        }
        problem = remote_agent.read_config(values).problem if enabled else ""
        if problem:
            self.remote_status.configure(text=problem, foreground=ui_theme.ERR)
            return
        try:
            for name, value in values.items():
                save_setting(name, value)
        except OSError as exc:
            self.remote_status.configure(text=f"Không lưu được cài đặt: {exc}", foreground=ui_theme.ERR)
            return
        self.remote_token_var.set("")
        self.refresh_remote_token_note()
        self.remote_status.configure(
            text="Đã lưu. Gateway nhận cấu hình trong vài giây." if enabled else "Đã lưu; kết nối ra server đang tắt.",
            foreground=ui_theme.OK)
        if enabled:
            self.ensure_remote_deps()

    def ensure_remote_deps(self):
        """Cài thư viện websockets vào môi trường của gateway khi bật lần đầu (chỉ khi thiếu)."""
        self.remote_install = {"result": None}

        def worker():
            repo = REPOS["puran"]
            try:
                if install_ui.installed(repo, "import websockets"):
                    self.remote_install["result"] = (True, "")
                    return
                done = subprocess.run([str(python_in(repo)), "-m", "pip", "install", "websockets>=13"],
                                      capture_output=True, text=True, timeout=300,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                tail = (done.stdout + done.stderr).strip().splitlines()[-1:] or [""]
                self.remote_install["result"] = (done.returncode == 0, tail[0])
            except Exception as exc:
                self.remote_install["result"] = (False, str(exc))

        threading.Thread(target=worker, daemon=True).start()
        self.after(500, self.poll_remote_install)

    def poll_remote_install(self):
        result = self.remote_install["result"]
        if result is None:
            self.after(500, self.poll_remote_install)
            return
        ok, detail = result
        if not ok:
            self.remote_status.configure(text=f"Không cài được thư viện websockets: {detail}", foreground=ui_theme.ERR)

    def save_skill_gate_setting(self):
        enabled = self.skill_gate_var.get()
        try:
            save_setting("skill_gate", enabled)
            self.settings_status.configure(
                text="Đã bật: tool CAD chỉ chạy sau khi agent đọc skill điều phối." if enabled
                else "Đã tắt: gateway không còn chặn tool CAD khi chưa đọc skill."
            )
        except OSError as exc:
            self.skill_gate_var.set(not enabled)
            self.settings_status.configure(text=f"Không lưu được cài đặt: {exc}")

    @staticmethod
    def knowledge_dir():
        saved = load_settings().get("knowledge_dir")
        return saved if isinstance(saved, str) and saved else str(Path.home() / "autocad-knowledge")

    @staticmethod
    def block_library_summary():
        folder = block_library_dir()
        try:
            count = sum(1 for path in folder.iterdir() if path.suffix.lower() in (".dwg", ".dxf"))
            stores = sorted(path for path in folder.iterdir()
                            if path.is_dir() and not path.name.startswith(".") and (path / "index.json").is_file())
        except OSError:
            return "Thư mục chưa có; sẽ được tạo khi bạn mở."
        text = f"Hiện có {count} tệp block (.dwg/.dxf)."
        for store in stores:
            try:
                in_store = sum(1 for path in store.iterdir() if path.suffix.lower() in (".dwg", ".dxf"))
            except OSError:
                continue
            text += f" Kho riêng \"{store.name}\": {in_store} tệp."
        return text

    def open_block_library(self):
        folder = block_library_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except OSError as exc:
            self.block_library_status.configure(text=f"Không mở được thư mục: {exc}", foreground=ui_theme.ERR)
            return
        self.block_library_status.configure(text=self.block_library_summary(), foreground=ui_theme.OK)

    def choose_knowledge_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.knowledge_dir_var.get(), parent=self,
                                         title="Chọn thư mục lưu tri thức")
        if not chosen:
            return
        chosen = str(Path(chosen))
        try:
            save_setting("knowledge_dir", chosen)
        except OSError as exc:
            self.knowledge_status.configure(text=f"Không lưu được thư mục: {exc}", foreground=ui_theme.ERR)
            return
        self.knowledge_dir_var.set(chosen)
        self.refresh_knowledge_status()
        if self.knowledge_auto_var.get():
            self.run_knowledge_check(force=False)

    def run_dutoan_download(self):
        if self.dutoan_busy:
            return
        url = self.dutoan_url_var.get().strip()
        sha = self.dutoan_sha_var.get().strip()
        if not url:
            self.dutoan_status.configure(text="Chưa có địa chỉ tải. Hãy dán địa chỉ do người quản lý cấp.", foreground=ui_theme.ERR)
            return
        try:
            save_setting("dutoan_db_url", url)
            save_setting("dutoan_db_sha256", sha)
        except OSError as exc:
            self.dutoan_status.configure(text=f"Không lưu được cấu hình: {exc}", foreground=ui_theme.ERR)
            return
        self.dutoan_busy = True
        self.dutoan_button.configure(state="disabled")
        self.dutoan_progress = {"text": "Đang tải…", "result": None}

        def progress(done, total):
            mb = done / (1024 * 1024)
            self.dutoan_progress["text"] = f"Đang tải… {mb:.0f}/{total / (1024 * 1024):.0f} MB" if total else f"Đang tải… {mb:.0f} MB"

        def worker():
            self.dutoan_progress["result"] = dutoan_data.download(url, sha, progress=progress)

        threading.Thread(target=worker, daemon=True).start()
        self.after(300, self.poll_dutoan_download)

    def poll_dutoan_download(self):
        result = self.dutoan_progress["result"]
        if result is None:
            self.dutoan_status.configure(text=self.dutoan_progress["text"], foreground=ui_theme.OK)
            self.after(300, self.poll_dutoan_download)
            return
        self.dutoan_busy = False
        self.dutoan_button.configure(state="normal")
        self.dutoan_status.configure(text=result["message"], foreground=ui_theme.OK if result["ok"] else ui_theme.ERR)
        if result["ok"] and hasattr(self, "dutoan_label"):
            self.dutoan_label.configure(text="●  dutoan  ·  Sẵn sàng (HTTP qua gateway)")

    def save_dutoan_auto_setting(self):
        enabled = bool(self.dutoan_auto_var.get())
        try:
            save_setting("dutoan_auto_update", enabled)
        except OSError as exc:
            self.dutoan_auto_var.set(not enabled)
            self.dutoan_status.configure(text=f"Không lưu được cài đặt: {exc}", foreground=ui_theme.ERR)
            return
        if enabled:
            self.run_dutoan_sync(manual=False)

    def dutoan_tick(self):
        """Look at the team gateway once after start and then every six hours."""
        if self.closing:
            return
        if self.dutoan_auto_var.get():
            self.run_dutoan_sync(manual=False)
        self.after(6 * 3600 * 1000, self.dutoan_tick)

    def run_dutoan_sync(self, manual):
        if self.dutoan_busy:
            return
        if manual:
            try:
                save_setting("dutoan_data_key", self.dutoan_key_var.get().strip())
            except OSError as exc:
                self.dutoan_status.configure(text=f"Không lưu được khóa: {exc}", foreground=ui_theme.ERR)
                return
        settings = knowledge_propose.load_settings()
        key = dutoan_data.sync_key(settings, knowledge_propose.team_key(settings))
        if not key:
            if manual:
                self.dutoan_status.configure(text="Chưa có khóa dữ liệu dự toán nên chưa tự tải được. Nhập khóa bên dưới hoặc dùng địa chỉ tải riêng.", foreground=ui_theme.ERR)
            return
        self.dutoan_busy = True
        self.dutoan_sync_button.configure(state="disabled")
        self.dutoan_progress = {"text": "Đang hỏi cổng nhóm…", "result": None, "manual": manual}
        gateway = knowledge_propose.gateway_url(settings)

        def progress(done, total):
            mb = done / (1024 * 1024)
            self.dutoan_progress["text"] = f"Đang tải… {mb:.0f}/{total / (1024 * 1024):.0f} MB" if total else f"Đang tải… {mb:.0f} MB"

        def worker():
            try:
                self.dutoan_progress["result"] = dutoan_data.sync(gateway, key, progress=progress)
            except Exception as exc:  # never leave the button disabled
                self.dutoan_progress["result"] = {"ok": False, "changed": False, "message": f"Không cập nhật được: {exc}"}

        threading.Thread(target=worker, daemon=True).start()
        self.after(300, self.poll_dutoan_sync)

    def poll_dutoan_sync(self):
        result = self.dutoan_progress["result"]
        if result is None:
            self.dutoan_status.configure(text=self.dutoan_progress["text"], foreground=ui_theme.OK)
            self.after(300, self.poll_dutoan_sync)
            return
        self.dutoan_busy = False
        self.dutoan_sync_button.configure(state="normal")
        # A quiet start-up check only speaks when something changed or went wrong with a database that is missing.
        if self.dutoan_progress.get("manual") or result.get("changed") or (not result["ok"] and not dutoan_data.describe()["present"]):
            self.dutoan_status.configure(text=result["message"], foreground=ui_theme.OK if result["ok"] else ui_theme.ERR)
        if result["ok"] and hasattr(self, "dutoan_label"):
            self.dutoan_label.configure(text="●  dutoan  ·  Sẵn sàng (HTTP qua gateway)")

    def import_dutoan_file(self):
        if self.dutoan_busy:
            return
        chosen = filedialog.askopenfilename(
            parent=self, title="Chọn tệp dữ liệu dự toán",
            filetypes=[("Dữ liệu dự toán", "*.db *.zip"), ("Tất cả", "*.*")])
        if not chosen:
            return
        self.dutoan_busy = True
        self.dutoan_progress = {"text": "Đang nhập và kiểm tra tệp…", "result": None}

        def worker():
            try:
                self.dutoan_progress["result"] = dutoan_data.import_file(chosen)
            except Exception as exc:  # never leave the buttons blocked
                self.dutoan_progress["result"] = {"ok": False, "message": f"Không nhập được: {exc}"}

        threading.Thread(target=worker, daemon=True).start()
        self.after(300, self.poll_dutoan_download)

    def open_dutoan_folder(self):
        folder = dutoan_data.db_path().parent
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(folder)
        except OSError as exc:
            self.dutoan_status.configure(text=f"Không mở được thư mục: {exc}", foreground=ui_theme.ERR)

    def save_propose_settings(self):
        url = self.propose_url_var.get().strip().rstrip("/")
        key = self.propose_key_var.get().strip() if not knowledge_propose.embedded_key() else None
        if not url.startswith("https://"):
            self.propose_status.configure(text="Địa chỉ cổng phải bắt đầu bằng https://", foreground=ui_theme.ERR)
            return
        try:
            save_setting("knowledge_gateway_url", url)
            if key is not None:
                save_setting("knowledge_team_key", key)
        except OSError as exc:
            self.propose_status.configure(text=f"Không lưu được cấu hình: {exc}", foreground=ui_theme.ERR)
            return
        self.propose_status.configure(
            text="Đã lưu. Agent gửi được đề xuất." if knowledge_propose.team_key() else "Đã lưu địa chỉ. Chưa có khóa nhóm nên chưa gửi được.",
            foreground=ui_theme.OK)

    def save_knowledge_auto_setting(self):
        enabled = bool(self.knowledge_auto_var.get())
        try:
            save_setting("knowledge_auto_update", enabled)
        except OSError as exc:
            self.knowledge_auto_var.set(not enabled)
            self.knowledge_status.configure(text=f"Không lưu được cài đặt: {exc}", foreground=ui_theme.ERR)
            return
        if enabled:
            self.run_knowledge_check(force=False)
        else:
            self.refresh_knowledge_status("Đã tắt tự cập nhật.")

    def refresh_knowledge_status(self, note=None):
        version = knowledge.read_version(self.knowledge_dir_var.get())
        last = load_settings().get("knowledge_last_check")
        parts = [f"Tri thức {version['tag']}" if version else "Chưa tải tri thức"]
        if isinstance(last, (int, float)) and last > 0:
            parts.append("kiểm tra lần cuối " + time.strftime("%H:%M %d/%m", time.localtime(last)))
        text = "; ".join(parts) + "."
        if note:
            text += " " + note
        self.knowledge_status.configure(text=text, foreground=ui_theme.OK)

    def knowledge_tick(self):
        """Look once after start and then every hour; a look only contacts GitHub when 24 hours have passed."""
        if self.closing:
            return
        if self.knowledge_auto_var.get():
            self.run_knowledge_check(force=False)
        self.after(3600 * 1000, self.knowledge_tick)

    def run_knowledge_check(self, force):
        if self.knowledge_checking:
            return
        self.knowledge_checking = True
        destination = self.knowledge_dir_var.get()
        last_check = load_settings().get("knowledge_last_check")
        if force:
            self.knowledge_btn.configure(state="disabled")
            self.knowledge_status.configure(text="Đang tải…", foreground=ui_theme.OK)

        def worker():
            result = knowledge.check(destination, last_check=last_check if isinstance(last_check, (int, float)) else None,
                                     force=force)
            self.after(0, lambda: self.finish_knowledge_check(result))

        threading.Thread(target=worker, daemon=True).start()

    def finish_knowledge_check(self, result):
        self.knowledge_checking = False
        self.knowledge_btn.configure(state="normal")
        if result.get("checked"):
            try:
                save_setting("knowledge_last_check", time.time())
            except OSError:
                pass
        if result["state"] == "error":
            self.knowledge_status.configure(text=result["message"], foreground=ui_theme.ERR)
        elif result["state"] == "unavailable":
            self.knowledge_status.configure(text=result["message"], foreground=ui_theme.MUTED)
        else:
            self.refresh_knowledge_status(result["message"] if result["state"] == "updated" else None)

    def refresh_config(self):
        steps = {
            "OpenAI Codex": "Thủ công: gộp các mục trong ô dưới vào cấu hình Codex, rồi mở lại Codex.",
            "Claude Code": "Thủ công: chạy các lệnh trong ô dưới, rồi mở phiên Claude Code mới.",
            "Claude Desktop": "Thủ công: gộp ô dưới vào cấu hình Claude Desktop, rồi thoát hẳn và mở lại Claude Desktop.",
            "Cursor": "Thủ công: gộp ô dưới vào cấu hình Cursor, rồi mở lại Cursor.",
        }
        self.hint.configure(text=steps[self.agent.get()])
        self.config_box.delete("1.0", "end")
        self.config_box.insert("1.0", config_for(self.agent.get()))

    def auto_configure(self, remove=False):
        """Tự thêm (hoặc gỡ) ba mục của launcher trong agent đang chọn, sau khi người dùng xác nhận."""
        if getattr(self, "agentcfg_busy", False):
            return
        agent = self.agent.get()
        ctx = agent_context()
        plan = agentconfig.describe_plan(agent, ctx, remove=remove)
        if plan["problem"]:
            self.agentcfg_status.configure(text=plan["problem"], foreground=ui_theme.ERR)
            return
        if not plan["changes"]:
            self.agentcfg_status.configure(
                text="Không có gì phải đổi: " + ("chưa có mục nào của launcher." if remove else "cấu hình đã đúng sẵn."),
                foreground=ui_theme.OK)
            return
        title = "Gỡ cấu hình khỏi agent" if remove else "Tự thêm cấu hình vào agent"
        if not dialogs.ask(self, title, "Launcher sẽ ghi các thay đổi dưới đây (có sao lưu bản cũ). Tiếp tục?",
                           ok="Gỡ khỏi agent" if remove else "Ghi cấu hình", danger=remove, detail=plan["text"]):
            return
        self.agentcfg_busy = True
        self.auto_btn.configure(state="disabled")
        self.unauto_btn.configure(state="disabled")
        self.agentcfg_status.configure(text="Đang ghi cấu hình…", foreground=ui_theme.OK)
        self.agentcfg_result = {"value": None}

        def worker():
            try:
                self.agentcfg_result["value"] = agentconfig.apply(agent, ctx, remove=remove)
            except Exception as exc:  # không để luồng nền chết im lặng
                self.agentcfg_result["value"] = {"ok": False, "message": f"Lỗi không mong đợi: {exc}", "backup": None, "next": ""}

        threading.Thread(target=worker, daemon=True).start()
        self.after(200, self.poll_auto_configure)

    def poll_auto_configure(self):
        result = self.agentcfg_result["value"]
        if result is None:
            self.after(200, self.poll_auto_configure)
            return
        self.agentcfg_busy = False
        self.auto_btn.configure(state="normal")
        self.unauto_btn.configure(state="normal")
        text = result["message"]
        if result.get("backup"):
            text += " Đã sao lưu bản cũ."
        if result.get("next"):
            text += " " + result["next"]
        self.agentcfg_status.configure(text=text, foreground=ui_theme.OK if result["ok"] else ui_theme.ERR)

    def copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.config_box.get("1.0", "end-1c"))
        self.status.set("Đã sao chép cấu hình")

    def on_unmap(self, event):
        if event.widget is self and self.tray:
            self.after(0, self.hide_if_iconic)

    def hide_if_iconic(self):
        if self.state() == "iconic":
            self.withdraw()

    def hide_to_tray(self):
        if self.tray:
            self.withdraw()
        else:
            self.close()

    def restore(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def show_tray_menu(self, x, y):
        try:
            self.tray_menu.tk_popup(x, y)
        finally:
            self.tray_menu.grab_release()

    def set_cadweb(self, level, text):
        self.cadweb_level = level
        if self.cadweb_row:
            self.cadweb_dot.configure(foreground=ui_theme.LEVEL_COLOR.get(level, ui_theme.LEVEL_COLOR["off"]))
            self.cadweb_label.configure(text=text)

    def poll_cadweb(self):
        """Đang 'khởi động': hỏi nền xem web đã lên chưa, lên rồi thì báo Đang chạy kèm địa chỉ."""
        if self.cadweb_busy or getattr(self, "cadweb_probe", False):
            return
        self.cadweb_probe = True

        def worker():
            try:
                port = self.cadweb.wait_web(timeout=1.0) if self.cadweb.running() else None
                if port:
                    self.events.put(("cadweb_status", ("ok", f"Đang chạy ở http://localhost:{port}")))
            except Exception:
                pass
            finally:
                self.cadweb_probe = False

        threading.Thread(target=worker, daemon=True).start()

    def start(self):
        if self.updating or self.busy or (self.gateway and self.gateway.poll() is None):
            return
        self.busy = True
        self.last_error = None
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.status.set("Đang mở gateway cho agent…")
        threading.Thread(target=self.start_worker, daemon=True).start()

    def start_worker(self):
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            for key, repo in REPOS.items():
                if not python_in(repo).is_file():
                    raise RuntimeError(f"Thiếu thư viện {NAMES[key]}. Thoát app rồi mở lại để cài.")
            if self.closing:
                return

            if listening(8764):
                pid = listener_pid(8764) if is_launcher_gateway() else None
                if not pid:
                    raise RuntimeError("Cổng 8764 đã được chương trình khác sử dụng")
                self.gateway = AdoptedGateway(pid)
                self.events.put(("status", "Gateway đã chạy sẵn trên cổng 8764; app dùng lại nó."))
                self._maybe_start_cadweb()
                return
            self.log = RotatingLog(LOG_DIR / "gateway.log")
            command = [str(python_in(REPOS["puran"])), str(ROOT / "launcher" / "gateway.py")]
            self.gateway = start_logged(command, self.log, cwd=ROOT)
            for _ in range(100):
                if self.gateway.poll() is not None:
                    raise RuntimeError("Gateway thoát khi khởi động; xem launcher/logs/gateway.log")
                if listening(8764):
                    break
                threading.Event().wait(0.1)
            else:
                raise RuntimeError("Gateway chưa mở cổng 8764")
            self.events.put(("status", "Gateway sẵn sàng. Agent sẽ thử AutoCAD khi gọi tool; nếu không có AutoCAD, agent sẽ hỏi bạn trước khi xuất DXF."))
            self._maybe_start_cadweb()
        except Exception as exc:
            kill_tree(self.gateway)
            self.gateway = None
            if self.log:
                self.log.close()
                self.log = None
            self.events.put(("error", str(exc)))
        finally:
            self.events.put(("ready", ""))

    def stop(self):
        kill_tree(self.gateway)
        self.gateway = None
        if self.log:
            self.log.close()
            self.log = None
        for key in REPOS:
            self.services[key].set("off", "Chưa khởi chạy")
        self.cadweb.stop()
        if self.cadweb_row:
            self.set_cadweb("off", "Chưa mở. Web chat dùng các MCP ngay trên máy này.")
        self.status.set("Đã dừng gateway và MCP đang hoạt động")

    def _maybe_start_cadweb(self):
        """Best-effort: tự mở CAD Studio (local) cùng gateway, nếu máy này có project và đã bật tùy chọn."""
        if not self.cadweb_row or not self.cadweb_auto_var.get():
            return
        try:
            self.cadweb.start()
        except Exception as exc:
            self.events.put(("cadweb_status", ("err", str(exc))))
            return
        self.events.put(("cadweb_status", ("busy", "Đang khởi động… bấm Mở CAD Studio để vào.")))

    def open_cadweb_local(self):
        if self.cadweb_busy:
            return
        self.cadweb_busy = True
        self.cadweb_open_btn.configure(state="disabled")
        self.set_cadweb("busy", "Đang mở…")
        threading.Thread(target=self._open_cadweb_worker, daemon=True).start()

    def _open_cadweb_worker(self):
        try:
            self.cadweb.start()
            port = self.cadweb.wait_web()
        except Exception as exc:
            self.events.put(("cadweb_status", ("err", str(exc))))
        else:
            if port:
                webbrowser.open(f"http://localhost:{port}")
                self.events.put(("cadweb_status", ("ok", f"Đang chạy ở http://localhost:{port}")))
            else:
                self.events.put(("cadweb_status", ("err", "Chưa thấy web sẵn sàng; xem launcher/logs/cadweb-local-*.log")))
        finally:
            self.events.put(("cadweb_ready", ""))

    def save_cadweb_auto_setting(self):
        enabled = bool(self.cadweb_auto_var.get())
        try:
            save_setting("cadweb_local_auto", enabled)
        except OSError as exc:
            self.cadweb_auto_var.set(not enabled)
            dialogs.error(self, "Không lưu được cài đặt", str(exc))

    def check_for_updates(self, manual=False):
        """Kiểm tra bản mới ở nền. Tự động (lúc mở app) chỉ khi bật tuỳ chọn; bản người dùng đã 'Bỏ qua' thì không báo lại."""
        if self.closing or self.updating:
            return
        if not manual and load_settings().get("update_auto_check", True) is False:
            return
        if manual:
            self.update_check_status.configure(text="Đang kiểm tra…", foreground=ui_theme.MUTED)

        def worker():
            try:
                update = dialogs.fake_update()
                if update is None:
                    from updater import find_update
                    update = find_update(UPDATE_REPO, app_version())
                try:
                    save_setting("update_last_check", time.strftime("%Y-%m-%d %H:%M"))
                except OSError:
                    pass
                if update and (manual or load_settings().get("skipped_update_version") != update["version"]):
                    self.events.put(("update_available", (update, manual)))
                elif manual:
                    self.events.put(("update_none", ""))
            except Exception as exc:
                if manual:
                    self.events.put(("update_check_failed", str(exc)))
                # Best-effort and quiet in the UI, but leave the reason in a log so a
                # release without its package is not invisible.
                try:
                    from logfile import RotatingLog

                    log = RotatingLog(LOG_DIR / "updater.log", max_bytes=256 * 1024, keep=1)
                    log.banner(f"update check failed: {type(exc).__name__}: {exc}")
                    log.close()
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def refresh_update_settings(self, message=None, error=False):
        """Mục Cập nhật ở tab Cài đặt: phiên bản hiện tại, lần kiểm tra cuối, kết quả kiểm tra."""
        last = load_settings().get("update_last_check") or "chưa kiểm tra"
        pending = getattr(self, "pending_update", None)
        text = f"Phiên bản hiện tại v{app_version()}  ·  Kiểm tra lần cuối: {last}"
        if pending:
            text += f"  ·  Có bản mới v{pending['version']}"
        self.update_info_label.configure(text=text)
        if message is not None:
            self.update_check_status.configure(text=message, foreground=ui_theme.ERR if error else ui_theme.OK)

    def save_update_auto_setting(self):
        try:
            save_setting("update_auto_check", bool(self.update_auto_var.get()))
        except OSError as exc:
            dialogs.error(self, "Không lưu được cài đặt", str(exc))

    def notify_update(self, update, manual=False):
        """Có bản mới: hiện thẻ thông báo gọn trên tab Điều khiển (không bật hộp chặn); kiểm tra tay thì mở hộp luôn."""
        self.pending_update = update
        self.update_banner.show(update["version"], before=self.banner_anchor)
        self.refresh_update_settings()
        self.after(50, self.fit_to_content)   # thẻ thông báo làm tab cao thêm: nới cửa sổ cho vừa
        if manual:
            self.open_update_dialog()

    def dismiss_update_banner(self):
        self.update_banner.hide()

    def open_update_dialog(self):
        update = getattr(self, "pending_update", None)
        if not update:
            return
        if getattr(self, "update_dialog", None) and self.update_dialog.winfo_exists():
            self.update_dialog.lift()
            return
        self.update_dialog = dialogs.UpdateDialog(self, app_version(), update, {
            "start": self.begin_update, "cancel": self.cancel_update, "skip": self.skip_update,
            "restart": self.restart_for_update})
        if self.updating:
            self.update_dialog.state_downloading()
        elif self.update_archive:
            self.update_dialog.state_done()
        self.update_dialog.show(wait=False)

    def skip_update(self, version):
        try:
            save_setting("skipped_update_version", version)
        except OSError:
            pass
        self.update_banner.hide()

    def cancel_update(self):
        """Huỷ tải: bỏ kết quả của luồng tải (luồng nền tự dừng ở lần đọc kế tiếp với bản giả lập)."""
        self.update_cancelled = True
        self.updating = False
        self.start_btn.configure(state="normal")
        self.status.set("Đã huỷ tải bản cập nhật.")

    def restart_for_update(self):
        if getattr(self, "pending_update", {}).get("fake"):
            dialogs.info(self, "Bản giả lập", "Đây là bản cập nhật giả lập (LAUNCHER_FAKE_UPDATE); không cài gì.")
            return
        self.update_wait_started = time.monotonic()
        self.wait_for_idle_then_apply()

    def _dialog_state(self, name, *args):
        d = getattr(self, "update_dialog", None)
        if d is not None and d.winfo_exists():
            getattr(d, name)(*args)

    def begin_update(self, update):
        if self.updating:
            return
        self.updating = True
        self.update_cancelled = False
        self.update_archive = None
        self.status.set(f"Đang tải bản cập nhật v{update['version']}…")

        def worker():
            try:
                report = lambda received, total: self.events.put(("update_progress", received, total))
                if update.get("fake"):
                    archive = dialogs.fake_download(update, report, cancelled=lambda: self.update_cancelled)
                else:
                    from updater import download_release
                    archive = download_release(update, report)
                if not self.update_cancelled:
                    self.events.put(("update_downloaded", str(archive)))
            except Exception as exc:
                if not self.update_cancelled:
                    self.events.put(("update_failed", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def wait_for_idle_then_apply(self):
        if self.closing or not self.update_archive:
            return
        busy = False
        if self.gateway and self.gateway.poll() is None:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8764/status", timeout=0.5) as response:
                    state = json.load(response)
                busy = bool(state.get("active_request") or state.get("queued_requests"))
            except (OSError, ValueError):
                busy = True
        if busy:
            self.status.set("Đang chờ các yêu cầu AutoCAD đang chạy hoàn tất trước khi cập nhật…")
            if self.update_wait_started and time.monotonic() - self.update_wait_started > 600:
                if not self.update_busy_notice_shown:
                    self.update_busy_notice_shown = True
                    proceed = dialogs.ask(
                        self, "Đang chờ MCP",
                        "MCP vẫn đang xử lý yêu cầu sau 10 phút. Tiếp tục chờ?\n"
                        "Chọn Dừng cập nhật để giữ launcher đang chạy.",
                        ok="Tiếp tục chờ", cancel="Dừng cập nhật",
                    )
                    if not proceed:
                        self.updating = False
                        self.update_archive = None
                        self.start_btn.configure(state="normal")
                        self.stop_btn.configure(state="normal")
                        self.status.set("Đã hủy cập nhật; launcher vẫn hoạt động.")
                        return
                    self.update_wait_started = time.monotonic()
                    self.update_busy_notice_shown = False
            self.after(1000, self.wait_for_idle_then_apply)
            return

        self.status.set("Đang cài đặt bản mới và khởi động lại launcher…")
        try:
            updater = ROOT / "launcher" / "updater.py"
            command = [
                sys.executable,
                str(updater),
                "--apply",
                "--archive",
                str(self.update_archive),
                "--root",
                str(ROOT),
                "--parent-pid",
                str(os.getpid()),
                "--version",
                str(self.pending_update["version"]),
                "--python",
                sys.executable,
            ]
            if self.gateway and self.gateway.poll() is None:
                command.append("--start")
            subprocess.Popen(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self.close()
        except Exception as exc:
            self.updating = False
            self.update_archive = None
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="normal")
            self.status.set(f"Không thể chạy trình cập nhật: {exc}")

    def finish_update_download(self, archive):
        """Tải xong: chờ người dùng bấm 'Khởi động lại để hoàn tất' (không tự khởi động lại giữa chừng)."""
        self.update_archive = Path(archive)
        self.updating = False
        self.status.set("Đã tải và xác minh gói cập nhật; bấm Khởi động lại để hoàn tất.")
        if getattr(self, "update_dialog", None) and self.update_dialog.winfo_exists():
            self.update_dialog.state_done()
        else:
            self.open_update_dialog()

    def tick(self):
        if self.tray:
            self.tray.poll()
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                value = event[1] if len(event) > 1 else None
                if kind == "status":
                    self.status.set(value)
                elif kind == "error":
                    self.status.set(value)
                    self.last_error = value
                    dialogs.error(self, "Không thể khởi động", value)
                elif kind == "ready":
                    self.busy = False
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="normal")
                elif kind == "cadweb_status":
                    self.set_cadweb(*value)
                elif kind == "cadweb_ready":
                    self.cadweb_busy = False
                    if self.cadweb_row:
                        self.cadweb_open_btn.configure(state="normal")
                elif kind == "update_available":
                    self.notify_update(*value)
                elif kind == "update_none":
                    self.refresh_update_settings("Đang dùng bản mới nhất.")
                elif kind == "update_check_failed":
                    self.refresh_update_settings(f"Không kiểm tra được: {value}", error=True)
                elif kind == "update_progress":
                    received, total = event[1], event[2]
                    if not self.updating:
                        continue   # đã huỷ
                    if total:
                        self.status.set(f"Đang tải bản cập nhật… {received * 100 // total}%")
                    else:
                        self.status.set(f"Đang tải bản cập nhật… {received // (1024 * 1024)} MB")
                    self._dialog_state("progress", received, total)
                elif kind == "update_downloaded":
                    self.finish_update_download(value)
                elif kind == "update_failed":
                    self.updating = False
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="normal")
                    self.status.set("Không tải được bản cập nhật; launcher vẫn đang chạy.")
                    if getattr(self, "update_dialog", None) and self.update_dialog.winfo_exists():
                        self.update_dialog.state_error(value)
                    else:
                        dialogs.error(self, "Cập nhật thất bại", value)
        except queue.Empty:
            pass
        if self.gateway and self.gateway.poll() is None and not self.busy:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8764/status", timeout=0.3) as response:
                    state = json.load(response)
                active = state["active"]
                offline = state.get("mode") == "ezdxf"
                for key in REPOS:
                    if key == active:
                        self.services[key].set("ok", "DXF offline" if offline else "Đã kết nối AutoCAD")
                    else:
                        self.services[key].set("off", "Chờ agent gọi tool (chưa nối AutoCAD)")
                status_text = state.get("error") or state["state"]
                waiting = int(state.get("queued_requests", 0) or 0)
                active_request = state.get("active_request")
                if active_request:
                    status_text += f" · Đang xử lý {active_request.get('tool', 'yêu cầu')}"
                if waiting:
                    status_text += f" · {waiting} yêu cầu đang chờ"
                remote_text = remote_agent.describe(state.get("remote_agent"))
                if remote_text:
                    status_text += f" · Server: {remote_text}"
                for key, row in self.pipe_labels.items():
                    row.set(*litebim_bridge.status(key, state.get(key)))
                self.status.set(status_text)
                self.remote_live.configure(text="Trạng thái: " + (remote_text or "đang tắt."))
            except (OSError, ValueError, KeyError):
                pass
        self.refresh_power()
        self.ticks = getattr(self, "ticks", 0) + 1
        if self.cadweb_row and self.cadweb_level == "busy" and self.ticks % 4 == 0:
            self.poll_cadweb()
        if self.ticks % 8 == 0:
            self.check_theme()
        self.after(500, self.tick)

    def close(self):
        self.closing = True
        self.stop()
        if self.tray:
            self.tray.close()
        self.destroy()


if __name__ == "__main__":
    try:
        from updater import migrate_beiming_rename

        migrate_beiming_rename(ROOT)
    except Exception:
        pass   # best-effort; nếu hỏng, launcher sẽ báo Beiming chưa cài và cho cài lại
    App().mainloop()
