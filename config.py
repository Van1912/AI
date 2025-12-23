from dataclasses import dataclass, field

@dataclass
class SAParams:
    t0: float = 200.0
    t_min: float = 0.5
    alpha: float = 0.95
    iters_per_temp: int = 200

@dataclass
class GWOParams:
    wolves: int = 25
    iters: int = 150

@dataclass
class Weights:
    w_tardiness: float = 5.0
    w_makespan: float = 1.0
    w_earliness: float = 0.0  # nếu thầy không yêu cầu, để 0 cho dễ

@dataclass
class AppConfig:
    sa: SAParams = field(default_factory=SAParams)
    gwo: GWOParams = field(default_factory=GWOParams)
    weights: Weights = field(default_factory=Weights)
    random_seed: int = 42
    results_dir: str = "Output/results"
