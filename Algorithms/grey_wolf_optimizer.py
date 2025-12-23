from __future__ import annotations
import random
import time
from typing import List, Dict

from Algorithms.base import SchedulerBase
from Algorithms.initial_solution import (
    priority_list_edd,
    decode_priority_list
)
from Core.objective import total_cost, ObjectiveWeights
from Core.feasibility import check_feasible
from Model.models import Task, Resource, Result


class GWOConfig:
    def __init__(self, wolves=25, iters=150):
        self.wolves = wolves
        self.iters = iters


def rank_map(p: List[str]) -> Dict[str, int]:    #Chuyển priority list thành thứ hạng 
    return {tid: i for i, tid in enumerate(p)}


def combine(alpha, beta, delta, a):   # a là hệ số điều khiển khám phá
    ra, rb, rd = rank_map(alpha), rank_map(beta), rank_map(delta)   #chuyển 3 nghiệm thành bản đồ thứ hạng 
    n = len(alpha)

    scored = [] #danh sách chấm điểm từng task 
    for tid in alpha:  # duyệt theo task trong alpha (đảm bảo đủ task)
        score = (
            ra[tid] + rb[tid] + rd[tid]
        ) / (3 * max(1, n - 1))              # lấy vi trí trung bình của task trong 3 nghiệm tốt nhất, task nào càng xuất hiện sớm thì score càng nhỏ và ưu tiên cao hơn 
        score += (random.random() - 0.5) * 0.2 * a        # đây là nhiễu GWO khi a lớn thì nhiễu càng mạnh 
        scored.append((score, tid))       # Lưu điểm và task

    scored.sort(key=lambda x: x[0])  # sắp xếp sort tăng dần 
    return [tid for _, tid in scored]


class GreyWolfOptimizerScheduler(SchedulerBase):
    """
    Grey Wolf Optimizer cho Job Scheduling (Discrete)
    Wolf = priority list
    """

    def __init__(self, cfg: GWOConfig, weights: ObjectiveWeights):  #Hàm khởi tạo 
        self.cfg = cfg
        self.weights = weights

    def _fitness(self, priority, tasks_map, resources):   # đánh giá một sói 
        schedule, _ = decode_priority_list(priority, tasks_map, resources)   # biến priority thành schedule thực tế 
        res_map = {r.id: r for r in resources} # map tài nguyên cho hàm objective 
        return total_cost(schedule, tasks_map, res_map, self.weights), schedule

    def solve(self, tasks: List[Task], resources: List[Resource]) -> Result:
        start = time.time()    # Bắt đầu đo runtime 
        tasks_map = {t.id: t for t in tasks}   # tăng tốc truy xuất 
        res_map = {r.id: r for r in resources} 
        task_ids = [t.id for t in tasks]   # Danh sách ID công việc 

        # 1) khởi tạo đàn sói
        wolves = [priority_list_edd(tasks)] # sói đầu tiên bằng nghiệm EDD tốt 
        for _ in range(self.cfg.wolves - 1):
            p = task_ids[:]
            random.shuffle(p)
            wolves.append(p)

        history = [] # lưu lịch sử cost tốt nhất 

        # 2) vòng lặp GWO
        for it in range(self.cfg.iters):
            evaluated = [self._fitness(w, tasks_map, resources) for w in wolves]   # đánh giá toàn độ đàn sói 
            ranked = sorted(zip(wolves, evaluated), key=lambda x: x[1][0])  # Sắp theo cost tăng dần 

            # 3 sói tốt nhất 
            alpha = ranked[0][0]
            beta = ranked[1][0]
            delta = ranked[2][0]

            a = 2 * (1 - it / self.cfg.iters)   # a giảm tuyến tính 
            # Ban đầu a lớn thì khám phá không gian nghiệm 
            # Về cuối a nhỏ thì khai thác nghiệm tốt 
            # Tránh kẹt cực tiểu cục bộ, hội tụ dần về nghiệm tối ưu 

            new_wolves = []  # tạo đàn mới 
            for _ in range(self.cfg.wolves):   # mỗi sói mới học theo 3 sói đầu đàn 
                new_p = combine(alpha, beta, delta, a)
                new_wolves.append(new_p)

            wolves = new_wolves   # Cập nhật đàn 
            history.append(ranked[0][1][0])    # Lưu best cost 

        best_p = ranked[0][0]
        best_cost, best_s = ranked[0][1]

        feasible, violations = check_feasible(best_s, tasks_map, res_map)   # kiểm tra ràng buộc 

        return Result(
            schedule=best_s,
            cost=best_cost,
            feasible=feasible,
            violations=violations,
            history=history,
            runtime_sec=time.time() - start,
            algorithm="Grey Wolf Optimizer",
        )
