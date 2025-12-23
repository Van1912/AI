# Data/data_controller.py
import csv
import json
from datetime import datetime
from typing import List, Tuple, Optional

try:
    import pandas as pd
except Exception:
    pd = None

from Model.models import Task, Resource
from Data.schemas import TASK_COLUMNS, RESOURCE_COLUMNS

_DT_FMT = "%Y-%m-%d %H:%M"

def _parse_dt(x: str) -> datetime:
    # cho phép "2025-12-14 08:00"
    return datetime.strptime(x.strip(), _DT_FMT)

def _parse_preds(x: str) -> List[str]:
    x = (x or "").strip()
    if not x:
        return []
    # "T1|T2|T3"
    return [p.strip() for p in x.split("|") if p.strip()]

def load_tasks_csv(path: str) -> List[Task]:
    tasks: List[Task] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(Task(
                task_id=row[TASK_COLUMNS["id"]],
                name=row.get(TASK_COLUMNS["name"], ""),
                duration_min=int(row[TASK_COLUMNS["duration_min"]]),
                release_time=_parse_dt(row[TASK_COLUMNS["release_time"]]),
                due_date=_parse_dt(row[TASK_COLUMNS["due_date"]]),
                priority=int(row.get(TASK_COLUMNS["priority"], 1)),
                required_type=row.get(TASK_COLUMNS["required_type"], "ANY") or "ANY",
                predecessors=_parse_preds(row.get(TASK_COLUMNS["predecessors"], "")),
            ))
    return tasks

def load_resources_csv(path: str) -> List[Resource]:
    resources: List[Resource] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resources.append(Resource(
                resource_id=row[RESOURCE_COLUMNS["id"]],
                name=row.get(RESOURCE_COLUMNS["name"], ""),
                rtype=row.get(RESOURCE_COLUMNS["rtype"], "ANY") or "ANY",
                capacity=int(row.get(RESOURCE_COLUMNS["capacity"], 1)),
            ))
    return resources

def load_from_json(path: str) -> Tuple[List[Task], List[Resource]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tasks: List[Task] = []
    for row in data.get("tasks", []):
        tasks.append(Task(
            task_id=row["id"],
            name=row.get("name", ""),
            duration_min=int(row["duration_min"]),
            release_time=_parse_dt(row["release_time"]),
            due_date=_parse_dt(row["due_date"]),
            priority=int(row.get("priority", 1)),
            required_type=row.get("required_type", "ANY"),
            predecessors=_parse_preds(row.get("predecessors", "")),
        ))

    resources: List[Resource] = []
    for row in data.get("resources", []):
        resources.append(Resource(
            resource_id=row["id"],
            name=row.get("name", ""),
            rtype=row.get("rtype", "ANY"),
            capacity=int(row.get("capacity", 1)),
        ))

    return tasks, resources

def load_excel(tasks_xlsx: str, resources_xlsx: str) -> Tuple[List[Task], List[Resource]]:
    if pd is None:
        raise RuntimeError("pandas not installed. Use CSV/JSON or install pandas+openpyxl.")
    tdf = pd.read_excel(tasks_xlsx)
    rdf = pd.read_excel(resources_xlsx)

    tasks: List[Task] = []
    for _, row in tdf.iterrows():
        tasks.append(Task(
            task_id=str(row["id"]),
            name=str(row.get("name", "")),
            duration_min=int(row["duration_min"]),
            release_time=_parse_dt(str(row["release_time"])),
            due_date=_parse_dt(str(row["due_date"])),
            priority=int(row.get("priority", 1)),
            required_type=str(row.get("required_type", "ANY")),
            predecessors=_parse_preds(str(row.get("predecessors", ""))),
        ))

    resources: List[Resource] = []
    for _, row in rdf.iterrows():
        resources.append(Resource(
            resource_id=str(row["id"]),
            name=str(row.get("name", "")),
            rtype=str(row.get("rtype", "ANY")),
            capacity=int(row.get("capacity", 1)),
        ))

    return tasks, resources
