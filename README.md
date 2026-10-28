# Aral Price Monitor v0.4.1

V0.4.1 makes the tank log independent from live price providers and adds a lossless Spritmonitor fueling CSV import.

## Included

- Fixed duplicate navigation entries.
- Full import of the real Spritmonitor fueling export schema.
- RS3, S3, Golf GTI and arbitrary additional vehicles can be imported independently.
- Exact Spritmonitor fields: date, odometer, trip distance, quantity, total cost, currency, tank type 0–3, tires, route bit mask, driving style, fuel code, notes, consumption, BC values, brand, country, region, location and coordinates.
- Liter price calculated from total cost / fuel quantity.
- Preview and deterministic duplicate detection.
- Generic provider model: Aral, Tankerkönig and no provider.
- Vehicle editor supports Aral Ultimate 102, Aral SuperPlus, Tankerkönig E10 or no monitoring.
- Tankerkönig is modeled but its live collector remains planned for V0.5.
- Existing V0.4 database, price history and manual refuels are migrated in place.

## Upgrade

Keep the existing `/data` volume. Push this project to GitHub, wait for GHCR, and redeploy `latest` in Portainer.

```bash
git add .
git commit -m "feat: add full Spritmonitor import and provider-independent vehicles"
git push origin main
git tag v0.4.1
git push origin v0.4.1
```
