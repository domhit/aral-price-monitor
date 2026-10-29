# Aral Price Monitor v0.5.1

V0.5.1 is the real merge of V0.4.4 vehicle dashboards and V0.5 read-only Spritmonitor sync.

## Included
- All V0.4.4 vehicle dashboards, KPIs, charts and detail pages.
- Spritmonitor read-only API vehicle mapping and manual sync.
- Fingerprint linking of prior CSV imports to remote IDs.
- Unknown remote fuelings imported locally without deleting local data.
- Vehicle detail histories now show fuel code, station and location in separate columns.
- Tokens remain environment variables only.

## Portainer
```yaml
SPRITMONITOR_ENABLED: "true"
SPRITMONITOR_APP_TOKEN: "YOUR_APPLICATION_ID"
SPRITMONITOR_BEARER_TOKEN: "YOUR_BEARER_TOKEN"
SPRITMONITOR_SYNC_INTERVAL: 900
```

## Release
```bash
git add .
git commit -m "fix: merge vehicle dashboards with Spritmonitor read-only sync"
git push origin main
git tag v0.5.1
git push origin v0.5.1
```
