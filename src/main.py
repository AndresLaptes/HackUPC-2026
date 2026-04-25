import sys
import os
import zipfile
import time
import tempfile
import warnings
import numpy as np
from pathlib import Path

# ============================================================================
# RESOLUCIÓN DINÁMICA DE RUTAS (A prueba de balas)
# ============================================================================
# Detectamos dónde se está ejecutando el script
current_dir = Path(__file__).resolve().parent

# Si metes main.py dentro de 'src', la raíz es un nivel arriba.
# Si lo pones en la raíz, la raíz es el current_dir.
if current_dir.name == "src":
    PROJECT_ROOT = current_dir.parent
else:
    PROJECT_ROOT = current_dir

# Inyectamos las rutas para que los imports de Python no fallen
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
src_path = PROJECT_ROOT / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# ============================================================================
# IMPORTS DEL MOTOR
# ============================================================================
from src.warehouse import Warehouse
from src.faster_solver import FastSolver

# ============================================================================
# CONFIGURACIÓN DE DIRECTORIOS DE ENTREGA
# ============================================================================
# Ajustado según tu estructura: el ZIP suele estar en 'resource' o 'resources'
ZIP_PATH = PROJECT_ROOT / "resource" / "PublicTestCases.zip"

# Aquí es donde el juez o tú iréis a buscar los CSV generados
TEMPLATES_DIR = PROJECT_ROOT / "templates"


# ============================================================================
# UTILIDADES
# ============================================================================
def find_file_ci(directory: Path, filename: str) -> Path:
    """Busca archivos ignorando mayúsculas y minúsculas (warehouse.csv vs WAREHOUSE.csv)"""
    for f in directory.iterdir():
        if f.name.lower() == filename.lower():
            return f
    return None


def _load_csv_safe(path: Path, ncols: int) -> np.ndarray:
    """Carga de matrices segura a prueba de archivos vacíos o corruptos."""
    if not path or not path.exists() or path.stat().st_size == 0:
        return np.empty((0, ncols), dtype=np.int32)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = np.loadtxt(path, delimiter=',', dtype=np.int32, ndmin=2)
            if data.shape[1] == ncols:
                return data
    except Exception as e:
        print(f"  [!] Aviso: Archivo malformado {path.name}: {e}")
    return np.empty((0, ncols), dtype=np.int32)


# ============================================================================
# MOTOR GENERADOR DE ENTREGABLES
# ============================================================================
def main():
    global ZIP_PATH  # <--- ¡ESTA ES LA CLAVE! Lo declaramos antes de hacer nada más.

    print("=" * 60)
    print(" 🚀 INICIANDO GENERADOR DE ENTREGABLES (HACKUPC 2026) 🚀")
    print("=" * 60)

    if not ZIP_PATH.exists():
        # Fallback por si la carpeta se llama 'resources' con 's'
        fallback_zip = PROJECT_ROOT / "resources" / "PublicTestCases.zip"
        if fallback_zip.exists():
            ZIP_PATH = fallback_zip
        else:
            print(f"[FATAL] No se encuentra el dataset en: {ZIP_PATH}")
            sys.exit(1)

    # Creamos la carpeta templates (al mismo nivel que src) si no existe
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[i] Carpeta de salida lista en: {TEMPLATES_DIR}")

    # Extraemos a la RAM/Temp para máxima velocidad de I/O
    with tempfile.TemporaryDirectory() as tmpdirname:
        print(f"[i] Descomprimiendo casos de prueba...")
        with zipfile.ZipFile(ZIP_PATH, "r") as z:
            z.extractall(tmpdirname)

        tmp_path = Path(tmpdirname)
        case_dirs = []
        for root, dirs, files in os.walk(tmp_path):
            if any(f.lower() == 'warehouse.csv' for f in files):
                case_dirs.append(Path(root))

        case_dirs.sort()
        print(f"[i] Encontrados {len(case_dirs)} casos para procesar.\n")

        for case_dir in case_dirs:
            case_name = case_dir.name
            print(f"▶ Procesando {case_name}...")

            # 1. Localizar Archivos
            wh_file = find_file_ci(case_dir, "warehouse.csv")
            bays_file = find_file_ci(case_dir, "types_of_bays.csv")
            obs_file = find_file_ci(case_dir, "obstacles.csv")
            ceil_file = find_file_ci(case_dir, "ceiling.csv")

            if not wh_file or not bays_file:
                print(f"  [!] Error: Faltan archivos críticos en {case_name}. Saltando...")
                continue

            # 2. Cargar Geometría
            t_start = time.perf_counter()
            coords = _load_csv_safe(wh_file, 2)
            obstacles = _load_csv_safe(obs_file, 4)
            ceiling_pts = _load_csv_safe(ceil_file, 2)
            bays = _load_csv_safe(bays_file, 7)

            wh = Warehouse(coords)
            wh.apply_obstacles(obstacles)
            if ceiling_pts.size > 0:
                wh.apply_ceiling(ceiling_pts)
            wh.apply_bays(bays)

            # 3. Lanzar FastSolver (El motor C++ Killer)
            solver = FastSolver(wh, weights=[5, 0, 0, 0, 95])

            TIME_LIMIT_PER_CASE = 28.5

            greedy_budget = TIME_LIMIT_PER_CASE * 0.85
            solver.run_row_packing(time_budget=greedy_budget)

            elapsed_so_far = time.perf_counter() - t_start
            sa_budget = max(1.0, TIME_LIMIT_PER_CASE - elapsed_so_far - 0.2)
            solver.run_sa_parallel(time_budget=sa_budget)

            # 4. Generar Output
            best_solution = solver.export_solution()
            our_score = solver.score()
            elapsed = time.perf_counter() - t_start

            out_filename = f"output_{case_name}.csv"
            out_path = TEMPLATES_DIR / out_filename

            with open(out_path, "w", encoding="utf-8") as f:
                for bay in best_solution:
                    f.write(f"{bay[0]},{bay[1]},{bay[2]},{bay[3]}\n")

            print(f"  └─ Completado en {elapsed:.2f}s | Score Q = {our_score:.2f} | Guardado en {out_filename}")

    print("\n" + "=" * 60)
    print(" ✅ TODOS LOS CASOS PROCESADOS CON ÉXITO")
    print(f" 📂 Tus archivos finales están en la carpeta: {TEMPLATES_DIR.resolve()}")
    print("=" * 60)

if __name__ == "__main__":
    main()