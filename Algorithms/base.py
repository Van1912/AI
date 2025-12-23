# Algorithms/base.py
from abc import ABC, abstractmethod
from typing import List
from Model.models import Task, Resource, Result

class SchedulerBase(ABC):  # lớp trừu tượng 
    @abstractmethod   # ép các lớp con phải cài đặt hàm này 
    def solve(self, tasks: List[Task], resources: List[Resource]) -> Result:
        pass
