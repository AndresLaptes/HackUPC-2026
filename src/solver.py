"""
solver.py — Warehouse Bay Placement Optimizer
=============================================
- Parche de Obstáculos: Forzados a 10000 (Muro)
- SA Restringido: Prohibido vaciar el almacén (REMOVE=0)
- Greedy de alta densidad
"""

from __future__ import annotations

import math
import os
import sys
import time
import random
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from numba import njit

from warehouse import Warehouse

# ═══════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════
TIME_LIMIT = 27.0  # segundos hard limit
GREEDY_FRAC = 0.15  # fracción de tiempo para greedy
TIMER_BATCH = 200  # iters SA entre checks de tiempo

# Pesos: [ADD, REMOVE, MOVE, ROTATE, TYPE_SWAP]
# REMOVE a 0: Obligamos al algoritmo a llenar el almacén, nunca vaciarlo.
MOVE_WEIGHTS = [50, 0, 20, 10, 20]

GREEDY_ANGLES = [0, 90, 180, 270]
SA_ANGLES = [0, 90, 180, 270]


# ═══════════════════════════════════════════════════════
# NUMBA KERNELS
# ═══════════════════════════════════════════════════════

@njit(fastmath=True, cache=True)
def _rotated_bbox(x: float, y: float, w: float, d: float, angle_deg: float):
    rad = math.radians(angle_deg)
    ca = math.cos(rad);
    sa = math.sin(rad)
    min_rx = 1e18;
    max_rx = -1e18
    min_ry = 1e18;
    max_ry = -1e18
    cxs = (0.0, float(w), float(w), 0.0)
    cys = (0.0, 0.0, float(d), float(d))
    for i in range(4):
        rx = cxs[i] * ca - cys[i] * sa + x
        ry = cxs[i] * sa + cys[i] * ca + y
        if rx < min_rx: min_rx = rx
        if rx > max_rx: max_rx = rx
        if ry < min_ry: min_ry = ry
        if ry > max_ry: max_ry = ry
    return (int(math.floor(min_rx)), int(math.floor(min_ry)),
            int(math.ceil(max_rx)), int(math.ceil(max_ry)))


@njit(fastmath=True, cache=True)
def _check_rotated_solid(grid: np.ndarray, x: float, y: float, w: float, d: float,
                         angle_deg: float, H: int, W: int) -> bool:
    bx0, by0, bx1, by1 = _rotated_bbox(x, y, w, d, angle_deg)
    if bx0 < 0 or by0 < 0 or bx1 >= W or by1 >= H: return False

    rad = math.radians(-angle_deg)
    ca = math.cos(rad);
    sa = math.sin(rad)

    for cy in range(by0, by1 + 1):
        for cx in range(bx0, bx1 + 1):
            lx = (cx - x) * ca - (cy - y) * sa
            ly = (cx - x) * sa + (cy - y) * ca
            if -0.1 <= lx <= w + 0.1 and -0.1 <= ly <= d + 0.1:
                # El cuerpo no puede pisar ABSOLUTAMENTE NADA (ni gaps, ni muros)
                if grid[cy, cx] != 0:
                    return False
    return True


@njit(fastmath=True, cache=True)
def _check_rotated_gap_area(grid: np.ndarray, x: float, y: float, w: float, d: float,
                            angle_deg: float, H: int, W: int) -> bool:
    bx0, by0, bx1, by1 = _rotated_bbox(x, y, w, d, angle_deg)
    # El gap no puede estar fuera del mapa
    if bx0 < 0 or by0 < 0 or bx1 >= W or by1 >= H: return False

    rad = math.radians(-angle_deg)
    ca = math.cos(rad);
    sa = math.sin(rad)

    for cy in range(by0, by1 + 1):
        for cx in range(bx0, bx1 + 1):
            lx = (cx - x) * ca - (cy - y) * sa
            ly = (cx - x) * sa + (cy - y) * ca
            if -0.1 <= lx <= w + 0.1 and -0.1 <= ly <= d + 0.1:
                # El gap falla si choca con SÓLIDOS (100) o MUROS/OBSTÁCULOS (10000)
                if grid[cy, cx] >= 100:
                    return False
    return True


