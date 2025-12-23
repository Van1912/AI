from __future__ import annotations
import math
import random
import time
from typing import List, Dict

from Algorithms.base import SchedulerBase
from Algorithms.initial_solution import (
    priority_list_priority,
    decode_priority_list
)
from Core.neighborhood import NEIGHBORS
from Core.objective import total_cost, ObjectiveWeights
from Core.feasibility import check_feasible
from Model.models import Task, Resource, Result

class SAConfig:
    def __init__(self, t0=200.0, t_min=0.5, alpha=0.95, iters_per_temp=200):
        self.t0 = t0   # Nhiệt độ ban đầu 
        self.t_min = t_min  # Nhiệt độ dừng 
        self.alpha = alpha  # Hệ số làm nguội 
        self.iters_per_temp = iters_per_temp  # số lần thử tại mỗi nhiệt dộ 

class SimulatedAnnealingScheduler(SchedulerBase):
    """
    Simulated Annealing cho Job Scheduling
    State: priority list (List[str])
    """

    def __init__(self, cfg: SAConfig, weights: ObjectiveWeights):
        self.cfg = cfg
        self.weights = weights

    def _evaluate(
        self,
        priority: List[str],
        tasks_map: Dict[str, Task],
        resources: List[Resource],
    ):
        schedule, _ = decode_priority_list(priority, tasks_map, resources)
        res_map = {r.id: r for r in resources}
        cost = total_cost(schedule, tasks_map, res_map, self.weights)
        return cost, schedule

    def solve(self, tasks: List[Task], resources: List[Resource]) -> Result:
        start = time.time()
        tasks_map = {t.id: t for t in tasks}
        res_map = {r.id: r for r in resources}

        # 1) nghiệm khởi tạo
        current_p = priority_list_priority(tasks)
        current_cost, current_s = self._evaluate(current_p, tasks_map, resources)

        best_p = current_p[:]
        best_cost = current_cost
        best_s = current_s

        history = [best_cost]

        # 2) vòng lặp SA
        T = self.cfg.t0
        while T > self.cfg.t_min:
            for _ in range(self.cfg.iters_per_temp):
                op = random.choice(NEIGHBORS)
                candidate_p = op(current_p)

                cand_cost, cand_s = self._evaluate(candidate_p, tasks_map, resources)
                delta = cand_cost - current_cost

                if delta <= 0 or random.random() < math.exp(-delta / max(T, 1e-9)):
                    current_p, current_cost, current_s = candidate_p, cand_cost, cand_s

                if current_cost < best_cost:
                    best_cost = current_cost
                    best_p = current_p[:]
                    best_s = current_s

            history.append(best_cost)
            T *= self.cfg.alpha

        feasible, violations = check_feasible(best_s, tasks_map, res_map)

        return Result(
            schedule=best_s,
            cost=best_cost,
            feasible=feasible,
            violations=violations,
            history=history,
            runtime_sec=time.time() - start,
            algorithm="Simulated Annealing",
        )
