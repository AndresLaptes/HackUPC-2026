"""
faster_solver.py — Ultra-Optimized Warehouse Optimizer
======================================================
Implementa 100% C-Compiled Scanline con Numba (No-GIL),
Continuous GRASP Loop con Early Stopping (Ultra Fast).
"""

import time
import random
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from numba import njit

FREE = 0
GAP = 1
SOLID = 2
DEAD = 9
WALL = 10000


# ═══════════════════════════════════════════════════════
# NUMBA KERNELS (Velocidad C++)
# ═══════════════════════════════════════════════════════


@njit(fastmath=True, cache=True, nogil=True)
def _find_next_free(grid, start_x, start_y, W, H):
    for y in range(start_y, H):
        sx = start_x if y == start_y else 0
        for x in range(sx, W):
            if grid[y, x] == FREE:
                return x, y
    return -1, -1


@njit(fastmath=True, cache=True, nogil=True)
def _check_solid(grid, x, y, w, d, W, H):
    if x < 0 or y < 0 or x + w > W or y + d > H:
        return False
    for iy in range(y, y + d):
        for ix in range(x, x + w):
            val = grid[iy, ix]
            if val == GAP or val == SOLID or val >= WALL:
                return False
    return True


@njit(fastmath=True, cache=True, nogil=True)
def _check_gap(grid, x, y, w, d, W, H):
    if w <= 0 or d <= 0:
        return True
    if x < 0 or y < 0 or x + w > W or y + d > H:
        return False
    for iy in range(y, y + d):
        for ix in range(x, x + w):
            val = grid[iy, ix]
            if val == SOLID or val >= WALL:
                return False
    return True


@njit(fastmath=True, cache=True, nogil=True)
def _paint_solid(grid, x, y, w, d):
    for iy in range(y, y + d):
        for ix in range(x, x + w):
            grid[iy, ix] = SOLID


@njit(fastmath=True, cache=True, nogil=True)
def _paint_gap(grid, x, y, w, d):
    if w <= 0 or d <= 0:
        return
    for iy in range(y, y + d):
        for ix in range(x, x + w):
            if grid[iy, ix] == FREE or grid[iy, ix] == DEAD:
                grid[iy, ix] = GAP


@njit(fastmath=True, cache=True, nogil=True)
def _ceiling_ok(ceiling_map, x, w, h, W):
    x_end = min(W, x + w)
    for cx in range(x, x_end):
        limit = ceiling_map[cx]
        if limit > 0 and limit < h:
            return False
    return True


