# Core/constraints_hard.py
from typing import Dict, List
from Model.models import Schedule, Task, Resource

'''Đảm bảo mỗi resource chỉ xử lý 1 task tại 1 thời điểm'''
def hc_no_overlap(schedule: Schedule, tasks: Dict[str, Task], resources: Dict[str, Resource]) -> List[str]:
    violations: List[str] = []  # danh sách lỗi vi phạm 
    grouped = schedule.by_resource()  # gom assignment theo id 
    for rid, lst in grouped.items(): # duyệt từng resource
        for i in range(len(lst) - 1): # so sánh các assignment liên tiếp 
            if lst[i].end > lst[i + 1].start:
                violations.append(f"OVERLAP: {rid} {lst[i].task_id} overlaps {lst[i+1].task_id}")
    return violations

'''Đảm bảo task không bắt đầu trước thời điểm release_time'''
def hc_release_time(schedule: Schedule, tasks: Dict[str, Task], resources: Dict[str, Resource]) -> List[str]:
    violations: List[str] = []
    for a in schedule.all_assignments():
        t = tasks[a.task_id]
        if a.start < t.release_time:
            violations.append(f"RELEASE: {t.id} starts before release_time")
    return violations

'''Kiểm tra quan hệ trước sau'''   
def hc_precedence(schedule: Schedule, tasks: Dict[str, Task], resources: Dict[str, Resource]) -> List[str]:
    violations: List[str] = []
    for t in tasks.values():
        a_t = schedule.get(t.id)  # nếu task chưa được schedule thì bỏ qua 
        if not a_t:
            continue
        for p in t.predecessors:
            a_p = schedule.get(p)
            if a_p and a_p.end > a_t.start:
                violations.append(f"PREC: {t.id} starts before predecessor {p} ends")
    return violations

'''Đảm bảo task được gán đúng loại tài nguyên'''
def hc_resource_type(schedule: Schedule, tasks: Dict[str, Task], resources: Dict[str, Resource]) -> List[str]:
    violations: List[str] = []
    for a in schedule.all_assignments():
        t = tasks[a.task_id]
        r = resources[a.resource_id]
        if t.required_type != "ANY" and r.rtype != "ANY" and t.required_type != r.rtype:
            violations.append(f"TYPE: {t.id} requires {t.required_type} but assigned to {r.rtype}")
    return violations

HARD_CONSTRAINTS = [hc_no_overlap, hc_release_time, hc_precedence, hc_resource_type]
