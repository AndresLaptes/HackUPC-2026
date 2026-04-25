import os
import time
import threading
import numpy as np
import pandas as pd
from numba import njit
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from concurrent.futures import ThreadPoolExecutor

# --- MATHEMATICAL HELPER ---
def calculate_polygon_area(coords: np.ndarray) -> float:
    """Calculates the exact area of the warehouse polygon using the Shoelace formula."""
    x = coords[:, 0]
    y = coords[:, 1]
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- NUMBA GRID GENERATION & COLLISION FUNCTIONS ---
@njit(fastmath=True, cache=True)
def _fill_ceiling_map(ceiling_map, points):
    num_points = points.shape[0]
    for i in range(num_points - 1):
        x_start = int(points[i, 0])
        x_end   = int(points[i + 1, 0])
        x_start = max(0, min(x_start, ceiling_map.shape[0]))
        x_end   = max(0, min(x_end,   ceiling_map.shape[0]))
        h = int(points[i, 1])
        if x_start < x_end:
            ceiling_map[x_start:x_end] = h
    last_x = int(points[-1, 0])
    last_x = max(0, min(last_x, ceiling_map.shape[0]))
    last_h = int(points[-1, 1])
    ceiling_map[last_x:] = last_h

@njit(fastmath=True, cache=True)
def _add_obstacles_kernel(grid: np.ndarray, obstacles: np.ndarray):
    H, W = grid.shape
    num_obs = obstacles.shape[0]
    for i in range(num_obs):
        x, y, w, d = obstacles[i, 0], obstacles[i, 1], obstacles[i, 2], obstacles[i, 3]
        x_start, y_start = max(0, x), max(0, y)
        x_end,   y_end   = min(W, x + w), min(H, y + d)
        if x_start < x_end and y_start < y_end:
            grid[y_start:y_end, x_start:x_end] = 1

@njit(fastmath=True, cache=True)
def fast_orthogonal_scanline(grid_shape, vert_x, vert_ymin, vert_ymax):
    H, W = grid_shape
    grid = np.full(grid_shape, 1, dtype=np.int32)
    num_edges = len(vert_x)
    active_x = np.empty(128, dtype=np.int32)

    for y in range(H):
        count = 0
        for i in range(num_edges):
            if vert_ymin[i] <= y < vert_ymax[i]:
                active_x[count] = vert_x[i]
                count += 1
        if count == 0:
            continue
        active_slice = active_x[:count]
        active_slice.sort()
        for i in range(0, count, 2):
            x_start = max(0, active_slice[i])
            x_end   = min(W, active_slice[i + 1])
            grid[y, x_start:x_end] = 0
    return grid

# nogil=True releases the GIL so multiple threads run truly in parallel
@njit(fastmath=True, cache=True, nogil=True)
def check_collision_numba(grid, y, x, w, d, gy, gx, gw, gd):
    if y + d > grid.shape[0] or x + w > grid.shape[1] or y < 0 or x < 0:
        return False
    for i in range(y, y + d):
        for j in range(x, x + w):
            if grid[i, j] != 0:
                return False
    if gy + gd > grid.shape[0] or gx + gw > grid.shape[1] or gy < 0 or gx < 0:
        return False
    for i in range(gy, gy + gd):
        for j in range(gx, gx + gw):
            if grid[i, j] == 1:
                return False
    return True

@njit(fastmath=True, cache=True, nogil=True)
def mark_grid_numba(grid, y, x, w, d, gy, gx, gw, gd):
    grid[y:y+d, x:x+w] = 1
    for i in range(gy, gy + gd):
        for j in range(gx, gx + gw):
            if grid[i, j] == 0:
                grid[i, j] = 2

