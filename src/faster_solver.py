"""
fast_solver.py — Ultra-Optimized Warehouse Optimizer
====================================================
Implementa Row-Based Strip Packing (Big Rocks First) y
Micro-Optimizador In-Place Paralelo.
"""

import math
import time
import random
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from numba import njit

# ═══════════════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL
# ═══════════════════════════════════════════════════════
PACKING_ANGLES = (0.0, 90.0)
SA_ANGLES = (0.0, 90.0)
TIMER_BATCH = 200
MIN_BAYS = 1


# ═══════════════════════════════════════════════════════
# NUMBA KERNELS (nogil=True para liberar la CPU)
# ═══════════════════════════════════════════════════════

@njit(fastmath=True, cache=True, nogil=True)
def _rotated_bbox_fast(x: float, y: float, w: float, d: float, ca: float, sa: float):
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


@njit(fastmath=True, cache=True, nogil=True)
def _check_rotated_solid_fast(grid: np.ndarray, x: float, y: float, w: float, d: float,
                              ca: float, sa: float, H: int, W: int) -> bool:
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


@njit(fastmath=True, cache=True, nogil=True)
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


@njit(fastmath=True, cache=True, nogil=True)
def _find_valid_gap_fast(grid: np.ndarray, x: float, y: float, w: float, d: float,
                         gap: float, ca: float, sa: float, H: int, W_grid: int) -> int:
    if gap <= 0: return 0

    # Priorizamos Ejes Y para compartir pasillos y crear filas limpias
    wx2, wy2 = x - d * sa, y + d * ca
    if _check_rotated_gap_area_fast(grid, wx2, wy2, w, gap, ca, sa, H, W_grid): return 2

    wx1, wy1 = x + gap * sa, y - gap * ca
    if _check_rotated_gap_area_fast(grid, wx1, wy1, w, gap, ca, sa, H, W_grid): return 1

    wx4, wy4 = x + w * ca, y + w * sa
    if _check_rotated_gap_area_fast(grid, wx4, wy4, gap, d, ca, sa, H, W_grid): return 4

    wx3, wy3 = x - gap * ca, y - gap * sa
    if _check_rotated_gap_area_fast(grid, wx3, wy3, gap, d, ca, sa, H, W_grid): return 3

    return -1


@njit(fastmath=True, cache=True, nogil=True)
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


@njit(fastmath=True, cache=True, nogil=True)
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


@njit(fastmath=True, cache=True, nogil=True)
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
    type_id: int;
    x: int;
    y: int;
    angle: float
    width: int;
    depth: int;
    height: int
    gap: int;
    nloads: int;
    price: int;
    gap_side: int

    @property
    def area(self) -> int: return self.width * self.depth


# ═══════════════════════════════════════════════════════
# MAIN SOLVER CLASS
# ═══════════════════════════════════════════════════════

