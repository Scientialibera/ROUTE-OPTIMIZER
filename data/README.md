# Data directory

The Amazon Last Mile Routing Research Challenge data is intentionally not committed here. The public dataset is approximately 3.1 GB and is licensed under CC BY-NC 4.0.

Download it directly from the official AWS Open Data bucket:

```bash
aws s3 sync --no-sign-request s3://amazon-last-mile-challenges/almrrc2021/ data/amazon/
```

The official challenge structure includes `route_data.json`, `package_data.json`, `travel_times.json` and `actual_sequences.json` in the training inputs.

Use `scripts/import_amazon_route.py` to convert a route into the application's normalized format and `scripts/train_zone_preferences.py` to learn historical zone-transition priors.
