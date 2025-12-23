from typing import Dict, List
from Model.models import Result, Task, Resource
from Core.feasibility import check_feasible

def summarize(result: Result, tasks: Dict[str, Task], resources: Dict[str, Resource]) -> str:
    feasible, violations = check_feasible(result.schedule, tasks, resources)
    lines: List[str] = []
    lines.append(f"Algorithm: {result.algorithm}")
    lines.append(f"Cost: {result.cost:.2f}")
    lines.append(f"Feasible: {feasible}")
    lines.append(f"Runtime: {result.runtime_sec:.2f}s")
    if violations:
        lines.append("Violations:")
        for v in violations[:30]:
            lines.append(f"  - {v}")
        if len(violations) > 30:
            lines.append(f"  ... ({len(violations)-30} more)")
    return "\n".join(lines)
