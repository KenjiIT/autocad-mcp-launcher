"""First-run dependency installer shown before the main launcher."""

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk


ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "launcher" / "logs"
REPOS = (
    ("autocad_puran", ROOT / "puran-water-autocad-mcp"),
    ("autocad_beiming", ROOT / "autocad-beiming-mcp-custom"),
)


def installed(repo):
    python = repo / ".venv" / "Scripts" / "python.exe"
    return python.is_file() and subprocess.run(
        [str(python), "-c", "import mcp, ezdxf, autocad_mcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    ).returncode == 0


def prepare():
    """Return True when both MCP environments are ready; show setup when needed."""
    missing = [(name, repo) for name, repo in REPOS if not installed(repo)]
    if not missing:
        return True

    root = tk.Tk()
    root.title("Cài đặt AutoCAD MCP")
    root.geometry("560x300")
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Chuẩn bị thư viện MCP", font=("Segoe UI", 17, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Chỉ cần cài ở lần chạy đầu hoặc khi thư viện bị thiếu.",
              wraplength=510).pack(anchor="w", pady=(5, 18))
    status = tk.StringVar(value="Đang kiểm tra mã nguồn…")
    ttk.Label(frame, textvariable=status, wraplength=510).pack(anchor="w")
    overall = ttk.Progressbar(frame, mode="determinate", maximum=len(missing), length=510)
    overall.pack(fill="x", pady=(12, 7))
    current = ttk.Progressbar(frame, mode="indeterminate", length=510)
    current.pack(fill="x")
    events = queue.Queue()
    result = {"ok": False}

    def worker():
        try:
            for index, (name, repo) in enumerate(missing, 1):
                if not (repo / "pyproject.toml").is_file():
                    raise RuntimeError(
                        f"Thiếu mã nguồn {name}. Bản Download ZIP của GitHub không chứa submodule. "
                        "Hãy giải nén dist/autocad-mcp-launcher-complete.zip và chạy app trong đó."
                    )
                events.put(("status", f"Đang cài {name} ({index}/{len(missing)})…"))
                python = repo / ".venv" / "Scripts" / "python.exe"
                if not python.is_file():
                    subprocess.run([sys.executable, "-m", "venv", str(repo / ".venv")],
                                   check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                log_path = LOG_DIR / f"{name}-install.log"
                with log_path.open("w", encoding="utf-8") as log:
                    process = subprocess.run(
                        [str(python), "-m", "pip", "install", "-e", str(repo)],
                        stdout=log, stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                if process.returncode:
                    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                    detail = next((line for line in reversed(lines) if line.startswith("ERROR:")),
                                  f"pip trả mã {process.returncode}")
                    raise RuntimeError(f"Không thể cài {name}: {detail}\nLog: {log_path}")
                if not installed(repo):
                    raise RuntimeError(f"Cài {name} xong nhưng không nạp được thư viện. Xem {log_path}")
                events.put(("progress", index))
            events.put(("done", None))
        except Exception as exc:
            events.put(("error", str(exc)))

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == "status":
                    status.set(value)
                elif kind == "progress":
                    overall.configure(value=value)
                elif kind == "done":
                    result["ok"] = True
                    current.stop()
                    root.destroy()
                    return
                elif kind == "error":
                    current.stop()
                    status.set(value)
                    root.protocol("WM_DELETE_WINDOW", root.destroy)
                    ttk.Button(frame, text="Đóng", command=root.destroy).pack(anchor="e", pady=(12, 0))
                    return
        except queue.Empty:
            pass
        root.after(100, poll)

    current.start(12)
    threading.Thread(target=worker, daemon=True).start()
    root.after(100, poll)
    root.mainloop()
    return result["ok"]
