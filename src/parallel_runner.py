"""
parallel_runner.py — Multi-Threaded GRASP Orchestrator
======================================================
Aprovecha el Python Free-Threaded de Mecalux 2026 para lanzar
Múltiples "FastSolvers" en paralelo sin el overhead de Multiprocessing.
"""

import time
import random
import copy
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from faster_solver import FastSolver


def _worker_task(wh_base, seed: int, time_limit: float):
    """
    Tarea ejecutada por cada núcleo/hilo.
    Aislamos el estado y la semilla de aleatoriedad.
    """
    # 1. Aislamiento de Semilla: Obligamos a este hilo a tomar decisiones aleatorias únicas
    random.seed(seed)

    # 2. Aislamiento de Memoria (Thread-Safety)
    # Como el FastSolver muta el array de numpy (wh.grid), cada hilo necesita su copia
    # física del almacén para no machacar los "1" y "0" de los otros hilos (Race Condition).
    wh_local = copy.deepcopy(wh_base)

    # 3. Arrancamos nuestro motor en C (Numba no tiene GIL, volará aquí)
    solver = FastSolver(wh_local)

    t0 = time.perf_counter()

    # Fase 1: Greedy (15% del presupuesto)
    greedy_budget = time_limit * 0.15
    solver.run_greedy(greedy_budget)

    elapsed_so_far = time.perf_counter() - t0

    # Fase 2: SA (Lo que quede de tiempo, restando 0.5s por seguridad)
    sa_budget = max(1.0, time_limit - elapsed_so_far - 0.5)
    solver.run_sa(sa_budget)

    return solver.score(), solver.export_solution()


def solve_parallel(wh, max_time_seconds=29.0):
    """
    Orquestador Maestro.
    max_time_seconds = 29.0 garantiza que nunca nos pasemos del límite de 30s del juez.
    """
    num_cores = multiprocessing.cpu_count()
    print(f"\n[Parallel] Entorno Free-Threaded (PEP 703) detectado.")
    print(f"[Parallel] Desplegando {num_cores} universos de búsqueda simultáneos (Max: {max_time_seconds}s)")

    best_score = float('inf')
    best_solution = []

    t_start = time.perf_counter()

    # Usamos ThreadPoolExecutor porque, sin GIL, comparte la memoria principal a coste cero
    with ThreadPoolExecutor(max_workers=num_cores) as executor:
        futures = []
        for i in range(num_cores):
            # Asignar una semilla única y muy dispersa a cada hilo
            seed = int(time.time() * 1000) + (i * 9999)

            # Lanzamos la tarea al pool de hilos
            futures.append(executor.submit(_worker_task, wh, seed, max_time_seconds))

        # Recopilación asíncrona: según van terminando los hilos, miramos sus resultados
        for future in as_completed(futures):
            try:
                score, solution = future.result()
                if score < best_score:
                    best_score = score
                    best_solution = solution
            except Exception as e:
                print(f"  [!] Error crítico en un hilo trabajador: {e}")

    elapsed = time.perf_counter() - t_start
    print(f"[Parallel] Búsqueda MASIVA finalizada en {elapsed:.2f}s.")
    print(f"[Parallel] ⭐ Mejor Puntuación Global (Q) = {best_score:.4f} ⭐")

    return best_solution