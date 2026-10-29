# Aral Price Monitor v0.5.3

V0.5.3 adds safe bidirectional Spritmonitor synchronization for **new local fuelings**.

## Safety model
- Pull from Spritmonitor remains read-only.
- Existing CSV imports are linked using fingerprints.
- New manual local fuelings can be previewed and sent individually.
- `create_only` first pulls, then sends unsynced manual fuelings.
- Existing remote fuelings are not modified or deleted.
- API responses are checked for `errors` and `errormessages`, even on HTTP 200.
- Failed writes remain local with `sync_status=sync_error` and can be retried.

## Portainer
```yaml
SPRITMONITOR_ENABLED: "true"
SPRITMONITOR_APP_TOKEN: "..."
SPRITMONITOR_BEARER_TOKEN: "..."
SPRITMONITOR_SYNC_MODE: "read_only"
SPRITMONITOR_SYNC_INTERVAL: 900
```

Start with `read_only`. Use the web UI to inspect the outgoing preview and send one test fueling individually before using `create_only`.

## Release
```bash
git add .
git commit -m "feat: add safe create-only Spritmonitor sync"
git push origin main
git tag v0.5.3
git push origin v0.5.3
```
