"""
faster_solver.py — Ultra-Optimized Warehouse Optimizer
======================================================
Implementa Fast Orthogonal Scanline (Bottom-Left Fill) y
Parallel GRASP (Multi-Start Constructive Heuristics).
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
# NUMBA KERNELS (ORTOGONALES)
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
    if x + w > W or y + d > H: return False
    for iy in range(y, y + d):
        for ix in range(x, x + w):
            val = grid[iy, ix]
            if val == GAP or val == SOLID or val >= WALL:
                return False
    return True


@njit(fastmath=True, cache=True, nogil=True)
def _check_gap(grid, x, y, w, d, W, H):
    if x < 0 or y < 0 or x + w > W or y + d > H: return False
    for iy in range(y, y + d):
        for ix in range(x, x + w):
            val = grid[iy, ix]
            if val == SOLID or val >= WALL:
                return False
    return True


@njit(fastmath=True, cache=True, nogil=True)
def _find_valid_gap(grid, x, y, w, d, gap, W, H, is_rotated):
    if gap <= 0: return 5

    # REGLA DEL HACKATHON: "El Gap solo puede estar en las caras del Width"
    if not is_rotated:
        # Angle 0: El Width es horizontal. El pasillo debe ir Arriba o Abajo.
        if _check_gap(grid, x, y - gap, w, gap, W, H): return 2  # Abajo
        if _check_gap(grid, x, y + d, w, gap, W, H): return 1  # Arriba
    else:
        # Angle 90: El Width ahora es vertical. El pasillo debe ir a Derecha o Izquierda.
        if _check_gap(grid, x - gap, y, gap, d, W, H): return 3  # Izquierda
        if _check_gap(grid, x + w, y, gap, d, W, H): return 4  # Derecha

    return -1


@njit(fastmath=True, cache=True, nogil=True)
def _paint_solid(grid, x, y, w, d):
    for iy in range(y, y + d):
        for ix in range(x, x + w):
            grid[iy, ix] = SOLID


@njit(fastmath=True, cache=True, nogil=True)
def _paint_gap_side(grid, x, y, w, d, gap, side):
    if side == 0 or gap <= 0 or side == 5: return
    gx, gy, gw, gd = 0, 0, 0, 0

    if side == 1:
        gx, gy, gw, gd = x, y + d, w, gap
    elif side == 2:
        gx, gy, gw, gd = x, y - gap, w, gap
    elif side == 3:
        gx, gy, gw, gd = x - gap, y, gap, d
    elif side == 4:
        gx, gy, gw, gd = x + w, y, gap, d

    for iy in range(gy, gy + gd):
        for ix in range(gx, gx + gw):
            if grid[iy, ix] == FREE or grid[iy, ix] == DEAD:
                grid[iy, ix] = GAP


@njit(fastmath=True, cache=True, nogil=True)
def _ceiling_ok(ceiling_map, x, w, h, W):
    x_end = min(W, x + w)
    for cx in range(x, x_end):
        if ceiling_map[cx] < h: return False
    return True


# ═══════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════
@dataclass
class PlacedBay:
    type_id: int;
    aabb_x: int;
    aabb_y: int;
    export_x: int;
    export_y: int
    angle: float;
    aabb_w: int;
    aabb_d: int;
    h: int;
    gap: int;
    gap_side: int;
    nl: int;
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

        self.placed: List[PlacedBay] = []
        self.tot_price = 0
        self.tot_loads = 0
        self.tot_area = 0
        self.best_q = float('inf')

        self._cat = {
            int(row[0]): (int(row[1]), int(row[2]), int(row[3]), int(row[4]), int(row[5]), int(row[6]))
            for row in wh.bay_catalogue
        }
        self.tids = list(self._cat.keys())

    def score(self) -> float:
        if self.tot_loads == 0: return float('inf')
        r = self.tot_price / self.tot_loads
        return r ** (2.0 - (self.tot_area / self.warehouse_area))

    def run_parallel_grasp(self, time_budget: float):
        num_threads = multiprocessing.cpu_count()
        t0 = time.perf_counter()

        base_v_bays = []
        for tid in self.tids:
            orig_w, orig_d, h, gap, nl, pr = self._cat[tid]
            if nl == 0: continue

            eff = nl / pr if pr > 0 else 0
            area = orig_w * orig_d

            # Unrotated
            base_v_bays.append((tid, 0.0, orig_w, orig_d, orig_w, orig_d, h, gap, nl, pr, eff, area))
            # Rotated
            if orig_w != orig_d:
                base_v_bays.append((tid, 90.0, orig_w, orig_d, orig_d, orig_w, h, gap, nl, pr, eff, area))

        pristine_grid = np.copy(self.wh.grid)

        def worker(thread_id):
            grid = np.copy(pristine_grid)
            local_placed = []
            l_price, l_loads, l_area = 0, 0, 0

            v_bays = list(base_v_bays)
            if thread_id > 0:
                random.seed(int(time.time() * 1000) + thread_id * 738)
                for i in range(len(v_bays)):
                    v = list(v_bays[i])
                    v[10] *= random.uniform(0.95, 1.05)
                    v_bays[i] = tuple(v)

            # Priorizamos cajas de Máxima Eficiencia -> Mayor Área
            v_bays.sort(key=lambda b: (b[10], b[11]), reverse=True)

            curr_x, curr_y = 0, 0
            while curr_y < self.H and (time.perf_counter() - t0) < time_budget:
                nx, ny = _find_next_free(grid, curr_x, curr_y, self.W, self.H)
                if nx == -1: break

                bay_placed = False
                for bay in v_bays:
                    tid, angle, orig_w, orig_d, aabb_w, aabb_d, h, gap, nl, pr, eff, area = bay
                    is_rotated = (angle == 90.0)

                    if self._has_ceiling and not _ceiling_ok(self.wh.ceiling_map, nx, aabb_w, h, self.W):
                        continue

                    if _check_solid(grid, nx, ny, aabb_w, aabb_d, self.W, self.H):
                        gap_side = _find_valid_gap(grid, nx, ny, aabb_w, aabb_d, gap, self.W, self.H, is_rotated)

                        if gap_side != -1:
                            _paint_solid(grid, nx, ny, aabb_w, aabb_d)
                            _paint_gap_side(grid, nx, ny, aabb_w, aabb_d, gap, gap_side)

                            export_x, export_y = nx, ny
                            if is_rotated: export_x = nx + orig_d

                            local_placed.append(
                                PlacedBay(tid, nx, ny, export_x, export_y, angle, aabb_w, aabb_d, h, gap, gap_side, nl,
                                          pr))
                            l_price += pr;
                            l_loads += nl;
                            l_area += area

                            curr_x = nx + aabb_w
                            curr_y = ny
                            bay_placed = True
                            break

                if not bay_placed:
                    grid[ny, nx] = DEAD
                    curr_x = nx + 1
                    curr_y = ny
                    if curr_x >= self.W:
                        curr_x, curr_y = 0, ny + 1

            score = float('inf')
            if l_loads > 0:
                score = (l_price / l_loads) ** (2.0 - (l_area / self.warehouse_area))

            return score, local_placed, l_price, l_loads, l_area

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in futures:
                score, l_placed, l_pr, l_nl, l_ar = future.result()
                if score < self.best_q:
                    self.best_q = score
                    self.placed = l_placed
                    self.tot_price = l_pr;
                    self.tot_loads = l_nl;
                    self.tot_area = l_ar

    def export_solution(self) -> List[Tuple]:
        return [(b.type_id, b.export_x, b.export_y, int(b.angle)) for b in self.placed]

    def plot(self, coords: np.ndarray, obstacles: np.ndarray, gcd: int = 1, save_path: str = None):
        try:
            import matplotlib
            if save_path: matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from matplotlib.colors import to_rgba
        except ImportError:
            return

        fig, ax = plt.subplots(figsize=(14, 14), facecolor='#1e1e1e')
        ax.set_facecolor('#2d2d2d')

        if coords.size > 0:
            x_c, y_c = coords[:, 0], coords[:, 1]
            ax.plot(np.append(x_c, x_c[0]), np.append(y_c, y_c[0]), color='#00ffcc', lw=2.5, label='Perímetro')

        if obstacles.size > 0:
            for i, obs in enumerate(obstacles):
                ox, oy, ow, od = obs
                ax.add_patch(mpatches.Rectangle((ox, oy), ow, od, lw=0, facecolor='#ff3366', alpha=0.6,
                                                label='Obstáculo' if i == 0 else ''))

        import matplotlib.cm as cm
        cmap = cm.get_cmap('tab20')
        type_colors = {tid: cmap(i % 20) for i, tid in enumerate(sorted(self._cat.keys()))}

        for b in self.placed:
            color = type_colors.get(b.type_id, 'gray')

            # EL FIX DE ESCALA ESTÁ AQUÍ (* gcd)
            rx, ry = b.aabb_x * gcd, b.aabb_y * gcd
            rw, rd = b.aabb_w * gcd, b.aabb_d * gcd
            rgap = b.gap * gcd

            # Estantería Sólida
            rect = mpatches.Rectangle((rx, ry), rw, rd, facecolor=to_rgba(color, 0.8), edgecolor='white', lw=1.0)
            ax.add_patch(rect)

            # Pasillo
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
                    mpatches.Rectangle((gx, gy), gw, gd, facecolor='none', edgecolor='#aaaaaa', hatch='////', lw=0.5))

            cx, cy = rx + rw / 2, ry + rd / 2
            ax.text(cx, cy, f"{b.type_id}\\n{int(b.angle)}º", ha='center', va='center', fontsize=7, fontweight='bold',
                    color='white')

        if coords.size > 0:
            ax.set_xlim(min(coords[:, 0]) - 500, max(coords[:, 0]) + 500)
            ax.set_ylim(min(coords[:, 1]) - 500, max(coords[:, 1]) + 500)
        else:
            ax.set_xlim(0, self.W * gcd);
            ax.set_ylim(0, self.H * gcd)

        ax.set_aspect('equal')
        ax.set_title(f"Solución HackUPC | {len(self.placed)} Bays | Q={self.score():.2f}", color='white', fontsize=18,
                     pad=20)
        ax.tick_params(colors='white')

        try:
            plt.tight_layout()
        except Exception:
            pass

        if save_path:
            plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
            plt.close(fig);
            plt.clf()