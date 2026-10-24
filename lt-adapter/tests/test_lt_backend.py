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
