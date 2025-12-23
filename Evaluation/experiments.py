# experiment.py
import statistics
from typing import List, Dict

from Algorithms.simulated_annealing import (
    SimulatedAnnealingScheduler,
    SAConfig
)
from Algorithms.grey_wolf_optimizer import (
    GreyWolfOptimizerScheduler,
    GWOConfig
)
from Core.objective import ObjectiveWeights
from Model.models import Task, Resource, Result


# ============================================================ 
# Helper: chạy 1 thuật toán nhiều lần
# ============================================================ 

def run_multiple(
    scheduler,
    tasks: List[Task],
    resources: List[Resource],
    runs: int = 10,
    progress_callback=None
) -> Dict:
    results: List[Result] = []

    for i in range(runs):
        if progress_callback:
            progress_callback(f"Run {i+1}/{runs}...")
        res = scheduler.solve(tasks, resources)
        results.append(res)

    costs = [r.cost for r in results]
    runtimes = [r.runtime_sec for r in results]
    feasible_rate = sum(1 for r in results if r.feasible) / runs

    return {
        "best_cost": min(costs),
        "avg_cost": statistics.mean(costs),
        "worst_cost": max(costs),
        "std_cost": statistics.pstdev(costs) if len(costs) > 1 else 0,
        "avg_runtime": statistics.mean(runtimes),
        "feasible_rate": feasible_rate,
        "history_example": results[0].history,
    }


# ============================================================ 
# Main experiment
# ============================================================ 

def experiment(
    tasks: List[Task],
    resources: List[Resource],
    runs: int = 10,
    progress_callback=None
):
    weights = ObjectiveWeights(
        w_tardiness=5.0,
        w_makespan=1.0,
        w_earliness=0.0
    )

    # ---------------- SA ----------------
    if progress_callback:
        progress_callback("\n=== Running Simulated Annealing ===")
    sa_cfg = SAConfig(
        t0=200.0,
        t_min=0.5,
        alpha=0.95,
        iters_per_temp=200
    )
    sa = SimulatedAnnealingScheduler(sa_cfg, weights)
    sa_stats = run_multiple(sa, tasks, resources, runs, progress_callback)

    # ---------------- GWO ----------------
    if progress_callback:
        progress_callback("\n=== Running Grey Wolf Optimizer ===")
    gwo_cfg = GWOConfig(
        wolves=25,
        iters=150
    )
    gwo = GreyWolfOptimizerScheduler(gwo_cfg, weights)
    gwo_stats = run_multiple(gwo, tasks, resources, runs, progress_callback)

    return sa_stats, gwo_stats