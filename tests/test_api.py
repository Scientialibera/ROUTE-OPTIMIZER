from api.main import health, optimize
from api.schemas import MapPoint, ScenarioRequest


def test_health_contract():
    assert health()["status"] == "ok"


def test_optimize_contract():
    response = optimize(ScenarioRequest())
    assert response.dataset["mode"] == "built_in_demo"
    assert response.optimized["vehicles_used"] > 0
    assert response.optimized["total_distance_km"] > 0


def test_optimize_with_missing_vehicle_contract():
    response = optimize(ScenarioRequest(unavailable_vehicle_id="V-03", demand_spike_percent=20))
    route_ids = {route["vehicle_id"] for route in response.optimized["routes"]}
    assert "V-03" not in route_ids
    assert response.optimized["vehicles_used"] <= 7


def test_custom_map_uses_multiple_start_points():
    starts = [MapPoint(lat=42.36, lng=-71.10), MapPoint(lat=42.36, lng=-71.02)]
    deliveries = [
        MapPoint(lat=42.37, lng=-71.11),
        MapPoint(lat=42.35, lng=-71.09),
        MapPoint(lat=42.37, lng=-71.01),
        MapPoint(lat=42.35, lng=-71.03),
    ]
    response = optimize(ScenarioRequest(start_points=starts, delivery_locations=deliveries))
    routes = response.optimized["routes"]

    assert response.dataset["mode"] == "custom_map"
    assert len(routes) == 2
    assert sum(len(route["stop_ids"]) for route in routes) == 4
    for route in routes:
        assert route["geometry"][0] == route["geometry"][-1]
        assert route["geometry"][0]["stop_id"].startswith("DEPOT-")
