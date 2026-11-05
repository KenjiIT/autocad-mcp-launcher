"""Download the shared-knowledge pages from the latest tagged release of the public knowledge repository.

Only a release that a reviewer deliberately tagged (``vX.Y.Z``) is installed, never the tip of ``main``.
Each check asks GitHub for ``releases/latest`` with an ETag (an unchanged answer is a free ``304``),
verifies the SHA-256 of ``autocad-knowledge-wiki.zip``, validates every entry, and only then replaces
the managed pages under ``<knowledge folder>/wiki``.  Pages that the new release no longer contains are
removed, so a retracted page disappears from every machine.  ``proposals/`` and
``sensitive-terms.local.txt`` next to ``wiki/`` are never touched.  Nothing is ever uploaded.
"""
import hashlib
import io
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REPOSITORY = "KenjiIT/autocad-knowledge"
ASSET = "autocad-knowledge-wiki.zip"
API_ROOT = "https://api.github.com/repos"
USER_AGENT = "autocad-mcp-launcher-knowledge"
CHECK_INTERVAL = 24 * 3600
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_FILE_BYTES = 5 * 1024 * 1024
VERSION_FILE = ".version"
MANAGED_SUFFIXES = {".md", ".txt"}


class KnowledgeError(RuntimeError):
    pass


def version_key(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value).strip(), re.IGNORECASE)
    return tuple(int(part) for part in match.groups()) if match else None


def read_version(destination):
    """The installed release marker, or None when nothing was installed from a release."""
    try:
        data = json.loads((Path(destination) / "wiki" / VERSION_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("tag") else None


def cache_path(repository=REPOSITORY):
    root = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    return root / "AutoCADMcpLauncher" / "knowledge" / (re.sub(r"[^A-Za-z0-9._-]", "_", repository) + "-release.json")


def latest_release(repository=REPOSITORY, opener=urllib.request.urlopen, cache_file=None):
    """The latest published release (JSON), or None when the repository has none."""
    cache_file = Path(cache_file) if cache_file else cache_path(repository)
    cached = None
    try:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": USER_AGENT}
    if cached and cached.get("etag"):
        headers["If-None-Match"] = str(cached["etag"])
    request = urllib.request.Request(f"{API_ROOT}/{repository}/releases/latest", headers=headers)
    try:
        with opener(request, timeout=8) as response:
            release = json.loads(response.read().decode("utf-8"))
            etag = response.headers.get("ETag")
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and cached:
            return cached.get("release")
        if exc.code == 404:
            return None
        if exc.code in (403, 429) and cached:  # rate limited: keep the last known answer
            return cached.get("release")
        raise
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"etag": etag, "release": release}), encoding="utf-8")
    except OSError:
        pass
    return release


def find_release(release):
    """Pick the knowledge asset and its checksum out of a release; raise KnowledgeError if unusable."""
    tag = str(release.get("tag_name", ""))
    if version_key(tag) is None:
        raise KnowledgeError(f"Tên tag không hợp lệ: {tag!r}")
    assets = release.get("assets", [])
    asset = next((a for a in assets if a.get("name") == ASSET), None)
    if not asset or not asset.get("browser_download_url"):
        raise KnowledgeError(f"Bản phát hành {tag} thiếu tệp {ASSET}.")
    digest = str(asset.get("digest") or "")
    checksum = next((a for a in assets if a.get("name") == ASSET + ".sha256"), None)
    if not digest.startswith("sha256:") and not (checksum and checksum.get("browser_download_url")):
        raise KnowledgeError(f"Bản phát hành {tag} chưa công bố SHA-256.")
    size = int(asset.get("size") or 0)
    if size <= 0 or size > MAX_ARCHIVE_BYTES:
        raise KnowledgeError("Kích thước gói tri thức không hợp lệ.")
    return {"tag": tag, "url": str(asset["browser_download_url"]), "size": size,
            "sha256": digest.removeprefix("sha256:").lower(),
            "checksum_url": str(checksum["browser_download_url"]) if checksum else None,
            "notes": str(release.get("body") or "").strip()}


