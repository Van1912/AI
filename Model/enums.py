from enum import Enum

class Priority(Enum):
    LOW = 1
    MEDIUM = 3
    HIGH = 5

class ConstraintType(Enum):
    HARD = "HARD"
    SOFT = "SOFT"

class ObjectiveMode(Enum):
    MINIMIZE = "MINIMIZE"
