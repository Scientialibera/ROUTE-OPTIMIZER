# Route Optimizer

Route Optimizer is a last-mile fleet planning and disruption-recovery application. It combines a constraint-aware vehicle-routing heuristic with a map-based operations console and adapters for the 2021 Amazon Last Mile Routing Research Challenge data.

The product is designed around operational decisions: how many routes are required, which stops belong on each route, whether delivery windows remain feasible, what a disruption does to the plan and what the revised network costs.

## Product surface

The application has three operating modes.

**Dispatch Board** compares a current plan with an optimized plan. The route engine considers vehicle capacity, customer time windows, service duration, route duration, overtime, route balance and operating cost. Every route can be inspected stop by stop.

**Disruption Recovery** reruns the network after changes such as a missing vehicle, higher traffic or a package-demand spike. The result is a complete reassignment and resequencing rather than a static risk score.

**Dataset Lab** documents the Amazon challenge adapter and the optional historical driver-preference model.

## Solver

The zero-setup solver is a dependency-light interactive heuristic:

1. prioritize stops by time-window urgency, priority and demand;
2. evaluate best feasible insertion across all available vehicles;
3. reject capacity-infeasible assignments;
4. calculate travel, waiting, service, lateness and overtime;
5. price each route using fixed vehicle cost, distance and driver time;
6. run 2-opt sequence improvements;
7. run cross-route relocation improvements;
8. optionally penalize historically unusual zone transitions.

It is intended for interactive planning and moderate instances. It does not claim global optimality. For large production networks, the domain model can be mapped to OR-Tools or a commercial routing solver.

## Real Amazon research data

Amazon and the MIT Center for Transportation and Logistics released 9,184 historical last-mile routes from 2018 across Seattle, Los Angeles, Austin, Chicago and Boston. The public dataset contains route-, stop- and package-level features including coordinates, package dimensions, delivery time windows, planned service time, vehicle capacity, zone identifiers, actual driver sequences and asymmetric stop-to-stop travel times.

The dataset is about 3.1 GB and is licensed CC BY-NC 4.0. It is therefore not copied into this MIT-licensed repository.

Download the official dataset directly from AWS Open Data:

```bash
aws s3 sync --no-sign-request s3://amazon-last-mile-challenges/almrrc2021/ data/amazon/
```

Normalize an official route:

```bash
python scripts/import_amazon_route.py \
  --route-data data/amazon/almrrc2021_data_training/model_build_inputs/route_data.json \
  --package-data data/amazon/almrrc2021_data_training/model_build_inputs/package_data.json \
  --travel-times data/amazon/almrrc2021_data_training/model_build_inputs/travel_times.json \
  --route-id ROUTE_ID
```

Learn zone transition preferences from historical driver sequences:

```bash
python scripts/train_zone_preferences.py \
  --route-data data/amazon/almrrc2021_data_training/model_build_inputs/route_data.json \
  --actual-sequences data/amazon/almrrc2021_data_training/model_build_inputs/actual_sequences.json
```

## Built-in demo

The UI starts with a deterministic Boston-like network containing 56 delivery stops and eight vehicles. This is deliberately labelled as built-in demo data. It exists so the full application can be evaluated without downloading 3.1 GB first.

Imported Amazon challenge data remains separate from the demo and retains its original research-data licensing requirements.

## Run locally

```bash
pip install -e ".[dev]"
uvicorn api.main:app --reload --port 8000
```

Open `http://localhost:8000`.

Run validation:

```bash
pytest -q
python scripts/check_no_emoji.py
```

## Research basis

The repository follows three ideas from the routing literature.

First, route planning is a constrained VRP/VRPTW rather than a nearest-neighbour map exercise. Google OR-Tools uses the same core constructs for travel time, vehicle capacities and delivery time windows.

Second, Amazon's challenge data shows why route quality cannot be reduced to geometric distance. High-quality driver sequences also reflect delivery windows, backtracking, loading structure, zones and tacit operational preferences.

Third, leading Amazon challenge approaches combine learned global or zone-level structure with conventional optimization or local search. `scripts/train_zone_preferences.py` implements a deliberately simple and explainable version of that idea by learning zone-to-zone transition probabilities from actual historical driver sequences.

See `docs/RESEARCH.md` for implementation details and references.

## Architecture

```text
Browser operations console
        |
        v
FastAPI
        |
        +-- scenario service
        +-- route optimizer
        |     +-- capacity constraints
        |     +-- time windows
        |     +-- local search
        |     +-- cost model
        |     +-- zone preference prior
        |
        +-- Amazon challenge adapter
              +-- route_data.json
              +-- package_data.json
              +-- travel_times.json
              +-- actual_sequences.json
```

There is no CI/CD configuration in this repository. Tests and quality checks are local commands only.

## Sources

- Amazon Science, 2021 Amazon Last Mile Routing Research Challenge data publication.
- AWS Registry of Open Data, Amazon Last Mile Routing Research Challenge dataset.
- Merchán et al., *2021 Amazon Last Mile Routing Research Challenge: Data Set*, Transportation Science.
- Wu et al., *Learning from Drivers to Tackle the Amazon Last Mile Routing Research Challenge*.
- Cook, Held and Helsgaun, *Constrained Local Search for Last-Mile Routing*.
- Google OR-Tools vehicle-routing and VRPTW documentation.
