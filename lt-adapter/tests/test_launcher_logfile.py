import importlib.util
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "logfile", Path(__file__).resolve().parents[2] / "launcher" / "logfile.py")
logfile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(logfile)


def test_rotates_and_keeps_limited_history(tmp_path):
    log = logfile.RotatingLog(tmp_path / "a.log", max_bytes=100, keep=2)
    for index in range(30):
        log.write_line(f"line {index:02d} " + "x" * 20)
    log.close()
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["a.log", "a.log.1", "a.log.2"]
    assert all(p.stat().st_size <= 100 for p in tmp_path.iterdir())
    assert "line 29" in (tmp_path / "a.log").read_text()


def test_appends_to_existing_file_and_ignores_writes_after_close(tmp_path):
    path = tmp_path / "b.log"
    path.write_text("old\n")
    log = logfile.RotatingLog(path)
    log.banner("hello")
    log.close()
    log.write_line("late")
    text = path.read_text()
    assert text.startswith("old\n") and "hello" in text and "late" not in text


def test_start_logged_copies_output_and_exit_banner(tmp_path):
    log = logfile.RotatingLog(tmp_path / "c.log")
    process = logfile.start_logged([sys.executable, "-c", "print('hi'); import sys; sys.exit(3)"], log)
    process.wait(timeout=20)
    for _ in range(50):
        if "exited with code 3" in (tmp_path / "c.log").read_text():
            break
        import time
        time.sleep(0.1)
    log.close()
    text = (tmp_path / "c.log").read_text()
    assert "hi" in text and "exited with code 3" in text and "started" in text
