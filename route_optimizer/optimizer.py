from __future__ import annotations

from dataclasses import dataclass
from math import inf

from .geo import road_distance_km, travel_minutes
from .models import FleetPlan, RoutePlan, RouteStop, Stop, Vehicle
from .preference import ZonePreferenceModel


@dataclass(frozen=True)
class OptimizerConfig:
    traffic_multiplier: float = 1.0
    average_speed_kph: float = 27.0
    lateness_penalty_per_minute: float = 3.0
    unassigned_penalty: float = 2500.0
    overtime_penalty_per_minute: float = 1.2
    preference_weight: float = 8.0
    route_balance_weight: float = 0.18
    max_local_search_passes: int = 4


class RouteOptimizer:
    """Constraint-aware constructive VRP heuristic with local improvement.

    The implementation is intentionally dependency-light for zero-setup demos.
    It supports vehicle capacity, service time, delivery time windows, overtime,
    route balance and an optional learned zone-transition prior. For larger or
    mission-critical workloads, the same domain model can be mapped to OR-Tools.
    """

    def __init__(
        self,
        depot: Stop,
        stops: list[Stop],
        vehicles: list[Vehicle],
        config: OptimizerConfig | None = None,
        travel_time_matrix_seconds: dict[str, dict[str, float]] | None = None,
        preference_model: ZonePreferenceModel | None = None,
        blocked_pairs: set[tuple[str, str]] | None = None,
    ) -> None:
        self.depot = depot
        self.stops = {s.stop_id: s for s in stops}
        self.vehicles = vehicles
        self.config = config or OptimizerConfig()
        self.matrix = travel_time_matrix_seconds or {}
        self.preference_model = preference_model
        self.blocked_pairs = blocked_pairs or set()

    def optimize(self) -> FleetPlan:
        routes: dict[str, list[str]] = {vehicle.vehicle_id: [] for vehicle in self.vehicles}
        unassigned: list[str] = []

        ordered_stops = sorted(
            self.stops.values(),
            key=lambda s: (
                0 if s.time_window else 1,
                s.time_window.end_minute if s.time_window else inf,
                -s.priority,
                -s.demand_units,
            ),
        )

        for stop in ordered_stops:
            best: tuple[float, str, int] | None = None
            for vehicle in self.vehicles:
                current = routes[vehicle.vehicle_id]
                for position in range(len(current) + 1):
                    candidate = current[:position] + [stop.stop_id] + current[position:]
                    plan = self._evaluate(vehicle, candidate)
                    if plan is None:
                        continue
                    score = self._route_objective(plan)
                    if best is None or score < best[0]:
                        best = (score, vehicle.vehicle_id, position)
            if best is None:
                unassigned.append(stop.stop_id)
            else:
                _, vehicle_id, position = best
                routes[vehicle_id].insert(position, stop.stop_id)

        routes = self._local_search(routes)
        plans = [self._evaluate(v, routes[v.vehicle_id]) for v in self.vehicles if routes[v.vehicle_id]]
        materialized = [p for p in plans if p is not None]
        return self._fleet_summary(materialized, unassigned)

    def _local_search(self, routes: dict[str, list[str]]) -> dict[str, list[str]]:
        routes = {k: list(v) for k, v in routes.items()}
        vehicle_map = {v.vehicle_id: v for v in self.vehicles}

        for _ in range(self.config.max_local_search_passes):
            changed = False

            for vehicle_id, sequence in list(routes.items()):
                if len(sequence) < 4:
                    continue
                vehicle = vehicle_map[vehicle_id]
                current_plan = self._evaluate(vehicle, sequence)
                if current_plan is None:
                    continue
                current_score = self._route_objective(current_plan)
                best_sequence = sequence
                best_score = current_score
                for i in range(len(sequence) - 2):
                    for j in range(i + 2, len(sequence)):
                        candidate = sequence[:i] + list(reversed(sequence[i:j])) + sequence[j:]
                        plan = self._evaluate(vehicle, candidate)
                        if plan is None:
                            continue
                        score = self._route_objective(plan)
                        if score + 1e-6 < best_score:
                            best_sequence = candidate
                            best_score = score
                if best_sequence is not sequence:
                    routes[vehicle_id] = best_sequence
                    changed = True

            vehicle_ids = list(routes)
            for from_id in vehicle_ids:
                for stop_id in list(routes[from_id]):
                    best_move = None
                    best_move_score = inf
                    for to_id in vehicle_ids:
                        if to_id == from_id:
                            continue
                        base_total = self._pair_score(vehicle_map, routes, from_id, to_id)
                        for pos in range(len(routes[to_id]) + 1):
                            from_candidate = [s for s in routes[from_id] if s != stop_id]
                            to_candidate = routes[to_id][:pos] + [stop_id] + routes[to_id][pos:]
                            fp = self._evaluate(vehicle_map[from_id], from_candidate) if from_candidate else None
                            tp = self._evaluate(vehicle_map[to_id], to_candidate)
                            if tp is None:
                                continue
                            candidate_score = (self._route_objective(fp) if fp else 0.0) + self._route_objective(tp)
                            if candidate_score + 1e-6 < base_total and candidate_score < best_move_score:
                                best_move_score = candidate_score
                                best_move = (to_id, pos)
                    if best_move:
                        to_id, pos = best_move
                        routes[from_id].remove(stop_id)
                        routes[to_id].insert(pos, stop_id)
                        changed = True
                        break
                if changed:
                    break
            if not changed:
                break
        return routes

    def _pair_score(self, vehicle_map, routes, first_id: str, second_id: str | None) -> float:
        total = 0.0
        ids = [first_id] + ([second_id] if second_id else [])
        for vehicle_id in ids:
            seq = routes[vehicle_id]
            if not seq:
                continue
            plan = self._evaluate(vehicle_map[vehicle_id], seq)
            if plan:
                total += self._route_objective(plan)
        return total

    def _travel_minutes(self, from_id: str, to_id: str) -> float:
        if (from_id, to_id) in self.blocked_pairs:
            return 1e6
        row = self.matrix.get(from_id)
        if row and to_id in row:
            return (float(row[to_id]) / 60.0) * self.config.traffic_multiplier
        a = self.depot if from_id == self.depot.stop_id else self.stops[from_id]
        b = self.depot if to_id == self.depot.stop_id else self.stops[to_id]
        km = road_distance_km(a.lat, a.lng, b.lat, b.lng)
        return travel_minutes(km, self.config.average_speed_kph, self.config.traffic_multiplier)

    def _travel_distance(self, from_id: str, to_id: str) -> float:
        a = self.depot if from_id == self.depot.stop_id else self.stops[from_id]
        b = self.depot if to_id == self.depot.stop_id else self.stops[to_id]
        return road_distance_km(a.lat, a.lng, b.lat, b.lng)

    def _evaluate(self, vehicle: Vehicle, sequence: list[str]) -> RoutePlan | None:
        load = sum(self.stops[stop_id].demand_units for stop_id in sequence)
        if load > vehicle.capacity_units + 1e-9:
            return None

        now = float(vehicle.shift_start_minute)
        distance = 0.0
        drive = 0.0
        service = 0.0
        waiting = 0.0
        total_late = 0.0
        route_stops: list[RouteStop] = []
        violations: list[str] = []
        previous = self.depot.stop_id
        remaining = load

        for stop_id in sequence:
            stop = self.stops[stop_id]
            leg_drive = self._travel_minutes(previous, stop_id)
            if leg_drive >= 1e5:
                return None
            leg_distance = self._travel_distance(previous, stop_id)
            now += leg_drive
            drive += leg_drive
            distance += leg_distance

            late = 0.0
            slack = None
            if stop.time_window:
                if now < stop.time_window.start_minute:
                    wait = stop.time_window.start_minute - now
                    waiting += wait
                    now += wait
                if now > stop.time_window.end_minute:
                    late = now - stop.time_window.end_minute
                    total_late += late
                    violations.append(f"{stop_id}: late {late:.0f} min")
                slack = stop.time_window.end_minute - now

            arrival = now
            now += stop.service_minutes
            service += stop.service_minutes
            remaining -= stop.demand_units
            route_stops.append(
                RouteStop(
                    stop_id=stop_id,
                    arrival_minute=arrival,
                    departure_minute=now,
                    load_after=max(0.0, remaining),
                    late_minutes=late,
                    slack_minutes=slack,
                )
            )
            previous = stop_id

        if sequence:
            leg_drive = self._travel_minutes(previous, self.depot.stop_id)
            if leg_drive >= 1e5:
                return None
            drive += leg_drive
            now += leg_drive
            distance += self._travel_distance(previous, self.depot.stop_id)

        overtime = max(0.0, now - vehicle.shift_end_minute)
        if overtime > 0:
            violations.append(f"overtime {overtime:.0f} min")

        hours = (drive + service + waiting) / 60.0
        cost = vehicle.fixed_cost + distance * vehicle.cost_per_km + hours * vehicle.cost_per_hour
        cost += overtime * self.config.overtime_penalty_per_minute
        cost += total_late * self.config.lateness_penalty_per_minute

        preference_penalty = 0.0
        if self.preference_model and len(sequence) > 1:
            for a, b in zip(sequence, sequence[1:]):
                preference_penalty += self.preference_model.transition_penalty(
                    self.stops[a].zone_id, self.stops[b].zone_id
                ) * self.config.preference_weight

        if preference_penalty:
            cost += preference_penalty

        return RoutePlan(
            vehicle_id=vehicle.vehicle_id,
            stop_ids=list(sequence),
            route_stops=route_stops,
            distance_km=distance,
            drive_minutes=drive,
            service_minutes=service,
            waiting_minutes=waiting,
            late_minutes=total_late,
            capacity_used=load,
            max_capacity=vehicle.capacity_units,
            overtime_minutes=overtime,
            cost=cost,
            violations=violations,
        )

    def _route_objective(self, plan: RoutePlan | None) -> float:
        if plan is None:
            return 0.0
        duration = plan.drive_minutes + plan.service_minutes + plan.waiting_minutes
        return plan.cost + duration * self.config.route_balance_weight

    def _fleet_summary(self, routes: list[RoutePlan], unassigned: list[str]) -> FleetPlan:
        total_distance = sum(r.distance_km for r in routes)
        driver_hours = sum(r.drive_minutes + r.service_minutes + r.waiting_minutes for r in routes) / 60.0
        late_stops = sum(1 for r in routes for s in r.route_stops if s.late_minutes > 0)
        late_minutes = sum(r.late_minutes for r in routes)
        utilization = [r.capacity_used / r.max_capacity for r in routes if r.max_capacity > 0]
        estimated_cost = sum(r.cost for r in routes)
        total_served = sum(len(r.stop_ids) for r in routes)
        on_time_rate = 100.0 if total_served == 0 else 100.0 * (total_served - late_stops) / total_served
        objective = estimated_cost + len(unassigned) * self.config.unassigned_penalty
        return FleetPlan(
            routes=routes,
            unassigned_stop_ids=unassigned,
            objective_score=objective,
            total_distance_km=total_distance,
            total_driver_hours=driver_hours,
            late_stops=late_stops,
            late_minutes=late_minutes,
            vehicles_used=len(routes),
            average_utilization=sum(utilization) / len(utilization) if utilization else 0.0,
            estimated_cost=estimated_cost,
            on_time_rate=on_time_rate,
        )
