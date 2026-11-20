"""Optional: start CAD Studio local (cad-web-local) alongside the launcher gateway.

cad-web-local is a separate Node.js project (a small web chat UI + its own gateway) that calls
this launcher's MCP gateway directly at 127.0.0.1:8764 — no login, no remote-machine pairing,
everything on this one machine. It lives in its own repo, as a sibling folder of this launcher's
own repo root (``cad-web-local/`` next to ``mcp/``); most installs of this launcher will not have
it, so every check here is best-effort and the launcher must keep working fine without it.

Release packages instead ship a prebuilt copy in ``cadweb/`` inside the launcher folder (web already
built, gateway bundled into one ``server.mjs``, plus a portable ``node.exe``): no Node.js or npm
install needed. One process serves both the web and its API on GATEWAY_PORT. A developer clone
next to ``mcp/`` still wins, so editing cad-web-local keeps using the Vite dev servers.
"""
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

from logfile import RotatingLog, start_logged

GATEWAY_PORT = 8788
WEB_PORT = 5174   # cổng Vite ưu tiên; nếu bận, Vite tự chuyển cổng khác và ta đọc cổng thật từ log

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_URL_RE = re.compile(r"http://localhost:(\d+)")


def dev_dir(root):
    """``cad-web-local/`` next to ``root`` (the launcher's own repo root), or None if not present."""
    candidate = root.parent / "cad-web-local"
    return candidate if (candidate / "package.json").is_file() else None


def packaged_dir(root):
    """Prebuilt copy shipped inside the release package, or None."""
    candidate = root / "cadweb"
    return candidate if (candidate / "gateway" / "server.mjs").is_file() else None


def project_dir(root):
    return dev_dir(root) or packaged_dir(root)


def node_exe(packaged):
    bundled = packaged / "node" / "node.exe"
    return str(bundled) if bundled.is_file() else shutil.which("node")


def npm_cmd():
    return shutil.which("npm.cmd") or shutil.which("npm")


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def _kill(process):
    if process and process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


class CadWebLocal:
    """Spawns the gateway (Node) and web (Vite) dev servers as two child processes, same pattern
    as the main AutoCAD gateway (``start_logged`` + a size-capped log file; stopped with taskkill)."""

    def __init__(self, root, log_dir):
        self.dir = dev_dir(root)
        self.packaged = None if self.dir else packaged_dir(root)
        self.state_dir = root / "launcher" / "state" / "cadweb"
        self.log_dir = log_dir
        self.gateway_proc = None
        self.web_proc = None
        self.gateway_log = None
        self.web_log = None
        self.web_port = None   # cổng Vite THẬT SỰ dùng; biết được sau khi đọc log (xem wait_web)

    def running(self):
        if self.packaged:
            return bool(self.gateway_proc and self.gateway_proc.poll() is None)
        return bool(self.gateway_proc and self.gateway_proc.poll() is None
                    and self.web_proc and self.web_proc.poll() is None)

    def start(self):
        """Best-effort start of both dev servers. Raises RuntimeError with a message fit for the UI."""
        if self.running():
            return
        if self.packaged:
            return self._start_packaged()
        if not self.dir:
            raise RuntimeError("Không thấy thư mục cad-web-local cạnh mcp/.")
        npm = npm_cmd()
        if not npm:
            raise RuntimeError("Không tìm thấy npm trên máy (cần Node.js để chạy CAD Studio local).")
        if not (self.dir / "node_modules").is_dir():
            raise RuntimeError(f"cad-web-local chưa cài thư viện. Mở PowerShell tại {self.dir} và chạy: npm install")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        if not (self.gateway_proc and self.gateway_proc.poll() is None):
            self.gateway_log = RotatingLog(self.log_dir / "cadweb-local-gateway.log")
            self.gateway_proc = start_logged([npm, "run", "dev:gateway"], self.gateway_log, cwd=self.dir)
        if not (self.web_proc and self.web_proc.poll() is None):
            self.web_port = None
            self.web_log = RotatingLog(self.log_dir / "cadweb-local-web.log")
            self.web_proc = start_logged([npm, "run", "dev:web"], self.web_log, cwd=self.dir)

    def _start_packaged(self):
        node = node_exe(self.packaged)
        if not node:
            raise RuntimeError("Gói cài thiếu cadweb/node/node.exe; hãy cài lại launcher.")
        if listening(GATEWAY_PORT):
            raise RuntimeError(f"Cổng {GATEWAY_PORT} đang bị chương trình khác giữ.")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        (self.state_dir / "data").mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "PORT": str(GATEWAY_PORT), "WEB_DIR": str(self.packaged / "web"),
               # Hội thoại và cấu hình nằm ở launcher/state: bản cập nhật không ghi đè thư mục này.
               "CAD_DATA_DIR": str(self.state_dir / "data") + os.sep,
               "CAD_CONFIG_FILE": str(self.state_dir / "config.json"),
               "CORS_ORIGIN": f"http://localhost:{GATEWAY_PORT},http://127.0.0.1:{GATEWAY_PORT}"}
        self.gateway_log = RotatingLog(self.log_dir / "cadweb-local-gateway.log")
        self.gateway_proc = start_logged([node, str(self.packaged / "gateway" / "server.mjs")],
                                         self.gateway_log, cwd=self.packaged, env=env)

    def wait_web(self, timeout=20.0):
        """Chờ Vite báo cổng thật của nó qua log rồi lưu vào self.web_port (trả None nếu hết giờ).

        Vite tự chuyển sang cổng khác nếu WEB_PORT đang bận (nhiều lượt chạy thử/rớt tiến trình cũ
        có thể chiếm 5174, 5175…), nên phải đọc đúng dòng "Local: http://localhost:<cổng>/" trong
        log của CHÍNH tiến trình đang chạy, không đoán theo WEB_PORT.
        """
        if self.web_port:
            return self.web_port
        if self.packaged:
            deadline = time.time() + timeout
            while time.time() < deadline and self.running():
                if listening(GATEWAY_PORT):
                    self.web_port = GATEWAY_PORT
                    return self.web_port
                time.sleep(0.3)
            return None
        if not self.web_proc:
            return None
        log_path = self.log_dir / "cadweb-local-web.log"
        marker = f"pid {self.web_proc.pid} started"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            start = text.rfind(marker)
            tail = text[start:] if start >= 0 else text
            match = _URL_RE.search(_ANSI_RE.sub("", tail))
            if match:
                self.web_port = int(match.group(1))
                return self.web_port
            time.sleep(0.3)
        return None

    def stop(self):
        _kill(self.gateway_proc); self.gateway_proc = None
        _kill(self.web_proc); self.web_proc = None
        self.web_port = None
        if self.gateway_log:
            self.gateway_log.close(); self.gateway_log = None
        if self.web_log:
            self.web_log.close(); self.web_log = None
