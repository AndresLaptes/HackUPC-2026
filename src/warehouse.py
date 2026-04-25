import numpy as np
import pandas as pd
from numba import njit

@njit(fastmath=True, cache=True)
def fast_orthogonal_scanline(grid_shape, vert_x, vert_ymin, vert_ymax):
    H, W = grid_shape
    grid = np.zeros(grid_shape, dtype=np.uint8)
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
            grid[y, x_start:x_end] = 1

    return grid

class Warehouse:
    def __init__(self, coords_array: np.ndarray):
        if coords_array.ndim != 2 or coords_array.shape[1] != 2:
            raise ValueError("Se espera un tensor de forma (N, 2)")

        self.coords = coords_array

        self.max_x = np.max(self.coords[:, 0])
        self.max_y = np.max(self.coords[:, 1])

        self.grid = self._generate_grid()

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