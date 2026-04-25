from pathlib import Path
from models import Warehouse, Obstacle, BayType

CASES_DIR = Path(__file__).parent.parent / "resource" / "PublicTestCases"


def list_cases() -> list[str]:
    if not CASES_DIR.exists():
        return []
    return sorted(d.name for d in CASES_DIR.iterdir() if d.is_dir() and d.name.startswith("Case"))


def _rows(filepath: Path) -> list[list[str]]:
    if not filepath.exists():
        return []
    result = []
    with open(filepath) as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                cols = [v.strip() for v in stripped.split(",")]
                if any(c for c in cols):
                    result.append(cols)
    return result


def _find_case_file(case_dir: Path, filename: str) -> Path:
    """Find a case file by name, ignoring case (e.g. OBSTACLES.csv vs obstacles.csv)."""
    expected = filename.lower()
    direct = case_dir / filename
    if direct.exists():
        return direct
    for child in case_dir.iterdir():
        if child.is_file() and child.name.lower() == expected:
            return child
    return direct


def _parse_float_row(row: list[str], n: int) -> list[float] | None:
    """Parse first n columns as float. Returns None for header/invalid rows."""
    if len(row) < n:
        return None
    try:
        return [float(row[i]) for i in range(n)]
    except (ValueError, TypeError):
        # Header rows like: Id, Width, Depth, ...
        return None


def load_case(name: str, *, include_output: bool = False) -> dict:
    d = CASES_DIR / name
    if not d.is_dir():
        return None

    poly_rows = _rows(_find_case_file(d, "warehouse.csv"))
    polygon = []
    for r in poly_rows:
        nums = _parse_float_row(r, 2)
        if nums is not None:
            polygon.append([nums[0], nums[1]])

    ceil_rows = _rows(_find_case_file(d, "ceiling.csv"))
    ceiling = []
    for r in ceil_rows:
        nums = _parse_float_row(r, 2)
        if nums is not None:
            ceiling.append([nums[0], nums[1]])

    warehouse = Warehouse(label=name, polygon=polygon, ceilingCtrlPoints=ceiling)

    obs_rows = _rows(_find_case_file(d, "obstacles.csv"))
    obstacles = []
    for i, r in enumerate(obs_rows):
        nums = _parse_float_row(r, 4)
        if nums is not None:
            obstacles.append(Obstacle(
                id=f"obs-{i}",
                x=nums[0], y=nums[1],
                width=nums[2], depth=nums[3],
                label=chr(65 + i),
            ))

    type_rows = _rows(_find_case_file(d, "types_of_bays.csv"))
    bay_types = []
    for r in type_rows:
        nums = _parse_float_row(r, 7)
        if nums is not None:
            bay_types.append(BayType(
                id=int(nums[0]),
                width=nums[1],
                depth=nums[2],
                height=nums[3],
                gap=nums[4],
                nLoads=int(nums[5]),
                price=nums[6],
            ))

    bays = []
    if include_output:
        bay_type_by_id = {bt.id: bt for bt in bay_types}
        out_rows = _rows(_find_case_file(d, f"output_{name}.csv"))
        for i, r in enumerate(out_rows):
            nums = _parse_float_row(r, 4)
            if nums is None:
                continue

            bay_type_id = int(nums[0])
            bay_type = bay_type_by_id.get(bay_type_id)
            if bay_type is None:
                # Ignore invalid rows that reference unknown bay type IDs
                continue

            bays.append({
                "id": f"bay-{i}",
                "bayTypeId": bay_type_id,
                "x": nums[1],
                "y": nums[2],
                "width": bay_type.width,
                "depth": bay_type.depth,
                "height": bay_type.height,
                "gap": bay_type.gap,
                "nLoads": bay_type.nLoads,
                "price": bay_type.price,
                "label": f"T{bay_type_id}-{i}",
                "rotation": nums[3],
            })

    return {
        "warehouse": warehouse.model_dump(),
        "obstacles": [o.model_dump() for o in obstacles],
        "bay_types": [bt.model_dump() for bt in bay_types],
        "bays": bays,
    }
