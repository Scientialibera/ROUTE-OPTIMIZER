from __future__ import annotations

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    traffic_multiplier: float = Field(default=1.0, ge=0.5, le=3.0)
    demand_spike_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    unavailable_vehicle_id: str | None = None
    average_speed_kph: float = Field(default=27.0, ge=8.0, le=80.0)
    preference_weight: float = Field(default=0.0, ge=0.0, le=50.0)


class OptimizeResponse(BaseModel):
    baseline: dict
    optimized: dict
    scenario: dict
    dataset: dict
