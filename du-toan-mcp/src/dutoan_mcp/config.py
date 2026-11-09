import os
from pathlib import Path


class Settings:
    APP_TITLE = "Dự Toán MCP"
    # src/dutoan_mcp/config.py -> src/dutoan_mcp -> src -> du-toan-mcp
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE_DIR / "data"

    _db_override = os.environ.get("DUTOAN_DB_PATH")
    if _db_override:
        DATABASE_URL = f"sqlite:///{_db_override}"
    else:
        DATABASE_URL = f"sqlite:///{DATA_DIR / 'dutoan.db'}"

    # Folder of the source MDB files, only needed by scripts/migrate_mdb.py.
    MDB_DATA_DIR = Path(os.environ.get("DUTOAN_MDB_DIR", "Dulieu"))


settings = Settings()
