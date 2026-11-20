"""A dimension made through COM must honour DIMSCALE, the layer and the text override."""

from __future__ import annotations

from autocad_mcp.backends.file_ipc import FileIPCBackend


class FakeDocument:
    def __init__(self, dimscale):
        self.dimscale = dimscale

    def GetVariable(self, name):
        assert name == "DIMSCALE"
        return self.dimscale


class FakeDimension:
    def __init__(self, scale=1.0, fail_layer=False):
        self.ScaleFactor = scale
        self.Layer = "0"
        self.TextOverride = ""
        self._fail_layer = fail_layer

    def __setattr__(self, name, value):
        if name == "Layer" and getattr(self, "_fail_layer", False):
            raise RuntimeError("layer missing")
        object.__setattr__(self, name, value)


def test_dimscale_copied_onto_new_dimension():
    dimension = FakeDimension()
    FileIPCBackend._finish_dimension(FakeDocument(100.0), dimension, None, None)
    assert dimension.ScaleFactor == 100.0


def test_layer_and_text_applied():
    dimension = FakeDimension()
    FileIPCBackend._finish_dimension(FakeDocument(1.0), dimension, "250x10=2500", "A-DIM")
    assert dimension.Layer == "A-DIM"
    assert dimension.TextOverride == "250x10=2500"


def test_default_layer_failure_is_ignored_but_scale_still_applied():
    dimension = FakeDimension(fail_layer=True)
    FileIPCBackend._finish_dimension(FakeDocument(50.0), dimension, None, None)
    assert dimension.ScaleFactor == 50.0


def test_unreadable_dimscale_leaves_dimension_alone():
    class Busy:
        def GetVariable(self, name):
            raise AttributeError(name)

    dimension = FakeDimension()
    FileIPCBackend._finish_dimension(Busy(), dimension, None, "A-DIM")
    assert dimension.ScaleFactor == 1.0
    assert dimension.Layer == "A-DIM"