@njit(fastmath=True, cache=True)
def _find_valid_gap(grid: np.ndarray, x: float, y: float, w: float, d: float,
                    gap: float, angle_deg: float, H: int, W_grid: int) -> int:
    if gap <= 0: return 0

    rad = math.radians(angle_deg)
    ca = math.cos(rad);
    sa = math.sin(rad)

    wx1 = x + (0.0 * ca) - (-gap * sa)
    wy1 = y + (0.0 * sa) + (-gap * ca)
    if _check_rotated_gap_area(grid, wx1, wy1, w, gap, angle_deg, H, W_grid): return 1

    wx2 = x + (0.0 * ca) - (d * sa)
    wy2 = y + (0.0 * sa) + (d * ca)
    if _check_rotated_gap_area(grid, wx2, wy2, w, gap, angle_deg, H, W_grid): return 2

    wx3 = x + (-gap * ca) - (0.0 * sa)
    wy3 = y + (-gap * sa) + (0.0 * ca)
    if _check_rotated_gap_area(grid, wx3, wy3, gap, d, angle_deg, H, W_grid): return 3

    wx4 = x + (w * ca) - (0.0 * sa)
    wy4 = y + (w * sa) + (0.0 * ca)
    if _check_rotated_gap_area(grid, wx4, wy4, gap, d, angle_deg, H, W_grid): return 4

    return -1


@njit(fastmath=True, cache=True)
def _paint_rotated(grid: np.ndarray, x: float, y: float, w: float, d: float,
                   angle_deg: float, H: int, W: int, delta: int):
    bx0, by0, bx1, by1 = _rotated_bbox(x, y, w, d, angle_deg)
    bx0 = max(0, bx0);
    by0 = max(0, by0)
    bx1 = min(W - 1, bx1);
    by1 = min(H - 1, by1)

    rad = math.radians(-angle_deg)
    ca = math.cos(rad);
    sa = math.sin(rad)

    for cy in range(by0, by1 + 1):
        for cx in range(bx0, bx1 + 1):
            lx = (cx - x) * ca - (cy - y) * sa
            ly = (cx - x) * sa + (cy - y) * ca
            if -0.1 <= lx <= w + 0.1 and -0.1 <= ly <= d + 0.1:
                grid[cy, cx] += delta


@njit(fastmath=True, cache=True)
def _paint_gap_side(grid: np.ndarray, x: float, y: float, w: float, d: float,
                    gap: float, angle_deg: float, H: int, W_grid: int, side: int, delta: int):
    if side == 0 or gap <= 0: return
    rad = math.radians(angle_deg)
    ca = math.cos(rad);
    sa = math.sin(rad)

    if side == 1:
        gx, gy, gw, gd = x + (0.0 * ca) - (-gap * sa), y + (0.0 * sa) + (-gap * ca), w, gap
    elif side == 2:
        gx, gy, gw, gd = x + (0.0 * ca) - (d * sa), y + (0.0 * sa) + (d * ca), w, gap
    elif side == 3:
        gx, gy, gw, gd = x + (-gap * ca) - (0.0 * sa), y + (-gap * sa) + (0.0 * ca), gap, d
    elif side == 4:
        gx, gy, gw, gd = x + (w * ca) - (0.0 * sa), y + (w * sa) + (0.0 * ca), gap, d
    else:
        return

    _paint_rotated(grid, gx, gy, gw, gd, angle_deg, H, W_grid, delta)


@njit(fastmath=True, cache=True)
def _ceiling_ok(ceiling_map: np.ndarray, x: int, y: int, w: int, d: int,
                angle_deg: float, bay_height: int, max_x: int) -> bool:
    bx0, _, bx1, _ = _rotated_bbox(float(x), float(y), float(w), float(d), angle_deg)
    cx_start = max(0, bx0)
    cx_end = min(max_x, bx1 + 1)
    if cx_start >= cx_end: return False
    for cx in range(cx_start, cx_end):
        if ceiling_map[cx] < bay_height:
            return False
    return True


