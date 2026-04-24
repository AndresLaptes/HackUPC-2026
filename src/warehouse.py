import numpy as np
import pandas as pd
from numba import njit


@njit(fastmath=True, cache=True)
def _fill_ceiling_map(ceiling_map, points):
    num_points = points.shape[0]
    for i in range(num_points - 1):
        x_start = int(points[i, 0])
        x_end = int(points[i + 1, 0])
        h = int(points[i, 1])
        ceiling_map[x_start:x_end] = h

    last_x = int(points[-1, 0])
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
            grid[y_start:y_end, x_start:x_end] += 1


@njit(fastmath=True, cache=True)
def move_object_in_place(
    grid: np.ndarray, obj_tensor: np.ndarray, obj_idx: int, new_x: int, new_y: int
):
    H, W = grid.shape

    old_x, old_y = obj_tensor[obj_idx, 0], obj_tensor[obj_idx, 1]
    w, d = obj_tensor[obj_idx, 2], obj_tensor[obj_idx, 3]

    old_xs, old_ys = max(0, old_x), max(0, old_y)
    old_xe, old_ye = min(W, old_x + w), min(H, old_y + d)
    if old_xs < old_xe and old_ys < old_ye:
        grid[old_ys:old_ye, old_xs:old_xe] -= 1

    new_xs, new_ys = max(0, new_x), max(0, new_y)
    new_xe, new_ye = min(W, new_x + w), min(H, new_y + d)
    if new_xs < new_xe and new_ys < new_ye:
        grid[new_ys:new_ye, new_xs:new_xe] += 1

    obj_tensor[obj_idx, 0] = new_x
    obj_tensor[obj_idx, 1] = new_y


@njit(fastmath=True, cache=True)
def fast_orthogonal_scanline(grid_shape, vert_x, vert_ymin, vert_ymax):
    H, W = grid_shape
    grid = np.full(grid_shape, 10000, dtype=np.int32)
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


class Warehouse:
    def __init__(self, coords_array: np.ndarray):
        if coords_array.ndim != 2 or coords_array.shape[1] != 2:
            raise ValueError("Se espera un tensor de forma (N, 2)")

        self.coords = coords_array
        self.max_x = np.max(self.coords[:, 0])
        self.max_y = np.max(self.coords[:, 1])

        self.grid = self._generate_grid()
        self.ceiling_map = np.zeros(self.max_x, dtype=np.int32)
        self.obs_tensor = np.empty((0, 4), dtype=np.int32)
        self.bay_catalogue = np.empty((0, 7), dtype=np.int32)

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

        return fast_orthogonal_scanline(
            (self.max_y, self.max_x), arr_vx, arr_vmin, arr_vmax
        )

    def apply_obstacles(self, obs_tensor: np.ndarray):
        if obs_tensor.size == 0:
            return
        if obs_tensor.shape[1] != 4:
            raise ValueError(
                "El tensor de obstáculos debe tener 4 columnas (X, Y, W, D)."
            )
        self.obs_tensor = obs_tensor
        _add_obstacles_kernel(self.grid, self.obs_tensor)

    def move_obstacle(self, obs_index: int, new_x: int, new_y: int):
        move_object_in_place(self.grid, self.obs_tensor, obs_index, new_x, new_y)

    def check_valid_placement(self, x: int, y: int, w: int, d: int) -> bool:
        if x < 0 or y < 0 or x + w > self.max_x or y + d > self.max_y:
            return False
        return np.sum(self.grid[y : y + d, x : x + w]) == 0

    def apply_ceiling(self, ceiling_points: np.ndarray):
        idx = np.argsort(ceiling_points[:, 0])
        sorted_points = ceiling_points[idx]
        _fill_ceiling_map(self.ceiling_map, sorted_points)

    def is_height_legal(self, x: int, width: int, bay_height: int) -> bool:
        x_end = min(self.max_x, x + width)
        return np.min(self.ceiling_map[x:x_end]) >= bay_height

    def apply_bays(self, bay_tensor: np.ndarray):
        if bay_tensor.size == 0:
            return
        if bay_tensor.shape[1] != 7:
            raise ValueError(
                "El tensor de bays debe tener 7 columnas (id, width, depth, height, gap, nLoads, price)."
            )
        self.bay_catalogue = bay_tensor

    def clone(self):
        new_wh = object.__new__(Warehouse)
        new_wh.coords = self.coords
        new_wh.max_x = self.max_x
        new_wh.max_y = self.max_y
        new_wh.grid = self.grid.copy()
        new_wh.ceiling_map = self.ceiling_map.copy()
        new_wh.obs_tensor = self.obs_tensor.copy()
        new_wh.bay_catalogue = self.bay_catalogue.copy()
        return new_wh
