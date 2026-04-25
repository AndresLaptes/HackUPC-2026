from __future__ import annotations

import math
import sys
import time
import warnings
from functools import reduce
from pathlib import Path

CASES_DIR = Path(__file__).parent.parent / "resource" / "PublicTestCases"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _find_file_ci(directory: Path, filename: str) -> Path | None:
    expected = filename.lower()
    for child in directory.iterdir():
        if child.is_file() and child.name.lower() == expected:
            return child
    return None


def _load_csv_safe(path: Path | None, ncols: int, np):
    if not path or not path.exists() or path.stat().st_size == 0:
        return np.empty((0, ncols), dtype=np.int32)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = np.loadtxt(path, delimiter=",", dtype=np.int32, ndmin=2)
            if data.shape[1] == ncols:
                return data
    except Exception:
        pass

    return np.empty((0, ncols), dtype=np.int32)


def _compute_spatial_gcd(coords, obstacles, bays, ceiling_pts) -> int:
    vals: list[int] = []

    if coords.size > 0:
        vals.extend(coords.flatten().tolist())
    if obstacles.size > 0:
        vals.extend(obstacles[:, 0:4].flatten().tolist())
    if bays.size > 0:
        vals.extend(bays[:, [1, 2, 4]].flatten().tolist())
    if ceiling_pts.size > 0:
        vals.extend(ceiling_pts[:, 0].flatten().tolist())

    vals = [abs(int(v)) for v in vals if int(v) != 0]
    if not vals:
        return 1

    return max(1, reduce(math.gcd, vals))


def solve_case(case_name: str, *, time_limit: float = 28.0) -> dict:
    case_dir = CASES_DIR / case_name
    if not case_dir.is_dir():
        raise FileNotFoundError(f"Case '{case_name}' not found")

    wh_file = _find_file_ci(case_dir, "warehouse.csv")
    bays_file = _find_file_ci(case_dir, "types_of_bays.csv")
    obs_file = _find_file_ci(case_dir, "obstacles.csv")
    ceil_file = _find_file_ci(case_dir, "ceiling.csv")

    if not wh_file or not bays_file:
        raise ValueError(f"Missing required files in case '{case_name}'")

    try:
        import numpy as np
        from src.warehouse import Warehouse
        from src.faster_solver import FastSolver
    except Exception as e:
        raise RuntimeError(f"Solver dependencies are not available: {e}") from e

    coords = _load_csv_safe(wh_file, 2, np)
    obstacles = _load_csv_safe(obs_file, 4, np)
    ceiling_pts = _load_csv_safe(ceil_file, 2, np)
    bays = _load_csv_safe(bays_file, 7, np)

    if coords.size == 0 or bays.size == 0:
        raise ValueError(f"Case '{case_name}' has invalid/empty warehouse or bay catalog")

    gcd = _compute_spatial_gcd(coords, obstacles, bays, ceiling_pts)
    if gcd > 1:
        coords = coords // gcd
        if obstacles.size > 0:
            obstacles[:, 0:4] = obstacles[:, 0:4] // gcd
        if ceiling_pts.size > 0:
            ceiling_pts[:, 0] = ceiling_pts[:, 0] // gcd
        if bays.size > 0:
            bays[:, [1, 2, 4]] = bays[:, [1, 2, 4]] // gcd

    wh = Warehouse(coords)
    wh.apply_obstacles(obstacles)
    if ceiling_pts.size > 0:
        wh.apply_ceiling(ceiling_pts)
    wh.apply_bays(bays)

    solver = FastSolver(wh)

    start = time.perf_counter()
    solver.run_parallel_grasp(time_budget=max(1.0, float(time_limit)))
    elapsed = time.perf_counter() - start

    solution = solver.export_solution()
    score = float(solver.score())

    output_path = case_dir / f"output_{case_name}.csv"
    with open(output_path, "w", encoding="utf-8") as f:
        for bay_type_id, x, y, rotation in solution:
            real_x = int(x * gcd)
            real_y = int(y * gcd)
            f.write(f"{bay_type_id},{real_x},{real_y},{rotation}\n")

    return {
        "case": case_name,
        "score": score,
        "elapsedSeconds": elapsed,
        "baysCount": len(solution),
        "outputFile": str(output_path),
        "gcd": gcd,
    }