def download(info, opener=urllib.request.urlopen):
    """Download the asset and verify its size and SHA-256 before returning the bytes."""
    request = urllib.request.Request(info["url"], headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"})
    with opener(request, timeout=30) as response:
        data = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise KnowledgeError("Gói tri thức lớn bất thường, đã dừng.")
    if len(data) != info["size"]:
        raise KnowledgeError(f"Tệp tải về thiếu dữ liệu ({len(data)}/{info['size']} byte).")
    expected = info.get("sha256")
    if not expected and info.get("checksum_url"):
        checksum_request = urllib.request.Request(info["checksum_url"], headers={"User-Agent": USER_AGENT})
        with opener(checksum_request, timeout=15) as response:
            text = response.read(4096).decode("ascii", errors="replace")
        found = re.search(r"\b([a-fA-F0-9]{64})\b", text)
        if not found:
            raise KnowledgeError("Không đọc được SHA-256 trong tệp checksum.")
        expected = found.group(1)
    actual = hashlib.sha256(data).hexdigest()
    if actual.lower() != str(expected).lower():
        raise KnowledgeError("SHA-256 của gói tri thức không khớp với bản phát hành.")
    return data


def _entries(archive):
    """Validate every entry first; returns {relative path under wiki/: bytes}. Nothing is written here."""
    entries = {}
    try:
        bundle = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise KnowledgeError(f"Gói tri thức không phải tệp zip hợp lệ: {exc}") from exc
    with bundle:
        for info in bundle.infolist():
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            if len(parts) < 2 or parts[0] != "wiki":
                continue
            relative = PurePosixPath(*parts[1:])
            if relative.is_absolute() or ".." in relative.parts or ":" in relative.as_posix() or relative.name == VERSION_FILE:
                raise KnowledgeError(f"Đường dẫn không hợp lệ trong gói: {info.filename}")
            if info.file_size > MAX_FILE_BYTES:
                raise KnowledgeError(f"Tệp quá lớn: {info.filename}")
            entries[relative.as_posix()] = bundle.read(info)
    if "index.md" not in entries:
        raise KnowledgeError("Gói tri thức không có wiki/index.md.")
    return entries


def install(archive, destination, info):
    """Replace the managed pages with the release contents; returns the written relative paths."""
    entries = _entries(archive)
    destination = Path(destination).resolve()
    wiki = destination / "wiki"
    for relative, data in entries.items():
        target = (wiki / Path(*relative.split("/"))).resolve()
        if wiki not in target.parents:
            raise KnowledgeError(f"Đường dẫn ra ngoài thư mục đích: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for stale in sorted(wiki.rglob("*"), reverse=True):  # pages the release no longer contains
        if stale.is_file() and stale.suffix.lower() in MANAGED_SUFFIXES and stale.relative_to(wiki).as_posix() not in entries:
            stale.unlink()
        elif stale.is_dir() and not any(stale.iterdir()):
            stale.rmdir()
    marker = {"tag": info["tag"], "sha256": hashlib.sha256(archive).hexdigest(), "downloaded_at": int(time.time()),
              "pages": len(entries) - 1}
    (wiki / VERSION_FILE).write_text(json.dumps(marker), encoding="utf-8")
    return sorted(entries)


def check(destination, last_check=None, force=False, now=None, opener=urllib.request.urlopen, cache_file=None):
    """Bring the knowledge folder up to date. Never raises; returns a status dict.

    ``state`` is one of: updated, current, skipped (checked less than a day ago), unavailable (no release
    published), error.  ``checked`` is True when GitHub was contacted.  ``force`` ignores the 24 hour wait and
    reinstalls even the same tag (the manual button).
    """
    now = time.time() if now is None else now
    installed = read_version(destination)
    present = (Path(destination) / "wiki" / "index.md").is_file()
    if not force and present and installed and last_check and now - last_check < CHECK_INTERVAL:
        return {"state": "skipped", "checked": False, "tag": installed["tag"],
                "message": f"Tri thức {installed['tag']}; kiểm tra lần sau sau 24 giờ."}
    try:
        release = latest_release(opener=opener, cache_file=cache_file)
        if release is None:
            return {"state": "unavailable", "checked": True, "tag": installed["tag"] if installed else None,
                    "message": "Chưa có bản phát hành tri thức nào được đóng tag."}
        info = find_release(release)
        latest, current = version_key(info["tag"]), version_key(installed["tag"]) if installed else None
        if not force and present and installed and (info["tag"] == installed["tag"] or (latest and current and latest <= current)):
            return {"state": "current", "checked": True, "tag": installed["tag"],
                    "message": f"Tri thức {installed['tag']} là bản mới nhất."}
        files = install(download(info, opener), destination, info)
    except urllib.error.HTTPError as exc:
        return {"state": "error", "checked": False, "tag": installed["tag"] if installed else None,
                "message": f"GitHub trả lỗi {exc.code}."}
    except (OSError, ValueError, KnowledgeError, zipfile.BadZipFile) as exc:
        return {"state": "error", "checked": False, "tag": installed["tag"] if installed else None,
                "message": f"Không cập nhật được tri thức: {exc}"}
    return {"state": "updated", "checked": True, "tag": info["tag"], "files": len(files) - 1,
            "message": f"Đã tải tri thức {info['tag']} ({len(files) - 1} trang)."}
