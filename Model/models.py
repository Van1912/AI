from datetime import datetime
from typing import Dict, List, Optional

class Task:
    """
    Task = công việc trong công ty.
    - release_time: thời điểm sớm nhất được bắt đầu
    - due_date: deadline
    - predecessors: danh sách task phải xong trước
    - required_type: yêu cầu kỹ năng / loại máy
    """
    def __init__(
        self,
        task_id: str,
        name: str,
        duration_min: int,
        release_time: datetime,
        due_date: datetime,
        priority: int = 1,
        required_type: str = "ANY",
        predecessors: Optional[List[str]] = None,
        setup_group: str = "DEFAULT",
    ):
        self.id = task_id
        self.name = name
        self.duration_min = int(duration_min)
        self.release_time = release_time
        self.due_date = due_date
        self.priority = int(priority)
        self.required_type = required_type or "ANY"
        self.predecessors = predecessors[:] if predecessors else []
        self.setup_group = setup_group or "DEFAULT"

class Resource:
    """
    Resource = nhân sự / máy.
    """
    def __init__(self, resource_id: str, name: str, rtype: str = "ANY", capacity: int = 1):
        self.id = resource_id
        self.name = name
        self.rtype = rtype or "ANY"
        self.capacity = int(capacity)

class Assignment:
    """
    Quyết định phân công:
    task -> resource -> start/end
    """
    def __init__(self, task_id: str, resource_id: str, start: datetime, end: datetime):
        self.task_id = task_id
        self.resource_id = resource_id
        self.start = start
        self.end = end

class Schedule:
    """
    Lịch phân công tổng thể.
    """
    def __init__(self):
        self.by_task: Dict[str, Assignment] = {}

    def add(self, assignment: Assignment) -> None:
        self.by_task[assignment.task_id] = assignment

    def get(self, task_id: str) -> Optional[Assignment]:
        return self.by_task.get(task_id)

    def all_assignments(self) -> List[Assignment]:
        return list(self.by_task.values())

    def by_resource(self) -> Dict[str, List[Assignment]]:
        grouped: Dict[str, List[Assignment]] = {}
        for a in self.by_task.values():
            grouped.setdefault(a.resource_id, []).append(a)
        for rid in grouped:
            grouped[rid].sort(key=lambda x: x.start)
        return grouped

    def clone_shallow(self) -> "Schedule":
        s = Schedule()
        s.by_task = dict(self.by_task)
        return s

class Result:
    """
    Kết quả thuật toán:
    - schedule: lịch tốt nhất
    - cost: điểm KPI
    - feasible: có vi phạm HARD không
    - violations: danh sách vi phạm để debug
    - history: hội tụ theo vòng lặp
    """
    def __init__(
        self,
        schedule: Schedule,
        cost: float,
        feasible: bool,
        violations: Optional[List[str]] = None,
        history: Optional[List[float]] = None,
        runtime_sec: float = 0.0,
        algorithm: str = "",
    ):
        self.schedule = schedule
        self.cost = float(cost)
        self.feasible = bool(feasible)
        self.violations = violations[:] if violations else []
        self.history = history[:] if history else []
        self.runtime_sec = float(runtime_sec)
        self.algorithm = algorithm
