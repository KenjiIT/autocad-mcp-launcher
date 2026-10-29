import pytest

from autocad_mcp.backends.base import CommandResult
from lt_adapter.lt_file_ipc import LtFileIPCBackend


@pytest.mark.asyncio
async def test_lt_unimplemented_tool_fails_without_com():
    backend = LtFileIPCBackend()
    try:
        result = await backend.drawing_create("unused.dwg")
        assert result.ok is False
        assert result.error_code == "E_NOT_SUPPORTED_ON_LT"
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_hatch_requires_explicit_handle():
    backend = LtFileIPCBackend()
    try:
        result = await backend.create_hatch("last")
        assert result.ok is False
        assert result.error_code == "E_PARAMETER_REJECTED"
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_hatch_accepts_padded_numeric_handle():
    backend = LtFileIPCBackend()
    calls = []

    async def dispatch(command, params):
        calls.append((command, params))
        return CommandResult(ok=True, payload={"handle": "B1"})

    backend._dispatch = dispatch
    try:
        result = await backend.create_hatch(" 400", "SOLID")
        assert result.ok is True
        assert calls == [("create-hatch-lt", {
            "entity_id": "400", "pattern": "SOLID", "angle": 0.0, "scale": 1.0, "layer": None,
        })]
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize("colour, sent", [
    ("255, 250, 205", "255,250,205"),
    ("#FFFACD", "255,250,205"),
    (51, "51"),
])
async def test_layer_colour_accepts_true_color(colour, sent):
    backend = LtFileIPCBackend()
    calls = []

    async def dispatch(command, params):
        calls.append((command, params))
        if command == "layer-exists-lt":
            return CommandResult(ok=True, payload={"exists": True})
        return CommandResult(ok=True, payload={"name": "H-CAM"})

    backend._dispatch = dispatch
    try:
        result = await backend.layer_set_properties("H-CAM", colour)
        assert result.ok is True
        assert calls[-1] == ("layer-set-properties", {
            "name": "H-CAM", "color": sent, "linetype": None, "lineweight": None,
        })
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize("colour", ["256,0,0", "1,2", "#FFF", "orange"])
async def test_layer_colour_rejects_bad_true_color(colour):
    backend = LtFileIPCBackend()
    try:
        result = await backend.layer_set_properties("H-CAM", colour)
        assert result.ok is False
        assert result.error_code == "E_PARAMETER_REJECTED"
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_entity_creation_and_readback_skip_python_com():
    backend = LtFileIPCBackend()
    calls = []

    async def dispatch(command, params):
        calls.append((command, params))
        if command == "create-line":
            return CommandResult(ok=True, payload={"handle": "A1"})
        return CommandResult(ok=True, payload={"handle": "A1", "type": "LINE"})

    backend._dispatch = dispatch
    backend._get_autocad_application = lambda: (_ for _ in ()).throw(AssertionError("COM must not be used"))
    try:
        created = await backend.create_line(0, 0, 10, 5, "A-WALL")
        read = await backend.entity_get("A1")
        assert created.payload["renderer"] == "autolisp"
        assert read.payload["type"] == "LINE"
        assert [command for command, _ in calls] == ["create-line", "entity-get"]
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", sorted(LtFileIPCBackend._UNSUPPORTED))
async def test_unimplemented_com_operations_fail_immediately(method):
    backend = LtFileIPCBackend()
    try:
        result = await getattr(backend, method)()
        assert result.ok is False
        assert result.error_code == "E_NOT_SUPPORTED_ON_LT"
        assert result.recoverable is False
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_variable_update_uses_validated_lisp_dispatch():
    backend = LtFileIPCBackend()
    seen = {}

    async def dispatch(command, params):
        seen.update(command=command, params=params)
        return CommandResult(ok=True, payload={"updated": {"INSUNITS": 4}})

    backend._dispatch = dispatch
    try:
        result = await backend.drawing_set_variables({"$insunits": "4"})
        assert result.ok is True
        assert seen["command"] == "drawing-set-variables-lt"
        assert seen["params"]["updates_str"] == "INSUNITS=4"
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_layer_update_validates_handles_before_dispatch():
    backend = LtFileIPCBackend()
    seen = []

    async def dispatch(command, params):
        seen.append((command, params))
        return CommandResult(ok=True, payload={"changed": 1})

    async def exists(name):
        return CommandResult(ok=True, payload={"exists": name == "A-WALL"})

    backend._dispatch = dispatch
    backend.layer_exists = exists
    try:
        result = await backend.entity_set_layer(["A1"], "A-WALL")
        assert result.ok is True
        assert seen[0][0] == "entity-set-layer-lt"
        assert seen[0][1]["handles_str"] == "A1"
        invalid = await backend.entity_set_layer(["bad handle"], "A-WALL")
        assert invalid.error_code == "E_PARAMETER_REJECTED"
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_line_file_accepts_lines_and_rejects_other_entities(tmp_path):
    backend = LtFileIPCBackend()
    source = tmp_path / "lines.json"
    source.write_text('[{"type":"line","layer":"A-WALL","x1":0,"y1":0,"x2":10,"y2":5}]', encoding="utf-8")
    seen = {}

    async def dispatch(command, params):
        seen.update(command=command, params=params)
        return CommandResult(ok=True, payload={"created": 1})

    backend._dispatch = dispatch
    try:
        result = await backend.entity_create_lines_file(source)
        assert result.ok is True
        assert seen["command"] == "entity-create-lines-lt"
        assert seen["params"]["lines_str"] == "0,0,10,5,A-WALL"
        source.write_text('[{"type":"CIRCLE","layer":"A-WALL"}]', encoding="utf-8")
        rejected = await backend.entity_create_lines_file(source)
        assert rejected.error_code == "E_PARAMETER_REJECTED"
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_layer_erase_refuses_layer_zero_without_dispatch():
    backend = LtFileIPCBackend()
    try:
        result = await backend.entity_erase_layers(["0"])
        assert result.error_code == "E_PARAMETER_REJECTED"
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_block_definition_rejects_unsupported_types():
    backend = LtFileIPCBackend()
    try:
        result = await backend.block_define("B1", [{"type": "ARC"}])
        assert result.ok is False
        assert result.error_code == "E_PARAMETER_REJECTED"
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_hatch_verification_uses_independent_lisp_probes_without_com():
    backend = LtFileIPCBackend()
    calls = []

    async def dispatch(command, params):
        calls.append((command, params))
        if command == "probe-hatch":
            return CommandResult(ok=True, payload={
                "handle": "A1", "type": "HATCH", "layer": "A-HATCH",
                "pattern": "ANSI31", "angle": 0.0, "scale": 2.0,
                "loops": 1, "area": 100.0,
            })
        if command == "probe-area":
            return CommandResult(ok=True, payload={"handle": "B1", "area": 100.0})
        raise AssertionError(f"Unexpected LT verification command: {command}")

    backend._dispatch = dispatch
    backend._get_autocad_application = lambda: (_ for _ in ()).throw(AssertionError("COM must not be used"))
    try:
        result = await backend.verify_created_hatch(
            CommandResult(ok=True, payload={"handle": "A1"}),
            entity_id="B1", pattern="ANSI31", angle=0, scale=2, layer="A-HATCH",
            boundary_area=100.0,
        )
        assert result.ok is True
        assert result.payload["verified"] is True
        assert result.payload["hatch_area_verified"] == 100.0
        assert [command for command, _ in calls] == ["probe-hatch", "probe-area"]
    finally:
        await backend.shutdown()


