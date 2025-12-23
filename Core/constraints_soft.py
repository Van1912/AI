'''Dùng để phạt bằng cost'''
from typing import Dict
from Model.models import Schedule, Task, Resource

'''Tính tổng tời gian trễ deadline'''
def sc_total_tardiness(schedule: Schedule, tasks: Dict[str, Task], resources: Dict[str, Resource]) -> float:
    total = 0.0
    for a in schedule.all_assignments():
        t = tasks[a.task_id]
        late_min = (a.end - t.due_date).total_seconds() / 60.0
        if late_min > 0:
            total += late_min * max(1, t.priority)
    return total

'''Phạt nhẹ nếu task hoàn thành quá sớm vì trong doanh nghiệp nếu hoàn thành quá sớm thì có thể gây nhiều chi phí'''
def sc_total_earliness(schedule: Schedule, tasks: Dict[str, Task], resources: Dict[str, Resource]) -> float:
    # Tuỳ chọn: phạt sớm nhẹ theo mô hình JIT; muốn tắt => weight = 0 trong config
    total = 0.0
    for a in schedule.all_assignments():
        t = tasks[a.task_id]
        early_min = (t.due_date - a.end).total_seconds() / 60.0
        if early_min > 0:
            total += early_min * 0.1
    return total

