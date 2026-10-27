"""Download the public AutoCAD knowledge pages into a local folder.

Only files under ``wiki/`` of the knowledge repository are written, existing
files with the same name are replaced, and nothing in the folder is deleted.
Nothing is ever uploaded.
"""
import io
import urllib.request
import zipfile
from pathlib import PurePosixPath, Path

KNOWLEDGE_ZIP_URL = "https://github.com/KenjiIT/autocad-knowledge/archive/refs/heads/main.zip"
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_FILE_BYTES = 5 * 1024 * 1024


def fetch_archive(url=KNOWLEDGE_ZIP_URL, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "autocad-mcp-launcher"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("Gói tri thức lớn bất thường, đã dừng.")
    return data


def extract_wiki(archive, destination):
    """Write the ``wiki/`` pages from a GitHub zip into ``destination``.

    Returns the relative paths written.  Entries that are absolute, climb out
    of the folder, or are too large are rejected.
    """
    destination = Path(destination).resolve()
    written = []
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for info in bundle.infolist():
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            # GitHub wraps the repository in one top-level folder.
            if len(parts) < 3 or parts[1] != "wiki":
                continue
            relative = PurePosixPath(*parts[1:])
            if relative.is_absolute() or ".." in relative.parts or ":" in relative.as_posix():
                raise ValueError(f"Đường dẫn không hợp lệ trong gói: {info.filename}")
            if info.file_size > MAX_FILE_BYTES:
                raise ValueError(f"Tệp quá lớn: {info.filename}")
            target = (destination / Path(*relative.parts)).resolve()
            if destination not in target.parents:
                raise ValueError(f"Đường dẫn ra ngoài thư mục đích: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(info))
            written.append(relative.as_posix())
    if not written:
        raise ValueError("Gói tri thức không có trang nào trong wiki/.")
    return written


def download_knowledge(destination, url=KNOWLEDGE_ZIP_URL):
    return extract_wiki(fetch_archive(url), destination)