@pytest.mark.asyncio
async def test_lt_hatch_verification_erases_mismatch_through_ipc():
    backend = LtFileIPCBackend()
    calls = []

    async def dispatch(command, params):
        calls.append(command)
        if command == "probe-hatch":
            return CommandResult(ok=True, payload={
                "handle": "A1", "type": "HATCH", "layer": "0",
                "pattern": "ANSI31", "angle": 0.0, "scale": 3.0,
                "loops": 1, "area": 90.0,
            })
        if command == "probe-area":
            return CommandResult(ok=True, payload={"area": 100.0})
        if command == "entity-erase":
            return CommandResult(ok=True, payload={"erased": True})
        raise AssertionError(f"Unexpected LT verification command: {command}")

    backend._dispatch = dispatch
    backend._get_autocad_application = lambda: (_ for _ in ()).throw(AssertionError("COM must not be used"))
    try:
        result = await backend.verify_created_hatch(
            CommandResult(ok=True, payload={"handle": "A1"}),
            entity_id="B1", pattern="ANSI31", angle=0, scale=2,
        )
        assert result.ok is False
        assert result.error_code == "E_POSTCONDITION_MISMATCH"
        assert result.payload["deleted"] is True
        assert calls == ["probe-hatch", "probe-area", "entity-erase"]
    finally:
        await backend.shutdown()


