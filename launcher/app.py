"""Windows desktop controller for the exclusive AutoCAD MCP gateway."""
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

from tray import TrayIcon

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "launcher" / "logs"
REPOS = {
    "puran": ROOT / "puran-water-autocad-mcp",
    "beiming": ROOT / "autocad-beiming-mcp-custom",
}
NAMES = {"puran": "autocad_puran", "beiming": "autocad_beiming"}
UPDATE_REPO = "KenjiIT/autocad-mcp-launcher"


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
        return ("ChatGPT chạy trên cloud nên không truy cập được 127.0.0.1.\n"
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
        self.updating = False
        self.update_archive = None
        self.update_wait_started = None
        self.update_busy_notice_shown = False
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
        self.after(1600, self.check_for_updates)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        if "--start" in sys.argv[1:]:
            self.after(300, self.start)

    def build(self):
        main = ttk.Frame(self, padding=22)
        main.pack(fill="both", expand=True)
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
                              values=("OpenAI Codex", "Claude Code", "Cursor",
                                      "Claude Desktop", "ChatGPT (web)"))
        agents.pack(side="left", padx=10)
        agents.bind("<<ComboboxSelected>>", lambda _: self.refresh_config())
        ttk.Button(row, text="Sao chép cấu hình", command=self.copy).pack(side="right")
        self.hint = ttk.Label(main, wraplength=690, justify="left")
        self.hint.pack(fill="x", pady=(10, 7))
        self.config_box = tk.Text(main, height=9, wrap="none", font=("Consolas", 10),
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
                raise RuntimeError("Cổng 8764 đã được chương trình khác sử dụng")
            self.log = (LOG_DIR / "gateway.log").open("a", encoding="utf-8", buffering=1)
            command = [str(python_in(REPOS["puran"])), str(ROOT / "launcher" / "gateway.py")]
            self.gateway = subprocess.Popen(
                command,
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
