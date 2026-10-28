# Aral Price Monitor v0.3.0

V0.3 turns the collector into a refuelling decision assistant. Existing V0.2 SQLite databases are migrated automatically. Keep the same `/data` volume.

## New in V0.3

- Analysis page with recommendation per fuel
- Expected remaining daily low from the 15-minute historical median
- Remaining saving in ct/L and EUR per tank
- Data maturity/confidence indicator
- Typical low-price window
- Automatic seasonal vehicle selection
- Economic station calculation using vehicle consumption and configurable extra round-trip km
- Extra-round-trip field in station editor
- MQTT Discovery sensors for refuel recommendation and best current price
- Existing V0.2 charts, exact `last_price_update` history and CRUD remain intact

## Important

The Aral API exposes current prices and the latest change time, not historical backfill. Recommendations therefore begin in `Daten sammeln` mode until at least seven days have been observed. 30 days gives the full configured analysis window.

If vehicle tank capacity is empty, analysis temporarily assumes a 50 L fill. Add the real tank capacity in the Vehicles page for EUR savings estimates.

`extra_distance_km` means additional round-trip distance compared with the normal route. Set 0 when a station is already on the route.

## Update from V0.2

1. Push all files to the existing GitHub repository.
2. Wait for GHCR `latest` to build.
3. In Portainer pull latest image and update the existing stack.
4. Do not delete `/volume1/docker/aral-price-monitor/data`.
5. Open `/analysis` after deployment.

## Release

```bash
git add .
git commit -m "feat: add refuel intelligence and economic station analysis"
git push origin main
git tag v0.3.0
git push origin v0.3.0
```
