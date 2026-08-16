# Research basis

## Problem formulation

The product models last-mile planning as a constrained vehicle-routing problem. The zero-setup solver supports fleet capacity, delivery service time, customer time windows, driver shifts, overtime penalties, route balancing and optional driver-preference priors.

For production-scale deployments, this domain model can be mapped directly to a VRP/VRPTW solver such as Google OR-Tools. OR-Tools represents accumulated quantities such as time and capacity with routing dimensions and supports time-window constraints, vehicle capacities, dropped visits and search limits.

## Amazon Last Mile Routing Research Challenge

Amazon and the MIT Center for Transportation and Logistics released 9,184 historical routes from 2018 across Seattle, Los Angeles, Austin, Chicago and Boston. The dataset contains route, stop and package features and anonymized geographic information. Training data contains 6,112 routes and evaluation data contains 3,072 routes.

The dataset includes:

- depot/station and stop coordinates;
- actual historical stop sequence;
- average point-to-point travel times;
- delivery time windows;
- planned service times;
- package dimensions;
- vehicle volume capacity;
- zone identifiers;
- route-quality labels.

The dataset is licensed CC BY-NC 4.0. It is not bundled in this repository. The application code is MIT licensed.

## Driver knowledge

The Amazon challenge demonstrated that minimizing route length alone misses operational preferences. Strong challenge solutions learned zone-level transition behavior from historical driver sequences and then optimized stop order within or between zones. The repository implements a small, explainable first-order zone transition model that can be learned from `route_data.json` and `actual_sequences.json` and used as a soft penalty in the routing objective.

This is intentionally simpler than the strongest published challenge methods. It provides a transparent research hook while keeping the POC runnable without a large ML stack.

## Solver design

The built-in solver uses:

1. urgency ordering by time-window end, stop priority and demand;
2. best feasible insertion across vehicles;
3. capacity and shift feasibility evaluation;
4. waiting and lateness calculations for time windows;
5. route-level cost including distance, labor, lateness and overtime;
6. 2-opt style sequence improvement;
7. cross-route relocation moves;
8. optional learned zone transition penalties.

The heuristic is suitable for interactive demonstrations and moderate instances. It does not claim global optimality.

## References

- Merchán et al. (2022), *2021 Amazon Last Mile Routing Research Challenge: Data Set*, Transportation Science.
- Wu et al. (2022), *Learning from Drivers to Tackle the Amazon Last Mile Routing Research Challenge*.
- Cook, Held and Helsgaun (2021), *Constrained Local Search for Last-Mile Routing*.
- Google OR-Tools documentation for VRP and VRPTW formulations.
