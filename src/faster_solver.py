"""
fast_solver.py — Ultra-Optimized Warehouse Optimizer
====================================================
Módulo de producción. Diseñado para velocidad pura.
Cero instanciaciones en bucles internos, Trig Caching y O(1) Arrays.
"""

import math
import time
import random
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from numba import njit

# ═══════════════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL
# ═══════════════════════════════════════════════════════
GREEDY_ANGLES = (0.0, 90.0, 180.0, 270.0)
SA_ANGLES = tuple(float(x) for x in range(0, 360, 15))
TIMER_BATCH = 200
MIN_BAYS = 1


# ═══════════════════════════════════════════════════════
# NUMBA KERNELS (JIT COMPILADOS Y DESENROLLADOS)
# ═══════════════════════════════════════════════════════

@njit(fastmath=True, cache=True)
def _rotated_bbox_fast(x: float, y: float, w: float, d: float, ca: float, sa: float):
    """Loop Unrolling: Sin bucles for. Cálculo directo en registros del procesador."""
    # Vértices pre-calculados (Optimizando multiplicaciones por 0)
    rx1, ry1 = x, y
    rx2, ry2 = w * ca + x, w * sa + y
    rx3, ry3 = w * ca - d * sa + x, w * sa + d * ca + y
    rx4, ry4 = -d * sa + x, d * ca + y

    min_rx = min(rx1, rx2, rx3, rx4)
    max_rx = max(rx1, rx2, rx3, rx4)
    min_ry = min(ry1, ry2, ry3, ry4)
    max_ry = max(ry1, ry2, ry3, ry4)

    return (int(math.floor(min_rx)), int(math.floor(min_ry)),
            int(math.ceil(max_rx)), int(math.ceil(max_ry)))


@njit(fastmath=True, cache=True)
def _check_rotated_solid_fast(grid: np.ndarray, x: float, y: float, w: float, d: float,
                              ca: float, sa: float, H: int, W: int) -> bool:
    """Valida el cuerpo. Recibe ca/sa cacheados."""
    bx0, by0, bx1, by1 = _rotated_bbox_fast(x, y, w, d, ca, sa)
    if bx0 < 0 or by0 < 0 or bx1 >= W or by1 >= H: return False

    for cy in range(by0, by1 + 1):
        for cx in range(bx0, bx1 + 1):
            lx = (cx - x) * ca + (cy - y) * sa
            ly = -(cx - x) * sa + (cy - y) * ca
            if -0.1 <= lx <= w + 0.1 and -0.1 <= ly <= d + 0.1:
                if grid[cy, cx] != 0:
                    return False
    return True


@njit(fastmath=True, cache=True)
def _check_rotated_gap_area_fast(grid: np.ndarray, x: float, y: float, w: float, d: float,
                                 ca: float, sa: float, H: int, W: int) -> bool:
    bx0, by0, bx1, by1 = _rotated_bbox_fast(x, y, w, d, ca, sa)
    if bx0 < 0 or by0 < 0 or bx1 >= W or by1 >= H: return False

    for cy in range(by0, by1 + 1):
        for cx in range(bx0, bx1 + 1):
            lx = (cx - x) * ca + (cy - y) * sa
            ly = -(cx - x) * sa + (cy - y) * ca
            if -0.1 <= lx <= w + 0.1 and -0.1 <= ly <= d + 0.1:
                if grid[cy, cx] >= 100:
                    return False
    return True


@njit(fastmath=True, cache=True)
def _find_valid_gap_fast(grid: np.ndarray, x: float, y: float, w: float, d: float,
                         gap: float, ca: float, sa: float, H: int, W_grid: int) -> int:
    """Busca gap usando las proyecciones trigonométricas pre-calculadas"""
    if gap <= 0: return 0

    wx1, wy1 = x + gap * sa, y - gap * ca
    if _check_rotated_gap_area_fast(grid, wx1, wy1, w, gap, ca, sa, H, W_grid): return 1

    wx2, wy2 = x - d * sa, y + d * ca
    if _check_rotated_gap_area_fast(grid, wx2, wy2, w, gap, ca, sa, H, W_grid): return 2

    wx3, wy3 = x - gap * ca, y - gap * sa
    if _check_rotated_gap_area_fast(grid, wx3, wy3, gap, d, ca, sa, H, W_grid): return 3

    wx4, wy4 = x + w * ca, y + w * sa
    if _check_rotated_gap_area_fast(grid, wx4, wy4, gap, d, ca, sa, H, W_grid): return 4

    return -1