# ═══════════════════════════════════════════════════════
# PLACED BAY
# ═══════════════════════════════════════════════════════

@dataclass
class PlacedBay:
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
    gap_side: int = 0

    @property
    def area(self) -> int:
        return self.width * self.depth


# ═══════════════════════════════════════════════════════
# SOLVER
# ═══════════════════════════════════════════════════════

class Solver:

    def __init__(self, wh: Warehouse):
        self.wh = wh
        self.H = int(wh.grid.shape[0])
        self.W = int(wh.grid.shape[1])

        # FIX DE OBSTÁCULOS: Forzamos físicamente todos los obstáculos a 10000
        if self.wh.obs_tensor.size > 0:
            for obs in self.wh.obs_tensor:
                ox, oy, ow, od = obs
                # Saturamos a 10000 para que los GAPS choquen con ellos
                self.wh.grid[max(0, oy):oy + od, max(0, ox):ox + ow] = 10000

        self.warehouse_area = float(np.count_nonzero(wh.grid < 10000))
        self._has_ceiling = bool(np.any(wh.ceiling_map > 0))

        self.placed: List[PlacedBay] = []
        self.tot_price = 0
        self.tot_loads = 0
        self.tot_area = 0

        self._cat: dict[int, tuple] = {}
        for row in wh.bay_catalogue:
            tid = int(row[0])
            self._cat[tid] = (int(row[1]), int(row[2]), int(row[3]),
                              int(row[4]), int(row[5]), int(row[6]))

        total = sum(MOVE_WEIGHTS)
        self._move_cum = []
        acc = 0
        for w in MOVE_WEIGHTS:
            acc += w
            self._move_cum.append(acc / total)

    def _pick_move(self) -> int:
        r = random.random()
        for i, c in enumerate(self._move_cum):
            if r < c: return i
        return len(self._move_cum) - 1

    # ── heurística ──────────────────────────────────────────────────────────

    def _Q(self, tp: int, tl: int, ta: int) -> float:
        if tl == 0:
            return float('inf')
        r = tp / tl
        # Minimizamos la función oficial
        return r ** (2.0 - (ta / self.warehouse_area))

    def score(self) -> float:
        return self._Q(self.tot_price, self.tot_loads, self.tot_area)

    def _dQ(self, dp: int, dl: int, da: int) -> float:
        return (self._Q(self.tot_price + dp, self.tot_loads + dl, self.tot_area + da)
                - self._Q(self.tot_price, self.tot_loads, self.tot_area))

    # ── helpers ─────────────────────────────────────────────────────────────

    def _make(self, tid: int, x: int, y: int, angle: float) -> PlacedBay:
        w, d, h, gap, nl, pr = self._cat[tid]
        return PlacedBay(tid, x, y, angle, w, d, h, gap, nl, pr)

    def _valid(self, b: PlacedBay) -> bool:
        if not _check_rotated_solid(self.wh.grid, float(b.x), float(b.y), float(b.width), float(b.depth),
                                    b.angle, self.H, self.W):
            return False

        if self._has_ceiling:
            if not _ceiling_ok(self.wh.ceiling_map, b.x, b.y, b.width, b.depth,
                               b.angle, b.height, int(self.wh.max_x)):
                return False

        if b.gap > 0:
            side = _find_valid_gap(self.wh.grid, float(b.x), float(b.y), float(b.width), float(b.depth),
                                   float(b.gap), b.angle, self.H, self.W)
            if side == -1:
                return False
            b.gap_side = side

        return True

    def _paint_bay_full(self, b: PlacedBay, sign: int):
        _paint_rotated(self.wh.grid, float(b.x), float(b.y), float(b.width), float(b.depth),
                       b.angle, self.H, self.W, 100 * sign)
        if b.gap > 0 and b.gap_side > 0:
            _paint_gap_side(self.wh.grid, float(b.x), float(b.y), float(b.width), float(b.depth),
                            float(b.gap), b.angle, self.H, self.W, b.gap_side, 1 * sign)

    def _add(self, b: PlacedBay):
        self._paint_bay_full(b, +1)
        self.placed.append(b)
        self.tot_price += b.price
        self.tot_loads += b.nloads
        self.tot_area += b.area

    def _remove(self, idx: int) -> PlacedBay:
        b = self.placed.pop(idx)
        self._paint_bay_full(b, -1)
        self.tot_price -= b.price
        self.tot_loads -= b.nloads
        self.tot_area -= b.area
        return b

    def _snap(self):
        return (
            [(b.type_id, b.x, b.y, b.angle,
              b.width, b.depth, b.height, b.gap, b.nloads, b.price, b.gap_side)
             for b in self.placed],
            self.tot_price, self.tot_loads, self.tot_area
        )

    def _restore(self, snap):
        blist, tp, tl, ta = snap
        for b in self.placed:
            self._paint_bay_full(b, -1)
        self.placed = [PlacedBay(*s) for s in blist]
        self.tot_price = tp
        self.tot_loads = tl
        self.tot_area = ta
        for b in self.placed:
            self._paint_bay_full(b, +1)

    # ── FASE 1: Greedy Denso ────────────────────────────────────────────────

    def greedy(self, time_budget: float):
        t0 = time.perf_counter()

        types_sorted = sorted(
            self._cat.keys(),
            key=lambda tid: self._cat[tid][5] / max(1, self._cat[tid][4]),
            reverse=True
        )

        placed_any = True
        while placed_any and (time.perf_counter() - t0) < time_budget:
            placed_any = False
            for tid in types_sorted:
                if (time.perf_counter() - t0) >= time_budget: break
                w, d, h, gap, nl, pr = self._cat[tid]

                for angle in GREEDY_ANGLES:
                    if (time.perf_counter() - t0) >= time_budget: break
                    bx0, by0, bx1, by1 = _rotated_bbox(0, 0, w, d, float(angle))
                    bw = bx1 - bx0
                    bd = by1 - by0

                    # DENSE SWEEP: Avanzamos de a 100 píxeles para no perder huecos
                    step_x = max(100, bw // 3)
                    step_y = max(100, bd // 3)

                    y = 0
                    while y + bd <= self.H:
                        x = 0
                        while x + bw <= self.W:
                            b = self._make(tid, x, y, float(angle))
                            if self._valid(b):
                                self._add(b)
                                placed_any = True
                                x += step_x
                            else:
                                x += step_x
                        y += step_y

        elapsed = time.perf_counter() - t0
        print(f"  [Greedy] {len(self.placed):>4} bays | Q={self.score():>12.4f} | {elapsed:.2f}s")

    # ── FASE 2: Simulated Annealing ─────────────────────────────────────────

    def anneal(self, time_budget: float):
        t0 = time.perf_counter()
        iters = 0

        T = self._calibrate_T()
        print(f"  [SA]     T_init={T:.4f}")

        best_q = self.score()
        best_snp = self._snap()

        tids = list(self._cat.keys())

        expected_iters = 15000
        alpha = math.exp(math.log(0.001) / expected_iters)

        running = True
        while running:
            for _ in range(TIMER_BATCH):
                iters += 1
                move = self._pick_move()

                # ── ADD ──────────────────────────────────────────────────
                if move == 0:
                    tid = random.choice(tids)
                    angle = float(random.choice(SA_ANGLES))
                    x = random.randint(0, self.W - 1)
                    y = random.randint(0, self.H - 1)
                    b = self._make(tid, x, y, angle)
                    if not self._valid(b):
                        continue
                    dq = self._dQ(b.price, b.nloads, b.area)
                    if dq <= 0.0 or random.random() < math.exp(-dq / T):
                        self._add(b)

                # ── REMOVE (Desactivado por pesos, pero lógica intacta) ──
                elif move == 1:
                    if len(self.placed) <= MIN_BAYS: continue
                    idx = random.randrange(len(self.placed))
                    b = self.placed[idx]
                    dq = self._dQ(-b.price, -b.nloads, -b.area)
                    if dq <= 0.0 or random.random() < math.exp(-dq / T):
                        self._remove(idx)

                # ── LOCAL MOVE ───────────────────────────────────────────
                elif move == 2:
                    if not self.placed: continue
                    idx = random.randrange(len(self.placed))
                    old = self.placed[idx]

                    saved = PlacedBay(old.type_id, old.x, old.y, old.angle,
                                      old.width, old.depth, old.height,
                                      old.gap, old.nloads, old.price, old.gap_side)
                    self._remove(idx)

                    nx = max(0, min(self.W - 1, old.x + random.randint(-200, 200)))
                    ny = max(0, min(self.H - 1, old.y + random.randint(-200, 200)))

                    nb = self._make(old.type_id, nx, ny, old.angle)
                    if self._valid(nb):
                        self._add(nb)
                    else:
                        self._add(saved)

                # ── ROTATE ───────────────────────────────────────────────
                elif move == 3:
                    if not self.placed: continue
                    idx = random.randrange(len(self.placed))
                    old = self.placed[idx]
                    new_a = float(random.choice(SA_ANGLES))
                    if new_a == old.angle: continue

                    saved = PlacedBay(old.type_id, old.x, old.y, old.angle,
                                      old.width, old.depth, old.height,
                                      old.gap, old.nloads, old.price, old.gap_side)
                    self._remove(idx)
                    nb = self._make(old.type_id, old.x, old.y, new_a)
                    if self._valid(nb):
                        self._add(nb)
                    else:
                        self._add(saved)

                # ── TYPE SWAP ────────────────────────────────────────────
                elif move == 4:
                    if not self.placed: continue
                    idx = random.randrange(len(self.placed))
                    old = self.placed[idx]
                    new_tid = random.choice(tids)
                    if new_tid == old.type_id: continue

                    saved = PlacedBay(old.type_id, old.x, old.y, old.angle,
                                      old.width, old.depth, old.height,
                                      old.gap, old.nloads, old.price, old.gap_side)
                    self._remove(idx)
                    nb = self._make(new_tid, old.x, old.y, old.angle)
                    if self._valid(nb):
                        dq = self._dQ(nb.price - saved.price,
                                      nb.nloads - saved.nloads,
                                      nb.area - saved.area)
                        if dq <= 0.0 or random.random() < math.exp(-dq / T):
                            self._add(nb)
                        else:
                            self._add(saved)
                    else:
                        self._add(saved)

                T = max(1e-9, T * alpha)

                cq = self.score()
                if cq < best_q:
                    best_q = cq
                    best_snp = self._snap()

            if (time.perf_counter() - t0) >= time_budget:
                running = False

        self._restore(best_snp)
        elapsed = time.perf_counter() - t0
        print(f"  [SA]     {len(self.placed):>4} bays | Q={best_q:>12.4f} "
              f"| {iters:>7} iters | {elapsed:.2f}s")

    def _calibrate_T(self) -> float:
        if not self.placed: return 1.0
        worst = min(self.placed, key=lambda b: b.price / max(1, b.nloads))
        dq = abs(self._dQ(-worst.price, -worst.nloads, -worst.area))
        if dq < 1e-10: return 1.0
        return dq / math.log(5.0)

    # ── OUTPUT ──────────────────────────────────────────────────────────────

    def print_solution(self):
        print("\nId, X, Y, Rotation, GapSide, Height")
        for b in self.placed:
            side_str = {0: "None", 1: "Top", 2: "Bottom", 3: "Left", 4: "Right"}.get(b.gap_side, "Unknown")
            print(f"{b.type_id}, {b.x}, {b.y}, {int(b.angle)}, Gap:{side_str}, H:{b.height}")

    def export_solution(self):
        return [(b.type_id, b.x, b.y, b.angle) for b in self.placed]

    # ── PLOT ─────────────────────────────────────────────────────────────────

    def plot(self, coords: np.ndarray, obstacles: np.ndarray):
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from matplotlib.patches import Polygon
            from matplotlib.colors import to_rgba
        except ImportError:
            print("  [Plot] matplotlib no disponible")
            return

        fig, ax = plt.subplots(figsize=(12, 12))

        vis = np.copy(self.wh.grid).astype(np.float32)
        vis[vis >= 10000] = np.nan
        ax.imshow(vis, cmap='Greys', origin='lower', interpolation='none',
                  alpha=0.2, vmin=0, vmax=100)

        x_c, y_c = coords[:, 0], coords[:, 1]
        ax.plot(np.append(x_c, x_c[0]), np.append(y_c, y_c[0]),
                'b--', lw=1.5, label='Perímetro')

        if obstacles.size > 0:
            for i, obs in enumerate(obstacles):
                ox, oy, ow, od = obs
                rect = mpatches.Rectangle(
                    (ox, oy), ow, od, lw=1.2,
                    edgecolor='red', facecolor='salmon', alpha=0.5,
                    label='Obstáculo' if i == 0 else '')
                ax.add_patch(rect)

        cmap = plt.cm.get_cmap('tab10', len(self._cat))
        type_colors = {tid: cmap(i) for i, tid in enumerate(sorted(self._cat.keys()))}
        legend_handles = {}

        for b in self.placed:
            rad = math.radians(b.angle)
            ca, sa = math.cos(rad), math.sin(rad)

            corners_local = [(0, 0), (b.width, 0), (b.width, b.depth), (0, b.depth)]
            corners_world = [
                (b.x + lx * ca - ly * sa, b.y + lx * sa + ly * ca)
                for lx, ly in corners_local
            ]
            color = type_colors[b.type_id]
            poly = Polygon(corners_world, closed=True,
                           facecolor=to_rgba(color, 0.6),
                           edgecolor=color, lw=1.5)
            ax.add_patch(poly)

            if b.gap > 0 and b.gap_side > 0:
                gx, gy, gw, gd = 0, 0, 0, 0
                if b.gap_side == 1:
                    gx, gy, gw, gd = 0.0, -b.gap, b.width, b.gap
                elif b.gap_side == 2:
                    gx, gy, gw, gd = 0.0, b.depth, b.width, b.gap
                elif b.gap_side == 3:
                    gx, gy, gw, gd = -b.gap, 0.0, b.gap, b.depth
                elif b.gap_side == 4:
                    gx, gy, gw, gd = b.width, 0.0, b.gap, b.depth

                gap_local = [(gx, gy), (gx + gw, gy), (gx + gw, gy + gd), (gx, gy + gd)]
                gap_world = [(b.x + lx * ca - ly * sa, b.y + lx * sa + ly * ca) for lx, ly in gap_local]

                gap_poly = Polygon(gap_world, closed=True,
                                   facecolor='none', edgecolor=color,
                                   hatch='///', lw=0.5, alpha=0.7)
                ax.add_patch(gap_poly)

            bx0 = min(c[0] for c in corners_world)
            bx1 = max(c[0] for c in corners_world)
            cx_start = max(0, int(math.floor(bx0)))
            cx_end = min(self.W, int(math.ceil(bx1)) + 1)

            local_ceil = "N/A"
            if self._has_ceiling and cx_start < cx_end:
                local_ceil = str(np.min(self.wh.ceiling_map[cx_start:cx_end]))

            cx_b = sum(c[0] for c in corners_world) / 4
            cy_b = sum(c[1] for c in corners_world) / 4

            debug_text = f"T:{b.type_id}\nH:{b.height}\n(C:{local_ceil})"
            ax.text(cx_b, cy_b, debug_text,
                    ha='center', va='center', fontsize=7, fontweight='bold',
                    color='white', bbox=dict(facecolor='black', alpha=0.4, pad=1, edgecolor='none'))

            if b.type_id not in legend_handles:
                legend_handles[b.type_id] = mpatches.Patch(
                    facecolor=color, label=f'Bay {b.type_id}')

        ax.legend(handles=list(legend_handles.values()) +
                          [mpatches.Patch(facecolor='salmon', label='Obstáculo'),
                           mpatches.Patch(facecolor='none', edgecolor='grey', hatch='///', label='Gap (Pasillo)'),
                           mpatches.Patch(facecolor='none', edgecolor='blue', linestyle='--', label='Perímetro')],
                  loc='upper right', fontsize=8)

        ax.set_xlim(0, self.W)
        ax.set_ylim(0, self.H)
        ax.set_aspect('equal')
        ax.set_title(f"Solución Hackathon: {len(self.placed)} bays | Q={self.score():.4f}")
        ax.set_xlabel("X Coordinate");
        ax.set_ylabel("Y Coordinate")
        plt.tight_layout()
        print("\n  [i] Mostrando interfaz gráfica (cierra la ventana para terminar el proceso)...")
        plt.show()


# ═══════════════════════════════════════════════════════
# LOADERS + MAIN
# ═══════════════════════════════════════════════════════

def _load_csv(path: str, ncols: int, dtype=np.int32) -> np.ndarray:
    if not os.path.isfile(path):
        return np.empty((0, ncols), dtype=dtype)
    try:
        data = np.loadtxt(path, delimiter=',', dtype=dtype, ndmin=2)
        if data.ndim == 1:
            data = data.reshape(1, -1)
        if data.shape[1] != ncols:
            return np.empty((0, ncols), dtype=dtype)
        return data
    except Exception:
        return np.empty((0, ncols), dtype=dtype)


def run(case_dir: str = '.'):
    t_start = time.perf_counter()
    print(f"\n{'=' * 52}")
    print(f"  Warehouse Optimizer")
    print(f"  Caso: {os.path.abspath(case_dir)}")
    print(f"{'=' * 52}")

    coords = _load_csv(os.path.join(case_dir, 'warehouse.csv'), 2)
    obstacles = _load_csv(os.path.join(case_dir, 'obstacles.csv'), 4)
    ceiling_pts = _load_csv(os.path.join(case_dir, 'ceiling.csv'), 2)
    bays = _load_csv(os.path.join(case_dir, 'types_of_bays.csv'), 7)

    if coords.size == 0 or bays.size == 0:
        print("[FATAL] CSV vacío o no encontrado");
        sys.exit(1)

    t_build = time.perf_counter()
    wh = Warehouse(coords)
    wh.apply_obstacles(obstacles)
    if ceiling_pts.size > 0:
        wh.apply_ceiling(ceiling_pts)
    wh.apply_bays(bays)
    print(f"  [Build]  {wh.max_x}×{wh.max_y} | {time.perf_counter() - t_build:.2f}s")

    solver = Solver(wh)

    elapsed_build = time.perf_counter() - t_start
    remaining = TIME_LIMIT - elapsed_build
    greedy_budget = remaining * GREEDY_FRAC
    sa_budget = remaining * (1.0 - GREEDY_FRAC)

    solver.greedy(greedy_budget)

    elapsed_g = time.perf_counter() - t_start - elapsed_build
    sa_budget = max(1.0, remaining - elapsed_g)
    solver.anneal(sa_budget)

    solver.print_solution()

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    print(f"\n{'=' * 52}")
    print(f"  Q final  : {solver.score():.6f}")
    print(f"  Bays     : {len(solver.placed)}")
    print(f"  Tiempo   : {elapsed:.3f}s")
    print(f"{'=' * 52}\n")

    solver.plot(coords, obstacles)


if __name__ == '__main__':
    case_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    run(case_dir)