from autocad_mcp.custom_tools.cad_batch import normalize_params


def test_params_inside_params_unchanged():
    item = {"op": "get", "params": {"entity_id": "2A3F"}}
    assert normalize_params(item, item["params"]) == {"entity_id": "2A3F"}


def test_flat_keys_beside_op_are_accepted():
    item = {"op": "move", "entity_id": "2A3F", "dx": 100, "dy": 0}
    assert normalize_params(item, {}) == {"entity_id": "2A3F", "dx": 100, "dy": 0}


def test_handle_is_alias_of_entity_id():
    item = {"op": "get", "handle": "2A3F"}
    assert normalize_params(item, {}) == {"entity_id": "2A3F"}


def test_params_win_over_flat_keys():
    item = {"op": "move", "dx": 1, "params": {"dx": 5, "entity_id": "A"}}
    assert normalize_params(item, item["params"]) == {"dx": 5, "entity_id": "A"}
