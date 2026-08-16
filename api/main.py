from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.schemas import OptimizeResponse, ScenarioRequest
from api.serialization import fleet_to_dict
from route_optimizer.demo import baseline_sequence, build_demo
from route_optimizer.geo import road_distance_km
from route_optimizer.models import Stop, Vehicle
from route_optimizer.optimizer import OptimizerConfig, RouteOptimizer
from route_optimizer.scenario import apply_demand_spike, remove_vehicle

APP_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = APP_ROOT / "frontend"

app = FastAPI(title="Route Optimizer", version="0.1.0")
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


def _baseline_plan(depot, stops, vehicles, config):
    optimizer = RouteOptimizer(depot, stops, vehicles, config=config)
    stop_map = {s.stop_id: s for s in stops}
    routes = baseline_sequence(stops, [vehicle.vehicle_id for vehicle in vehicles])
    plans = []
    for vehicle in vehicles:
        plan = optimizer._evaluate(vehicle, routes[vehicle.vehicle_id])
        if plan:
            plans.append(plan)
    return optimizer._fleet_summary(plans, []), stop_map


def _merge_fleets(fleets: list[dict], source: str) -> dict:
    routes = [route for fleet in fleets for route in fleet["routes"]]
    total_stops = sum(len(route["stop_ids"]) for route in routes)
    late_stops = sum(sum(stop["late_minutes"] > 0 for stop in route["route_stops"]) for route in routes)
    capacity = sum(route["max_capacity"] for route in routes)
    used = sum(route["capacity_used"] for route in routes)
    return {
        "routes": routes,
        "unassigned_stop_ids": [stop_id for fleet in fleets for stop_id in fleet["unassigned_stop_ids"]],
        "objective_score": sum(fleet["objective_score"] for fleet in fleets),
        "total_distance_km": sum(fleet["total_distance_km"] for fleet in fleets),
        "total_driver_hours": sum(fleet["total_driver_hours"] for fleet in fleets),
        "late_stops": late_stops,
        "late_minutes": sum(fleet["late_minutes"] for fleet in fleets),
        "vehicles_used": len(routes),
        "average_utilization": used / capacity if capacity else 0,
        "estimated_cost": sum(fleet["estimated_cost"] for fleet in fleets),
        "on_time_rate": 100 * (total_stops - late_stops) / total_stops if total_stops else 100,
        "source": source,
    }


def _optimize_custom(request: ScenarioRequest, config: OptimizerConfig) -> tuple[dict, dict]:
    depots = [
        Stop(f"DEPOT-{index + 1:02d}", point.lat, point.lng, 0, 0, f"DEPOT-{index + 1:02d}", stop_type="station")
        for index, point in enumerate(request.start_points)
    ]
    stops = [
        Stop(f"CUSTOM-{index + 1:03d}", point.lat, point.lng, 1, 8, "CUSTOM")
        for index, point in enumerate(request.delivery_locations)
    ]
    groups: list[list[Stop]] = [[] for _ in depots]
    remaining = list(stops)
    # Seed every origin with a delivery when possible so each clicked start
    # produces a visible route, then allocate the remainder by proximity.
    for index, depot in enumerate(depots):
        if not remaining:
            break
        closest = min(remaining, key=lambda stop: road_distance_km(depot.lat, depot.lng, stop.lat, stop.lng))
        groups[index].append(closest)
        remaining.remove(closest)
    for stop in remaining:
        nearest = min(range(len(depots)), key=lambda index: road_distance_km(depots[index].lat, depots[index].lng, stop.lat, stop.lng))
        groups[nearest].append(stop)

    baseline_payloads = []
    optimized_payloads = []
    for index, (depot, assigned) in enumerate(zip(depots, groups)):
        vehicle = Vehicle(f"V-{index + 1:02d}", capacity_units=max(1, len(assigned) + 5))
        baseline_plan, stop_map = _baseline_plan(depot, assigned, [vehicle], config)
        optimized_plan = RouteOptimizer(depot, assigned, [vehicle], config=config).optimize()
        baseline_payloads.append(fleet_to_dict(baseline_plan, stop_map, depot))
        optimized_payloads.append(fleet_to_dict(optimized_plan, stop_map, depot))
    return _merge_fleets(baseline_payloads, "custom_map"), _merge_fleets(optimized_payloads, "custom_map")


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "solver": "constraint-aware local search", "dataset": "built_in_demo"}


@app.get("/api/demo")
def demo():
    depot, stops, vehicles = build_demo()
    return {
        "depot": asdict(depot),
        "stops": [asdict(s) for s in stops],
        "vehicles": [asdict(v) for v in vehicles],
        "dataset": {
            "mode": "built_in_demo",
            "label": "Deterministic built-in demo",
            "real_data_available": True,
            "amazon_dataset_adapter": True,
        },
    }


@app.post("/api/optimize", response_model=OptimizeResponse)
def optimize(request: ScenarioRequest):
    config = OptimizerConfig(
        traffic_multiplier=request.traffic_multiplier,
        average_speed_kph=request.average_speed_kph,
        preference_weight=request.preference_weight,
    )

    if request.start_points or request.delivery_locations:
        if not request.start_points or not request.delivery_locations:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Custom planning requires at least one start point and one delivery location.")
        baseline, optimized = _optimize_custom(request, config)
        return OptimizeResponse(
            baseline=baseline,
            optimized=optimized,
            scenario=request.model_dump(),
            dataset={"mode": "custom_map", "label": "Custom map scenario", "start_points": len(request.start_points), "delivery_locations": len(request.delivery_locations)},
        )

    depot, stops, vehicles = build_demo()
    stops = apply_demand_spike(stops, request.demand_spike_percent)
    vehicles = remove_vehicle(vehicles, request.unavailable_vehicle_id)

    baseline, stop_map = _baseline_plan(depot, stops, vehicles, config)
    optimized = RouteOptimizer(depot, stops, vehicles, config=config).optimize()
    optimized.source = "built_in_demo"

    return OptimizeResponse(
        baseline=fleet_to_dict(baseline, stop_map, depot),
        optimized=fleet_to_dict(optimized, stop_map, depot),
        scenario=request.model_dump(),
        dataset={
            "mode": "built_in_demo",
            "label": "Deterministic built-in demo",
            "amazon_dataset": "Supported through scripts/import_amazon_route.py",
            "license_note": "Amazon challenge data is CC BY-NC 4.0 and is not bundled in this repository.",
        },
    )
