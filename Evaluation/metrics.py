# Evaluation/metrics.py
from typing import Dict
from Model.models import Schedule, Task

def makespan_minutes(schedule: Schedule) -> float:  # Thời gian hoàn thành toàn bộ lịch 
    assigns = schedule.all_assignments()
    if not assigns:
        return 0.0
    s = min(a.start for a in assigns)
    e = max(a.end for a in assigns)
    return (e - s).total_seconds() / 60.0

def total_tardiness_minutes(schedule: Schedule, tasks: Dict[str, Task]) -> float:  # tổng phút trễ dealine 
    total = 0.0
    for a in schedule.all_assignments():
        t = tasks[a.task_id]
        late = (a.end - t.due_date).total_seconds() / 60.0
        if late > 0:
            total += late
    return total

def weighted_tardiness(schedule: Schedule, tasks: Dict[str, Task]) -> float:  # trễ deadline có xét priorty 
    total = 0.0
    for a in schedule.all_assignments():
        t = tasks[a.task_id]
        late = (a.end - t.due_date).total_seconds() / 60.0
        if late > 0:
            total += late * max(1, t.priority)
    return total

def utilization(schedule: Schedule) -> float:
    grouped = schedule.by_resource()
    if not grouped:
        return 0.0
    total_busy = 0.0
    total_span = 0.0
    for rid, lst in grouped.items():
        if not lst:
            continue
        busy = sum((a.end - a.start).total_seconds() for a in lst)
        span = (max(a.end for a in lst) - min(a.start for a in lst)).total_seconds()
        total_busy += busy
        total_span += max(span, 1.0)
    return total_busy / total_span
