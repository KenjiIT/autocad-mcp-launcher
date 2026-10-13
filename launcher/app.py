"""Windows desktop controller for the exclusive AutoCAD MCP gateway."""
import json
import queue
import socket
import subprocess
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

from tray import TrayIcon

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "launcher" / "logs"
REPOS = {
    "puran": ROOT / "puran-water-autocad-mcp",
    "beiming": ROOT / "beiming183-cloud-AutoCAD-MCP",
}
NAMES = {"puran": "autocad_puran", "beiming": "autocad_beiming"}


def python_in(repo):
    return repo / ".venv" / "Scripts" / "python.exe"


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


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
    if agent == "Cursor":
        return json.dumps({"mcpServers": {name: {"url": url} for name, url in urls.items()}}, indent=2)
    if agent == "Claude Desktop":
        python = str(python_in(REPOS["puran"]))
        bridge = str(ROOT / "launcher" / "stdio_bridge.py")
        return json.dumps({"mcpServers": {
            NAMES[key]: {"command": python, "args": [bridge, key]} for key in REPOS
        }}, indent=2)
    if agent == "ChatGPT (web)":
        return ("ChatGPT chạy trên cloud, nên không truy cập được 127.0.0.1.\n"
                "Cần tunnel an toàn hoặc HTTPS public đến gateway trước khi thêm custom MCP server.")
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
        self.agent = tk.StringVar(value="OpenAI Codex")
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
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        if "--start" in sys.argv[1:]:
            self.after(300, self.start)

    def build(self):
        main = ttk.Frame(self, padding=22)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="AutoCAD MCP", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(main, text="Agent tự chọn MCP · app ngắt kết nối cũ trước khi chuyển").pack(
            anchor="w", pady=(2, 18))
        self.start_btn = ttk.Button(main, text="▶  Bật kết nối cho agent", command=self.start)
        self.start_btn.pack(anchor="w")
        self.stop_btn = ttk.Button(main, text="■  Dừng", command=self.stop)
        self.stop_btn.pack(anchor="w", pady=(7, 14))
        self.labels = {}
        for key in REPOS:
            label = ttk.Label(main, text=f"○  {NAMES[key]}  ·  Chưa kết nối AutoCAD")
            label.pack(anchor="w", pady=3)
            self.labels[key] = label
        ttk.Label(main, textvariable=self.status, foreground="#225c53",
                  wraplength=690).pack(anchor="w", pady=(11, 16))
        row = ttk.Frame(main)
        row.pack(fill="x")
        ttk.Label(row, text="Agent:").pack(side="left")
        agents = ttk.Combobox(row, textvariable=self.agent, state="readonly", width=21,
                              values=("OpenAI Codex", "Claude Code", "Cursor",
                                      "Claude Desktop", "ChatGPT (web)"))
        agents.pack(side="left", padx=10)
        agents.bind("<<ComboboxSelected>>", lambda _: self.refresh_config())
        ttk.Button(row, text="Sao chép cấu hình", command=self.copy).pack(side="right")
        self.hint = ttk.Label(main, wraplength=690, justify="left")
        self.hint.pack(fill="x", pady=(10, 7))
        self.config_box = tk.Text(main, height=13, wrap="none", font=("Consolas", 10),
                                  bg="#ffffff", fg="#1b2926", relief="flat", padx=12, pady=12)
        self.config_box.pack(fill="both", expand=True)

    def refresh_config(self):
        hints = {
            "OpenAI Codex": "Gộp hai mục vào %USERPROFILE%\\.codex\\config.toml rồi mở lại Codex.",
            "Claude Code": "Chạy hai lệnh trong terminal của project cần dùng.",
            "Cursor": "Gộp mcpServers vào %USERPROFILE%\\.cursor\\mcp.json rồi mở lại Cursor.",
            "Claude Desktop": "Gộp mcpServers vào %APPDATA%\\Claude\\claude_desktop_config.json rồi mở lại Claude Desktop. App phải tiếp tục chạy.",
            "ChatGPT (web)": "ChatGPT cần endpoint HTTPS ngoài máy; gateway local không truy cập được từ cloud.",
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
        if self.busy or (self.gateway and self.gateway.poll() is None):
            return
        self.busy = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.status.set("Đang chuẩn bị môi trường Python…")
        threading.Thread(target=self.start_worker, daemon=True).start()

    def start_worker(self):
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            for key, repo in REPOS.items():
                if self.closing:
                    return
                python = python_in(repo)
                installed = python.is_file() and subprocess.run(
                    [str(python), "-c", "import mcp, ezdxf, autocad_mcp"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW).returncode == 0
                if not installed:
                    self.events.put(("status", f"Đang cài thư viện cho {NAMES[key]}…"))
                    if not python.is_file():
                        subprocess.run([sys.executable, "-m", "venv", str(repo / ".venv")],
                                       check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    with (LOG_DIR / f"{NAMES[key]}-install.log").open(
                            "w", encoding="utf-8") as log:
                        subprocess.run([str(python), "-m", "pip", "install", "-e", str(repo)],
                                       check=True, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            if self.closing:
                return
            if listening(8764):
                raise RuntimeError("Cổng 8764 đã được chương trình khác sử dụng")
            self.log = (LOG_DIR / "gateway.log").open("a", encoding="utf-8", buffering=1)
            self.gateway = subprocess.Popen(
                [str(python_in(REPOS["puran"])), str(ROOT / "launcher" / "gateway.py")],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(100):
                if self.gateway.poll() is not None:
                    raise RuntimeError("Gateway thoát khi khởi động; xem launcher/logs/gateway.log")
                if listening(8764):
                    break
                threading.Event().wait(0.1)
            else:
                raise RuntimeError("Gateway chưa mở cổng 8764")
            self.events.put(("status", "Đang kết nối autocad_beiming với AutoCAD…"))
            request = urllib.request.Request(
                "http://127.0.0.1:8764/beiming/select", method="POST")
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    state = json.load(response)
            except urllib.error.HTTPError as exc:
                try:
                    detail = json.load(exc).get("error", str(exc))
                except (ValueError, OSError):
                    detail = str(exc)
                raise RuntimeError(f"Không thể kết nối autocad_beiming: {detail}") from exc
            if state.get("active") != "beiming":
                raise RuntimeError("Gateway chưa kích hoạt autocad_beiming")
            self.events.put(("status", "autocad_beiming đã kết nối AutoCAD. Agent có thể chuyển MCP khi gọi tool."))
        except Exception as exc:
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
            self.labels[key].configure(text=f"○  {NAMES[key]}  ·  Chưa kết nối AutoCAD")
        self.status.set("Đã dừng gateway và MCP đang hoạt động")

    def tick(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.status.set(value)
                elif kind == "error":
                    self.status.set(value)
                    messagebox.showerror("Không thể khởi động", value)
                elif kind == "ready":
                    self.busy = False
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="normal")
        except queue.Empty:
            pass
        if self.gateway and self.gateway.poll() is None and not self.busy:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8764/status", timeout=0.3) as response:
                    state = json.load(response)
                active = state["active"]
                for key in REPOS:
                    label = ("●  " if key == active else "○  ") + NAMES[key]
                    label += "  ·  Đã kết nối AutoCAD" if key == active else "  ·  Chưa kết nối AutoCAD"
                    self.labels[key].configure(text=label)
                self.status.set(state.get("error") or state["state"])
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