# --- WAREHOUSE CLASS ---
class Warehouse:
    def __init__(self, coords_array: np.ndarray):
        self.min_x = np.min(coords_array[:, 0])
        self.min_y = np.min(coords_array[:, 1])

        self.coords = coords_array.copy()
        self.coords[:, 0] -= self.min_x
        self.coords[:, 1] -= self.min_y

        self.max_x = np.max(self.coords[:, 0])
        self.max_y = np.max(self.coords[:, 1])

        self.total_area  = calculate_polygon_area(self.coords)
        self.grid        = self._generate_grid()
        self.ceiling_map = np.zeros(self.max_x, dtype=np.int32)

    def _generate_grid(self) -> np.ndarray:
        num_vertices = len(self.coords)
        vert_x, vert_ymin, vert_ymax = [], [], []
        for i in range(num_vertices):
            p1 = self.coords[i]
            p2 = self.coords[(i + 1) % num_vertices]
            if p1[0] == p2[0] and p1[1] != p2[1]:
                vert_x.append(p1[0])
                vert_ymin.append(min(p1[1], p2[1]))
                vert_ymax.append(max(p1[1], p2[1]))
        arr_vx   = np.array(vert_x,   dtype=np.int32)
        arr_vmin = np.array(vert_ymin, dtype=np.int32)
        arr_vmax = np.array(vert_ymax, dtype=np.int32)
        return fast_orthogonal_scanline((self.max_y, self.max_x), arr_vx, arr_vmin, arr_vmax)

    def apply_obstacles(self, obs_tensor: np.ndarray):
        if obs_tensor.size == 0:
            return
        self.obs_tensor = obs_tensor.copy()
        self.obs_tensor[:, 0] -= self.min_x
        self.obs_tensor[:, 1] -= self.min_y
        _add_obstacles_kernel(self.grid, self.obs_tensor)

    def apply_ceiling(self, ceiling_points: np.ndarray):
        if ceiling_points.size == 0:
            return
        shifted_points = ceiling_points.copy()
        shifted_points[:, 0] -= self.min_x
        idx            = np.argsort(shifted_points[:, 0])
        sorted_points  = shifted_points[idx]
        _fill_ceiling_map(self.ceiling_map, sorted_points)

    def is_height_legal(self, x: int, width: int, bay_height: int) -> bool:
        x_end = min(self.max_x, x + width)
        return np.min(self.ceiling_map[x:x_end]) >= bay_height

    def get_original_coords(self, grid_x: int, grid_y: int):
        return grid_x + self.min_x, grid_y + self.min_y

