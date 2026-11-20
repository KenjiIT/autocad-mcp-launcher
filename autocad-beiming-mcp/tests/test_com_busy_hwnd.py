"""A busy AutoCAD must not be reported as "COM application has no HWND for expected PID".

With late-bound pywin32, a call AutoCAD rejects while busy (RPC_E_CALL_REJECTED) during the property-name
lookup becomes AttributeError, so ``getattr(app, "HWND", 0)`` read 0 on a healthy instance. That produced a
false E_AUTOCAD_INSTANCE_UNVERIFIED after a few drawing commands, and the window-message fallback then failed.
"""

from __future__ import annotations

import pytest

import autocad_mcp.backends.file_ipc as file_ipc
from autocad_mcp.backends.file_ipc import FileIPCBackend


class FlakyApplication:
    """Application whose HWND property is rejected (AttributeError, as pywin32 reports it) `busy_reads` times."""

    def __init__(self, hwnd=4242, busy_reads=0):
        self._hwnd = hwnd
        self.busy_reads = busy_reads
        self.reads = 0
        self.sent = []

        outer = self

        class Document:
            def SendCommand(self, command):
                outer.sent.append(command)

        self.ActiveDocument = Document()

    @property
    def HWND(self):
        self.reads += 1
        if self.reads <= self.busy_reads:
            raise AttributeError("AutoCAD.Application.HWND")
        return self._hwnd


@pytest.fixture
def backend(monkeypatch):
    backend = FileIPCBackend()
    backend._acad_process_id = 456
    backend._hwnd = 4242
    monkeypatch.setattr(backend._com_executor, "cooperative_sleep", lambda seconds: None)  # nhanh
    monkeypatch.setattr(file_ipc, "_window_process_id", lambda hwnd: 456)
    return backend


def bind(monkeypatch, application):
    import win32com.client

    monkeypatch.setattr(win32com.client, "GetActiveObject", lambda name: application)


def test_a_few_rejected_reads_do_not_look_like_a_missing_hwnd(backend, monkeypatch):
    application = FlakyApplication(busy_reads=3)
    bind(monkeypatch, application)
    assert backend._get_autocad_application() is application
    assert application.reads == 4


def test_a_healthy_application_is_read_once(backend, monkeypatch):
    application = FlakyApplication()
    bind(monkeypatch, application)
    assert backend._get_autocad_application() is application
    assert application.reads == 1


def test_a_genuinely_missing_hwnd_still_fails_after_the_retries(backend, monkeypatch):
    application = FlakyApplication(busy_reads=10 ** 6)
    bind(monkeypatch, application)
    with pytest.raises(RuntimeError) as caught:
        backend._get_autocad_application()
    assert "E_AUTOCAD_INSTANCE_UNVERIFIED" in str(caught.value) and "busy" in str(caught.value)
    assert application.reads == file_ipc._HWND_READ_ATTEMPTS


def test_the_wrong_process_is_still_refused(backend, monkeypatch):
    monkeypatch.setattr(file_ipc, "_window_process_id", lambda hwnd: 999)
    bind(monkeypatch, FlakyApplication())
    with pytest.raises(RuntimeError, match="E_AUTOCAD_INSTANCE_MISMATCH"):
        backend._get_autocad_application()


def test_the_com_command_path_waits_out_a_busy_autocad(backend, monkeypatch):
    # Hơn số lần thử của một lần đọc, để buộc vòng gửi lệnh cũng phải thử lại.
    application = FlakyApplication(busy_reads=file_ipc._HWND_READ_ATTEMPTS + 2)
    bind(monkeypatch, application)
    assert backend._send_command_via_com("(c:demo)") is True
    assert application.sent == ["(c:demo)\n"]


def test_the_com_command_path_gives_up_so_the_fallback_can_run(backend, monkeypatch):
    application = FlakyApplication(busy_reads=10 ** 6)
    bind(monkeypatch, application)
    ticks = iter(range(0, 10 ** 6))
    monkeypatch.setattr(file_ipc.time, "time", lambda: float(next(ticks)))  # hạn 5 giây trôi nhanh
    assert backend._send_command_via_com("(c:demo)") is False
    assert application.sent == []
