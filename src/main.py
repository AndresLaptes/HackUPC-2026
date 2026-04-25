import sys
import os
import zipfile
import time
import tempfile
import warnings
import math
import gc
import numpy as np
from functools import reduce
from pathlib import Path

# ============================================================================
# RESOLUCIÓN DINÁMICA DE RUTAS
# ============================================================================
current_dir = Path(__file__).resolve().parent

if current_dir.name == "src":
    PROJECT_ROOT = current_dir.parent
else:
    PROJECT_ROOT = current_dir

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
src_path = PROJECT_ROOT / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# ============================================================================
# IMPORTS DEL MOTOR
# ============================================================================
from src.warehouse import Warehouse
from src.faster_solver import FastSolver, PlacedBay

ZIP_PATH = PROJECT_ROOT / "resource" / "PublicTestCases.zip"
TEMPLATES_DIR = PROJECT_ROOT / "templates"


def find_file_ci(directory: Path, filename: str) -> Path:
    for f in directory.iterdir():
        if f.name.lower() == filename.lower():
            return f
    return None


def _load_csv_safe(path: Path, ncols: int) -> np.ndarray:
    if not path or not path.exists() or path.stat().st_size == 0:
        return np.empty((0, ncols), dtype=np.int32)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = np.loadtxt(path, delimiter=',', dtype=np.int32, ndmin=2)
            if data.shape[1] == ncols:
                return data
    except Exception:
        pass
    return np.empty((0, ncols), dtype=np.int32)


def compute_spatial_gcd(coords, obstacles, bays, ceiling_pts) -> int:
    vals = []
    if coords.size > 0: vals.extend(coords.flatten().tolist())
    if obstacles.size > 0: vals.extend(obstacles[:, 0:4].flatten().tolist())
    if bays.size > 0: vals.extend(bays[:, [1, 2, 4]].flatten().tolist())
    if ceiling_pts.size > 0: vals.extend(ceiling_pts[:, 0].flatten().tolist())

    vals = [abs(int(v)) for v in vals if int(v) != 0]
    if not vals: return 1
    return max(1, reduce(math.gcd, vals))


def main():
    global ZIP_PATH

    print("=" * 60)
    print(" 🚀 INICIANDO GENERADOR: SCANLINE GRASP (COMPRESIÓN GCD) 🚀")
    print("=" * 60)

    if not ZIP_PATH.exists():
        fallback_zip = PROJECT_ROOT / "resources" / "PublicTestCases.zip"
        if fallback_zip.exists():
            ZIP_PATH = fallback_zip
        else:
            print(f"[FATAL] Dataset no encontrado: {ZIP_PATH}")
            sys.exit(1)

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile(ZIP_PATH, "r") as z:
            z.extractall(tmpdirname)

        tmp_path = Path(tmpdirname)
        case_dirs = [Path(root) for root, dirs, files in os.walk(tmp_path) if
                     any(f.lower() == 'warehouse.csv' for f in files)]
        case_dirs.sort()

        for case_dir in case_dirs:
            case_name = case_dir.name
            print(f"▶ Procesando {case_name}...")

            wh_file = find_file_ci(case_dir, "warehouse.csv")
            bays_file = find_file_ci(case_dir, "types_of_bays.csv")
            obs_file = find_file_ci(case_dir, "obstacles.csv")
            ceil_file = find_file_ci(case_dir, "ceiling.csv")

            if not wh_file or not bays_file:
                continue

            t_start = time.perf_counter()
            coords = _load_csv_safe(wh_file, 2)
            obstacles = _load_csv_safe(obs_file, 4)
            ceiling_pts = _load_csv_safe(ceil_file, 2)
            bays = _load_csv_safe(bays_file, 7)

            # --- GUARDAR ORIGINALES PARA EL PLOT EXACTO ---
            orig_coords = coords.copy()
            orig_obstacles = obstacles.copy()

            # --- COMPRESIÓN DE MEMORIA (GCD) ---
            gcd = compute_spatial_gcd(coords, obstacles, bays, ceiling_pts)
            if gcd > 1:
                print(f"  [i] Factor GCD: {gcd}. Compresión RAM: {gcd * gcd}x")
                coords = coords // gcd
                if obstacles.size > 0: obstacles[:, 0:4] = obstacles[:, 0:4] // gcd
                if ceiling_pts.size > 0: ceiling_pts[:, 0] = ceiling_pts[:, 0] // gcd
                if bays.size > 0: bays[:, [1, 2, 4]] = bays[:, [1, 2, 4]] // gcd

            wh_base = Warehouse(coords)
            wh_base.apply_obstacles(obstacles)
            if ceiling_pts.size > 0: wh_base.apply_ceiling(ceiling_pts)
            wh_base.apply_bays(bays)

            # ==============================================================
            # Lanzar FastSolver (El motor Scanline GRASP Paralelo)
            # ==============================================================
            solver = FastSolver(wh_base)
            TIME_LIMIT_PER_CASE = 28.5

            solver.run_parallel_grasp(time_budget=TIME_LIMIT_PER_CASE)

            best_global_solution = solver.export_solution()
            best_global_score = solver.score()
            elapsed = time.perf_counter() - t_start

            # --- VOLCADO A DISCO ---
            out_csv_path = TEMPLATES_DIR / f"output_{case_name}.csv"
            with open(out_csv_path, "w", encoding="utf-8") as f:
                for bay in best_global_solution:
                    # Escalado Inverso (Devolver valores al juez)
                    real_x = int(bay[1] * gcd)
                    real_y = int(bay[2] * gcd)
                    f.write(f"{bay[0]},{real_x},{real_y},{bay[3]}\n")

            # --- RENDERIZADO VISUAL ---
            try:
                import matplotlib.pyplot as plt
                out_img_path = TEMPLATES_DIR / f"plot_{case_name}.png"

                # Le pasamos las coordenadas ORIGINALES y el factor GCD
                solver.plot(orig_coords, orig_obstacles, gcd=gcd, save_path=str(out_img_path))
            except Exception as e:
                print(f"  [!] Plot fallido (Ignorable): {e}")

            print(f"  └─ Completado en {elapsed:.2f}s | Score Q = {best_global_score:.4f}")

            del wh_base
            del solver
            if 'plt' in sys.modules:
                plt.close('all')
            gc.collect()

    print("\n ✅ HACKUPC BATCH COMPLETADO. PREPARADO PARA SUBMIT.")


if __name__ == "__main__":
    main()