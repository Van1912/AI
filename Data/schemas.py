# Data/schemas.py
TASK_COLUMNS = {
    "id": "id",
    "name": "name",
    "duration_min": "duration_min",
    "release_time": "release_time",
    "due_date": "due_date",
    "priority": "priority",
    "required_type": "required_type",
    "predecessors": "predecessors",  # "T1|T2|T3" hoặc rỗng
}

RESOURCE_COLUMNS = {
    "id": "id",
    "name": "name",
    "rtype": "rtype",
    "capacity": "capacity",
}
