import time
import math

class Warehouse:
    def __init__(self, layout, height_map):
        self.height = len(layout)
        self.width = max(len(row) for row in layout)
        # 0 = free, -1 = obstacle
        self.grid = [[0 if cell == "." else -1 for cell in row] for row in layout]
        # Mapa d'altures variable (Variable externa)
        self.height_map = height_map 

    def get_max_height_at(self, x, y):
        """ Retorna l'altura del sostre en un punt específic """
        ix, iy = int(round(x)), int(round(y))
        if 0 <= ix < self.width and 0 <= iy < self.height:
            return self.height_map[iy][ix]
        return 0

    def can_place_rotated_rack(self, cx, cy, w, h, angle):
        rad = math.radians(angle)
        corners = []
        for dx, dy in [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]:
            tx = cx + dx * math.cos(rad) - dy * math.sin(rad)
            ty = cy + dx * math.sin(rad) + dy * math.cos(rad)
            corners.append((tx, ty))

        for tx, ty in corners:
            ix, iy = int(round(tx)), int(round(ty))
            if not (0 <= ix < self.width and 0 <= iy < self.height): return False
            if self.grid[iy][ix] == -1: return False
        return True

    def fill_with_smart_racks(self, r_w, r_h):
        placed_racks = []
        angles = [0, 90, 45]
        
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != 0: continue
                for angle in angles:
                    cx, cy = x + r_w/2, y + r_h/2
                    if self.can_place_rotated_rack(cx, cy, r_w, r_h, angle):
                        # Obtenim l'altura del sostre en aquest spot
                        max_z = self.get_max_height_at(cx, cy)
                        self.grid[y][x] = 1 
                        placed_racks.append({'x': cx, 'y': cy, 'angle': angle, 'max_z': max_z})
                        break
        return placed_racks

class Rack:
    def __init__(self, id, r_type, lim, price, angle=0, pos=(0,0), rack_h=8.0):
        self.id = id
        self.type = r_type
        self.lim = lim
        self.price = price
        self.angle = angle
        self.pos = pos       # (x, y)
        self.rack_h = rack_h # Altura física de l'estanteria
        self.current_load = 0
        self.levels = [[], [], []]

    def get_utilization(self):
        return self.current_load / self.lim if self.lim > 0 else 0

# --- LOSS FUNCTION AMB PARÀMETRE D'ALTURA (R2 + PUNISHMENT) ---
def calculate_objective_score(racks, boxes_left, warehouse):
    if not racks: return float('inf')
    
    total_price = sum(r.price for r in racks)
    total_load = sum(r.current_load for r in racks)
    avg_utilization = sum(r.get_utilization() for r in racks) / len(racks)

    # Càstig per altura (Punishment)
    total_penalty = 0
    for r in racks:
        # Obtenim el límit de la variable externa en la posició del rack
        ceiling_limit = warehouse.get_max_height_at(r.pos[0], r.pos[1])
        if r.rack_h > ceiling_limit:
            # Penalty quadràtic si l'altura de l'estanteria > sostre
            total_penalty += (r.rack_h - ceiling_limit) ** 2 * 5000

    # Fórmula base Mecalux + Penalty per violació de Z
    score = (total_price / total_load) ** (2 - avg_utilization)
    score += (boxes_left * 1000) + total_penalty
    
    return score

# --- ALGORITME DE CARGA ADAPTATIU ---
def solve_mecalux_ultimate(boxes, available_spots, shelf_lim, warehouse, default_rack_h=8.0):
    boxes = sorted(boxes, key=lambda x: -x['weight'])
    active_racks = []

    for box in boxes:
        best_choice = None
        min_score = float('inf')

        # OPCIÓ A: Estanteria existent
        for r in active_racks:
            if box['type'] == 'heavy' and r.type != 'reinforced': continue
            if r.current_load + box['weight'] <= r.lim:
                r.current_load += box['weight']
                score = calculate_objective_score(active_racks, 0, warehouse)
                if score < min_score:
                    min_score = score
                    best_choice = ("EXISTING", r)
                r.current_load -= box['weight']

        # OPCIÓ B: Obrir nova (la Z es castiga dins de calculate_objective_score)
        if len(active_racks) < len(available_spots):
            spot = available_spots[len(active_racks)]
            for t_name, t_price in [('standard', 100), ('reinforced', 150)]:
                if box['type'] == 'heavy' and t_name != 'reinforced': continue
                
                # Creem rack temporal per avaluar la Loss amb Penalty
                test_rack = Rack(99, t_name, shelf_lim, t_price, 
                                 angle=spot['angle'], pos=(spot['x'], spot['y']), rack_h=default_rack_h)
                test_rack.current_load = box['weight']
                
                score = calculate_objective_score(active_racks + [test_rack], 0, warehouse)
                if score < min_score:
                    min_score = score
                    best_choice = ("NEW", (t_name, t_price, spot))

        # EXECUCIÓ DE LA MILLOR DECISIÓ
        if best_choice:
            if best_choice[0] == "EXISTING":
                r = best_choice[1]
                r.current_load += box['weight']
                lvl = 0 if box['type'] == 'heavy' else (1 if box['weight'] > 20 else 2)
                r.levels[lvl].append(box)
            else:
                t_name, t_price, spot = best_choice[1]
                new_r = Rack(len(active_racks), t_name, shelf_lim, t_price, 
                             angle=spot['angle'], pos=(spot['x'], spot['y']), rack_h=default_rack_h)
                new_r.current_load = box['weight']
                new_r.levels[0 if box['type'] == 'heavy' else 1].append(box)
                active_racks.append(new_r)

    return active_racks