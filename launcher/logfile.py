"""Size-capped log files for the launcher, the gateway and the MCP servers.

A child process writes to a pipe; a thread copies its lines into a ``RotatingLog``
so a long-running gateway cannot grow one file without limit.  When the file
passes ``max_bytes`` it becomes ``name.log.1`` (older ones shift up to ``keep``).
"""
import subprocess
import threading
from datetime import datetime
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
KEEP = 3


class RotatingLog:
    def __init__(self, path, max_bytes=MAX_BYTES, keep=KEEP):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.keep = keep
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._file = None
        self._size = 0
        self._open()

    def _open(self):
        self._file = self.path.open("a", encoding="utf-8", errors="replace", buffering=1)
        self._size = self.path.stat().st_size

    def _rotate(self):
        self._file.close()
        for index in range(self.keep, 0, -1):
            source = self.path if index == 1 else self.path.with_name(f"{self.path.name}.{index - 1}")
            target = self.path.with_name(f"{self.path.name}.{index}")
            if source.exists():
                try:
                    target.unlink(missing_ok=True)
                    source.rename(target)
                except OSError:
                    pass  # another process holds it; keep appending rather than lose lines
        self._open()

    def write_line(self, text):
        with self._lock:
            if self._file is None:
                return
            line = text if text.endswith("\n") else text + "\n"
            if self._size + len(line) > self.max_bytes:
                self._rotate()
            self._file.write(line)
            self._size += len(line.encode("utf-8", errors="replace"))

    def banner(self, title):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.write_line(f"===== {stamp} | {title} =====")

    def close(self):
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None


def start_logged(command, log, **kwargs):
    """Popen ``command`` with stdout and stderr copied into ``log`` line by line."""
    process = subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)
    log.banner(f"pid {process.pid} started")

    def pump():
        for raw in iter(process.stdout.readline, b""):
            log.write_line(raw.decode("utf-8", errors="replace").rstrip("\r\n"))
        log.banner(f"pid {process.pid} exited with code {process.wait()}")

    threading.Thread(target=pump, daemon=True).start()
    return process