# --- PLACEMENT AND SCORING SOLVER ---
def greedy_solver(warehouse: Warehouse, bays_df: pd.DataFrame) -> pd.DataFrame:
    start_time = time.time()
    time_limit = 28.0

    bays_df = bays_df.copy()
    bays_df['area'] = bays_df['w'] * bays_df['d']

    # Objective-aware scoring: Q = (P/L)^(2-A)
    # We want low P/L and high area coverage. Score = (price/loads) / sqrt(area)
    # penalises expensive-per-load bays and rewards ones that fill space efficiently.
    bays_df['score'] = (bays_df['price'] / bays_df['loads']) / np.sqrt(bays_df['area'])
    sorted_bays = bays_df.sort_values(by='score', ascending=True)

    # Pre-extract to a numpy array — eliminates iterrows() overhead (~100-1000x faster)
    # Columns: [id, w, d, h, gap, loads, price]
    bay_data = sorted_bays[['id', 'w', 'd', 'h', 'gap', 'loads', 'price']].values.astype(np.float64)

    # Adaptive step size: half the smallest bay dimension so no valid position is skipped
    min_dim   = int(min(bays_df['w'].min(), bays_df['d'].min()))
    step_size = max(1, min_dim // 2)
    print(f"   Adaptive step_size={step_size}  (min bay dim={min_dim})")

    # Strip-based multithreading: divide warehouse into horizontal strips.
    # Each thread owns its strip exclusively — no cross-strip writes, so the grid
    # needs no lock. Only the results list is shared (locked once per strip).
    num_threads   = 4
    max_bay_depth = int(max(bays_df['d'].max(), bays_df['w'].max()))
    strip_height  = max(max_bay_depth * 2, warehouse.max_y // num_threads)
    y_starts      = list(range(0, warehouse.max_y, strip_height))

    all_placements = []
    sum_prices     = 0.0
    sum_loads      = 0.0
    sum_area_used  = 0.0
    timed_out      = False
    lock           = threading.Lock()

    def process_strip(y_start: int):
        nonlocal sum_prices, sum_loads, sum_area_used, timed_out

        local_placements = []
        local_prices     = 0.0
        local_loads      = 0.0
        local_area       = 0.0

        y_end = min(y_start + strip_height, warehouse.max_y)

        for y in range(y_start, y_end - 1, step_size):
            if timed_out or time.time() - start_time > time_limit:
                timed_out = True
                break

            for x in range(0, warehouse.max_x - 1, step_size):
                if warehouse.grid[y, x] != 0:
                    continue

                for bay_row in bay_data:
                    bid   = int(bay_row[0])
                    w, d  = int(bay_row[1]), int(bay_row[2])
                    h     = int(bay_row[3])
                    gap   = int(bay_row[4])
                    loads = bay_row[5]
                    price = bay_row[6]

                    # Keep bay entirely within this strip to avoid cross-strip writes
                    if y + max(d, w) > y_end:
                        continue

                    configs = [
                        (w, d, x,       y + d,   w,   gap),   # 0°   gap up
                        (d, w, x + d,   y,       gap, w  ),   # 90°  gap right
                        (w, d, x,       y - gap, w,   gap),   # 180° gap down
                        (d, w, x - gap, y,       gap, w  ),   # 270° gap left
                    ]

                    placed = False
                    for rot_idx, (bw, bd, gx, gy, gw, gd) in enumerate(configs):
                        if not warehouse.is_height_legal(x, bw, h):
                            continue
                        # nogil=True on both functions means threads run truly in parallel
                        if check_collision_numba(warehouse.grid, y, x, bw, bd, gy, gx, gw, gd):
                            mark_grid_numba(warehouse.grid, y, x, bw, bd, gy, gx, gw, gd)
                            ox, oy = warehouse.get_original_coords(x, y)
                            local_placements.append({
                                'bay_id': bid, 'x': ox, 'y': oy,
                                'w': bw, 'd': bd, 'h': h, 'rot': rot_idx * 90
                            })
                            local_prices += price
                            local_loads  += loads
                            local_area   += bw * bd
                            placed = True
                            break

                    if placed:
                        break  # move on to next (x, y) cell

        # Lock acquired once per strip, not per placement
        with lock:
            all_placements.extend(local_placements)
            sum_prices    += local_prices
            sum_loads     += local_loads
            sum_area_used += local_area

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(process_strip, y_starts)

    if timed_out:
        print("⚠️  TIME LIMIT REACHED: halted safely.")

    pct_area = sum_area_used / warehouse.total_area
    final_q  = (sum_prices / sum_loads) ** (2.0 - pct_area) if sum_loads > 0 else 0

    print("-" * 40)
    print(f"Total Bays Placed:     {len(all_placements)}")
    print(f"Warehouse Area Used:   {pct_area * 100:.4f}%")
    print(f"Average Price/Load:    {(sum_prices / sum_loads) if sum_loads > 0 else 0:.4f}")
    print(f"Final Q Score:         {final_q:.6f}")
    print("-" * 40)

    return pd.DataFrame(all_placements)

# --- VISUALISATION ---
def visualize_warehouse_with_gaps(warehouse_df, obstacles_df, placements_df, bays_df, case_name=""):
    fig, ax = plt.subplots(figsize=(14, 14))

    wh_polygon = Polygon(
        warehouse_df.values, closed=True,
        edgecolor='black', facecolor='lightgray', linewidth=2, label='Warehouse'
    )
    ax.add_patch(wh_polygon)

    for i, row in obstacles_df.iterrows():
        ox, oy, ow, od = row[0], row[1], row[2], row[3]
        obs_rect = Rectangle(
            (ox, oy), ow, od,
            edgecolor='red', facecolor='darkred', alpha=0.6,
            hatch='//', label='Obstacle' if i == 0 else ""
        )
        ax.add_patch(obs_rect)

    if not placements_df.empty:
        gap_dict = dict(zip(bays_df['id'], bays_df['gap']))
        for i, row in placements_df.iterrows():
            bx, by, bw, bd, rot = row['x'], row['y'], row['w'], row['d'], row['rot']
            bid = row['bay_id']
            gap = gap_dict[bid]

            if   rot == 0:   gx, gy, gw, gd = bx,       by + bd, bw,  gap
            elif rot == 90:  gx, gy, gw, gd = bx + bw,  by,      gap, bd
            elif rot == 180: gx, gy, gw, gd = bx,       by - gap, bw, gap
            elif rot == 270: gx, gy, gw, gd = bx - gap, by,      gap, bd

            gap_rect = Rectangle(
                (gx, gy), gw, gd,
                edgecolor='goldenrod', facecolor='yellow', alpha=0.3,
                label='Access Gap' if i == 0 else ""
            )
            ax.add_patch(gap_rect)

            bay_rect = Rectangle(
                (bx, by), bw, bd,
                edgecolor='darkblue', facecolor='cyan', alpha=0.8,
                linewidth=1, label='Physical Bay' if i == 0 else ""
            )
            ax.add_patch(bay_rect)
            ax.text(bx + bw / 2, by + bd / 2, str(bid),
                    color='black', fontsize=8, ha='center', va='center', fontweight='bold')

    ax.autoscale_view()
    ax.set_aspect('equal')
    ax.set_title(f'Warehouse Optimisation: {case_name}', fontsize=16)
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.grid(True, linestyle=':', alpha=0.6)

    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right')

    plt.show()

# --- MAIN ---
if __name__ == "__main__":
    for case_num in range(4):
        t0 = time.time()
        case_dir = f"PublicTestCases/Case{case_num}"
        print(f"\n{'='*50}")
        print(f"🚀 PROCESSING {case_dir.upper()}")
        print(f"{'='*50}")

        wh_path   = os.path.join(case_dir, 'warehouse.csv')
        obs_path  = os.path.join(case_dir, 'obstacles.csv')
        ceil_path = os.path.join(case_dir, 'ceiling.csv')
        bays_path = os.path.join(case_dir, 'types_of_bays.csv')

        if not os.path.exists(wh_path):
            print(f"⚠️  Could not find warehouse file in {case_dir}. Skipping...")
            continue

        wh_coords = pd.read_csv(wh_path,   header=None).values
        bays_df   = pd.read_csv(bays_path, header=None,
                                names=['id', 'w', 'd', 'h', 'gap', 'loads', 'price'])

        wh = Warehouse(wh_coords)

        try:
            obs_data = pd.read_csv(obs_path, header=None).values
            wh.apply_obstacles(obs_data)
        except pd.errors.EmptyDataError:
            print("   -> No obstacles found. Proceeding with empty floor.")
            obs_data = np.empty((0, 4), dtype=np.int32)

        try:
            ceil_data = pd.read_csv(ceil_path, header=None).values
            wh.apply_ceiling(ceil_data)
        except pd.errors.EmptyDataError:
            print("   -> No ceiling limits found. Proceeding with unlimited height.")
            ceil_data = np.empty((0, 2), dtype=np.int32)
            wh.ceiling_map[:] = 999999

        print("Running 4-way rotational greedy optimisation with multithreading...")
        results_df = greedy_solver(wh, bays_df)
        tf = time.time()

        print(f"Total Setup & Execution Time: {tf - t0:.4f}s")

        visualize_warehouse_with_gaps(
            pd.DataFrame(wh_coords),
            pd.DataFrame(obs_data) if obs_data.size > 0 else pd.DataFrame(),
            results_df,
            bays_df,
            case_name=f"Case {case_num}"
        )