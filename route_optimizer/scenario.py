from __future__ import annotations

from dataclasses import replace

from .models import Stop, Vehicle


def apply_demand_spike(stops: list[Stop], percent: float) -> list[Stop]:
    factor = 1.0 + max(percent, 0.0) / 100.0
    return [replace(stop, demand_units=stop.demand_units * factor) for stop in stops]


def remove_vehicle(vehicles: list[Vehicle], vehicle_id: str | None) -> list[Vehicle]:
    if not vehicle_id:
        return list(vehicles)
    return [vehicle for vehicle in vehicles if vehicle.vehicle_id != vehicle_id]
