from autocad_mcp.inventory import inventory


def poly(handle, x1, y1, x2, y2, layer="OTO", closed=True):
    return {"type": "LWPOLYLINE", "handle": handle, "layer": layer, "closed": closed,
            "points": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]] if closed else [[x1, y1], [x2, y2]],
            "bbox": [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]}


def car(tag, x, y, turned=False):
    """Body 4400x1800 with a window and a wheel box; turned = rotated 90 degrees."""
    parts = [(0, 0, 4400, 1800), (3000, 200, 4000, 1600), (500, -50, 1000, 50)]
    if turned:
        parts = [(y1, x1, y2, x2) for x1, y1, x2, y2 in parts]
    return [poly(f"{tag}{i}", x + a, y + b, x + c, y + d) for i, (a, b, c, d) in enumerate(parts)]


def test_same_car_in_any_direction_is_one_group():
    entities = car("A", 0, 0) + car("B", 6000, 0) + car("C", 0, 9000, turned=True)
    groups = inventory(entities)["groups"]
    assert len(groups) == 1
    assert groups[0]["count"] == 3
    assert groups[0]["entities_each"] == 3
    assert groups[0]["directions"] == 2
    assert groups[0]["size_mm"] == [4400, 1800 + 50]


def test_different_shape_is_not_grouped_and_single_is_dropped():
    entities = car("A", 0, 0) + car("B", 6000, 0) + [poly("Z", 0, 20000, 2500, 25000)]
    result = inventory(entities)
    assert [g["count"] for g in result["groups"]] == [2]
    assert inventory(entities, min_count=1)["groups"][-1]["count"] == 1


def test_small_part_sticking_out_belongs_to_its_body():
    bikes = []
    for k in range(5):
        x = 800 * k
        bikes += [poly(f"R{k}", x, 0, x + 300, 1600),
                  poly(f"L{k}", x - 200, 800, x + 500, 800, closed=False)]
    groups = inventory(bikes)["groups"]
    assert [(g["count"], g["entities_each"]) for g in groups] == [(5, 2)]


def test_blocks_group_by_name_and_text_is_ignored():
    entities = [{"type": "INSERT", "handle": f"I{i}", "layer": "B", "name": "CAR",
                 "bbox": [i * 6000, 0, i * 6000 + 4400, 1800], "xscale": 1, "rotation": 0}
                for i in range(3)]
    entities += [{"type": "TEXT", "handle": "T1", "layer": "B", "bbox": [0, 0, 10, 10]}]
    result = inventory(entities)
    assert result["blocks"][0]["block"] == "CAR" and result["blocks"][0]["count"] == 3
    assert result["blocks"][0]["size_mm"] == [4400, 1800]
    assert result["labels_ignored"] == 1 and result["groups"] == []


def test_big_frame_is_not_a_parent():
    frame = poly("F", -100000, -100000, 100000, 100000)
    result = inventory([frame] + car("A", 0, 0) + car("B", 6000, 0))
    assert result["frames_skipped"] == 1
    assert result["groups"][0]["count"] == 2


def test_centres_are_capped_and_the_extent_covers_every_object():
    entities = []
    for k in range(30):
        entities += car(f"C{k}_", 6000 * k, 0)
    group = inventory(entities)["groups"][0]
    assert group["count"] == 30 and len(group["centres_mm"]) == 20 and group["centres_listed"] == 20
    assert group["extent_mm"][0] == 0 and group["extent_mm"][2] == 6000 * 29 + 4400


class _FakeBackend:
    def __init__(self, entities, revision=0):
        self.entities, self.revision, self.lists = entities, revision, 0

    async def document_context(self):
        from autocad_mcp.backends.base import CommandResult
        return CommandResult(ok=True, payload={"doc_id": "d1", "revision": self.revision})

    async def entity_count(self, layer=None):
        from autocad_mcp.backends.base import CommandResult
        return CommandResult(ok=True, payload={"count": len(self.entities)})

    async def entity_list(self, layer=None):
        from autocad_mcp.backends.base import CommandResult
        self.lists += 1
        return CommandResult(ok=True, payload={"entities": list(self.entities)})


def test_cache_is_reused_until_the_entity_count_or_revision_changes():
    import asyncio

    from autocad_mcp import server

    server._INVENTORY_CACHE.clear()
    backend = _FakeBackend(car("A", 0, 0) + car("B", 6000, 0))
    run = lambda **data: asyncio.run(server._entity_inventory(backend, "OTO", data)).payload
    assert run()["cached"] is False
    assert run()["cached"] is True and backend.lists == 1
    backend.entities += car("C", 12000, 0)          # someone drew a third car by hand
    third = run()
    assert third["cached"] is False and third["groups"][0]["count"] == 3
    backend.revision = 5                              # the gateway saw a change
    assert run()["cached"] is False
    assert run(refresh=True)["cached"] is False
    assert run()["cached"] is True