@njit(fastmath=True, cache=True)
def _paint_rotated_fast(grid: np.ndarray, x: float, y: float, w: float, d: float,
                        ca: float, sa: float, H: int, W: int, delta: int):
    bx0, by0, bx1, by1 = _rotated_bbox_fast(x, y, w, d, ca, sa)
    bx0, by0 = max(0, bx0), max(0, by0)
    bx1, by1 = min(W - 1, bx1), min(H - 1, by1)

    for cy in range(by0, by1 + 1):
        for cx in range(bx0, bx1 + 1):
            lx = (cx - x) * ca + (cy - y) * sa
            ly = -(cx - x) * sa + (cy - y) * ca
            if -0.1 <= lx <= w + 0.1 and -0.1 <= ly <= d + 0.1:
                grid[cy, cx] += delta


@njit(fastmath=True, cache=True)
def _paint_gap_side_fast(grid: np.ndarray, x: float, y: float, w: float, d: float,
                         gap: float, ca: float, sa: float, H: int, W_grid: int, side: int, delta: int):
    if side == 0 or gap <= 0: return

    if side == 1:
        gx, gy, gw, gd = x + gap * sa, y - gap * ca, w, gap
    elif side == 2:
        gx, gy, gw, gd = x - d * sa, y + d * ca, w, gap
    elif side == 3:
        gx, gy, gw, gd = x - gap * ca, y - gap * sa, gap, d
    elif side == 4:
        gx, gy, gw, gd = x + w * ca, y + w * sa, gap, d
    else:
        return

    _paint_rotated_fast(grid, gx, gy, gw, gd, ca, sa, H, W_grid, delta)


@njit(fastmath=True, cache=True)
def _ceiling_ok_fast(ceiling_map: np.ndarray, x: float, y: float, w: float, d: float,
                     ca: float, sa: float, bay_height: int, max_x: int) -> bool:
    bx0, _, bx1, _ = _rotated_bbox_fast(x, y, w, d, ca, sa)
    cx_start, cx_end = max(0, bx0), min(max_x, bx1 + 1)
    if cx_start >= cx_end: return False

    for cx in range(cx_start, cx_end):
        if ceiling_map[cx] < bay_height: return False
    return True


# ═══════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════

@dataclass
class PlacedBay:
    __slots__ = ['type_id', 'x', 'y', 'angle', 'width', 'depth', 'height', 'gap', 'nloads', 'price', 'gap_side']
    type_id: int
    x: int;
    y: int;
    angle: float
    width: int;
    depth: int;
    height: int
    gap: int;
    nloads: int;
    price: int
    gap_side: int

    @property
    def area(self) -> int:
        return self.width * self.depth


# ═══════════════════════════════════════════════════════
# MAIN SOLVER CLASS
# ═══════════════════════════════════════════════════════

