from route_optimizer.demo import build_demo
from route_optimizer.optimizer import OptimizerConfig, RouteOptimizer


def test_optimizer_assigns_all_demo_stops():
    depot, stops, vehicles = build_demo()
    plan = RouteOptimizer(depot, stops, vehicles).optimize()
    assert not plan.unassigned_stop_ids
    assert sum(len(r.stop_ids) for r in plan.routes) == len(stops)
    assert plan.vehicles_used <= len(vehicles)


def test_route_capacity_is_respected():
    depot, stops, vehicles = build_demo()
    plan = RouteOptimizer(depot, stops, vehicles).optimize()
    assert all(r.capacity_used <= r.max_capacity + 1e-9 for r in plan.routes)


def test_traffic_multiplier_increases_driver_time():
    depot, stops, vehicles = build_demo()
    normal = RouteOptimizer(depot, stops, vehicles, OptimizerConfig(traffic_multiplier=1.0)).optimize()
    heavy = RouteOptimizer(depot, stops, vehicles, OptimizerConfig(traffic_multiplier=1.5)).optimize()
    assert heavy.total_driver_hours > normal.total_driver_hours
