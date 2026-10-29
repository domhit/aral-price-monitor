# Aral Price Monitor v0.5.5

- Discovers real Spritmonitor tanks through `/vehicle/{vehicleId}/tanks.json`.
- Tank selector replaces guessed Tank ID 1.
- Full-history reconciliation attempts larger API result windows instead of relying on the default last 15 fuelings.
- Existing CSV rows are fingerprint-linked to remote IDs, not duplicated.
- Sync page shows discovered tank and remote history count.
- Today's price chart ends at the current time; yesterday and median still extend through 24:00.

The Spritmonitor API documentation states that fueling list endpoints return only the last 15 entries without search parameters, which is why V0.5.5 explicitly requests larger result windows.

```bash
git add .
git commit -m "fix: reconcile full Spritmonitor history and discover tank ids"
git push origin main
git tag v0.5.5
git push origin v0.5.5
```
