
from typing import Dict, List, Tuple
from Model.models import Schedule, Task, Resource
from Core.constraints_hard import HARD_CONSTRAINTS

'''Chạy tất cả ràng buộc cứng'''
def check_feasible(schedule: Schedule, tasks: Dict[str, Task], resources: Dict[str, Resource]) -> Tuple[bool, List[str]]:
    violations: List[str] = []
    for fn in HARD_CONSTRAINTS:
        violations.extend(fn(schedule, tasks, resources))
    return (len(violations) == 0), violations
