import sys
import zipfile
import io
from pathlib import Path
from src.logger import LoggerManager


def get_polygon_area_stream(text_stream) -> float:
    coords = [
        tuple(map(float, line.strip().split(",")))
        for line in text_stream
        if line.strip()
    ]
    if len(coords) < 3:
        return 0.0
    x, y = [c[0] for c in coords], [c[1] for c in coords]
    return 0.5 * abs(sum(x[i] * y[i - 1] - x[i - 1] * y[i] for i in range(len(coords))))


def load_bays_stream(text_stream) -> dict:
    bays = {}
    for line in text_stream:
        if not line.strip():
            continue
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
        if not line.strip():
            continue
        bay_id = int(line.split(",")[0])
        meta = bays_meta.get(bay_id)
        if not meta:
            continue

        sum_price += meta["price"]
        sum_loads += meta["loads"]
        sum_area += meta["area"]

    if sum_loads == 0 or wh_area == 0:
        return float("inf")
    return (sum_price / sum_loads) ** (2.0 - (sum_area / wh_area))


def get_project_dirs() -> tuple[Path, Path]:
    base_dir = Path(__file__).resolve().parent.parent
    zip_path = base_dir / "resources" / "dataset.zip"
    out_dir = base_dir / "outputs"  # Procedural output directory
    return zip_path, out_dir


def extract_case_names(z: zipfile.ZipFile) -> list[str]:
    return sorted(
        list(set([Path(f).parts[0] for f in z.namelist() if f.startswith("case")]))
    )


def load_case_inputs(z: zipfile.ZipFile, case_name: str) -> tuple[float, dict]:
    with z.open(f"{case_name}/WAREHOUSE.csv") as f:
        wh_area = get_polygon_area_stream(io.TextIOWrapper(f, encoding="utf-8"))
    with z.open(f"{case_name}/TYPES_OF_BAYS.csv") as f:
        bays_meta = load_bays_stream(io.TextIOWrapper(f, encoding="utf-8"))
    return wh_area, bays_meta


def evaluate_sample_baseline(
    z: zipfile.ZipFile, case_name: str, bays_meta: dict, wh_area: float
) -> float:
    with z.open(f"{case_name}/sample_output.csv") as f:
        return evaluate_stream(
            io.TextIOWrapper(f, encoding="utf-8"), bays_meta, wh_area
        )


def evaluate_our_solution(
    case_name: str, out_dir: Path, bays_meta: dict, wh_area: float
) -> float | None:
    case_id = case_name.replace("case", "")
    our_out_path = out_dir / f"output{case_id}.csv"

    if not our_out_path.exists():
        return None

    with open(our_out_path, "r") as f:
        return evaluate_stream(f, bays_meta, wh_area)


def process_single_case(
    z: zipfile.ZipFile, case_name: str, out_dir: Path, logger
) -> bool:
    logger.info(f"--- Evaluating {case_name} ---")
    try:
        wh_area, bays_meta = load_case_inputs(z, case_name)
        sample_score = evaluate_sample_baseline(z, case_name, bays_meta, wh_area)
        our_score = evaluate_our_solution(case_name, out_dir, bays_meta, wh_area)

        if our_score is None:
            logger.warning(f"  [!] Output file not found for {case_name}. Skipping...")
            return False

        logger.info(f"  Sample: {sample_score:.4f} | Ours: {our_score:.4f}")

        # Objective: Minimize Q-Score
        if our_score < sample_score:
            logger.info(f"  [+] {case_name} PASSED.")
            return True
        else:
            logger.error(f"  [-] {case_name} FAILED (Worse or equal to baseline).")
            return False

    except KeyError as e:
        logger.error(f"  [-] Missing file in ZIP for {case_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"  [-] Internal error processing {case_name}: {e}")
        return False


def print_final_verdict(cases_won: int, total_cases: int, logger):
    logger.info("===================================")
    logger.info(f"FINAL RESULT: {cases_won} / {total_cases} passed.")

    if total_cases > 0 and cases_won == total_cases:
        logger.info("🎯 ACCEPTED: Ready for deployment.")
        sys.exit(0)
    else:
        logger.error("🛑 REJECTED: Algorithmic generator needs optimization.")
        sys.exit(1)


def main():
    logger = LoggerManager.getLogger("testCaseLogger")
    zip_path, out_dir = get_project_dirs()

    if not zip_path.exists():
        logger.error(f"Critical dataset ZIP not found at: {zip_path}")
        sys.exit(1)

    if not out_dir.exists():
        logger.warning(
            f"Output directory not found at: {out_dir}. Was the solver executed?"
        )

    cases_won = 0
    total_cases = 0

    with zipfile.ZipFile(zip_path, "r") as z:
        case_folders = extract_case_names(z)
        total_cases = len(case_folders)

        for case in case_folders:
            is_success = process_single_case(z, case, out_dir, logger)
            if is_success:
                cases_won += 1

    print_final_verdict(cases_won, total_cases, logger)


if __name__ == "__main__":
    main()
