from __future__ import annotations

import math
import random

from .models import Stop, TimeWindow, Vehicle


def build_demo(seed: int = 19) -> tuple[Stop, list[Stop], list[Vehicle]]:
    """Deterministic Boston-like demo used for zero-setup product exploration."""
    rng = random.Random(seed)
    depot = Stop(
        stop_id="DEPOT",
        lat=42.3554,
        lng=-71.0605,
        demand_units=0,
        service_minutes=0,
        zone_id="STATION",
        stop_type="station",
    )

    centers = [
        (42.3662, -71.0621, "Z-01"),
        (42.3471, -71.0801, "Z-02"),
        (42.3370, -71.0490, "Z-03"),
        (42.3727, -71.1097, "Z-04"),
        (42.3190, -71.0638, "Z-05"),
        (42.3876, -71.0995, "Z-06"),
        (42.3560, -71.1280, "Z-07"),
    ]
    stops: list[Stop] = []
    stop_number = 1
    for zone_index, (lat0, lng0, zone) in enumerate(centers):
        for j in range(8):
            angle = 2 * math.pi * j / 8 + rng.uniform(-0.25, 0.25)
            radius = rng.uniform(0.003, 0.011)
            lat = lat0 + math.cos(angle) * radius
            lng = lng0 + math.sin(angle) * radius * 1.3
            demand = rng.uniform(4.0, 11.0)
            service = rng.uniform(3.0, 8.0)
            has_window = rng.random() < 0.42
            tw = None
            if has_window:
                start = rng.choice([60, 120, 180, 240, 300, 360])
                width = rng.choice([90, 120, 180])
                tw = TimeWindow(start, min(570, start + width))
            stops.append(
                Stop(
                    stop_id=f"S{stop_number:03d}",
                    lat=lat,
                    lng=lng,
                    demand_units=demand,
                    service_minutes=service,
                    zone_id=zone,
                    time_window=tw,
                    priority=2 if tw else 1,
                )
            )
            stop_number += 1

    vehicles = [
        Vehicle(vehicle_id=f"V-{i+1:02d}", capacity_units=92.0, shift_end_minute=600)
        for i in range(8)
    ]
    return depot, stops, vehicles


def baseline_sequence(stops: list[Stop], vehicle_ids: list[str]) -> dict[str, list[str]]:
    """Create a deliberately operational but non-optimized baseline by zone."""
    if not vehicle_ids:
        return {}
    grouped: dict[str, list[Stop]] = {}
    for stop in stops:
        grouped.setdefault(stop.zone_id, []).append(stop)
    ordered = []
    for zone in sorted(grouped):
        ordered.extend(sorted(grouped[zone], key=lambda s: s.stop_id))
    routes = {vehicle_id: [] for vehicle_id in vehicle_ids}
    for index, stop in enumerate(ordered):
        routes[vehicle_ids[index % len(vehicle_ids)]].append(stop.stop_id)
    return routes
