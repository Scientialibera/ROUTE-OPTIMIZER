from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.schemas import OptimizeResponse, ScenarioRequest
from api.serialization import fleet_to_dict
from route_optimizer.demo import baseline_sequence, build_demo
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
    depot, stops, vehicles = build_demo()
    stops = apply_demand_spike(stops, request.demand_spike_percent)
    vehicles = remove_vehicle(vehicles, request.unavailable_vehicle_id)
    config = OptimizerConfig(
        traffic_multiplier=request.traffic_multiplier,
        average_speed_kph=request.average_speed_kph,
        preference_weight=request.preference_weight,
    )

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
