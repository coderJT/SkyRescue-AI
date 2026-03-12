from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class Settings:
    # World
    grid_size: float = 200.0
    sector_rows: int = 10
    sector_cols: int = 10
    base_x: float = 5.0
    base_z: float = 5.0

    # Hazards
    fire_multiplier: float = 3.0
    smoke_multiplier: float = 1.5

    # Drone/battery
    drain_per_unit: float = 0.05
    scan_cost: float = 0.5
    safety_margin: float = 3.0
    passive_survivor_radius: float = 18.0

    # Wind
    wind_speed_kmh: float = 35.0
    wind_angle_deg: float = 45.0
    wind_desc: str = "Wind blowing towards North-East (45°)"

    # Survivors
    survivor_min: int = 7
    survivor_max: int = 12


settings = Settings()


def to_dict() -> Dict[str, Any]:
    return asdict(settings)


def update(partial: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in partial.items():
        if hasattr(settings, k):
            setattr(settings, k, v)
    return to_dict()
