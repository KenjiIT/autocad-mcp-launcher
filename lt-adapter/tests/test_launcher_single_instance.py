"""A second launcher start must not open another window, even before the tray exists."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CODE = (
    "import sys; sys.path.insert(0, sys.argv[1]);"
    "import tray; print(tray.acquire_single_instance(), flush=True);"
    "sys.stdin.readline()"
)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows named mutex")
def test_second_process_is_refused_until_first_exits():
    first = subprocess.Popen([sys.executable, "-c", CODE, str(ROOT / "launcher")],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert first.stdout.readline().strip() == "True"
        second = subprocess.run([sys.executable, "-c", "import sys; sys.stdin=None;" + CODE.replace("sys.stdin.readline()", "pass"),
                                 str(ROOT / "launcher")], capture_output=True, text=True, timeout=30)
        assert second.stdout.strip() == "False", second.stderr
    finally:
        first.stdin.write("\n")
        first.stdin.flush()
        first.wait(timeout=10)
    third = subprocess.run([sys.executable, "-c", CODE.replace("sys.stdin.readline()", "pass"), str(ROOT / "launcher")],
                           capture_output=True, text=True, timeout=30)
    assert third.stdout.strip() == "True", third.stderr
