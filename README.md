# Aral Price Monitor v0.5.6

V0.5.6 closes the Spritmonitor synchronization chapter before Tankerkönig integration.

## New
- Sync diagnostics per vehicle: local total, last remote count, synced, unlinked, modified and conflicts.
- Remote snapshots for linked fuelings.
- Conflict detection when a locally modified entry differs from Spritmonitor.
- Explicit conflict resolution: keep local or take remote.
- Explicit update endpoint for already-synced fuelings.
- Explicit remote delete helper; never executed automatically.
- Real tank discovery and full-history reconciliation from V0.5.5 remain intact.
- Existing vehicle dashboards and chart-to-current-time fix remain intact.

Spritmonitor documents dedicated endpoints for listing tanks/fuelings and for add, update and delete fueling operations. Write responses are still checked for the API `errors` field even when HTTP status is 200.

```bash
git add .
git commit -m "feat: complete Spritmonitor sync diagnostics and conflict handling"
git push origin main
git tag v0.5.6
git push origin v0.5.6
```
