import sys
import os
import zipfile
import io
import time
import tempfile
import warnings
import numpy as np
from pathlib import Path

# ============================================================================
# FIX DE RUTAS (PATH RESOLVER)
# ============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
ZIP_PATH = BASE_DIR / "resource" / "PublicTestCases.zip"  # Ajustado al nombre real 'resource'
project_root = BASE_DIR

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# ============================================================================
# IMPORTS LOCALES
# ============================================================================
from src.warehouse import Warehouse
from src.faster_solver import FastSolver

try:
    from src.logger import LoggerManager
    logger = LoggerManager().getLogger()
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger("testCaseLogger")

# ============================================================================
# FUNCIONES DE EVALUACIÓN DEL BASELINE
# ============================================================================

def get_polygon_area_stream(text_stream) -> float:
    coords = [tuple(map(float, line.strip().split(","))) for line in text_stream if line.strip()]
    if len(coords) < 3: return 0.0
    x, y = [c[0] for c in coords], [c[1] for c in coords]
    return 0.5 * abs(sum(x[i] * y[i - 1] - x[i - 1] * y[i] for i in range(len(coords))))

def load_bays_stream(text_stream) -> dict:
    bays = {}
    for line in text_stream:
        if not line.strip(): continue
        parts = line.strip().split(",")
        bays[int(parts[0])] = {
            "area": float(parts[1]) * float(parts[2]),
            "loads": float(parts[5]),
            "price": float(parts[6]),
        }
    return bays

def evaluate_stream(text_stream, bays_meta: dict, wh_area: float) -> float:
    sum_price = sum_loads = sum_area = 0.0
    for line in text_stream:
        if not line.strip(): continue
        bay_id = int(line.split(",")[0])
        meta = bays_meta.get(bay_id)
        if not meta: continue

        sum_price += meta["price"]
        sum_loads += meta["loads"]
        sum_area += meta["area"]

    if sum_loads == 0 or wh_area == 0: return float("inf")
    return (sum_price / sum_loads) ** (2.0 - (sum_area / wh_area))

# ============================================================================
# UTILIDADES DE ARCHIVOS
# ============================================================================

def get_project_dirs() -> tuple[Path, Path]:
    out_dir = project_root / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    return ZIP_PATH, out_dir

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
    except Exception as e:
        logger.debug(f"Ignorando archivo corrupto/malformado {path.name}: {e}")
    return np.empty((0, ncols), dtype=np.int32)

# ============================================================================
# FLUJO PRINCIPAL DE EVALUACIÓN
# ============================================================================

def process_single_case(case_dir: Path, case_name: str, out_dir: Path, z: zipfile.ZipFile) -> bool:
    logger.info(f"\n--- Evaluando {case_name} ---")

    wh_file = find_file_ci(case_dir, "warehouse.csv")
    bays_file = find_file_ci(case_dir, "types_of_bays.csv")
    obs_file = find_file_ci(case_dir, "obstacles.csv")
    ceil_file = find_file_ci(case_dir, "ceiling.csv")
    sample_out = find_file_ci(case_dir, "sample_output.csv")

    if not wh_file or not bays_file:
        logger.error(f"  [-] Faltan archivos críticos en {case_name}.")
        return False

    with open(wh_file, "r", encoding="utf-8") as f: wh_area = get_polygon_area_stream(f)
    with open(bays_file, "r", encoding="utf-8") as f: bays_meta = load_bays_stream(f)

    sample_score = float('inf')
    if sample_out:
        with open(sample_out, "r", encoding="utf-8") as f:
            sample_score = evaluate_stream(f, bays_meta, wh_area)
    else:
        logger.warning("  [!] sample_output.csv no encontrado. Evaluando a ciegas.")

    try:
        # Cargar CSVs
        coords = _load_csv_safe(wh_file, 2)
        obstacles = _load_csv_safe(obs_file, 4)
        ceiling_pts = _load_csv_safe(ceil_file, 2)
        bays = _load_csv_safe(bays_file, 7)

        # Montar el entorno de Warehouse
        wh = Warehouse(coords)
        wh.apply_obstacles(obstacles)
        if ceiling_pts.size > 0: wh.apply_ceiling(ceiling_pts)
        wh.apply_bays(bays)

        # ============================================================
        # EJECUCIÓN DEL FAST SOLVER (PARALELISMO INTERNO)
        # ============================================================
        logger.info(f"  [i] Lanzando FastSolver con concurrencia optimista...")
        t_start = time.perf_counter()

        # Inyectamos los hiperparámetros ganadores
        solver = FastSolver(wh, weights=[43, 0, 29, 10, 8])

        # Asignamos 28.0 segundos globales de presupuesto para el caso
        # 17% del tiempo para Greedy, y el resto para SA paralelo
        TIME_LIMIT_PER_CASE = 28.0
        greedy_budget = TIME_LIMIT_PER_CASE * 0.17
        sa_budget = max(1.0, TIME_LIMIT_PER_CASE - greedy_budget - 0.5)

        # Lanzar fases
        solver.run_row_packing(time_budget=24.0)

        # Le damos el resto del tiempo al Micro-optimizador para que haga Swaps (ej. 4 segundos)
        solver.run_sa_parallel(time_budget=4.0)

        our_score = solver.score()
        best_solution = solver.export_solution()
        elapsed = time.perf_counter() - t_start

    except Exception as e:
        logger.error(f"  [-] Error interno para {case_name}: {e}")
        return False

    # Exportar output para validación final
    out_path = out_dir / f"output_{case_name}.csv"
    with open(out_path, "w", encoding="utf-8") as f:
        for bay in best_solution:
            f.write(f"{bay[0]},{bay[1]},{bay[2]},{bay[3]}\n")

    logger.info(f"  Baseline: {sample_score:12.4f} | FastSolver: {our_score:12.4f} | Tiempo: {elapsed:.2f}s")

    if our_score < sample_score:
        logger.info(f"  [+] {case_name} PASSED (Superamos al baseline).")
        return True
    else:
        logger.error(f"  [-] {case_name} FAILED (Peor o igual al baseline).")
        return False

def print_final_verdict(cases_won: int, total_cases: int):
    logger.info("\n==================================================")
    logger.info(f"RESULTADO FINAL: {cases_won} / {total_cases} casos superados.")
    if total_cases > 0 and cases_won == total_cases:
        logger.info("🎯 ACCEPTED: Arquitectura Paralela Lock-Free Validada. Hackathon Win.")
        sys.exit(0)
    else:
        logger.error("🛑 REJECTED: El algoritmo necesita más Tuning.")
        sys.exit(1)

def main():
    zip_path, out_dir = get_project_dirs()

    if not zip_path.exists():
        logger.error(f"Critical dataset ZIP no encontrado en: {zip_path}")
        sys.exit(1)

    cases_won = 0
    total_cases = 0

    with tempfile.TemporaryDirectory() as tmpdirname:
        logger.info("[i] Extrayendo PublicTestCases.zip en RAM/Temp...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmpdirname)

        tmp_path = Path(tmpdirname)
        case_dirs = []
        for root, dirs, files in os.walk(tmp_path):
            if any(f.lower() == 'warehouse.csv' for f in files):
                case_dirs.append(Path(root))

        case_dirs.sort()
        total_cases = len(case_dirs)

        for case_dir in case_dirs:
            case_name = case_dir.name
            is_success = process_single_case(case_dir, case_name, out_dir, z=None)
            if is_success:
                cases_won += 1

    print_final_verdict(cases_won, total_cases)

if __name__ == "__main__":
    main()