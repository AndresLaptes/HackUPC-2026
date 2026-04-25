import time
import math
import numpy as np

class OptimizedMecalux:

    def __init__(self, warehouse_instance, height_map):
        self.warehouse = warehouse_instance

        # Height map as numpy array for fast access
        self.height_map = np.array(height_map)

        # Safer: logger only if exists
        self.logger = getattr(self, "logger", None)

    def calculate_objective_score(self, active_racks, boxes_left_count):

        if not active_racks:
            return float('inf')

        total_price = 0
        total_load = 0
        utilization_sum = 0

        # Compute aggregates only once (faster + safer)
        for r in active_racks:
            total_price += r.price
            total_load += r.current_load
            utilization_sum += r.get_utilization()

        if total_load == 0:
            return float('inf')

        avg_utilization = utilization_sum / len(active_racks)

       
        total_penalty = 0

        for r in active_racks:

            ix = int(round(r.pos[0]))
            iy = int(round(r.pos[1]))

            if (
                0 <= iy < self.height_map.shape[0]
                and 0 <= ix < self.height_map.shape[1]
            ):
                ceiling_limit = self.height_map[iy, ix]
            else:
                ceiling_limit = 0

            overflow = r.rack_h - ceiling_limit

            if overflow > 0:
                total_penalty += overflow * overflow * 10000

        
        base_score = total_price / (total_load + 1e-9)

        final_score = (
            base_score
            * (2 - avg_utilization)
            + boxes_left_count * 1000
            + total_penalty
        )

        return final_score

    def solve(self, boxes, available_spots, shelf_lim, default_rack_h=8.0):

        if self.logger:
            self.logger.info("Starting optimization...")

        # Sort heavy first (good heuristic)
        boxes = sorted(boxes, key=lambda x: -x["weight"])

        active_racks = []
        remaining_boxes = len(boxes)

        for box in boxes:

            best_score = float("inf")
            decision = None

            for r in active_racks:

                if box["type"] == "heavy" and r.type != "reinforced":
                    continue

                if r.current_load + box["weight"] <= r.lim:

                    # SAFE SIMULATION (fix: avoid negative state bugs)
                    r.current_load += box["weight"]

                    score = self.calculate_objective_score(
                        active_racks,
                        remaining_boxes - 1
                    )

                    if score < best_score:
                        best_score = score
                        decision = ("EXISTING", r)

                    # rollback
                    r.current_load -= box["weight"]


            if len(active_racks) < len(available_spots):

                spot = available_spots[len(active_racks)]

                if self.warehouse.check_valid_placement(
                    spot["x"], spot["y"], spot["w"], spot["d"]
                ):

                    for t_name, t_price in [("standard", 100), ("reinforced", 150)]:

                        if box["type"] == "heavy" and t_name != "reinforced":
                            continue

                        temp_rack = type(active_racks[0])(
                            len(active_racks),
                            t_name,
                            shelf_lim,
                            t_price,
                            pos=(spot["x"], spot["y"]),
                            rack_h=default_rack_h
                        )

                        temp_rack.current_load = box["weight"]

                        score = self.calculate_objective_score(
                            active_racks + [temp_rack],
                            remaining_boxes - 1
                        )

                        if score < best_score:
                            best_score = score
                            decision = ("NEW", (t_name, t_price, spot))

       
            if decision is None:
                if self.logger:
                    self.logger.warning(f"Box {box} could not be placed")
                continue

            if decision[0] == "EXISTING":

                rack = decision[1]
                rack.current_load += box["weight"]

            else:

                t_name, t_price, spot = decision[1]

                new_rack = type(active_racks[0])(
                    len(active_racks),
                    t_name,
                    shelf_lim,
                    t_price,
                    pos=(spot["x"], spot["y"]),
                    rack_h=default_rack_h
                )

                new_rack.current_load = box["weight"]
                active_racks.append(new_rack)

                if self.logger:
                    self.logger.info(
                        f"Rack {t_name} placed at ({spot['x']},{spot['y']})"
                    )

            remaining_boxes -= 1

        return active_racks