def _fake_user32(monkeypatch, live_windows):
    from types import SimpleNamespace

    import lt_adapter.lt_file_ipc as module

    user32 = SimpleNamespace(IsWindow=lambda hwnd: hwnd in live_windows)
    monkeypatch.setattr(module, "ctypes", SimpleNamespace(windll=SimpleNamespace(user32=user32)))


def test_lt_type_command_looks_the_command_window_up_again_when_stale(monkeypatch):
    backend = LtFileIPCBackend()
    backend._hwnd, backend._command_hwnd = 10, 11  # 11 no longer exists
    _fake_user32(monkeypatch, {10, 12})
    monkeypatch.setattr(backend, "_find_command_line_hwnd", lambda: 12)
    posted = []
    monkeypatch.setattr(backend, "_post_keys", lambda target, command: posted.append((target, command)) or True)

    assert backend._type_command("(c:mcp-dispatch)") is True
    assert posted == [(12, "(c:mcp-dispatch)")]
    assert backend._command_hwnd == 12


def test_lt_type_command_fails_fast_when_keys_cannot_be_posted(monkeypatch):
    backend = LtFileIPCBackend()
    backend._hwnd, backend._command_hwnd = 10, 11
    _fake_user32(monkeypatch, {10, 11})
    monkeypatch.setattr(backend, "_find_command_line_hwnd", lambda: 11)
    attempts = []
    monkeypatch.setattr(backend, "_post_keys", lambda target, command: attempts.append(target) and False)

    assert backend._type_command("(c:mcp-dispatch)") is False
    assert len(attempts) == 2  # one retry after looking the window up again


def _loading_backend(monkeypatch, ping_results):
    import lt_adapter.lt_file_ipc as module

    backend = LtFileIPCBackend()
    typed, pings = [], []
    monkeypatch.setattr(backend, "_type_command", lambda expression: typed.append(expression) or True)
    monkeypatch.setattr(backend, "_window_key", lambda: ("hwnd", 1, "t"))
    monkeypatch.setattr(module.asyncio, "sleep", lambda _seconds: _noop())
    results = iter(ping_results)

    async def dispatch(command, params, timeout=None):
        pings.append((command, timeout))
        return next(results)

    backend._dispatch_unlocked = dispatch
    return backend, typed, pings


async def _noop():
    return None


@pytest.mark.asyncio
async def test_lt_dispatcher_load_retries_when_keys_were_dropped(monkeypatch):
    from autocad_mcp import __version__

    timeout = CommandResult(ok=False, error="Timeout", error_code="E_IPC_TIMEOUT")
    answer = CommandResult(ok=True, payload={"dispatcher_version": __version__})
    backend, typed, pings = _loading_backend(monkeypatch, [timeout, timeout, answer])
    try:
        assert (await backend._load_dispatcher_unlocked()).ok
    finally:
        await backend.shutdown()
    assert len(pings) == 3 and all(p == ("ping", backend._LOAD_PING_TIMEOUT) for p in pings)
    assert len(typed) == 6  # both dispatcher files are typed again on every attempt


@pytest.mark.asyncio
async def test_lt_dispatcher_load_gives_up_with_a_bounded_error(monkeypatch):
    timeout = CommandResult(ok=False, error="Timeout", error_code="E_IPC_TIMEOUT")
    backend, typed, pings = _loading_backend(monkeypatch, [timeout] * 10)
    try:
        result = await backend._load_dispatcher_unlocked()
    finally:
        await backend.shutdown()
    assert not result.ok and result.error_code == "E_DISPATCHER_NOT_LOADED" and result.recoverable
    assert len(pings) == backend._LOAD_ATTEMPTS


