from api.main import health, optimize
from api.schemas import ScenarioRequest


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
