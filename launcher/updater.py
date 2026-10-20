"""Check and safely apply public GitHub Releases for the desktop launcher."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath


API_ROOT = "https://api.github.com/repos"
ASSET_NAME = "autocad-mcp-launcher-complete.zip"
USER_AGENT = "AutoCAD-MCP-Launcher-Updater"
MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
MAX_EXPANDED_BYTES = 1024 * 1024 * 1024
PRESERVED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "logs", "output", ".local-data"}


class UpdateError(RuntimeError):
    pass


def version_key(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value).strip(), re.IGNORECASE)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _release_cache_path(repository: str) -> Path:
    cache_root = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    safe_repo = re.sub(r"[^A-Za-z0-9._-]", "_", repository)
    return cache_root / "AutoCADMcpLauncher" / "updates" / f"{safe_repo}-release.json"


def _latest_release(repository: str) -> dict | None:
    cache_path = _release_cache_path(repository)
    cached = None
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    if cached and cached.get("etag"):
        headers["If-None-Match"] = str(cached["etag"])
    request = urllib.request.Request(
        f"{API_ROOT}/{repository}/releases/latest", headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            release = json.loads(response.read().decode("utf-8"))
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps({"etag": response.headers.get("ETag"), "release": release}),
                encoding="utf-8",
            )
            os.replace(temporary, cache_path)
            return release
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and cached:
            return cached.get("release")
        if exc.code == 404:
            return None
        if exc.code in (403, 429) and cached:
            return cached.get("release")
        raise


def find_update(repository: str, installed_version: str) -> dict | None:
    """Return the newest published release when it is newer than installed."""
    installed = version_key(installed_version)
    if installed is None:
        return None
    # Public repos without releases and private repos both return 404 to this
    # unauthenticated client; the app therefore remains usable in either case.
    release = _latest_release(repository)
    if not release:
        return None
    latest_tag = str(release.get("tag_name", ""))
    latest = version_key(latest_tag)
    if not latest or latest <= installed:
        return None
    asset = next(
        (item for item in release.get("assets", []) if item.get("name") == ASSET_NAME),
        None,
    )
    if not asset or not asset.get("browser_download_url"):
        raise UpdateError(f"Release {latest_tag} thiếu tệp {ASSET_NAME}.")
    digest = str(asset.get("digest") or "")
    checksum_asset = next(
        (item for item in release.get("assets", []) if item.get("name") == ASSET_NAME + ".sha256"),
        None,
    )
    if not digest.startswith("sha256:") and not (checksum_asset and checksum_asset.get("browser_download_url")):
        raise UpdateError(f"Release {latest_tag} chưa công bố SHA-256 cho gói cập nhật.")
    size = int(asset.get("size") or 0)
    if size <= 0 or size > MAX_ARCHIVE_BYTES:
        raise UpdateError("Kích thước gói cập nhật không hợp lệ hoặc vượt giới hạn 250 MB.")
    return {
        "version": latest_tag.removeprefix("v"),
        "tag": latest_tag,
        "notes": str(release.get("body") or "").strip(),
        "url": str(asset["browser_download_url"]),
        "size": size,
        "sha256": digest.removeprefix("sha256:").lower(),
        "checksum_url": str(checksum_asset.get("browser_download_url")) if checksum_asset else None,
    }


def download_release(release: dict, progress=None) -> Path:
    """Download and hash-check one release asset before touching installation."""
    cache_root = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    cache_dir = cache_root / "AutoCADMcpLauncher" / "updates"
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_tag = re.sub(r"[^A-Za-z0-9._-]", "_", str(release["tag"]))
    archive = cache_dir / f"{safe_tag}.zip"
    request = urllib.request.Request(
        release["url"], headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"}
    )
    digest = hashlib.sha256()
    received = 0
    expected_size = int(release["size"])
    try:
        with urllib.request.urlopen(request, timeout=30) as response, archive.open("wb") as output:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > MAX_ARCHIVE_BYTES:
                    raise UpdateError("Gói cập nhật vượt giới hạn 250 MB.")
                digest.update(chunk)
                output.write(chunk)
                if progress:
                    progress(received, expected_size)
        if received != expected_size:
            raise UpdateError(f"Tệp tải về thiếu dữ liệu ({received}/{expected_size} byte).")
        expected_hash = release.get("sha256")
        if not expected_hash and release.get("checksum_url"):
            checksum_request = urllib.request.Request(
                release["checksum_url"], headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(checksum_request, timeout=15) as checksum_response:
                checksum_text = checksum_response.read(4096).decode("ascii", errors="replace")
            match = re.search(r"\b([a-fA-F0-9]{64})\b", checksum_text)
            if not match:
                raise UpdateError("Không đọc được SHA-256 trong tệp checksum của Release.")
            expected_hash = match.group(1)
        if digest.hexdigest().lower() != str(expected_hash).lower():
            raise UpdateError("SHA-256 của gói tải về không khớp với GitHub Release.")
        return archive
    except Exception:
        archive.unlink(missing_ok=True)
        raise


def _safe_extract(archive: Path, destination: Path) -> Path:
    package_root = destination / "autocad-mcp-launcher"
    total_size = 0
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            relative = PurePosixPath(member.filename)
            if "\\" in member.filename or relative.is_absolute() or not relative.parts or ".." in relative.parts:
                raise UpdateError("Gói cập nhật chứa đường dẫn không an toàn.")
            if relative.parts[0] != "autocad-mcp-launcher":
                raise UpdateError("Gói cập nhật không đúng cấu trúc AutoCAD MCP Launcher.")
            if member.is_dir():
                continue
            if member.external_attr >> 16 & 0o170000 == 0o120000:
                raise UpdateError("Gói cập nhật chứa symlink không được hỗ trợ.")
            total_size += member.file_size
            if total_size > MAX_EXPANDED_BYTES:
                raise UpdateError("Gói giải nén vượt giới hạn 1 GB.")
            target = destination.joinpath(*relative.parts)
            resolved = target.resolve()
            if not resolved.is_relative_to(destination.resolve()):
                raise UpdateError("Gói cập nhật chứa đường dẫn thoát khỏi thư mục tạm.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as input_file, target.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
    if not (package_root / "launcher" / "run_app.py").is_file():
        raise UpdateError("Gói tải về không có launcher/run_app.py.")
    if not (package_root / "VERSION").is_file():
        raise UpdateError("Gói tải về không có VERSION.")
    return package_root


def apply_archive(archive: Path, root: Path, expected_version: str) -> None:
    """Overlay the portable package, preserving virtualenvs, logs, and outputs."""
    work = Path(tempfile.mkdtemp(prefix="autocad-mcp-update-"))
    staging = work / "staging"
    backup_root = work / "backup"
    changed: list[tuple[Path, Path | None]] = []
    try:
        package = _safe_extract(archive, staging)
        packaged_version = (package / "VERSION").read_text(encoding="utf-8").strip()
        if version_key(packaged_version) != version_key(expected_version):
            raise UpdateError(
                f"Phiên bản trong gói ({packaged_version}) khác với Release ({expected_version})."
            )
        for source in sorted(path for path in package.rglob("*") if path.is_file()):
            relative = source.relative_to(package)
            if any(part in PRESERVED_PARTS for part in relative.parts):
                continue
            target = root / relative
            cursor = root
            for part in relative.parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    raise UpdateError(f"Không cập nhật qua đường dẫn symlink: {relative}")
            if not target.resolve().is_relative_to(root.resolve()):
                raise UpdateError(f"Đường dẫn cập nhật nằm ngoài thư mục cài đặt: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and not target.is_file():
                raise UpdateError(f"Không thể cập nhật vì đường dẫn đang là thư mục: {relative}")
            backup = None
            if target.is_file():
                backup = backup_root / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            temp_target = target.with_name(target.name + ".update-tmp")
            shutil.copy2(source, temp_target)
            os.replace(temp_target, target)
            changed.append((target, backup))
    except Exception:
        for target, backup in reversed(changed):
            if backup and backup.is_file():
                rollback = target.with_name(target.name + ".rollback-tmp")
                shutil.copy2(backup, rollback)
                os.replace(rollback, target)
            else:
                target.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def refresh_mcp_environments(root: Path) -> None:
    """Reconcile editable MCP installs with the updated project metadata."""
    for name, relative in (
        ("autocad_puran", "puran-water-autocad-mcp"),
        ("autocad_beiming", "autocad-beiming-mcp-custom"),
    ):
        project = root / relative
        python = project / ".venv" / "Scripts" / "python.exe"
        if not python.is_file() or not (project / "pyproject.toml").is_file():
            continue
        log_dir = root / "launcher" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{name}-update-install.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [str(python), "-m", "pip", "install", "-e", str(project)],
                cwd=project,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=900,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        if result.returncode:
            raise UpdateError(f"Không thể cập nhật thư viện {name}. Xem log: {log_path}")


def wait_for_process(pid: int, timeout: float = 90.0) -> None:
    """Wait for the launcher window to exit before replacing its files."""
    if os.name != "nt":
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except OSError:
                return
            time.sleep(0.25)
        raise UpdateError("Launcher vẫn đang mở; không thể thay file an toàn.")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not handle:
        return
    try:
        result = kernel32.WaitForSingleObject(handle, int(timeout * 1000))
        if result != 0:
            raise UpdateError("Hết thời gian chờ launcher đóng để cập nhật.")
    finally:
        kernel32.CloseHandle(handle)


def show_message(title: str, message: str, error=False) -> None:
    if os.name == "nt":
        style = 0x10 if error else 0x40
        ctypes.windll.user32.MessageBoxW(None, message, title, style)
    else:
        print(f"{title}: {message}", file=sys.stderr if error else sys.stdout)


def apply_and_restart(args) -> int:
    root = Path(args.root).resolve()
    archive = Path(args.archive).resolve()
    try:
        wait_for_process(args.parent_pid)
    except Exception as exc:
        show_message("Không thể đóng launcher để cập nhật", str(exc), error=True)
        return 1
    try:
        apply_archive(archive, root, args.version)
        archive.unlink(missing_ok=True)
        try:
            refresh_mcp_environments(root)
        except Exception as exc:
            show_message(
                "Launcher đã cập nhật",
                f"Đã cập nhật file phiên bản {args.version}, nhưng chưa đồng bộ được thư viện MCP.\n\n{exc}",
                error=True,
            )
        else:
            show_message("AutoCAD MCP Launcher", f"Đã cập nhật lên phiên bản {args.version}.")
    except Exception as exc:
        show_message("Không thể cập nhật launcher", str(exc), error=True)
    try:
        script = root / "launcher" / "run_app.py"
        subprocess.Popen(
            [args.python, str(script), *(["--start"] if args.start else [])],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        show_message("Không thể mở lại launcher", str(exc), error=True)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--python")
    parser.add_argument("--version")
    parser.add_argument("--start", action="store_true")
    args = parser.parse_args()
    if not args.apply or not all((args.archive, args.root, args.parent_pid, args.python, args.version)):
        parser.error("--apply requires --archive, --root, --parent-pid, --python, and --version")
    return apply_and_restart(args)


if __name__ == "__main__":
    raise SystemExit(main())
