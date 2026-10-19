"""Experimental multi-session Beiming launcher; isolated from launcher/."""
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
REPO = ROOT / "autocad-beiming-mcp-custom"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
PORT_BASE = 8800


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.15):
            return True
    except OSError:
        return False


def autocad_windows():
    script = "$ErrorActionPreference='SilentlyContinue'; Get-Process acad | ForEach-Object { '{0}|{1}' -f $_.Id,$_.MainWindowTitle }"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                            capture_output=True, text=True, timeout=5,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    rows = []
    for line in result.stdout.splitlines():
        pid, _, title = line.partition("|")
        if pid.strip().isdigit():
            rows.append((int(pid), title.strip() or "AutoCAD window not ready"))
    return rows


def kill_tree(process):
    if process and process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


class Session:
    def __init__(self, pid, title, port, process, log_file, runtime_dir):
        self.pid = pid
        self.title = title
        self.port = port
        self.process = process
        self.log_file = log_file
        self.runtime_dir = runtime_dir

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/mcp"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoCAD MCP Multi-Session — Experimental")
        self.geometry("820x580")
        self.minsize(700, 470)
        self.sessions = {}
        self.logs = {}
        self.events = queue.Queue()
        self.agent = tk.StringVar(value="OpenAI Codex")
        self.target = tk.StringVar()
        self.status = tk.StringVar(value="Thử nghiệm độc lập; launcher cũ không bị thay đổi")
        self.build()
        self.refresh_processes()
        self.after(400, self.tick)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def build(self):
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="AutoCAD MCP · Multi-Session thử nghiệm",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(root, text="Mỗi phiên MCP được ghim vào một PID AutoCAD và có IPC/output riêng. "
                  "Hãy kiểm tra kết nối trước khi giao việc cho agent.",
                  wraplength=760).pack(anchor="w", pady=(5, 14))
        row = ttk.Frame(root)
        row.pack(fill="x")
        self.process_box = ttk.Combobox(row, textvariable=self.target, state="readonly", width=60)
        self.process_box.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Làm mới AutoCAD", command=self.refresh_processes).pack(side="left", padx=6)
        ttk.Button(row, text="Mở MCP cho PID", command=self.start_session).pack(side="left")
        self.listing = tk.Listbox(root, height=7, exportselection=False)
        self.listing.pack(fill="x", pady=(13, 8))
        self.listing.bind("<<ListboxSelect>>", lambda _e: self.refresh_config())
        actions = ttk.Frame(root)
        actions.pack(fill="x")
        ttk.Button(actions, text="Test AutoCAD connection", command=self.probe).pack(side="left")
        ttk.Button(actions, text="Dừng phiên MCP đã chọn", command=self.stop_selected).pack(side="left", padx=8)
        ttk.Label(actions, text="Agent:").pack(side="left", padx=(14, 4))
        self.agent_box = ttk.Combobox(actions, textvariable=self.agent, state="readonly", width=18,
                                      values=("OpenAI Codex", "Claude Code", "Cursor", "Claude Desktop"))
        self.agent_box.pack(side="left")
        self.agent_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh_config())
        ttk.Button(actions, text="Sao chép cấu hình", command=self.copy_config).pack(side="right")
        self.config_box = tk.Text(root, height=7, wrap="none", font=("Consolas", 10))
        self.config_box.pack(fill="both", expand=True, pady=(10, 8))
        ttk.Label(root, textvariable=self.status, foreground="#225c53", wraplength=760).pack(anchor="w")

    def refresh_processes(self):
        try:
            items = autocad_windows()
            self.process_rows = items
            self.process_box["values"] = [f"PID {pid} · {title}" for pid, title in items]
            if items and not self.target.get():
                self.target.set(self.process_box["values"][0])
            if not items:
                self.target.set("")
                self.status.set("Không tìm thấy tiến trình acad.exe đang chạy")
        except Exception as exc:
            self.status.set(f"Không liệt kê được AutoCAD: {exc}")

    def selected_pid(self):
        index = self.process_box.current()
        if index < 0 or index >= len(self.process_rows):
            raise RuntimeError("Hãy chọn một cửa sổ AutoCAD")
        return self.process_rows[index]

    def start_session(self):
        try:
            pid, title = self.selected_pid()
            if pid in self.sessions:
                raise RuntimeError(f"PID {pid} đã có phiên MCP")
            if not PYTHON.is_file():
                raise RuntimeError(f"Thiếu môi trường Python của Beiming: {PYTHON}")
            port = next(p for p in range(PORT_BASE, PORT_BASE + 100)
                        if p not in {s.port for s in self.sessions.values()} and not listening(p))
            runtime = HERE / "runtime" / str(pid)
            ipc = runtime / "ipc"
            output = runtime / "output"
            ipc.mkdir(parents=True, exist_ok=True)
            output.mkdir(parents=True, exist_ok=True)
            dispatcher_wrapper = runtime / "mcp_dispatch_session.lsp"
            source_lisp = (REPO / "lisp-code" / "mcp_dispatch.lsp").resolve().as_posix()
            ipc_lisp = (ipc.resolve().as_posix().rstrip("/") + "/")
            dispatcher_wrapper.write_text(
                f'(load "{source_lisp}")\n'
                f'(setq *mcp-ipc-dir* "{ipc_lisp}")\n'
                '(princ "\\nMCP session IPC directory configured")\n',
                encoding="utf-8",
            )
            log_dir = HERE / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = (log_dir / f"beiming-{pid}.log").open("a", encoding="utf-8", buffering=1)
            env = os.environ.copy()
            env.update({
                "AUTOCAD_MCP_BACKEND": "file_ipc",
                "AUTOCAD_MCP_AUTOSTART": "false",
                "AUTOCAD_MCP_NATIVE_PLUGIN": "off",
                "AUTOCAD_MCP_ACAD_PID": str(pid),
                "AUTOCAD_MCP_IPC_DIR": str(ipc),
                "AUTOCAD_MCP_OUTPUT_ROOT": str(output),
                "AUTOCAD_MCP_LISP_PATH": str(dispatcher_wrapper),
                "AUTOCAD_MCP_READ_TIMEOUT": "600",
                "AUTOCAD_MCP_IPC_TIMEOUT": "300",
                "AUTOCAD_MCP_DOCUMENT_TIMEOUT": "120",
            })
            process = subprocess.Popen(
                [str(PYTHON), str(HERE / "serve_session.py"), str(REPO), str(port)],
                cwd=REPO, env=env, stdin=subprocess.DEVNULL,
                stdout=log_file, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.logs[pid] = log_file
            self.sessions[pid] = Session(pid, title, port, process, log_file, runtime)
            self.listing.insert("end", f"PID {pid} · :{port} · {title} · MCP starting")
            self.listing.selection_clear(0, "end")
            self.listing.selection_set("end")
            self.status.set(f"MCP process started for AutoCAD PID {pid}; connection is not yet verified")
            self.refresh_config()
        except Exception as exc:
            messagebox.showerror("Không thể mở phiên", str(exc))

    def selected_session(self):
        selection = self.listing.curselection()
        if not selection:
            raise RuntimeError("Hãy chọn phiên MCP")
        pid = list(self.sessions)[selection[0]]
        return self.sessions[pid]

    def probe(self):
        try:
            session = self.selected_session()
            if session.process.poll() is not None:
                raise RuntimeError("MCP đã dừng; xem log của phiên")
            self.status.set(f"Đang gọi system.ensure_ready cho PID {session.pid}…")
            threading.Thread(target=self._probe_worker, args=(session,), daemon=True).start()
        except Exception as exc:
            messagebox.showerror("Không thể kiểm tra", str(exc))

    def _probe_worker(self, session):
        try:
            for _ in range(100):
                if session.process.poll() is not None:
                    raise RuntimeError("MCP thoát khi khởi động; xem launcher_multi/logs")
                if listening(session.port):
                    break
                threading.Event().wait(0.1)
            else:
                raise RuntimeError(f"MCP chưa mở cổng {session.port}")
            result = subprocess.run(
                [str(PYTHON), str(HERE / "probe_session.py"), session.url],
                cwd=REPO, env={**os.environ, "PYTHONPATH": str(REPO / "src")},
                capture_output=True, text=True, timeout=240,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout)[-1800:])
            self.events.put(("probe", result.stdout[-2400:]))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def stop_selected(self):
        try:
            session = self.selected_session()
            kill_tree(session.process)
            session.log_file.close()
            self.sessions.pop(session.pid, None)
            self.logs.pop(session.pid, None)
            index = self.listing.curselection()[0]
            self.listing.delete(index)
            self.refresh_config()
            self.status.set(f"Đã dừng MCP PID {session.pid}; AutoCAD vẫn được giữ nguyên")
        except Exception as exc:
            messagebox.showerror("Không thể dừng", str(exc))

    def refresh_config(self):
        try:
            session = self.selected_session()
            name = f"autocad_beiming_{session.pid}"
            url = session.url
            agent = self.agent.get()
            if agent == "OpenAI Codex":
                config = f'[mcp_servers.{name}]\nurl = "{url}"'
            elif agent == "Claude Code":
                config = f"claude mcp add --transport http {name} {url}"
            elif agent == "Cursor":
                config = json.dumps({"mcpServers": {name: {"url": url}}}, indent=2)
            else:
                config = ("Claude Desktop cần stdio; launcher thử nghiệm hiện mới cung cấp "
                          "endpoint HTTP riêng cho từng phiên. Dùng Claude Code để thử.")
        except Exception:
            config = "Mở một MCP session rồi chọn dòng phiên để xem cấu hình agent."
        self.config_box.delete("1.0", "end")
        self.config_box.insert("1.0", config)

    def copy_config(self):
        self.refresh_config()
        self.clipboard_clear()
        self.clipboard_append(self.config_box.get("1.0", "end-1c"))
        self.status.set("Đã sao chép cấu hình cho phiên MCP đang chọn")

    def tick(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "probe":
                self.status.set("Kết quả ensure_ready: " + value[:350].replace("\n", " "))
                messagebox.showinfo("AutoCAD connection probe", value)
            else:
                self.status.set("Probe thất bại: " + value[:500])
                messagebox.showerror("AutoCAD connection probe thất bại", value)
        selected_pid = None
        selection = self.listing.curselection()
        rows = list(self.sessions.items())
        if selection and selection[0] < len(rows):
            selected_pid = rows[selection[0]][0]
        self.listing.delete(0, "end")
        for index, (pid, session) in enumerate(rows):
            state = "MCP running" if session.process.poll() is None else "MCP stopped (see log)"
            self.listing.insert("end", f"PID {pid} · :{session.port} · {session.title} · {state}")
            if pid == selected_pid:
                self.listing.selection_set(index)
        self.refresh_config()
        self.after(500, self.tick)

    def close(self):
        for session in list(self.sessions.values()):
            kill_tree(session.process)
            session.log_file.close()
        self.sessions.clear()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
