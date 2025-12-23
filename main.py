# main.py
import os
from datetime import datetime

from config import AppConfig
from Core.objective import ObjectiveWeights
from Output.exporter import (
    export_schedule_csv,
    export_gantt_chart
)
from Utils.logger import Logger
from Utils.seed import set_seed
from Utils.debug_checker import summarize
from Evaluation.plots import plot_convergence

# Algorithms
from Algorithms.simulated_annealing import SimulatedAnnealingScheduler, SAConfig
from Algorithms.grey_wolf_optimizer import GreyWolfOptimizerScheduler, GWOConfig

from Model.models import Task, Resource


# ------------------------------------------------------------
# Demo data (có precedence + resource type)
# ------------------------------------------------------------
def demo_data():
    tasks = [
        Task("T1", "Import orders", 60,
             datetime(2025, 12, 14, 8, 0),
             datetime(2025, 12, 14, 12, 0),
             3, "ANY", []),

        Task("T2", "Validate payment", 45,
             datetime(2025, 12, 14, 8, 0),
             datetime(2025, 12, 14, 11, 0),
             5, "ANY", ["T1"]),

        Task("T3", "Packing", 90,
             datetime(2025, 12, 14, 9, 0),
             datetime(2025, 12, 14, 16, 0),
             3, "PACK", []),

        Task("T4", "Shipping label", 40,
             datetime(2025, 12, 14, 10, 0),
             datetime(2025, 12, 14, 15, 0),
             4, "ANY", ["T2"]),

        Task("T5", "Dispatch", 50,
             datetime(2025, 12, 14, 13, 0),
             datetime(2025, 12, 14, 18, 0),
             2, "SHIP", ["T4"]),
    ]

    resources = [
        Resource("R1", "Worker A", "ANY", 1),
        Resource("R2", "Packing Machine", "PACK", 1),
        Resource("R3", "Shipping Desk", "SHIP", 1),
    ]
    return tasks, resources


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    cfg = AppConfig()
    set_seed(cfg.random_seed)

    os.makedirs(cfg.results_dir, exist_ok=True)
    logger = Logger(os.path.join(cfg.results_dir, "logs.txt"))

    tasks, resources = demo_data()
    tasks_map = {t.id: t for t in tasks}
    res_map = {r.id: r for r in resources}

    # Objective weights
    weights = ObjectiveWeights(
        w_tardiness=cfg.weights.w_tardiness,
        w_makespan=cfg.weights.w_makespan,
        w_earliness=cfg.weights.w_earliness,
    )

    # Algorithms
    sa = SimulatedAnnealingScheduler(
        SAConfig(cfg.sa.t0, cfg.sa.t_min, cfg.sa.alpha, cfg.sa.iters_per_temp),
        weights
    )

    gwo = GreyWolfOptimizerScheduler(
        GWOConfig(cfg.gwo.wolves, cfg.gwo.iters),
        weights
    )

    print("Choose algorithm:")
    print("1) Simulated Annealing")
    print("2) Grey Wolf Optimizer")
    print("3) Both (compare)")
    choice = input("Your choice: ").strip() or "3"

    res_sa = None
    res_gwo = None

    # --------------------------------------------------------
    # Run SA
    # --------------------------------------------------------
    if choice in ("1", "3"):
        res_sa = sa.solve(tasks, resources)

        summary = summarize(res_sa, tasks_map, res_map)
        print(summary)
        logger.log(summary)

        export_schedule_csv(
            res_sa,
            tasks_map,
            res_map,
            os.path.join(cfg.results_dir, "schedule_sa.csv")
        )

        export_gantt_chart(
            res_sa,
            os.path.join(cfg.results_dir, "gantt_sa.png"),
            title="Gantt Chart - Simulated Annealing"
        )

    # --------------------------------------------------------
    # Run GWO
    # --------------------------------------------------------
    if choice in ("2", "3"):
        res_gwo = gwo.solve(tasks, resources)

        summary = summarize(res_gwo, tasks_map, res_map)
        print(summary)
        logger.log(summary)

        export_schedule_csv(
            res_gwo,
            tasks_map,
            res_map,
            os.path.join(cfg.results_dir, "schedule_gwo.csv")
        )

        export_gantt_chart(
            res_gwo,
            os.path.join(cfg.results_dir, "gantt_gwo.png"),
            title="Gantt Chart - Grey Wolf Optimizer"
        )

    # --------------------------------------------------------
    # Compare (SA vs GWO)
    # --------------------------------------------------------
    if choice == "3" and res_sa and res_gwo:
        plot_convergence(
            res_sa.history,
            res_gwo.history,
            os.path.join(cfg.results_dir, "convergence.png")
        )
        logger.log("Saved convergence plot: convergence.png")


if __name__ == "__main__":
    main()