class FastSolver:
    def __init__(self, wh, weights: List[int] = None):
        """Inicializa el motor pasando el objeto Warehouse."""
        self.wh = wh
        self.H = int(wh.grid.shape[0])
        self.W = int(wh.grid.shape[1])

        if self.wh.obs_tensor.size > 0:
            for obs in self.wh.obs_tensor:
                ox, oy, ow, od = obs
                self.wh.grid[max(0, oy):oy + od, max(0, ox):ox + ow] = 10000

        self.warehouse_area = float(np.count_nonzero(wh.grid < 10000))
        self._has_ceiling = bool(np.any(wh.ceiling_map > 0))

        self.placed: List[PlacedBay] = []
        self.tot_price = 0
        self.tot_loads = 0
        self.tot_area = 0

        # Catálogo indexado para acceso rápido
        self._cat = {
            int(row[0]): (int(row[1]), int(row[2]), int(row[3]), int(row[4]), int(row[5]), int(row[6]))
            for row in wh.bay_catalogue
        }
        self.tids = list(self._cat.keys())

        # O(1) Move Selection (Roulette Wheel)
        weights = weights or [60, 2, 20, 8, 10]
        self.move_pool = []
        for i, weight in enumerate(weights):
            self.move_pool.extend([i] * weight)

    # ── STATE & SCORE ───────────────────────────────────────────────────────

    def score(self) -> float:
        if self.tot_loads == 0: return float('inf')
        r = self.tot_price / self.tot_loads
        return r ** (2.0 - (self.tot_area / self.warehouse_area))

    def _dQ(self, dp: int, dl: int, da: int) -> float:
        if (self.tot_loads + dl) == 0: return float('inf')
        r_new = (self.tot_price + dp) / (self.tot_loads + dl)
        r_old = self.tot_price / self.tot_loads if self.tot_loads > 0 else float('inf')
        q_new = r_new ** (2.0 - ((self.tot_area + da) / self.warehouse_area))
        q_old = r_old ** (2.0 - (self.tot_area / self.warehouse_area))
        return q_new - q_old

    # ── HIGH-PERFORMANCE VALIDATION & PAINTING ──────────────────────────────

    def _check_primitive(self, x: float, y: float, w: float, d: float, gap: float,
                         h: int, ca: float, sa: float) -> int:
        """Valida a baja cota (C-level). Retorna el gap_side si es válido, -1 si falla."""
        if not _check_rotated_solid_fast(self.wh.grid, x, y, w, d, ca, sa, self.H, self.W): return -1
        if self._has_ceiling and not _ceiling_ok_fast(self.wh.ceiling_map, x, y, w, d, ca, sa, h,
                                                      int(self.wh.max_x)): return -1
        if gap > 0:
            return _find_valid_gap_fast(self.wh.grid, x, y, w, d, gap, ca, sa, self.H, self.W)
        return 0

    def _paint_primitive(self, x: float, y: float, w: float, d: float, gap: float,
                         ca: float, sa: float, gap_side: int, sign: int):
        _paint_rotated_fast(self.wh.grid, x, y, w, d, ca, sa, self.H, self.W, 100 * sign)
        if gap > 0 and gap_side > 0:
            _paint_gap_side_fast(self.wh.grid, x, y, w, d, gap, ca, sa, self.H, self.W, gap_side, 1 * sign)

    def _add_bay(self, b: PlacedBay):
        rad = math.radians(b.angle)
        self._paint_primitive(float(b.x), float(b.y), float(b.width), float(b.depth), float(b.gap),
                              math.cos(rad), math.sin(rad), b.gap_side, 1)
        self.placed.append(b)
        self.tot_price += b.price
        self.tot_loads += b.nloads
        self.tot_area += b.area

    def _remove_bay(self, idx: int) -> PlacedBay:
        b = self.placed.pop(idx)
        rad = math.radians(b.angle)
        self._paint_primitive(float(b.x), float(b.y), float(b.width), float(b.depth), float(b.gap),
                              math.cos(rad), math.sin(rad), b.gap_side, -1)
        self.tot_price -= b.price
        self.tot_loads -= b.nloads
        self.tot_area -= b.area
        return b

    def _snap(self):
        return ([(b.type_id, b.x, b.y, b.angle, b.width, b.depth, b.height, b.gap, b.nloads, b.price, b.gap_side)
                 for b in self.placed], self.tot_price, self.tot_loads, self.tot_area)

    def _restore(self, snap):
        blist, tp, tl, ta = snap
        for i in range(len(self.placed) - 1, -1, -1): self._remove_bay(i)
        for s in blist: self._add_bay(PlacedBay(*s))

    # ── ALGORITHM PHASES ────────────────────────────────────────────────────

    def run_greedy(self, time_budget: float):
        t0 = time.perf_counter()
        types_sorted = sorted(self.tids, key=lambda tid: self._cat[tid][5] / max(1, self._cat[tid][4]), reverse=True)
        placed_any = True

        # Pre-caché trigonométrico para Greedy
        trig_cache = {a: (math.cos(math.radians(a)), math.sin(math.radians(a))) for a in GREEDY_ANGLES}

        while placed_any and (time.perf_counter() - t0) < time_budget:
            placed_any = False
            for tid in types_sorted:
                if (time.perf_counter() - t0) >= time_budget: break
                w, d, h, gap, nl, pr = self._cat[tid]
                area = w * d

                for angle in GREEDY_ANGLES:
                    if (time.perf_counter() - t0) >= time_budget: break
                    ca, sa = trig_cache[angle]
                    bx0, by0, bx1, by1 = _rotated_bbox_fast(0.0, 0.0, float(w), float(d), ca, sa)
                    step_x, step_y = max(100, (bx1 - bx0) // 3), max(100, (by1 - by0) // 3)

                    y = 0
                    while y + (by1 - by0) <= self.H:
                        x = 0
                        while x + (bx1 - bx0) <= self.W:
                            gap_side = self._check_primitive(float(x), float(y), float(w), float(d), float(gap), h, ca,
                                                             sa)
                            if gap_side != -1:
                                self._paint_primitive(float(x), float(y), float(w), float(d), float(gap), ca, sa,
                                                      gap_side, 1)
                                self.placed.append(PlacedBay(tid, x, y, angle, w, d, h, gap, nl, pr, gap_side))
                                self.tot_price += pr
                                self.tot_loads += nl
                                self.tot_area += area
                                placed_any = True
                            x += step_x
                        y += step_y

    def run_sa(self, time_budget: float):
        t0 = time.perf_counter()
        iters = 0
        T_init = 1.0 if not self.placed else abs(
            self._dQ(-self.placed[0].price, -self.placed[0].nloads, -self.placed[0].area)) / math.log(20.0)
        T_init = max(1.0, T_init)

        T = T_init
        best_q = self.score()
        best_snp = self._snap()

        # Cache trig para ángulos de SA
        trig_cache = {a: (math.cos(math.radians(a)), math.sin(math.radians(a))) for a in SA_ANGLES}
        greedy_trig = {a: (math.cos(math.radians(a)), math.sin(math.radians(a))) for a in GREEDY_ANGLES}

        running = True
        while running:
            for _ in range(TIMER_BATCH):
                iters += 1
                move = random.choice(self.move_pool)

                if move == 0:  # ADD
                    tid = random.choice(self.tids)
                    angle = random.choice(GREEDY_ANGLES) if random.random() < 0.7 else random.choice(SA_ANGLES)
                    ca, sa = greedy_trig[angle] if angle in greedy_trig else trig_cache[angle]

                    x, y = random.randint(0, self.W - 1), random.randint(0, self.H - 1)
                    w, d, h, gap, nl, pr = self._cat[tid]

                    # Zero-allocation check
                    gap_side = self._check_primitive(float(x), float(y), float(w), float(d), float(gap), h, ca, sa)
                    if gap_side != -1:
                        dq = self._dQ(pr, nl, w * d)
                        if dq <= 0.0 or random.random() < math.exp(-dq / T):
                            self._paint_primitive(float(x), float(y), float(w), float(d), float(gap), ca, sa, gap_side,
                                                  1)
                            self.placed.append(PlacedBay(tid, x, y, angle, w, d, h, gap, nl, pr, gap_side))
                            self.tot_price += pr
                            self.tot_loads += nl
                            self.tot_area += w * d

                elif move == 1:  # REMOVE
                    if len(self.placed) > MIN_BAYS:
                        idx = random.randrange(len(self.placed))
                        b = self.placed[idx]
                        dq = self._dQ(-b.price, -b.nloads, -b.area)
                        if dq <= 0.0 or random.random() < math.exp(-dq / T):
                            self._remove_bay(idx)

                elif move == 2:  # MOVE
                    if not self.placed: continue
                    idx = random.randrange(len(self.placed))
                    old = self.placed[idx]

                    nx = max(0, min(self.W - 1, old.x + random.randint(-200, 200)))
                    ny = max(0, min(self.H - 1, old.y + random.randint(-200, 200)))

                    ca, sa = math.cos(math.radians(old.angle)), math.sin(math.radians(old.angle))

                    self._remove_bay(idx)
                    gap_side = self._check_primitive(float(nx), float(ny), float(old.width), float(old.depth),
                                                     float(old.gap), old.height, ca, sa)
                    if gap_side != -1:
                        self._paint_primitive(float(nx), float(ny), float(old.width), float(old.depth), float(old.gap),
                                              ca, sa, gap_side, 1)
                        self.placed.append(
                            PlacedBay(old.type_id, nx, ny, old.angle, old.width, old.depth, old.height, old.gap,
                                      old.nloads, old.price, gap_side))
                        self.tot_price += old.price
                        self.tot_loads += old.nloads
                        self.tot_area += old.area
                    else:
                        self._add_bay(old)

                elif move == 3:  # ROTATE
                    if not self.placed: continue
                    idx = random.randrange(len(self.placed))
                    old = self.placed[idx]
                    new_a = (old.angle + random.choice(
                        (-15.0, 15.0))) % 360.0 if random.random() < 0.5 else random.choice(SA_ANGLES)
                    if new_a == old.angle: continue

                    ca, sa = math.cos(math.radians(new_a)), math.sin(math.radians(new_a))
                    self._remove_bay(idx)
                    gap_side = self._check_primitive(float(old.x), float(old.y), float(old.width), float(old.depth),
                                                     float(old.gap), old.height, ca, sa)
                    if gap_side != -1:
                        self._paint_primitive(float(old.x), float(old.y), float(old.width), float(old.depth),
                                              float(old.gap), ca, sa, gap_side, 1)
                        self.placed.append(
                            PlacedBay(old.type_id, old.x, old.y, new_a, old.width, old.depth, old.height, old.gap,
                                      old.nloads, old.price, gap_side))
                        self.tot_price += old.price
                        self.tot_loads += old.nloads
                        self.tot_area += old.area
                    else:
                        self._add_bay(old)

                elif move == 4:  # TYPE SWAP
                    if not self.placed: continue
                    idx = random.randrange(len(self.placed))
                    old = self.placed[idx]
                    new_tid = random.choice(self.tids)
                    if new_tid == old.type_id: continue

                    w, d, h, gap, nl, pr = self._cat[new_tid]
                    ca, sa = math.cos(math.radians(old.angle)), math.sin(math.radians(old.angle))

                    self._remove_bay(idx)
                    gap_side = self._check_primitive(float(old.x), float(old.y), float(w), float(d), float(gap), h, ca,
                                                     sa)
                    if gap_side != -1:
                        dq = self._dQ(pr - old.price, nl - old.nloads, (w * d) - old.area)
                        if dq <= 0.0 or random.random() < math.exp(-dq / T):
                            self._paint_primitive(float(old.x), float(old.y), float(w), float(d), float(gap), ca, sa,
                                                  gap_side, 1)
                            self.placed.append(
                                PlacedBay(new_tid, old.x, old.y, old.angle, w, d, h, gap, nl, pr, gap_side))
                            self.tot_price += pr;
                            self.tot_loads += nl;
                            self.tot_area += w * d
                            continue
                    self._add_bay(old)

                cq = self.score()
                if cq < best_q:
                    best_q = cq
                    best_snp = self._snap()

            elapsed = time.perf_counter() - t0
            if elapsed >= time_budget:
                running = False
            else:
                T = max(1e-9, T_init * (0.001 ** (elapsed / time_budget)))

        self._restore(best_snp)

    def export_solution(self) -> List[Tuple]:
        """Devuelve la lista final para ser volcada al fichero output"""
        return [(b.type_id, b.x, b.y, int(b.angle)) for b in self.placed]