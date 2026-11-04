"""Find repeated objects in an entity listing, so an agent copies one instead of redrawing it.

Read-only and pure: it takes the dicts that ``entity list`` returns (type, handle, layer, bbox,
points, name...) and groups

* INSERTs by block name, and
* loose entities by shape.  A loose object is an outline plus everything whose bbox lies inside
  it (a car: body polyline, windows, wheels).  Two objects match when their parts have the same
  types and the same bbox corners relative to the outline, within ``tolerance`` mm, after any of
  the 8 turns and mirror images, so "same shape, other direction" is one group.

Text is left out of the shape (labels differ from object to object) and only counted.
"""
from __future__ import annotations

from collections import Counter, defaultdict

TEXT_TYPES = {"TEXT", "MTEXT", "ATTDEF", "ATTRIB"}
MAX_ENTITIES = 6000
MAX_LISTED = 100
MAX_CENTRES = 20


def _area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def _centre_in(outer, inner, tol):
    cx, cy = (inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2
    return outer[0] - tol <= cx <= outer[2] + tol and outer[1] - tol <= cy <= outer[3] + tol


def _extra(entity):
    kind = entity.get("type")
    if kind in ("LWPOLYLINE", "POLYLINE"):
        return (len(entity.get("points") or ()), bool(entity.get("closed")))
    if kind == "CIRCLE":
        return (round(float(entity.get("radius", 0)) / 10),)
    return ()


def _transforms(width, depth):
    """The 8 maps of a (x1, y1, x2, y2) rectangle inside a width x depth frame."""
    def rot(box, w, d, turns):
        for _ in range(turns):
            x1, y1, x2, y2 = box
            box, w, d = (d - y2, x1, d - y1, x2), d, w
        return box
    maps = []
    for mirror in (False, True):
        for turns in range(4):
            def apply(box, mirror=mirror, turns=turns):
                if mirror:
                    box = (width - box[2], box[1], width - box[0], box[3])
                return rot(box, width, depth, turns)
            maps.append(apply)
    return maps


def _keys(parts, width, depth, quantum):
    """Canonical key plus the untransformed key of one object."""
    raw = None
    best = None
    for index, apply in enumerate(_transforms(width, depth)):
        key = tuple(sorted(
            (kind, extra) + tuple(round(v / quantum) for v in apply(box))
            for kind, extra, box in parts))
        if index == 0:
            raw = key
        if best is None or key < best:
            best = key
    return best, raw


def inventory(entities, tolerance=10.0, min_count=2, max_side=12000.0, layers=None):
    entities = [e for e in entities if isinstance(e, dict)]
    if layers:
        wanted = set(layers)
        entities = [e for e in entities if e.get("layer") in wanted]
    truncated = len(entities) > MAX_ENTITIES
    entities = entities[:MAX_ENTITIES]

    blocks = defaultdict(list)
    shapes = []
    labels = 0
    for entity in entities:
        kind = entity.get("type")
        if kind in TEXT_TYPES:
            labels += 1
        elif kind == "INSERT":
            blocks[(entity.get("name") or entity.get("block") or "?", entity.get("layer"))].append(entity)
        elif isinstance(entity.get("bbox"), (list, tuple)) and len(entity["bbox"]) == 4:
            shapes.append(entity)

    block_rows = []
    for (name, layer), items in blocks.items():
        if len(items) < min_count:
            continue
        block_rows.append({
            "block": name, "layer": layer, "count": len(items),
            "size_mm": _size(items[0].get("bbox")),
            "scales": sorted({str(i.get("xscale", i.get("scale", 1))) for i in items}),
            "rotations": sorted({str(i.get("rotation", 0)) for i in items}),
            "sample_handle": items[0].get("handle"),
            "handles": [i.get("handle") for i in items[:MAX_LISTED]],
        })
    block_rows.sort(key=lambda row: -row["count"])

    # Each shape hangs under the smallest larger shape whose box holds its centre (a bike's crossbar
    # sticks out of its body, so full containment would miss it); frames are skipped.
    boxes = [tuple(float(v) for v in e["bbox"]) for e in shapes]
    frames = {i for i, b in enumerate(boxes) if max(b[2] - b[0], b[3] - b[1]) > max_side}
    order = sorted((i for i in range(len(shapes)) if i not in frames), key=lambda i: (_area(boxes[i]), i))
    parent = {}
    for pos, i in enumerate(order):
        for j in order[pos + 1:]:
            if _area(boxes[j]) > _area(boxes[i]) + 1e-6 and _centre_in(boxes[j], boxes[i], tolerance):
                parent[i] = j
                break

    def root(i):
        while i in parent:
            i = parent[i]
        return i

    members = defaultdict(list)
    for i in order:
        members[root(i)].append(i)

    groups = defaultdict(list)
    for top, ids in members.items():
        outline = (min(boxes[i][0] for i in ids), min(boxes[i][1] for i in ids),
                   max(boxes[i][2] for i in ids), max(boxes[i][3] for i in ids))
        width, depth = outline[2] - outline[0], outline[3] - outline[1]
        if width <= 0 or depth <= 0:
            continue
        parts = [(shapes[i].get("type"), _extra(shapes[i]),
                  (boxes[i][0] - outline[0], boxes[i][1] - outline[1],
                   boxes[i][2] - outline[0], boxes[i][3] - outline[1])) for i in ids]
        canonical, raw = _keys(parts, width, depth, max(tolerance, 1.0))
        groups[canonical].append({"top": top, "ids": ids, "raw": raw, "w": width, "d": depth})

    rows = []
    for items in groups.values():
        if len(items) < min_count:
            continue
        first = items[0]
        sample = shapes[first["top"]]
        types = Counter(shapes[i].get("type") for i in first["ids"])
        rows.append({
            "count": len(items),
            "size_mm": [round(max(first["w"], first["d"])), round(min(first["w"], first["d"]))],
            "layers": sorted({shapes[i].get("layer") for it in items for i in it["ids"]}),
            "entities_each": len(first["ids"]),
            "types": dict(types),
            "directions": len({it["raw"] for it in items}),
            "sample_handle": sample.get("handle"),
            "sample_handles": [shapes[i].get("handle") for i in first["ids"]][:MAX_LISTED],
            "centres_mm": [_centre(boxes, it["ids"]) for it in items[:MAX_CENTRES]],
            "centres_listed": min(len(items), MAX_CENTRES),
            "extent_mm": _extent(boxes, [i for it in items for i in it["ids"]]),
        })
    rows.sort(key=lambda row: (-row["count"], -row["entities_each"]))
    return {
        "scanned": len(entities), "truncated": truncated, "labels_ignored": labels,
        "frames_skipped": len(frames), "tolerance_mm": tolerance,
        "blocks": block_rows[:MAX_LISTED], "groups": rows[:MAX_LISTED],
    }


def _size(box):
    if not box or len(box) != 4:
        return None
    return [round(box[2] - box[0]), round(box[3] - box[1])]


def _centre(boxes, ids):
    return [round((min(boxes[i][0] for i in ids) + max(boxes[i][2] for i in ids)) / 2),
            round((min(boxes[i][1] for i in ids) + max(boxes[i][3] for i in ids)) / 2)]


def _extent(boxes, ids):
    return [round(min(boxes[i][0] for i in ids)), round(min(boxes[i][1] for i in ids)),
            round(max(boxes[i][2] for i in ids)), round(max(boxes[i][3] for i in ids))]