@pytest.mark.asyncio
async def test_lt_dispatcher_loads_once_per_window_and_title(monkeypatch):
    backend = LtFileIPCBackend()
    loads = []
    title = ["Drawing1.dwg"]

    async def load():
        loads.append(title[0])
        backend._dispatcher_key = backend._window_key()
        return CommandResult(ok=True)

    backend._load_dispatcher_unlocked = load
    monkeypatch.setattr(backend, "_window_key", lambda: ("hwnd", 1, title[0]))
    try:
        for _ in range(3):
            assert (await backend._ensure_dispatcher_unlocked()).ok
        assert loads == ["Drawing1.dwg"]
        title[0] = "Other.dwg"
        assert (await backend._ensure_dispatcher_unlocked()).ok
        assert loads == ["Drawing1.dwg", "Other.dwg"]
    finally:
        await backend.shutdown()


def test_block_library_path_stays_inside_the_library(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOCAD_MCP_BLOCK_LIBRARY", str(tmp_path))
    (tmp_path / "FURN-BED.dxf").write_text("0")
    (tmp_path / "FURN-BED.dwg").write_text("0")
    (tmp_path / "PLANT-TREE.dxf").write_text("0")
    find = LtFileIPCBackend._block_library_path
    assert find("FURN-BED") == (tmp_path / "FURN-BED.dwg").resolve().as_posix()
    assert find("PLANT-TREE").endswith("PLANT-TREE.dxf")
    assert find("MISSING") is None
    for hostile in (r"..\FURN-BED","../FURN-BED", "a/b", "C:/x", "", "x" * 81, None, 7):
        assert find(hostile) is None


@pytest.mark.asyncio
async def test_lt_block_insert_sends_library_path_to_the_dispatcher(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOCAD_MCP_BLOCK_LIBRARY", str(tmp_path))
    (tmp_path / "FURN-BED.dxf").write_text("0")
    backend = LtFileIPCBackend()
    calls = []

    async def dispatch(command, params):
        calls.append((command, params))
        return CommandResult(ok=True, payload={"handle": "2E0"})

    backend._dispatch = dispatch
    try:
        await backend.block_insert("FURN-BED", 10, 20, 2.0, 90.0)
        await backend.block_insert("NOT-IN-LIBRARY", 0, 0)
    finally:
        await backend.shutdown()
    assert calls[0][0] == "block-insert-lt"
    assert calls[0][1]["library_path"].endswith("FURN-BED.dxf")
    assert (calls[0][1]["scale"], calls[0][1]["rotation"]) == (2.0, 90.0)
    assert calls[1][1]["library_path"] is None


def _dxf_with_units(path, units):
    path.write_text(f"0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n{units}\n0\nENDSEC\n0\nEOF\n")


@pytest.mark.asyncio
async def test_lt_block_list_adds_library_with_units(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOCAD_MCP_BLOCK_LIBRARY", str(tmp_path))
    _dxf_with_units(tmp_path / "FURN-MM.dxf", 4)
    _dxf_with_units(tmp_path / "FURN-M.dxf", 6)
    (tmp_path / "PLANT-TREE.dwg").write_bytes(b"AC1032")
    (tmp_path / "PLANT-TREE.dxf").write_text("0\nEOF\n")
    (tmp_path / "bad name.dxf").write_text("0\nEOF\n")
    (tmp_path / "notes.txt").write_text("x")
    backend = LtFileIPCBackend()

    async def dispatch(command, params):
        if command == "block-list":
            return CommandResult(ok=True, payload={"blocks": ["A"]})
        return CommandResult(ok=True, payload={"INSUNITS": 4})

    backend._dispatch = dispatch
    try:
        result = await backend.block_list()
    finally:
        await backend.shutdown()
    assert result.payload["blocks"] == ["A"]
    assert result.payload["drawing_units"] == "millimeters"
    library = {entry["name"]: entry for entry in result.payload["library"]}
    assert set(library) == {"FURN-MM", "FURN-M", "PLANT-TREE"}
    assert library["FURN-MM"]["units_match"] is True
    assert library["FURN-M"]["units"] == "meters" and library["FURN-M"]["units_match"] is False
    assert library["PLANT-TREE"]["file"] == "PLANT-TREE.dwg" and library["PLANT-TREE"]["units"] is None
    assert library["PLANT-TREE"]["units_match"] is None


@pytest.mark.asyncio
async def test_lt_block_list_uses_library_index(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOCAD_MCP_BLOCK_LIBRARY", str(tmp_path))
    (tmp_path / "SANI-WC-PLAN-535x840.dwg").write_bytes(b"AC1021")
    (tmp_path / "FURN-OWN-1000x500.dwg").write_bytes(b"AC1021")
    (tmp_path / "index.json").write_text(
        '{"SANI-WC-PLAN-535x840": {"source_file": "DesignCenter/House Designer.dwg",'
        ' "source_block": "Toilet - top", "view": "plan", "meaning": "Bon cau", "units": "inches",'
        ' "mm_per_unit": 25.4, "size_mm": [535, 840], "bbox_mm": [-267, -840, 267, 0], "dynamic": false}}',
        encoding="utf-8")
    backend = LtFileIPCBackend()
    try:
        entries = {e["name"]: e for e in backend._block_library_entries(4)}
    finally:
        await backend.shutdown()
    wc = entries["SANI-WC-PLAN-535x840"]
    assert wc["scale_factor"] == 25.4 and wc["units_match"] is False
    assert wc["view"] == "plan" and wc["size_mm"] == [535, 840] and wc["bbox_mm"][3] == 0
    assert wc["source"] == "DesignCenter/House Designer.dwg :: Toilet - top"
    assert entries["FURN-OWN-1000x500"]["scale_factor"] is None
    assert "meaning" not in entries["FURN-OWN-1000x500"]


@pytest.mark.asyncio
async def test_lt_drawing_activate_switches_and_rebinds(monkeypatch):
    import lt_adapter.lt_file_ipc as module

    backend = LtFileIPCBackend()
    backend._hwnd, backend._acad_process_id = 1, 2
    monkeypatch.setattr(module, "find_lt_window", lambda: (1, 2))
    calls = []
    active = ["C:/d/a.dwg"]

    async def ensure():
        return CommandResult(ok=True)

    async def dispatch(command, params):
        calls.append(command)
        if command == "probe-documents":
            return CommandResult(ok=True, payload={"documents": [
                {"path": p, "name": p.rsplit("/", 1)[1], "active": p == active[0]}
                for p in ("C:/d/a.dwg", "C:/d/b.dwg")]})
        if command == "document-activate-lt":
            active[0] = params["path"]
            return CommandResult(ok=True, payload={})
        raise AssertionError(command)

    async def load():
        calls.append("load")
        return CommandResult(ok=True)

    async def context():
        return CommandResult(ok=True, payload={"active_path": active[0], "doc_id": "acad-x"})

    backend._ensure_dispatcher_unlocked = ensure
    backend._dispatch_unlocked = dispatch
    backend._load_dispatcher_unlocked = load
    backend._context_unlocked = context
    monkeypatch.setattr(backend, "_wait_for_autocad_idle", lambda timeout=0: True)
    try:
        result = await backend.drawing_activate("C:/d/b.dwg", 0)
        assert result.ok and active[0] == "C:/d/b.dwg"
        assert calls == ["probe-documents", "document-activate-lt", "load"]

        missing = await backend.drawing_activate("C:/d/none.dwg", 0)
        assert missing.error_code == "E_PARAMETER_REJECTED"
        assert [item["name"] for item in missing.payload["open_documents"]] == ["a.dwg", "b.dwg"]

        assert (await backend.drawing_activate(None, 0)).error_code == "E_PARAMETER_REJECTED"
        assert (await backend.drawing_activate("C:/d/a.dwg", None)).error_code == "E_PARAMETER_REJECTED"
    finally:
        await backend.shutdown()
