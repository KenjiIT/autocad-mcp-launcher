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
import winreg
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import knowledge
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
    "beiming": ROOT / "autocad-beiming-mcp-custom",
}
NAMES = {"puran": "autocad_puran", "beiming": "autocad_beiming"}
UPDATE_REPO = "KenjiIT/autocad-mcp-launcher"
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


def config_for(agent):
    urls = {NAMES[key]: f"http://127.0.0.1:8764/{key}/mcp" for key in REPOS}
    if agent == "OpenAI Codex":
        return "\n\n".join(f'[mcp_servers.{name}]\nurl = "{url}"' for name, url in urls.items())
    if agent == "Claude Code":
        return "\n".join(f"claude mcp add --transport http {name} {url}" for name, url in urls.items())
    if agent == "Claude Desktop":
        python = str(python_in(REPOS["puran"]))
        bridge = str(ROOT / "launcher" / "stdio_bridge.py")
        return json.dumps({"mcpServers": {
            NAMES[key]: {"command": python, "args": [bridge, key]} for key in REPOS
        }}, indent=2)
    raise ValueError(agent)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoCAD MCP Launcher")
        self.geometry("760x590")
        self.minsize(650, 490)
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
        self.status = tk.StringVar(value="Sẵn sàng")
        self.build()
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
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        if "--start" in sys.argv[1:] or self.autostart_mcp_var.get():
            self.after(300, self.start)

    def build(self):
        pages = ttk.Notebook(self)
        pages.pack(fill="both", expand=True, padx=12, pady=12)
        main = ttk.Frame(pages, padding=18)
        settings_page = ttk.Frame(pages)
        settings = self.scrollable(settings_page)
        pages.add(main, text="Điều khiển")
        pages.add(settings_page, text="Cài đặt")
        self.build_settings(settings)
        ttk.Label(main, text="AutoCAD MCP", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(main, text=f"Phiên bản {app_version()}", foreground="#65736f").pack(anchor="w", pady=(0, 5))
        ttk.Label(main, text="Agent ưu tiên AutoCAD; nếu AutoCAD không chạy, agent sẽ hỏi trước khi dùng DXF.",
                  wraplength=690).pack(anchor="w", pady=(2, 18))
        self.start_btn = ttk.Button(main, text="▶  Bật kết nối cho agent", command=self.start)
        self.start_btn.pack(anchor="w")
        self.stop_btn = ttk.Button(main, text="■  Dừng", command=self.stop)
        self.stop_btn.pack(anchor="w", pady=(7, 14))
        self.labels = {}
        for key in REPOS:
            label = ttk.Label(main, text=f"○  {NAMES[key]}  ·  Chưa khởi chạy")
            label.pack(anchor="w", pady=3)
            self.labels[key] = label
        ttk.Label(main, textvariable=self.status, foreground="#225c53",
                  wraplength=690).pack(anchor="w", pady=(11, 16))
        row = ttk.Frame(main)
        row.pack(fill="x")
        ttk.Label(row, text="Agent:").pack(side="left")
        agents = ttk.Combobox(row, textvariable=self.agent, state="readonly", width=21,
                              values=("OpenAI Codex", "Claude Code", "Claude Desktop"))
        agents.pack(side="left", padx=10)
        agents.bind("<<ComboboxSelected>>", lambda _: self.refresh_config())
        ttk.Button(row, text="Sao chép cấu hình", command=self.copy).pack(side="right")
        self.hint = ttk.Label(main, wraplength=690, justify="left")
        self.hint.pack(fill="x", pady=(10, 7))
        self.config_box = tk.Text(main, height=9, wrap="none", font=("Consolas", 10),
                                  bg="#ffffff", fg="#1b2926", relief="flat", padx=12, pady=12)
        self.config_box.pack(fill="both", expand=True)

    def scrollable(self, page):
        """Return a padded frame inside ``page`` that scrolls when it grows taller than the window."""
        canvas = tk.Canvas(page, highlightthickness=0, borderwidth=0)
        bar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas, padding=24)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))

        def wheel(event):
            if isinstance(event.widget, tk.Listbox):
                return
            if inner.winfo_reqheight() > canvas.winfo_height():
                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

        canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))
        return inner

    def build_settings(self, frame):
        ttk.Label(frame, text="Cài đặt", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Tùy chỉnh cách AutoCAD MCP Launcher hoạt động trên máy này.",
                  wraplength=650).pack(anchor="w", pady=(6, 22))
        ttk.Checkbutton(frame, text="Khởi động AutoCAD MCP Launcher cùng Windows",
                        variable=self.startup_var,
                        command=self.save_startup_setting).pack(anchor="w")
        ttk.Label(frame,
                  text="Khi bật, launcher sẽ mở sau khi bạn đăng nhập Windows. Bạn có thể tắt lựa chọn này bất cứ lúc nào.",
                  foreground="#65736f", wraplength=650, justify="left").pack(anchor="w", padx=(24, 0), pady=(6, 12))
        ttk.Checkbutton(frame, text="Tự bật MCP khi mở launcher",
                        variable=self.autostart_mcp_var,
                        command=self.save_autostart_mcp_setting).pack(anchor="w", pady=(4, 0))
        ttk.Label(frame,
                  text="Khi bật, gateway MCP tự chạy ngay khi launcher mở, không cần bấm Bắt đầu. AutoCAD vẫn chỉ được kết nối khi agent gọi tool.",
                  foreground="#65736f", wraplength=650, justify="left").pack(anchor="w", padx=(24, 0), pady=(6, 12))
        self.settings_status = ttk.Label(frame, text="")
        self.settings_status.pack(anchor="w", padx=(24, 0))
        ttk.Separator(frame).pack(fill="x", pady=12)
        ttk.Label(frame, text="Tri thức AutoCAD", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(frame,
                  text="Tải các trang tri thức công khai (cách đọc mặt bằng kết cấu, kiến trúc) về máy. Chỉ tải về, không tải lên gì; tệp trùng tên sẽ được thay bằng bản mới.",
                  foreground="#65736f", wraplength=650, justify="left").pack(anchor="w", pady=(5, 6))
        self.knowledge_dir_var = tk.StringVar(value=self.knowledge_dir())
        knowledge_row = ttk.Frame(frame)
        knowledge_row.pack(fill="x")
        ttk.Entry(knowledge_row, textvariable=self.knowledge_dir_var, state="readonly").pack(
            side="left", fill="x", expand=True)
        ttk.Button(knowledge_row, text="Đổi thư mục…", command=self.choose_knowledge_dir).pack(side="left", padx=(6, 0))
        self.knowledge_btn = ttk.Button(knowledge_row, text="Tải tri thức", command=self.download_knowledge)
        self.knowledge_btn.pack(side="left", padx=(6, 0))
        self.knowledge_status = ttk.Label(frame, text="")
        self.knowledge_status.pack(anchor="w", pady=(6, 0))
        ttk.Separator(frame).pack(fill="x", pady=12)
        ttk.Label(frame, text="Thư viện block", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(frame,
                  text="Nơi lưu các block dựng sẵn (nội thất, cây cối, thiết bị vệ sinh) dạng .dwg hoặc .dxf. Agent chèn chúng bằng tên file; đơn vị mỗi file phải là mm. Quy ước đặt tên có trong README.md của thư mục.",
                  foreground="#65736f", wraplength=650, justify="left").pack(anchor="w", pady=(5, 6))
        library_row = ttk.Frame(frame)
        library_row.pack(fill="x")
        self.block_library_var = tk.StringVar(value=str(block_library_dir()))
        ttk.Entry(library_row, textvariable=self.block_library_var, state="readonly").pack(
            side="left", fill="x", expand=True)
        ttk.Button(library_row, text="Mở thư mục thư viện", command=self.open_block_library).pack(
            side="left", padx=(6, 0))
        self.block_library_status = ttk.Label(frame, text=self.block_library_summary())
        self.block_library_status.pack(anchor="w", pady=(6, 0))
        ttk.Separator(frame).pack(fill="x", pady=12)
        ttk.Label(frame, text="Cài skill cho agent", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(frame,
                  text="Chọn agent và các skill AutoCAD muốn cài hoặc cập nhật. Skill được chép vào thư mục dùng chung của tài khoản Windows.",
                  foreground="#65736f", wraplength=650, justify="left").pack(anchor="w", pady=(5, 10))
        self.skill_agent = tk.StringVar(value="OpenAI Codex")
        self.skill_agents = {
            "OpenAI Codex": Path.home() / ".codex" / "skills",
            "Claude Code": Path.home() / ".claude" / "skills",
            CLAUDE_DESKTOP: Path.home() / "AutoCAD-MCP-Skills-Claude-Desktop",
        }
        ttk.Combobox(frame, textvariable=self.skill_agent, state="readonly", width=24,
                     values=tuple(self.skill_agents)).pack(anchor="w", pady=(0, 8))
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
                                      foreground="#225c53")
        self.skill_status.pack(anchor="w", pady=(8, 0))

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
            self.skill_status.configure(text="Hãy chọn ít nhất một skill.", foreground="#9a5b00")
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
                foreground="#a12622")
            return
        try:
            target_root.mkdir(parents=True, exist_ok=True)
            for name in selected:
                source = source_root / name
                target = target_root / name
                if not (source / "SKILL.md").is_file():
                    raise FileNotFoundError(f"Không tìm thấy nội dung skill: {source}")
                shutil.copytree(source, target, dirs_exist_ok=True)
            self.skill_status.configure(
                text=f"Đã cài / cập nhật {len(selected)} skill cho {self.skill_agent.get()} tại {target_root}.",
                foreground="#225c53")
        except OSError as exc:
            self.skill_status.configure(text=f"Không cài được skill: {exc}", foreground="#a12622")

    def package_skills_for_claude_desktop(self, selected, target_dir):
        """Claude Desktop keeps its own skill store and only accepts uploaded zips."""
        try:
            build_skill_zips(SKILLS_SOURCE, selected, target_dir)
            os.startfile(str(target_dir))
        except OSError as exc:
            self.skill_status.configure(text=f"Không tạo được file zip: {exc}", foreground="#a12622")
            return
        self.skill_status.configure(
            text=f"Đã tạo {len(selected)} file zip tại {target_dir}. Trong Claude Desktop: Customize, Skills, "
                 "tải từng file lên (xem HUONG-DAN.txt).",
            foreground="#225c53")

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

    @staticmethod
    def knowledge_dir():
        saved = load_settings().get("knowledge_dir")
        return saved if isinstance(saved, str) and saved else str(Path.home() / "autocad-knowledge")

    @staticmethod
    def block_library_summary():
        folder = block_library_dir()
        try:
            count = sum(1 for path in folder.iterdir() if path.suffix.lower() in (".dwg", ".dxf"))
        except OSError:
            return "Thư mục chưa có; sẽ được tạo khi bạn mở."
        return f"Hiện có {count} tệp block (.dwg/.dxf)."

    def open_block_library(self):
        folder = block_library_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except OSError as exc:
            self.block_library_status.configure(text=f"Không mở được thư mục: {exc}", foreground="#a12622")
            return
        self.block_library_status.configure(text=self.block_library_summary(), foreground="#225c53")

    def choose_knowledge_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.knowledge_dir_var.get(), parent=self,
                                         title="Chọn thư mục lưu tri thức")
        if not chosen:
            return
        chosen = str(Path(chosen))
        try:
            save_setting("knowledge_dir", chosen)
        except OSError as exc:
            self.knowledge_status.configure(text=f"Không lưu được thư mục: {exc}", foreground="#a12622")
            return
        self.knowledge_dir_var.set(chosen)

    def download_knowledge(self):
        destination = self.knowledge_dir_var.get()
        self.knowledge_btn.configure(state="disabled")
        self.knowledge_status.configure(text="Đang tải…", foreground="#225c53")

        def worker():
            try:
                written = knowledge.download_knowledge(destination)
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                message, color = f"Không tải được tri thức: {exc}", "#a12622"
            else:
                message, color = f"Đã tải {len(written)} trang vào {destination}.", "#225c53"
            self.after(0, lambda: self.finish_knowledge_download(message, color))

        threading.Thread(target=worker, daemon=True).start()

    def finish_knowledge_download(self, message, color):
        self.knowledge_btn.configure(state="normal")
        self.knowledge_status.configure(text=message, foreground=color)

    def refresh_config(self):
        hints = {
            "OpenAI Codex": "Gộp hai mục vào %USERPROFILE%\\.codex\\config.toml rồi mở lại Codex.",
            "Claude Code": "Chạy hai lệnh trong terminal của project cần dùng.",
            "Claude Desktop": "Gộp mcpServers vào %APPDATA%\\Claude\\claude_desktop_config.json rồi thoát hẳn và mở lại Claude Desktop. Launcher phải tiếp tục chạy.",
        }
        self.hint.configure(text=hints[self.agent.get()])
        self.config_box.delete("1.0", "end")
        self.config_box.insert("1.0", config_for(self.agent.get()))

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

    def start(self):
        if self.updating or self.busy or (self.gateway and self.gateway.poll() is None):
            return
        self.busy = True
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
            self.labels[key].configure(text=f"○  {NAMES[key]}  ·  Chưa khởi chạy")
        self.status.set("Đã dừng gateway và MCP đang hoạt động")

    def check_for_updates(self):
        if self.closing or self.updating:
            return

        def worker():
            try:
                from updater import find_update

                update = find_update(UPDATE_REPO, app_version())
                if update:
                    self.events.put(("update_available", update))
            except Exception:
                # Update checks are best-effort; offline use should stay quiet.
                pass

        threading.Thread(target=worker, daemon=True).start()

    def offer_update(self, update):
        self.pending_update = update
        notes = (update.get("notes") or "Không có ghi chú phát hành.").strip()
        if len(notes) > 1800:
            notes = notes[:1800].rstrip() + "…"
        message = (
            f"Đang dùng: v{app_version()}\n"
            f"Bản mới: v{update['version']}\n\n"
            f"{notes}\n\n"
            "Cập nhật sẽ khởi động lại launcher và kết nối MCP. "
            "Bạn có muốn cập nhật ngay không?"
        )
        if messagebox.askyesno("Có bản cập nhật AutoCAD MCP Launcher", message, parent=self):
            self.begin_update(update)

    def begin_update(self, update):
        if self.updating:
            return
        self.updating = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.status.set(f"Đang tải bản cập nhật v{update['version']}…")

        def worker():
            try:
                from updater import download_release

                archive = download_release(
                    update,
                    lambda received, total: self.events.put(
                        ("update_progress", received, total)
                    ),
                )
                self.events.put(("update_downloaded", str(archive)))
            except Exception as exc:
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
                    proceed = messagebox.askyesno(
                        "Đang chờ MCP",
                        "MCP vẫn đang xử lý yêu cầu sau 10 phút. Tiếp tục chờ?\n"
                        "Chọn Không để dừng cập nhật và giữ launcher đang chạy.",
                        parent=self,
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
        self.update_archive = Path(archive)
        self.update_wait_started = time.monotonic()
        self.status.set("Đã tải và xác minh gói cập nhật.")
        self.wait_for_idle_then_apply()

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
                    messagebox.showerror("Không thể khởi động", value)
                elif kind == "ready":
                    self.busy = False
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="normal")
                elif kind == "update_available":
                    self.offer_update(value)
                elif kind == "update_progress":
                    received, total = event[1], event[2]
                    if total:
                        self.status.set(f"Đang tải bản cập nhật… {received * 100 // total}%")
                    else:
                        self.status.set(f"Đang tải bản cập nhật… {received // (1024 * 1024)} MB")
                elif kind == "update_downloaded":
                    self.finish_update_download(value)
                elif kind == "update_failed":
                    self.updating = False
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="normal")
                    self.status.set("Không tải được bản cập nhật; launcher vẫn đang chạy.")
                    messagebox.showerror("Cập nhật thất bại", value, parent=self)
        except queue.Empty:
            pass
        if self.gateway and self.gateway.poll() is None and not self.busy:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8764/status", timeout=0.3) as response:
                    state = json.load(response)
                active = state["active"]
                offline = state.get("mode") == "ezdxf"
                for key in REPOS:
                    label = ("●  " if key == active else "○  ") + NAMES[key]
                    label += ("  ·  DXF offline" if offline else "  ·  Đã kết nối AutoCAD") if key == active else "  ·  Chưa khởi chạy"
                    self.labels[key].configure(text=label)
                status_text = state.get("error") or state["state"]
                waiting = int(state.get("queued_requests", 0) or 0)
                active_request = state.get("active_request")
                if active_request:
                    status_text += f" · Đang xử lý {active_request.get('tool', 'yêu cầu')}"
                if waiting:
                    status_text += f" · {waiting} yêu cầu đang chờ"
                self.status.set(status_text)
            except (OSError, ValueError, KeyError):
                pass
        self.after(500, self.tick)

    def close(self):
        self.closing = True
        self.stop()
        if self.tray:
            self.tray.close()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
