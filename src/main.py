import os
import numpy as np
import pandas as pd
from numba import njit
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

# --- MATHEMATICAL HELPER ---
def calculate_polygon_area(coords: np.ndarray) -> float:
    """Calculates the exact area of the warehouse polygon using the Shoelace formula."""
    x = coords[:, 0]
    y = coords[:, 1]
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- NUMBA GRID GENERATION FUNCTIONS ---
@njit(fastmath=True, cache=True)
def _fill_ceiling_map(ceiling_map, points):
    num_points = points.shape[0]
    for i in range(num_points - 1):
        x_start = int(points[i, 0])
        x_end = int(points[i + 1, 0])
        x_start = max(0, min(x_start, ceiling_map.shape[0]))
        x_end = max(0, min(x_end, ceiling_map.shape[0]))
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
        x_end, y_end = min(W, x + w), min(H, y + d)
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
            x_end = min(W, active_slice[i + 1])
            grid[y, x_start:x_end] = 0
    return grid

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

        # Calculate exact total area for the Q formula
        self.total_area = calculate_polygon_area(self.coords)

        self.grid = self._generate_grid()
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
        arr_vx = np.array(vert_x, dtype=np.int32)
        arr_vmin = np.array(vert_ymin, dtype=np.int32)
        arr_vmax = np.array(vert_ymax, dtype=np.int32)
        return fast_orthogonal_scanline((self.max_y, self.max_x), arr_vx, arr_vmin, arr_vmax)

    def apply_obstacles(self, obs_tensor: np.ndarray):
        if obs_tensor.size == 0: return
        self.obs_tensor = obs_tensor.copy()
        self.obs_tensor[:, 0] -= self.min_x
        self.obs_tensor[:, 1] -= self.min_y
        _add_obstacles_kernel(self.grid, self.obs_tensor)

    def apply_ceiling(self, ceiling_points: np.ndarray):
        if ceiling_points.size == 0: return
        shifted_points = ceiling_points.copy()
        shifted_points[:, 0] -= self.min_x
        idx = np.argsort(shifted_points[:, 0])
        sorted_points = shifted_points[idx]
        _fill_ceiling_map(self.ceiling_map, sorted_points)

    def is_height_legal(self, x: int, width: int, bay_height: int) -> bool:
        x_end = min(self.max_x, x + width)
        return np.min(self.ceiling_map[x:x_end]) >= bay_height

    def get_original_coords(self, grid_x: int, grid_y: int):
        return grid_x + self.min_x, grid_y + self.min_y

# --- PLACEMENT AND SCORING SOLVER ---
def try_place_bay(wh: Warehouse, bx, by, bw, bd, gx, gy, gw, gd):
    if bx < 0 or by < 0 or bx + bw > wh.max_x or by + bd > wh.max_y: return False
    if gx < 0 or gy < 0 or gx + gw > wh.max_x or gy + gd > wh.max_y: return False
    if np.any(wh.grid[by:by+bd, bx:bx+bw] != 0): return False
    if np.any(wh.grid[gy:gy+gd, gx:gx+gw] == 1): return False

    wh.grid[by:by+bd, bx:bx+bw] = 1
    gap_slice = wh.grid[gy:gy+gd, gx:gx+gw]
    gap_slice[gap_slice == 0] = 2
    return True

def greedy_solver(warehouse: Warehouse, bays_df: pd.DataFrame) -> pd.DataFrame:
    # Sorting by efficiency forces the tallest, most load-bearing bays to be tested first, 
    # naturally maximizing and filling the ceiling constraints!
    bays_df['efficiency'] = bays_df['price'] / bays_df['loads']
    bays_df['area'] = bays_df['w'] * bays_df['d']
    sorted_bays = bays_df.sort_values(by=['efficiency', 'area'], ascending=[True, False])
    
    placements = []
    step_size = 100 
    
    sum_prices = 0.0
    sum_loads = 0.0
    sum_area_used = 0.0
    
    for y in range(0, warehouse.max_y, step_size):
        for x in range(0, warehouse.max_x, step_size):
            if warehouse.grid[y, x] != 0: continue
                
            for _, bay in sorted_bays.iterrows():
                w, d, h, gap = int(bay['w']), int(bay['d']), int(bay['h']), int(bay['gap'])
                price, loads = float(bay['price']), float(bay['loads'])
                bid = int(bay['id'])
                
                configurations = [
                    (w, d, x, y + d, w, gap),      # 0°: Gap UP
                    (d, w, x + d, y, gap, w),      # 90°: Gap RIGHT
                    (w, d, x, y - gap, w, gap),    # 180°: Gap DOWN
                    (d, w, x - gap, y, gap, w)     # 270°: Gap LEFT
                ]
                
                placed = False
                for rot_idx, (bw, bd, gx, gy, gw, gd) in enumerate(configurations):
                    # This check guarantees we don't violate the ceiling, while the sort above 
                    # guarantees we pick the tallest possible one that passes this check!
                    if warehouse.is_height_legal(x, bw, h):
                        if try_place_bay(warehouse, x, y, bw, bd, gx, gy, gw, gd):
                            orig_x, orig_y = warehouse.get_original_coords(x, y)
                            placements.append({
                                'bay_id': bid, 'x': orig_x, 'y': orig_y,
                                'w': bw, 'd': bd, 'h': h, 'rot': rot_idx * 90
                            })
                            
                            sum_prices += price
                            sum_loads += loads
                            sum_area_used += (bw * bd)
                            
                            pct_area = sum_area_used / warehouse.total_area
                            current_q = (sum_prices / sum_loads) ** (2.0 - pct_area)
                            
                            placed = True
                            break 
                
                if placed: break 

    pct_area = sum_area_used / warehouse.total_area
    final_q = (sum_prices / sum_loads) ** (2.0 - pct_area) if sum_loads > 0 else 0
    print("-" * 40)
    print(f"Total Bays Placed:    {len(placements)}")
    print(f"Warehouse Area Used:  {pct_area*100:.4f}%")
    print(f"Average Price/Load:   {(sum_prices / sum_loads) if sum_loads > 0 else 0:.4f}")
    print(f"Final Minimum Q Score:{final_q:.4f}")
    print("-" * 40)

    return pd.DataFrame(placements)

