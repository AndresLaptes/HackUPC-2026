"""
Simple greedy bay placer.

Picks the bay type with the best nLoads per floor-area ratio, then fills the
warehouse polygon row-by-row (left→right, top→bottom), skipping positions that
fall outside the polygon or overlap an obstacle.
"""


def _point_in_polygon(px: float, py: float, polygon: list) -> bool:
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > py) != (yj > py):
            if px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def _bay_inside(x: float, y: float, w: float, d: float, polygon: list) -> bool:
    return all(
        _point_in_polygon(px, py, polygon)
        for px, py in [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]
    )


def _overlaps(ax, ay, aw, ad, bx, by, bw, bd) -> bool:
    return not (ax + aw <= bx or bx + bw <= ax or ay + ad <= by or by + bd <= ay)


def place_bays(warehouse_polygon: list, obstacles: list, bay_types: list) -> list:
    if not bay_types or not warehouse_polygon:
        return []

    # Best bay type: highest nLoads per mm² of floor
    best = max(bay_types, key=lambda t: t["nLoads"] / (t["width"] * t["depth"]))

    w  = best["width"]
    d  = best["depth"]
    h  = best["height"]
    gap = best["gap"]

    xs = [p[0] for p in warehouse_polygon]
    ys = [p[1] for p in warehouse_polygon]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    MARGIN = max(gap, 200)

    placed: list[dict] = []
    bid = 0

    y = min_y + MARGIN
    row = 0
    while y + d <= max_y - MARGIN:
        x = min_x + MARGIN
        while x + w <= max_x - MARGIN:
            if _bay_inside(x, y, w, d, warehouse_polygon) and not any(
                _overlaps(x, y, w, d, o["x"], o["y"], o["width"], o["depth"])
                for o in obstacles
            ):
                placed.append(
                    {
                        "id": f"bay-{bid}",
                        "x": x,
                        "y": y,
                        "width": w,
                        "depth": d,
                        "height": h,
                        "gap": gap,
                        "nLoads": best["nLoads"],
                        "price": best["price"],
                        "label": f"R{row:02d}-{bid:03d}",
                    }
                )
                bid += 1
            x += w + gap
        y += d + gap
        row += 1

    return placed
