# Aral Price Monitor v0.5.0

V0.5 introduces a safe read-only Spritmonitor API sync.

## Spritmonitor API
The service uses the official v1 API with `APPLICATION-ID` and Bearer authentication. Read-only mode uses the vehicle list and each mapped vehicle's fuelings endpoint. It never sends mutations to Spritmonitor.

## Configure in Portainer
```yaml
SPRITMONITOR_ENABLED: "true"
SPRITMONITOR_APP_TOKEN: "YOUR_APPLICATION_ID"
SPRITMONITOR_BEARER_TOKEN: "YOUR_BEARER_TOKEN"
SPRITMONITOR_SYNC_INTERVAL: 900
```

Open **Spritmonitor Sync**, map each local vehicle to the corresponding remote vehicle, then run the first sync manually.

Existing CSV imports are matched using vehicle + date + odometer + liters + total cost. When matched, the remote ID is attached rather than creating a duplicate. Unknown remote fuelings are imported with source `spritmonitor_api`.

## Safety
- Read-only against Spritmonitor.
- Existing local data are never deleted by sync.
- No token is stored in SQLite.
- Every sync run is logged.

## Upgrade
Keep the existing `/data` volume.
```bash
git add .
git commit -m "feat: add read-only Spritmonitor API sync"
git push origin main
git tag v0.5.0
git push origin v0.5.0
```
