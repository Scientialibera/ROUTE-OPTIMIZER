from __future__ import annotations

from dataclasses import asdict

from route_optimizer.models import FleetPlan, Stop


def fleet_to_dict(plan: FleetPlan, stops: dict[str, Stop], depot: Stop) -> dict:
    payload = asdict(plan)
    for route in payload["routes"]:
        route["utilization_percent"] = round(100 * route["capacity_used"] / route["max_capacity"], 1) if route["max_capacity"] else 0
        route["geometry"] = [
            {"lat": depot.lat, "lng": depot.lng, "stop_id": depot.stop_id},
            *[
                {"lat": stops[stop_id].lat, "lng": stops[stop_id].lng, "stop_id": stop_id}
                for stop_id in route["stop_ids"]
            ],
            {"lat": depot.lat, "lng": depot.lng, "stop_id": depot.stop_id},
        ]
    return payload