# ── EL MOTOR C++: TODO EL SWEEP COMPILADO PARA EVITAR EL GIL ──
@njit(fastmath=True, cache=True, nogil=True)
def _run_sweep_pass(grid, bays_matrix, W_bound, H_bound, ceil_map, has_ceil):
    placed_bays = [
        (
            int(0),
            int(0),
            int(0),
            int(0),
            int(0),
            float(0.0),
            int(0),
            int(0),
            int(0),
            int(0),
            int(0),
            int(0),
            int(0),
        )
    ]
    placed_bays.pop()

    l_price = 0.0
    l_loads = 0.0
    l_area = 0.0

    curr_x, curr_y = 0, 0
    max_iters = W_bound * H_bound
    iters = 0

    while curr_y < H_bound and iters < max_iters:
        iters += 1
        nx, ny = _find_next_free(grid, curr_x, curr_y, W_bound, H_bound)
        if nx == -1:
            break

        bay_placed = False
        for i in range(bays_matrix.shape[0]):
            tid = int(bays_matrix[i, 0])
            angle = float(bays_matrix[i, 1])
            orig_w = int(bays_matrix[i, 2])
            orig_d = int(bays_matrix[i, 3])
            aabb_w = int(bays_matrix[i, 4])
            aabb_d = int(bays_matrix[i, 5])
            h = int(bays_matrix[i, 6])
            gap = int(bays_matrix[i, 7])
            nl = int(bays_matrix[i, 8])
            pr = int(bays_matrix[i, 9])

            is_rotated = angle == 90.0
            box_x, box_y, box_w, box_d = 0, 0, 0, 0
            gx, gy, gw, gd = 0, 0, 0, 0
            gap_side = 0
            success = False

            # ── 6-WAY DYNAMIC ANCHORING (FIX: BUG DEL GAP=0 RESUELTO) ──
            if not is_rotated:
                box_w, box_d = orig_w, orig_d
                if _check_solid(grid, nx, ny, box_w, box_d, W_bound, H_bound):
                    if gap == 0:
                        box_x, box_y = nx, ny
                        gx, gy, gw, gd = 0, 0, 0, 0
                        gap_side = 5
                        success = True
                    elif _check_gap(grid, nx, ny - gap, box_w, gap, W_bound, H_bound):
                        box_x, box_y = nx, ny
                        gx, gy, gw, gd = nx, ny - gap, box_w, gap
                        gap_side = 2
                        success = True
                    elif _check_gap(grid, nx, ny + box_d, box_w, gap, W_bound, H_bound):
                        box_x, box_y = nx, ny
                        gx, gy, gw, gd = nx, ny + box_d, box_w, gap
                        gap_side = 1
                        success = True

                if (
                    not success
                    and gap > 0
                    and _check_gap(grid, nx, ny, box_w, gap, W_bound, H_bound)
                ):
                    if _check_solid(grid, nx, ny + gap, box_w, box_d, W_bound, H_bound):
                        box_x, box_y = nx, ny + gap
                        gx, gy, gw, gd = nx, ny, box_w, gap
                        gap_side = 2
                        success = True
            else:
                box_w, box_d = orig_d, orig_w
                if _check_solid(grid, nx, ny, box_w, box_d, W_bound, H_bound):
                    if gap == 0:
                        box_x, box_y = nx, ny
                        gx, gy, gw, gd = 0, 0, 0, 0
                        gap_side = 5
                        success = True
                    elif _check_gap(grid, nx - gap, ny, gap, box_d, W_bound, H_bound):
                        box_x, box_y = nx, ny
                        gx, gy, gw, gd = nx - gap, ny, gap, box_d
                        gap_side = 3
                        success = True
                    elif _check_gap(grid, nx + box_w, ny, gap, box_d, W_bound, H_bound):
                        box_x, box_y = nx, ny
                        gx, gy, gw, gd = nx + box_w, ny, gap, box_d
                        gap_side = 4
                        success = True

                if (
                    not success
                    and gap > 0
                    and _check_gap(grid, nx, ny, gap, box_d, W_bound, H_bound)
                ):
                    if _check_solid(grid, nx + gap, ny, box_w, box_d, W_bound, H_bound):
                        box_x, box_y = nx + gap, ny
                        gx, gy, gw, gd = nx, ny, gap, box_d
                        gap_side = 3
                        success = True

            if success:
                if has_ceil and not _ceiling_ok(ceil_map, box_x, box_w, h, W_bound):
                    continue

                _paint_solid(grid, box_x, box_y, box_w, box_d)
                _paint_gap(grid, gx, gy, gw, gd)

                export_x, export_y = box_x, box_y
                if is_rotated:
                    export_x = box_x + orig_d

                placed_bays.append(
                    (
                        tid,
                        box_x,
                        box_y,
                        export_x,
                        export_y,
                        angle,
                        box_w,
                        box_d,
                        h,
                        gap,
                        gap_side,
                        nl,
                        pr,
                    )
                )
                l_price += pr
                l_loads += nl
                l_area += orig_w * orig_d

                occupied_w = max(box_x + box_w, gx + gw) - nx
                curr_x = nx + occupied_w
                curr_y = ny
                bay_placed = True
                break

        if not bay_placed:
            grid[ny, nx] = DEAD
            curr_x = nx + 1
            curr_y = ny
            if curr_x >= W_bound:
                curr_x, curr_y = 0, ny + 1

    return placed_bays, l_price, l_loads, l_area


# ═══════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════
@dataclass
class PlacedBay:
    type_id: int
    aabb_x: int
    aabb_y: int
    export_x: int
    export_y: int
    angle: float
    aabb_w: int
    aabb_d: int
    h: int
    gap: int
    gap_side: int
    nl: int
    pr: int