def visualize_warehouse_with_gaps(warehouse_df, obstacles_df, placements_df, bays_df, case_name=""):
    fig, ax = plt.subplots(figsize=(14, 14))
    
    wh_polygon = Polygon(warehouse_df.values, closed=True, edgecolor='black', facecolor='lightgray', linewidth=2, label='Warehouse')
    ax.add_patch(wh_polygon)
    
    for i, row in obstacles_df.iterrows():
        ox, oy, ow, od = row[0], row[1], row[2], row[3]
        obs_rect = Rectangle((ox, oy), ow, od, edgecolor='red', facecolor='darkred', alpha=0.6, hatch='//', label='Obstacle' if i==0 else "")
        ax.add_patch(obs_rect)
        
    if not placements_df.empty:
        gap_dict = dict(zip(bays_df['id'], bays_df['gap']))
        for i, row in placements_df.iterrows():
            bx, by, bw, bd, rot = row['x'], row['y'], row['w'], row['d'], row['rot']
            bid = row['bay_id']
            gap = gap_dict[bid]
            
            if rot == 0:     gx, gy, gw, gd = bx, by + bd, bw, gap
            elif rot == 90:  gx, gy, gw, gd = bx + bw, by, gap, bd
            elif rot == 180: gx, gy, gw, gd = bx, by - gap, bw, gap
            elif rot == 270: gx, gy, gw, gd = bx - gap, by, gap, bd
                
            gap_rect = Rectangle((gx, gy), gw, gd, edgecolor='goldenrod', facecolor='yellow', alpha=0.3, label='Access Gap' if i==0 else "")
            ax.add_patch(gap_rect)

            bay_rect = Rectangle((bx, by), bw, bd, edgecolor='darkblue', facecolor='cyan', alpha=0.8, linewidth=1, label='Physical Bay' if i==0 else "")
            ax.add_patch(bay_rect)
            
            # --- NEW ADDITION: ADD TEXT LABEL FOR THE BAY ID ---
            # We place the label at the center point of the physical bay rectangle
            ax.text(bx + bw/2, by + bd/2, str(bid), color='black', fontsize=8, ha='center', va='center', fontweight='bold')
            
    ax.autoscale_view()
    ax.set_aspect('equal')
    ax.set_title(f'Warehouse Optimization: {case_name}', fontsize=16)
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right')
    
    plt.show()

if __name__ == "__main__":
    # Loop through the 4 test cases
    for case_num in range(4):
        case_dir = f"PublicTestCases/Case{case_num}"
        print(f"\n{'='*50}")
        print(f"🚀 PROCESSING {case_dir.upper()}")
        print(f"{'='*50}")
        
        wh_path = os.path.join(case_dir, 'warehouse.csv')
        obs_path = os.path.join(case_dir, 'obstacles.csv')
        ceil_path = os.path.join(case_dir, 'ceiling.csv')
        bays_path = os.path.join(case_dir, 'types_of_bays.csv')
        
        if not os.path.exists(wh_path):
            print(f"⚠️ Could not find warehouse file in {case_dir}. Skipping...")
            continue
            
        # 1. Safely load core data
        wh_coords = pd.read_csv(wh_path, header=None).values
        bays_df = pd.read_csv(bays_path, header=None, names=['id', 'w', 'd', 'h', 'gap', 'loads', 'price'])
        
        # Initialize the game engine
        wh = Warehouse(wh_coords)
        
        # 2. Safely load Obstacles
        try:
            obs_data = pd.read_csv(obs_path, header=None).values
            wh.apply_obstacles(obs_data)
        except pd.errors.EmptyDataError:
            print("   -> No obstacles found for this case. Proceeding with empty floor.")
            obs_data = np.empty((0, 4), dtype=np.int32)
            
        # 3. Safely load Ceiling
        try:
            ceil_data = pd.read_csv(ceil_path, header=None).values
            wh.apply_ceiling(ceil_data)
        except pd.errors.EmptyDataError:
            print("   -> No ceiling limits found for this case. Proceeding with unlimited height.")
            ceil_data = np.empty((0, 2), dtype=np.int32)
            wh.ceiling_map[:] = 999999
        
        # Run solver
        print("Running 4-way rotational greedy optimization...")
        results_df = greedy_solver(wh, bays_df)
        
        # Visualize with Labels
        visualize_warehouse_with_gaps(
            pd.DataFrame(wh_coords), 
            pd.DataFrame(obs_data) if obs_data.size > 0 else pd.DataFrame(), 
            results_df, 
            bays_df,
            case_name=f"Case {case_num}"
        )