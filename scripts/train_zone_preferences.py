from __future__ import annotations

import argparse
from pathlib import Path

from route_optimizer.amazon_data import load_json
from route_optimizer.preference import learn_zone_transitions


def main() -> None:
    parser = argparse.ArgumentParser(description="Learn zone transition priors from actual Amazon driver sequences")
    parser.add_argument("--route-data", required=True)
    parser.add_argument("--actual-sequences", required=True)
    parser.add_argument("--output", default="data/processed/zone_preferences.json")
    args = parser.parse_args()

    model = learn_zone_transitions(load_json(args.route_data), load_json(args.actual_sequences))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    model.save(output)
    print(output)


if __name__ == "__main__":
    main()