# ═══════════════════════════════════════════════════════
# MAIN SOLVER CLASS
# ═══════════════════════════════════════════════════════
class FastSolver:
    def __init__(self, wh):
        self.wh = wh
        self.H = int(wh.grid.shape[0])
        self.W = int(wh.grid.shape[1])

        self.wh.grid[self.wh.grid >= 1] = WALL
        self.warehouse_area = float(np.count_nonzero(self.wh.grid < WALL))

        self._has_ceiling = bool(np.any(wh.ceiling_map > 0))
        if self._has_ceiling:
            self.wh.ceiling_map[self.wh.ceiling_map == 0] = 999999

        self.placed: List[PlacedBay] = []
        self.tot_price = 0
        self.tot_loads = 0
        self.tot_area = 0
        self.best_q = float("inf")

        self._cat = {
            int(row[0]): (
                int(row[1]),
                int(row[2]),
                int(row[3]),
                int(row[4]),
                int(row[5]),
                int(row[6]),
            )
            for row in wh.bay_catalogue
        }
        self.tids = list(self._cat.keys())

    def score(self) -> float:
        if self.tot_loads == 0:
            return float("inf")
        r = self.tot_price / self.tot_loads
        return r ** (2.0 - (self.tot_area / self.warehouse_area))

    def run_parallel_grasp(self, time_budget: float):
        num_threads = multiprocessing.cpu_count()
        t0 = time.perf_counter()

        base_v_bays = []
        for tid in self.tids:
            orig_w, orig_d, h, gap, nl, pr = self._cat[tid]
            if nl == 0:
                continue

            eff = nl / pr if pr > 0 else 0
            area = orig_w * orig_d
            base_v_bays.append(
                (tid, 0.0, orig_w, orig_d, orig_w, orig_d, h, gap, nl, pr, eff, area)
            )
            if orig_w != orig_d:
                base_v_bays.append(
                    (
                        tid,
                        90.0,
                        orig_w,
                        orig_d,
                        orig_d,
                        orig_w,
                        h,
                        gap,
                        nl,
                        pr,
                        eff,
                        area,
                    )
                )

        pristine_grid = np.copy(self.wh.grid)
        ceil_map = self.wh.ceiling_map.astype(np.int32)
        has_ceil = self._has_ceiling
        W_bound, H_bound = self.W, self.H

        def worker(thread_id):
            best_local_score = float("inf")
            best_local_placed = []
            best_local_pr, best_local_nl, best_local_ar = 0, 0, 0

            random.seed(int(time.time() * 1000) + thread_id * 738)
            strategy = thread_id % 4

            # Array estático para el Gravel Sweep (Las cajas más enanas primero)
            filler_bays = sorted(base_v_bays, key=lambda b: (b[11], -b[10]))
            arr_filler = np.array(filler_bays, dtype=np.float32)

            iteration = 0
            no_improve = 0
            MAX_NO_IMPROVE = 75  # <-- EARLY STOPPING: 75 intentos fallidos = ¡Ríndete y pasa al siguiente caso!

            # BUCLE MÁGICO con salida rápida
            while (time.perf_counter() - t0) < time_budget:
                grid = np.copy(pristine_grid)
                v_bays = list(base_v_bays)

                # Iteración 0 sin ruido. Iteraciones siguientes con ruido.
                if iteration > 0:
                    for i in range(len(v_bays)):
                        v = list(v_bays[i])
                        v[10] *= random.uniform(0.7, 1.3)
                        v[11] *= random.uniform(0.7, 1.3)
                        v_bays[i] = tuple(v)

                if strategy == 0:
                    v_bays.sort(key=lambda b: (b[10], b[11]), reverse=True)
                elif strategy == 1:
                    v_bays.sort(key=lambda b: (int(b[5] / 2), b[10]), reverse=True)
                elif strategy == 2:
                    v_bays.sort(key=lambda b: (b[11], b[10]), reverse=True)
                elif strategy == 3:
                    v_bays.sort(key=lambda b: b[10] * b[11], reverse=True)

                # 1. Sweep Principal (Velocidad C++)
                arr_primary = np.array(v_bays, dtype=np.float32)
                tuples_1, p1, l1, a1 = _run_sweep_pass(
                    grid, arr_primary, W_bound, H_bound, ceil_map, has_ceil
                )

                # 2. Gravel Sweep (Relleno Fino EXTREMO)
                grid[grid == DEAD] = FREE
                tuples_2, p2, l2, a2 = _run_sweep_pass(
                    grid, arr_filler, W_bound, H_bound, ceil_map, has_ceil
                )

                # Evaluación
                l_loads = l1 + l2
                if l_loads > 0:
                    l_price = p1 + p2
                    l_area = a1 + a2
                    score = (l_price / l_loads) ** (
                        2.0 - (l_area / self.warehouse_area)
                    )

                    if score < best_local_score:
                        best_local_score = score
                        best_local_placed = tuples_1 + tuples_2
                        best_local_pr = l_price
                        best_local_nl = l_loads
                        best_local_ar = l_area
                        no_improve = 0  # Hemos mejorado, reseteamos el contador
                    else:
                        no_improve += 1  # No mejoramos

                # LA MAGIA DE LA VELOCIDAD: Si tocamos techo, abortamos el hilo.
                if no_improve >= MAX_NO_IMPROVE:
                    break

                iteration += 1

            final_placed = [
                PlacedBay(
                    t[0],
                    t[1],
                    t[2],
                    t[3],
                    t[4],
                    t[5],
                    t[6],
                    t[7],
                    t[8],
                    t[9],
                    t[10],
                    t[11],
                    t[12],
                )
                for t in best_local_placed
            ]
            return (
                best_local_score,
                final_placed,
                best_local_pr,
                best_local_nl,
                best_local_ar,
            )

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in futures:
                score, l_placed, l_pr, l_nl, l_ar = future.result()
                if score < self.best_q:
                    self.best_q = score
                    self.placed = l_placed
                    self.tot_price = l_pr
                    self.tot_loads = l_nl
                    self.tot_area = l_ar

    def export_solution(self) -> List[Tuple]:
        return [(b.type_id, b.export_x, b.export_y, int(b.angle)) for b in self.placed]

    def plot(
        self,
        coords: np.ndarray,
        obstacles: np.ndarray,
        gcd: int = 1,
        save_path: str = None,
    ):
        try:
            import matplotlib

            if save_path:
                matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from matplotlib.colors import to_rgba
        except ImportError:
            return

        fig, ax = plt.subplots(figsize=(14, 14), facecolor="#1e1e1e")
        ax.set_facecolor("#2d2d2d")

        if coords.size > 0:
            x_c, y_c = coords[:, 0], coords[:, 1]
            ax.plot(
                np.append(x_c, x_c[0]),
                np.append(y_c, y_c[0]),
                color="#00ffcc",
                lw=2.5,
                label="Perímetro",
            )

        if obstacles.size > 0:
            for i, obs in enumerate(obstacles):
                ox, oy, ow, od = obs
                ax.add_patch(
                    mpatches.Rectangle(
                        (ox, oy),
                        ow,
                        od,
                        lw=0,
                        facecolor="#ff3366",
                        alpha=0.6,
                        label="Obstáculo" if i == 0 else "",
                    )
                )

        import matplotlib.cm as cm

        cmap = cm.get_cmap("tab20")
        type_colors = {
            tid: cmap(i % 20) for i, tid in enumerate(sorted(self._cat.keys()))
        }

        for b in self.placed:
            color = type_colors.get(b.type_id, "gray")
            rx, ry = b.aabb_x * gcd, b.aabb_y * gcd
            rw, rd = b.aabb_w * gcd, b.aabb_d * gcd
            rgap = b.gap * gcd

            rect = mpatches.Rectangle(
                (rx, ry),
                rw,
                rd,
                facecolor=to_rgba(color, 0.8),
                edgecolor="white",
                lw=1.0,
            )
            ax.add_patch(rect)

            if rgap > 0 and b.gap_side > 0 and b.gap_side != 5:
                gx, gy, gw, gd = 0, 0, 0, 0
                if b.gap_side == 1:
                    gx, gy, gw, gd = rx, ry + rd, rw, rgap
                elif b.gap_side == 2:
                    gx, gy, gw, gd = rx, ry - rgap, rw, rgap
                elif b.gap_side == 3:
                    gx, gy, gw, gd = rx - rgap, ry, rgap, rd
                elif b.gap_side == 4:
                    gx, gy, gw, gd = rx + rw, ry, rgap, rd
                ax.add_patch(
                    mpatches.Rectangle(
                        (gx, gy),
                        gw,
                        gd,
                        facecolor="none",
                        edgecolor="#aaaaaa",
                        hatch="////",
                        lw=0.5,
                    )
                )

            cx, cy = rx + rw / 2, ry + rd / 2
            ax.text(
                cx,
                cy,
                f"{b.type_id}\\n{int(b.angle)}º",
                ha="center",
                va="center",
                fontsize=7,
                fontweight="bold",
                color="white",
            )

        if coords.size > 0:
            ax.set_xlim(min(coords[:, 0]) - 500, max(coords[:, 0]) + 500)
            ax.set_ylim(min(coords[:, 1]) - 500, max(coords[:, 1]) + 500)
        else:
            ax.set_xlim(0, self.W * gcd)
            ax.set_ylim(0, self.H * gcd)

        ax.set_aspect("equal")
        ax.set_title(
            f"Solución HackUPC | {len(self.placed)} Bays | Q={self.score():.2f}",
            color="white",
            fontsize=18,
            pad=20,
        )
        ax.tick_params(colors="white")

        try:
            plt.tight_layout()
        except Exception:
            pass

        if save_path:
            plt.savefig(
                save_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor()
            )
            plt.close(fig)
            plt.clf()
