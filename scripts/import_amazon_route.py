from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from route_optimizer.amazon_data import extract_route, load_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one route from the Amazon Last Mile Routing Research Challenge data")
    parser.add_argument("--route-data", required=True)
    parser.add_argument("--package-data", required=True)
    parser.add_argument("--travel-times", required=True)
    parser.add_argument("--route-id", required=True)
    parser.add_argument("--output", default="data/processed/route.json")
    args = parser.parse_args()

    route_data = load_json(args.route_data)
    package_data = load_json(args.package_data)
    travel_times = load_json(args.travel_times)
    depot, stops, vehicles, matrix = extract_route(args.route_id, route_data, package_data, travel_times)
    payload = {
        "route_id": args.route_id,
        "source": "Amazon Last Mile Routing Research Challenge",
        "depot": asdict(depot),
        "stops": [asdict(stop) for stop in stops],
        "vehicles": [asdict(vehicle) for vehicle in vehicles],
        "travel_times_seconds": matrix,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