class FastSolver:
    def __init__(self, wh, weights: List[int] = None):
        self.wh = wh
        self.H = int(wh.grid.shape[0])
        self.W = int(wh.grid.shape[1])

        self.lock = threading.Lock()

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
        self.best_q = float('inf')

        self._cat = {
            int(row[0]): (int(row[1]), int(row[2]), int(row[3]), int(row[4]), int(row[5]), int(row[6]))
            for row in wh.bay_catalogue
        }
        self.tids = list(self._cat.keys())

        # SA Dedicado a Swaps locales y rellenado de micro-huecos (ADD)
        weights = weights or [15, 0, 5, 0, 80]  # [ADD, REMOVE, MOVE, ROTATE, SWAP]
        self.move_pool = []
        for i, weight in enumerate(weights):
            self.move_pool.extend([i] * weight)

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

    def _check_primitive(self, x: float, y: float, w: float, d: float, gap: float,
                         h: int, ca: float, sa: float) -> int:
        if not _check_rotated_solid_fast(self.wh.grid, x, y, w, d, ca, sa, self.H, self.W): return -1
        if self._has_ceiling and not _ceiling_ok_fast(self.wh.ceiling_map, x, y, w, d, ca, sa, h,
                                                      int(self.wh.max_x)): return -1
        if gap > 0: return _find_valid_gap_fast(self.wh.grid, x, y, w, d, gap, ca, sa, self.H, self.W)
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
        self.tot_price += b.price;
        self.tot_loads += b.nloads;
        self.tot_area += b.area

    def _remove_bay(self, idx: int) -> PlacedBay:
        b = self.placed.pop(idx)
        rad = math.radians(b.angle)
        self._paint_primitive(float(b.x), float(b.y), float(b.width), float(b.depth), float(b.gap),
                              math.cos(rad), math.sin(rad), b.gap_side, -1)
        self.tot_price -= b.price;
        self.tot_loads -= b.nloads;
        self.tot_area -= b.area
        return b

    def _snap(self):
        return ([(b.type_id, b.x, b.y, b.angle, b.width, b.depth, b.height, b.gap, b.nloads, b.price, b.gap_side)
                 for b in self.placed], self.tot_price, self.tot_loads, self.tot_area)

    def _restore(self, snap):
        blist, tp, tl, ta = snap
        for i in range(len(self.placed) - 1, -1, -1): self._remove_bay(i)
        for s in blist: self._add_bay(PlacedBay(*s))

    # ── FASE 1: ROW-BASED STRIP PACKING (2 PASADAS) ──────────────────────────
    def _sweep_grid(self, bay_types, step_fail, time_budget, t0):
        """Núcleo de barrido extraído para poder hacer pasadas múltiples."""
        trig_cache = {a: (math.cos(math.radians(a)), math.sin(math.radians(a))) for a in PACKING_ANGLES}
        y = 0.0

        while y < self.H and (time.perf_counter() - t0) < time_budget:
            x = 0.0
            current_row_depth = 0.0
            current_row_gap = 0.0
            placed_in_row = False

            while x < self.W and (time.perf_counter() - t0) < time_budget:
                best_bay_placed = False

                for tid in bay_types:
                    w, d, h, gap, nl, pr = self._cat[tid]

                    for angle in PACKING_ANGLES:
                        ca, sa = trig_cache[angle]
                        bx0, by0, bx1, by1 = _rotated_bbox_fast(x, y, float(w), float(d), ca, sa)
                        effective_w = float(bx1 - bx0)
                        effective_d = float(by1 - by0)

                        # REGLA DE ORO FFDH:
                        # Las cajas siguientes NUNCA pueden ser más altas que la primera de la fila.
                        if placed_in_row and effective_d > current_row_depth:
                            continue

                        gap_side = self._check_primitive(x, y, float(w), float(d), float(gap), h, ca, sa)

                        if gap_side != -1:
                            self._paint_primitive(x, y, float(w), float(d), float(gap), ca, sa, gap_side, 1)
                            self.placed.append(PlacedBay(tid, int(x), int(y), angle, w, d, h, gap, nl, pr, gap_side))
                            self.tot_price += pr
                            self.tot_loads += nl
                            self.tot_area += (w * d)

                            x += effective_w

                            if not placed_in_row:
                                current_row_depth = effective_d
                                current_row_gap = float(gap)
                            else:
                                current_row_gap = max(current_row_gap, float(gap))

                            best_bay_placed = True
                            placed_in_row = True
                            break

                    if best_bay_placed: break

                if not best_bay_placed:
                    # SALTO DE RAYCAST: Si no cabe NADA en este X, saltamos rápido.
                    # Esto arregla el bug del Case3 que tardaba 37 segundos.
                    x += step_fail

            if placed_in_row:
                y += current_row_depth + current_row_gap
            else:
                y += step_fail

    def run_row_packing(self, time_budget: float):
        t0 = time.perf_counter()

        # EL SECRETO DE C++: FFDH (First-Fit Decreasing Height) + Elite Filter
        def get_ffdh_key(tid):
            w, d, h, gap, nl, pr = self._cat[tid]
            area = w * d
            eff = (nl / pr) * (nl / area) if pr > 0 and area > 0 else 0

            # 1º Criterio: Profundidad (Depth). Redondeada a bloques de 50px.
            # Esto crea estanterías de alturas homogéneas (Cero desperdicio vertical).
            # 2º Criterio: Eficiencia real de la caja.
            return (int(max(w, d) / 50.0), eff)

        types_sorted = sorted(self.tids, key=get_ffdh_key, reverse=True)

        # FILTRO DE ÉLITE: Si el catálogo tiene 100 cajas y 50 son malísimas,
        # intentar meterlas nos destroza el Score Q. Las cortamos de raíz.
        eff_scores = [((self._cat[t][4] / self._cat[t][5]) * (self._cat[t][4] / (self._cat[t][0] * self._cat[t][1])))
                      for t in self.tids if self._cat[t][5] > 0]

        median_eff = np.median(eff_scores) if eff_scores else 0

        # Nos quedamos solo con las cajas que rinden por encima del 30% de la mediana
        elite_types = [t for t in types_sorted if
                       ((self._cat[t][4] / self._cat[t][5]) * (
                                   self._cat[t][4] / (self._cat[t][0] * self._cat[t][1]))) >= median_eff * 0.3]

        if not elite_types:
            elite_types = types_sorted  # Fallback de seguridad

        # PASADA 1: "BIG ROCKS" (Las estanterías Élite para la masa principal)
        # Le damos el 75% del tiempo con un salto agresivo de 40px para volar por el almacén
        self._sweep_grid(elite_types, step_fail=40.0, time_budget=time_budget * 0.75, t0=t0)

        # PASADA 2: "GRAVEL" (Cajas pequeñas para tapar huecos microscópicos)
        # Cogemos las cajas con menor área física del catálogo
        filler_types = sorted(self.tids, key=lambda t: self._cat[t][0] * self._cat[t][1])[:5]

        # Pasada rápida con salto de 15px para infiltrar cajas enanas en pasillos sobrantes
        self._sweep_grid(filler_types, step_fail=15.0, time_budget=time_budget, t0=t0)
    # ── FASE 2: MICRO-OPTIMIZADOR PARALELO ───────────────────────────────────

    def run_sa_parallel(self, time_budget: float):
        num_threads = multiprocessing.cpu_count()
        t0 = time.perf_counter()

        T_init = 1.0 if not self.placed else abs(
            self._dQ(-self.placed[0].price, -self.placed[0].nloads, -self.placed[0].area)) / math.log(20.0)
        T_init = max(1.0, T_init)

        self.best_q = self.score()
        self.best_snp = self._snap()

        trig_cache = {a: (math.cos(math.radians(a)), math.sin(math.radians(a))) for a in SA_ANGLES}

        def worker(thread_id):
            T = T_init
            random.seed(int(time.time() * 1000) + thread_id * 738)
            iters = 0

            running = True
            while running:
                for _ in range(TIMER_BATCH):
                    iters += 1
                    move = random.choice(self.move_pool)

                    if move == 0:  # ADD
                        tid = random.choice(self.tids)
                        angle = random.choice(SA_ANGLES)
                        ca, sa = trig_cache[angle]
                        x, y = random.randint(0, self.W - 1), random.randint(0, self.H - 1)
                        w, d, h, gap, nl, pr = self._cat[tid]

                        gap_side = self._check_primitive(float(x), float(y), float(w), float(d), float(gap), h, ca, sa)
                        if gap_side != -1:
                            with self.lock:
                                gap_side = self._check_primitive(float(x), float(y), float(w), float(d), float(gap), h,
                                                                 ca, sa)
                                if gap_side != -1:
                                    dq = self._dQ(pr, nl, w * d)
                                    if dq <= 0.0 or random.random() < math.exp(-dq / T):
                                        self._paint_primitive(float(x), float(y), float(w), float(d), float(gap), ca,
                                                              sa, gap_side, 1)
                                        self.placed.append(PlacedBay(tid, x, y, angle, w, d, h, gap, nl, pr, gap_side))
                                        self.tot_price += pr;
                                        self.tot_loads += nl;
                                        self.tot_area += w * d

                    elif move == 2:  # MOVE
                        with self.lock:
                            if not self.placed: continue
                            idx = random.randrange(len(self.placed))
                            old = self.placed[idx]
                            nx = max(0, min(self.W - 1, old.x + random.randint(-50, 50)))
                            ny = max(0, min(self.H - 1, old.y + random.randint(-50, 50)))
                            ca, sa = math.cos(math.radians(old.angle)), math.sin(math.radians(old.angle))

                            self._remove_bay(idx)
                            gap_side = self._check_primitive(float(nx), float(ny), float(old.width), float(old.depth),
                                                             float(old.gap), old.height, ca, sa)
                            if gap_side != -1:
                                self._paint_primitive(float(nx), float(ny), float(old.width), float(old.depth),
                                                      float(old.gap), ca, sa, gap_side, 1)
                                self.placed.append(
                                    PlacedBay(old.type_id, nx, ny, old.angle, old.width, old.depth, old.height, old.gap,
                                              old.nloads, old.price, gap_side))
                                self.tot_price += old.price;
                                self.tot_loads += old.nloads;
                                self.tot_area += old.area
                            else:
                                self._add_bay(old)

                    elif move == 4:  # TYPE SWAP
                        with self.lock:
                            if not self.placed: continue
                            idx = random.randrange(len(self.placed))
                            old = self.placed[idx]
                            new_tid = random.choice(self.tids)
                            if new_tid == old.type_id: continue
                            w, d, h, gap, nl, pr = self._cat[new_tid]
                            ca, sa = math.cos(math.radians(old.angle)), math.sin(math.radians(old.angle))

                            self._remove_bay(idx)
                            gap_side = self._check_primitive(float(old.x), float(old.y), float(w), float(d), float(gap),
                                                             h, ca, sa)
                            if gap_side != -1:
                                dq = self._dQ(pr - old.price, nl - old.nloads, (w * d) - old.area)
                                if dq <= 0.0 or random.random() < math.exp(-dq / T):
                                    self._paint_primitive(float(old.x), float(old.y), float(w), float(d), float(gap),
                                                          ca, sa, gap_side, 1)
                                    self.placed.append(
                                        PlacedBay(new_tid, old.x, old.y, old.angle, w, d, h, gap, nl, pr, gap_side))
                                    self.tot_price += pr;
                                    self.tot_loads += nl;
                                    self.tot_area += w * d
                                    continue
                            self._add_bay(old)

                cq = self.score()
                if cq < self.best_q:
                    with self.lock:
                        if cq < self.best_q:
                            self.best_q = cq
                            self.best_snp = self._snap()

                elapsed = time.perf_counter() - t0
                if elapsed >= time_budget:
                    running = False
                else:
                    T = max(1e-9, T_init * (0.001 ** (elapsed / time_budget)))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            for i in range(num_threads):
                executor.submit(worker, i)

        self._restore(self.best_snp)

    def export_solution(self) -> List[Tuple]:
        return [(b.type_id, b.x, b.y, int(b.angle)) for b in self.placed]