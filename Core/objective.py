
from typing import Dict
from Model.models import Schedule, Task, Resource
from Core.constraints_soft import sc_total_tardiness, sc_total_earliness
'''Điều chỉnh từng mức độ quan trọng của từng tiêu chí'''
class ObjectiveWeights:
    def __init__(self, w_tardiness=5.0, w_makespan=1.0, w_earliness=0.0):
        self.w_tardiness = float(w_tardiness)
        self.w_makespan = float(w_makespan)
        self.w_earliness = float(w_earliness)
'''Tính thời gian hoàn thành toàn bộ lịch'''
def makespan_minutes(schedule: Schedule) -> float:
    assigns = schedule.all_assignments()
    if not assigns:
        return 0.0
    s = min(a.start for a in assigns)
    e = max(a.end for a in assigns)
    return (e - s).total_seconds() / 60.0
'''Gộp tất cả ràng buộc mềm + makespan thành 1 số '''
def total_cost(schedule: Schedule, tasks: Dict[str, Task], resources: Dict[str, Resource], w: ObjectiveWeights) -> float:
    tard = sc_total_tardiness(schedule, tasks, resources)
    early = sc_total_earliness(schedule, tasks, resources)
    ms = makespan_minutes(schedule)
    return w.w_tardiness * tard + w.w_makespan * ms + w.w_earliness * early
