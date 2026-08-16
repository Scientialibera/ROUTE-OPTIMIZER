from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ZonePreferenceModel:
    probabilities: dict[str, dict[str, float]]

    def transition_penalty(self, from_zone: str, to_zone: str) -> float:
        if from_zone == to_zone:
            return 0.0
        p = self.probabilities.get(from_zone, {}).get(to_zone, 0.0)
        if p <= 0:
            return 1.0
        return max(0.0, 1.0 - p)

    def to_dict(self) -> dict:
        return {"probabilities": self.probabilities}

    @classmethod
    def from_dict(cls, payload: dict) -> "ZonePreferenceModel":
        return cls(probabilities=payload.get("probabilities", {}))

    @classmethod
    def load(cls, path: str | Path) -> "ZonePreferenceModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(cls, path: str | Path) -> None:
        Path(path).write_text(json.dumps(cls.to_dict(), indent=2), encoding="utf-8")


def learn_zone_transitions(route_data: dict, actual_sequences: dict) -> ZonePreferenceModel:
    """Learn first-order zone transition probabilities from Amazon route history."""
    counts: dict[str, Counter[str]] = defaultdict(Counter)

    for route_id, sequence_payload in actual_sequences.items():
        route = route_data.get(route_id)
        if not route:
            continue
        stop_map = route.get("stops", {})
        actual = sequence_payload.get("actual", {})
        ordered = sorted(actual.items(), key=lambda item: item[1])
        zones: list[str] = []
        for stop_id, _ in ordered:
            zone = (stop_map.get(stop_id) or {}).get("zone_id")
            if zone and (not zones or zones[-1] != zone):
                zones.append(zone)
        for current, nxt in zip(zones, zones[1:]):
            counts[current][nxt] += 1

    probabilities: dict[str, dict[str, float]] = {}
    for current, counter in counts.items():
        total = sum(counter.values())
        probabilities[current] = {nxt: value / total for nxt, value in counter.items()}
    return ZonePreferenceModel(probabilities=probabilities)
