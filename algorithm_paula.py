import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, box
import time
import csv
from numba import njit

# --- CONFIGURACIÓN DE ÉLITE ---
GRID_RES = 20 
GAP_SIZE = 40  # Milímetros de gap (se añade solo al ancho/width)

@njit(cache=True, fastmath=True)
def find_and_place(grid, w_grid, d_grid):
    rows, cols = grid.shape
    for ix in range(rows - w_grid + 1):
        for iy in range(cols - d_grid + 1):
            is_free = True
            # Escaneo de colisión optimizado
            for r in range(ix, ix + w_grid):
                for c in range(iy, iy + d_grid):
                    if grid[r, c] != 0:
                        is_free = False
                        break
                if not is_free: break
            
            if is_free:
                # Marcamos el bloque (incluyendo el gap) como ocupado
                grid[ix:ix + w_grid, iy:iy + d_grid] = 1
                return ix, iy
    return -1, -1

class MecaluxFullBinSolver:
    def __init__(self):
        folder = "resource/case2/"
        self.wh_coords = self._load_csv(folder + 'warehouse.csv')
        self.warehouse = Polygon(self.wh_coords)
        obs_raw = self._load_csv(folder + 'obstacles.csv')
        self.obstacles = [box(x, y, x+w, y+d) for x, y, w, d in obs_raw]
        self.bay_types = self._load_bays(folder + 'types_of_bays.csv')
        
        min_x, min_y, max_x, max_y = self.warehouse.bounds
        self.gw, self.gd = int(max_x/GRID_RES) + 1, int(max_y/GRID_RES) + 1
        self.grid = np.zeros((self.gw, self.gd), dtype=np.uint8)

        # Pre-llenado de obstáculos y límites
        for ix in range(self.gw):
            for iy in range(self.gd):
                rect = box(ix*GRID_RES, iy*GRID_RES, (ix+1)*GRID_RES, (iy+1)*GRID_RES)
                if not self.warehouse.contains(rect):
                    self.grid[ix, iy] = 1
        
        for o in self.obstacles:
            b = o.bounds
            x0, y0, x1, y1 = int(b[0]/GRID_RES), int(b[1]/GRID_RES), int(b[2]/GRID_RES)+1, int(b[3]/GRID_RES)+1
            self.grid[x0:x1, y0:y1] = 1

    def _load_csv(self, p):
        with open(p, 'r') as f: return [[float(x) for x in r] for r in csv.reader(f) if r]

    def _load_bays(self, p):
        bays = []
        with open(p, 'r') as f:
            for r in csv.reader(f):
                if r:
                    w, d = float(r[1]), float(r[2])
                    # CÁLCULO CRÍTICO: Añadimos el gap al ancho para la rejilla
                    # pero guardamos el ancho original para el dibujo/cálculo de área
                    w_with_gap = w + GAP_SIZE
                    bays.append({
                        'id': int(r[0]), 'w_real': w, 'd': d,
                        'w_grid': int(w_with_gap/GRID_RES), 
                        'd_grid': int(d/GRID_RES),
                        'l': float(r[5]), 'p': float(r[6])
                    })
        return bays

    def solve(self):
        start_t = time.time()
        bays_to_place = []
        for b in self.bay_types:
            bays_to_place.extend([b] * 60) # Aumentado el stock para mayor densidad
        
        # Heurística: Big Rocks First (por área real)
        bays_to_place.sort(key=lambda x: x['w_real'] * x['d'], reverse=True)

        placed = []
        working_grid = self.grid.copy()
        
        for bay in bays_to_place:
            ix, iy = find_and_place(working_grid, bay['w_grid'], bay['d_grid'])
            
            if ix != -1:
                placed.append({
                    'x': ix * GRID_RES, 
                    'y': iy * GRID_RES, 
                    'w': bay['w_real'], 
                    'd': bay['d'],
                    'p': bay['p'], 'l': bay['l'], 'a': bay['w_real'] * bay['d']
                })
        
        self.exec_time = time.time() - start_t
        self.placed_final = placed
        
        t_p = sum(x['p'] for x in placed)
        t_l = sum(x['l'] for x in placed)
        t_a = sum(x['a'] for x in placed)
        q = (t_p / t_l)**(2.0 - (t_a / self.warehouse.area)) if t_l > 0 else 1e12
        return q

    def visualize(self, q):
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.plot(*self.warehouse.exterior.xy, color='black', lw=2)
        for o in self.obstacles: ax.fill(*o.exterior.xy, color='gray', alpha=0.4)
        
        for r in self.placed_final:
            # Dibujamos la bahía original. El gap se verá como espacio vacío a la derecha.
            rect = plt.Rectangle((r['x'], r['y']), r['w'], r['d'], 
                                facecolor='royalblue', edgecolor='black', alpha=0.7, lw=0.5)
            ax.add_patch(rect)
            
        ax.set_aspect('equal')
        plt.title(f"Mecalux Solver | Gaps Width: {GAP_SIZE}mm | Q: {q:.4f} | {self.exec_time:.2f}s")
        plt.show()

if __name__ == "__main__":
    solver = MecaluxFullBinSolver()
    q_val = solver.solve()
    solver.visualize(q_val)