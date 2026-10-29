# Aral Price Monitor v0.5.4

V0.5.4 fixes the Spritmonitor write request and expands the manual refuel form.

## Fixes
- Uses the documented **GET fueling endpoint with query parameters**, not POST JSON.
- Sends the documented required parameter `fuelsortid`.
- Shows sync status, external ID, last sync and sync error per fueling.
- A failed fueling can be edited and retried without recreating it.

## Full form
Date, odometer, trip, liters, price, tank type, fuel sort, tires, route code, driving style, station, country, region, location, coordinates, note and BC values.

## Safety
Only new local manual fuelings are sent. Existing remote entries are not changed or deleted.

```bash
git add .
git commit -m "fix: correct Spritmonitor fueling request and complete refuel form"
git push origin main
git tag v0.5.4
git push origin v0.5.4
```
