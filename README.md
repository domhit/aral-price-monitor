# Aral Price Monitor v0.4.3

V0.4.3 improves the refuel history and adds full edit/delete support.

## New

- Edit and delete manual or imported refuels.
- Card-based refuel history with vehicle, station brand, imported location, liters, price, total, odometer, trip distance, tank type, fuel name, driving style, route profile, consumption and source.
- Imported Spritmonitor station brand and full location are displayed even when no internal station is linked.
- Editing recalculates total cost and marks the entry as `modified`, preparing future API synchronization.
- Sync preparation fields: `external_updated_at`, `last_synced_at`, and `sync_status`.
- Existing V0.4 database and imported history are migrated in place.
- Import preview uses collision-safe Jinja dictionary access.
- Existing `Kosten` data remain available.

## Remove old manual duplicates

Open `Tankungen`, locate the two old entries with source `manual`, and click `Löschen`. Imported rows use source `spritmonitor_csv`.

## Upgrade

Keep the existing `/data` volume.

```bash
git add .
git commit -m "feat: add refuel history edit and delete"
git push origin main
git tag v0.4.3
git push origin v0.4.3
```
