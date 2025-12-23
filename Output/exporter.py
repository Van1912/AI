# Output/exporter.py
import os
import csv
from typing import List, Dict
from Model.models import Result, Task, Resource

def export_schedule_csv(result: Result, tasks: Dict[str, Task], resources: Dict[str, Resource], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    rows: List[Dict] = []
    for a in result.schedule.all_assignments():
        t = tasks[a.task_id]
        r = resources[a.resource_id]
        rows.append({
            "task_id": t.id,
            "task_name": t.name,
            "resource_id": r.id,
            "resource_name": r.name,
            "start": a.start.strftime("%Y-%m-%d %H:%M"),
            "end": a.end.strftime("%Y-%m-%d %H:%M"),
            "due": t.due_date.strftime("%Y-%m-%d %H:%M"),
            "priority": t.priority,
            "required_type": t.required_type,
        })

    rows.sort(key=lambda x: (x["resource_id"], x["start"]))

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
import matplotlib.pyplot as plt
from datetime import datetime

def export_gantt_chart(result: Result, out_path: str, title: str = "Gantt Chart"):
    """
    Vẽ Gantt chart từ Result.schedule
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    assignments = result.schedule.all_assignments()
    if not assignments:
        return

    resources = sorted(set(a.resource_id for a in assignments))
    y_pos = {r: i for i, r in enumerate(resources)}

    fig, ax = plt.subplots(figsize=(12, 6))

    for a in assignments:
        start = a.start
        end = a.end
        y = y_pos[a.resource_id]

        duration = (end - start).total_seconds() / 60

        ax.barh(
            y=y,
            width=duration,
            left=start,
            height=0.4,
            align="center",
        )

        ax.text(
            start,
            y,
            a.task_id,
            va="center",
            ha="left",
            fontsize=8,
        )
    ax.set_yticks(list(y_pos.values()))
    ax.set_yticklabels(resources)
    ax.set_xlabel("Time")
    ax.set_ylabel("Resource")
    ax.set_title(title)

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
