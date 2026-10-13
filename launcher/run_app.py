"""Start the windowed app and preserve startup errors when no console is shown."""

import traceback
from pathlib import Path


try:
    from app import App

    App().mainloop()
except Exception:
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "startup.log").open("w", encoding="utf-8") as log:
        traceback.print_exc(file=log)
    raise
