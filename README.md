# Aral Price Monitor v0.4.4

V0.4.4 adds per-vehicle dashboards based on the local refuel history.

## New
- Vehicle overview dashboard for all configured vehicles.
- Individual vehicle detail page.
- Long-term consumption.
- Number of refuels, total liters and fuel costs.
- Average fuel price.
- Recorded odometer range.
- Fuel cost per 100 km.
- Consumption history chart.
- Fuel price history chart.
- Fuel-code breakdown.
- Per-vehicle refuel history including station information.
- Direct Dashboard button in the vehicle administration page.

The dashboard prefers imported Spritmonitor consumption values where available. Existing price data, refuels, settings and SQLite history are migrated in place.

## Upgrade
Keep the existing `/data` volume.
```bash
git add .
git commit -m "feat: add per-vehicle fuel and consumption dashboards"
git push origin main
git tag v0.4.4
git push origin v0.4.4
```
