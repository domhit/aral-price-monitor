# Aral Price Monitor v0.2.0

V0.2 adds step charts based on Aral `last_price_update`, today/yesterday comparison, a 30-day 15-minute median profile, and complete edit/delete workflows for stations and vehicles.

## Upgrade from V0.1

Keep the existing persistent `/data` mapping. The existing SQLite database is reused and upgraded non-destructively. Pull/redeploy `latest` in Portainer. No database reset is required.

## Features

- Exact price events, deduplicated by station, fuel and Aral change timestamp
- Today and yesterday step charts with carry-over at midnight
- 30-day median profile in 15-minute intervals
- Separate charts per configured fuel
- Data-quality indicator during the first 30 days
- Add, edit, pause and delete stations
- Add, edit and delete vehicles
- Deleting a station also deletes its price history after browser confirmation
- MQTT Discovery, no credentials required when anonymous broker access is enabled
- GitHub Actions builds amd64 and arm64 images for GHCR

## Deploy

1. Replace `DEIN_GITHUB_BENUTZER` in `docker-compose.yml`.
2. Set MQTT host. Leave `MQTT_USER` and `MQTT_PASSWORD` empty for anonymous access.
3. Push to GitHub main.
4. Wait for the GHCR build.
5. Redeploy the Portainer stack using the same `/data` volume.

Web UI: `http://NAS-IP:8095`

## Release commands

```bash
git add .
git commit -m "feat: add price charts and full configuration CRUD"
git push origin main
git tag v0.2.0
git push origin v0.2.0
```

## Notes about analytics

The API only exposes the current price and its latest change timestamp. The monitor therefore builds history from the moment it starts collecting. Median quality becomes useful after roughly 7 days, good after 14 days, and complete at 30 days.
