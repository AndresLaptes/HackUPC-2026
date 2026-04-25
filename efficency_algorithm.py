import time
import math
import random

# --- CONFIGURACIÓN ESTRUCTURAL ---
RACK_WIDTH = 2.0
RACK_DEPTH = 1.0
SHELF_LIMIT = 1000

def get_ceiling_height(x, y):
    """ Función a trozos que define el límite del techo """
    if x < 25: return 4.0
    if 25 <= x < 75: return 12.0
    return 7.0

# --- CLASE RACK PARA LA SIMULACIÓN ---
class Rack:
    def __init__(self, id, r_type, max_h):
        self.id = id
        self.type = r_type
        self.num_levels = int(max_h // 2.0)
        self.lim = self.num_levels * 500
        self.price = (150 if r_type == 'reinforced' else 100) * self.num_levels
        self.current_load = 0

# --- ALGORITMO R2 + PENALTY (TU ESTRATEGIA) ---
def solve_R2_penalty(boxes, num_spots):
    start = time.perf_counter()
    active_racks = []
    
    for box in boxes:
        best_score = float('inf')
        for i in range(num_spots):
            # Simulamos coordenadas X, Y
            x, y = i * 1.5, (i % 10) * 2.0
            max_h = get_ceiling_height(x, y)
            
            # PENALTY: En R2, la altura es solo un chequeo de coste
            # Si no cabe, el score sube tanto que el gradiente lo ignora
            penalty = 5000 if 8.0 > max_h else 0
            
            # Simulación de Score Mecalux
            score = (150 / (box['weight'] + 1))**1.5 + penalty
            if score < best_score:
                best_score = score
        
        # Simulación de apertura de rack
        active_racks.append(Rack(len(active_racks), box['type'], 8.0))
        
    return time.perf_counter() - start

# --- ALGORITMO R3 FULL (ALTURA COMO VARIABLE) ---
def solve_R3_variable(boxes, num_spots):
    start = time.perf_counter()
    active_racks = []
    
    for box in boxes:
        best_score = float('inf')
        for i in range(num_spots):
            x, y = i * 1.5, (i % 10) * 2.0
            
            # En R3, el algoritmo debe 'buscar' la Z óptima iterando
            z_variable = 0.0
            for _ in range(5): # Iteraciones de ajuste de altura
                max_h = get_ceiling_height(x, y)
                grad_z = 2 * (z_variable - max_h)
                z_variable -= 0.1 * grad_z # Descenso de gradiente en Z
            
            score = (150 / (box['weight'] + 1))**1.5
            if score < best_score:
                best_score = score
                
        active_racks.append(Rack(len(active_racks), box['type'], z_variable))
        
    return time.perf_counter() - start

# --- EJECUCIÓN DEL BENCHMARK ---
if __name__ == "__main__":
    print("="*60)
    print("🏆 MECALUX CHALLENGE: R2+PENALTY vs R3-VARIABLE")
    print("="*60)
    
    # Probamos con 1000 cajas y 100 posibles ubicaciones (Estrés medio)
    boxes = [{'weight': random.randint(10, 100), 'type': 'reinforced'} for _ in range(1000)]
    spots_count = 100

    print(f"[*] Procesando {len(boxes)} cajas en {spots_count} ubicaciones...")
    
    t2 = solve_R2_penalty(boxes, spots_count)
    print(f"✅ R2 + Penalty completado.")
    
    t3 = solve_R3_variable(boxes, spots_count)
    print(f"✅ R3 Variable completado.")
    
    print("\n" + "📊 RESULTADOS FINALES:")
    print(f"------------------------------------------------------------")
    print(f"Tiempo R2 (Tu modelo):  {t2:.4f} segundos")
    print(f"Tiempo R3 (Referencia): {t3:.4f} segundos")
    print(f"------------------------------------------------------------")
    
    diff = ((t3 - t2) / t3) * 100
    print(f"🚀 CONCLUSIÓN: Tu código es un {diff:.2f}% más rápido.")
    print(f"Esto te permite procesar {int(len(boxes)*(diff/100))} cajas extra en el mismo tiempo.")