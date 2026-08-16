from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import Stop, TimeWindow, Vehicle


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _minute_offset(timestamp: str | None, departure_date: str, departure_time: str) -> int | None:
    if not timestamp or str(timestamp).lower() == "nan":
        return None
    start = datetime.fromisoformat(f"{departure_date} {departure_time}")
    event = datetime.fromisoformat(timestamp)
    return max(0, round((event - start).total_seconds() / 60.0))


def extract_route(
    route_id: str,
    route_data: dict,
    package_data: dict,
    travel_times: dict | None = None,
) -> tuple[Stop, list[Stop], list[Vehicle], dict[str, dict[str, float]]]:
    """Convert one Amazon challenge route to the app domain model."""
    route = route_data[route_id]
    packages_by_stop = package_data.get(route_id, {})
    date = route["date_YYYY_MM_DD"]
    departure = route["departure_time_utc"]
    depot = None
    stops: list[Stop] = []

    for stop_id, raw in route["stops"].items():
        if raw.get("type") == "Station":
            depot = Stop(
                stop_id=stop_id,
                lat=float(raw["lat"]),
                lng=float(raw["lng"]),
                demand_units=0,
                service_minutes=0,
                zone_id="STATION",
                stop_type="station",
            )
            continue

        packages = list((packages_by_stop.get(stop_id) or {}).values())
        volume = 0.0
        service_seconds = 0.0
        starts: list[int] = []
        ends: list[int] = []
        for package in packages:
            dims = package.get("dimensions") or {}
            volume += float(dims.get("depth_cm") or 0) * float(dims.get("height_cm") or 0) * float(dims.get("width_cm") or 0)
            service_seconds = max(service_seconds, float(package.get("planned_service_time_seconds") or 0))
            window = package.get("time_window") or {}
            start = _minute_offset(window.get("start_time_utc"), date, departure)
            end = _minute_offset(window.get("end_time_utc"), date, departure)
            if start is not None and end is not None:
                starts.append(start)
                ends.append(end)
        time_window = TimeWindow(max(starts), min(ends)) if starts and ends and max(starts) <= min(ends) else None
        stops.append(
            Stop(
                stop_id=stop_id,
                lat=float(raw["lat"]),
                lng=float(raw["lng"]),
                demand_units=max(volume, 1.0),
                service_minutes=max(service_seconds / 60.0, 0.5),
                zone_id=raw.get("zone_id") or "UNZONED",
                time_window=time_window,
                priority=2 if time_window else 1,
            )
        )

    if depot is None:
        raise ValueError(f"Route {route_id} has no Station stop")

    capacity = float(route.get("executor_capacity_cm3") or 1.0)
    vehicle = Vehicle(vehicle_id="AMZ-01", capacity_units=capacity, shift_end_minute=720)
    matrix = (travel_times or {}).get(route_id, {})
    return depot, stops, [vehicle], matrix
