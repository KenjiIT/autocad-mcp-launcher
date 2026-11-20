"""A manual edit of the drawing must advance the revision so the agent's next change is fenced."""

from __future__ import annotations

import pytest

from autocad_mcp.backends.file_ipc import FileIPCBackend


class FakeDocument:
    def __init__(self):
        self.vars = {"HANDSEED": "2A3F", "EXTMIN": (0.0, 0.0, 0.0), "EXTMAX": (100.0, 50.0, 0.0)}
        self.count = 10
        self.busy = False

        outer = self

        class ModelSpace:
            @property
            def Count(self):
                if outer.busy:
                    raise AttributeError("ModelSpace.Count")
                return outer.count

        self.ModelSpace = ModelSpace()

    def GetVariable(self, name):
        if self.busy:
            raise AttributeError(name)
        return self.vars[name]


@pytest.fixture
def backend():
    backend = FileIPCBackend()
    backend._session.bind_worker(process_id=1, hwnd=1)
    return backend


def context(backend, document):
    payload = backend._session.context(backend._session.bind_document("key", path="a.dwg", name="a.dwg"))
    backend._detect_external_change(document, payload)
    return payload


def test_unchanged_drawing_keeps_revision(backend):
    document = FakeDocument()
    first = context(backend, document)
    second = context(backend, document)
    assert second["revision"] == first["revision"] == 0
    assert "external_change" not in second


def test_added_entity_advances_revision(backend):
    document = FakeDocument()
    context(backend, document)
    document.count += 1
    document.vars["HANDSEED"] = "2A40"
    changed = context(backend, document)
    assert changed["revision"] == 1
    assert changed["external_change"] is True


def test_erase_and_extent_changes_are_detected(backend):
    document = FakeDocument()
    context(backend, document)
    document.count -= 1
    assert context(backend, document)["revision"] == 1
    document.vars["EXTMAX"] = (200.0, 50.0, 0.0)
    assert context(backend, document)["revision"] == 2


def test_busy_autocad_is_not_a_change(backend):
    document = FakeDocument()
    context(backend, document)
    document.busy = True
    assert context(backend, document)["revision"] == 0
    document.busy = False
    assert context(backend, document)["revision"] == 0


def test_own_mutation_is_not_counted_as_outside_edit(backend):
    document = FakeDocument()
    context(backend, document)
    document.count += 1  # the agent's own change
    backend.__dict__["_suppress_external_check"] = 1
    try:
        context(backend, document)  # baseline refresh during record_document_mutation
    finally:
        backend.__dict__["_suppress_external_check"] = 0
    assert context(backend, document)["revision"] == 0


def test_can_be_turned_off(backend, monkeypatch):
    monkeypatch.setenv("AUTOCAD_MCP_DETECT_EXTERNAL_CHANGES", "0")
    document = FakeDocument()
    context(backend, document)
    document.count += 5
    assert context(backend, document)["revision"] == 0
