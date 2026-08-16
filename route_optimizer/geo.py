from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = p2 - p1
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def road_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Fast road-distance proxy used when a road matrix is unavailable.

    The multiplier approximates urban road circuity. Imported Amazon challenge
    routes should use the provided asymmetric travel-time matrix when available.
    """
    return haversine_km(lat1, lng1, lat2, lng2) * 1.23


def travel_minutes(distance_km: float, speed_kph: float = 27.0, traffic_multiplier: float = 1.0) -> float:
    return (distance_km / max(speed_kph, 1.0)) * 60.0 * max(traffic_multiplier, 0.25)
