from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class TimeWindow:
    start_minute: int
    end_minute: int


@dataclass(frozen=True)
class Stop:
    stop_id: str
    lat: float
    lng: float
    demand_units: float
    service_minutes: float
    zone_id: str
    time_window: TimeWindow | None = None
    priority: int = 1
    stop_type: Literal["station", "dropoff"] = "dropoff"


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    capacity_units: float
    shift_start_minute: int = 0
    shift_end_minute: int = 600
    fixed_cost: float = 85.0
    cost_per_km: float = 0.68
    cost_per_hour: float = 31.0


@dataclass
class RouteStop:
    stop_id: str
    arrival_minute: float
    departure_minute: float
    load_after: float
    late_minutes: float
    slack_minutes: float | None


@dataclass
class RoutePlan:
    vehicle_id: str
    stop_ids: list[str]
    route_stops: list[RouteStop]
    distance_km: float
    drive_minutes: float
    service_minutes: float
    waiting_minutes: float
    late_minutes: float
    capacity_used: float
    max_capacity: float
    overtime_minutes: float
    cost: float
    violations: list[str] = field(default_factory=list)


@dataclass
class FleetPlan:
    routes: list[RoutePlan]
    unassigned_stop_ids: list[str]
    objective_score: float
    total_distance_km: float
    total_driver_hours: float
    late_stops: int
    late_minutes: float
    vehicles_used: int
    average_utilization: float
    estimated_cost: float
    on_time_rate: float
    source: str = "built_in_demo"
