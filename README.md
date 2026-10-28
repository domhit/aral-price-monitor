# Aral Price Monitor v0.4.1

Patch release based on V0.4.0.

## Changes

- Fixed duplicate `Tankungen` and `Einstellungen` navigation entries.
- Added Spritmonitor CSV import with vehicle assignment and preview.
- Automatic delimiter and encoding detection (`;`, `,`, tab; UTF-8/Windows-1252).
- Flexible German and English column aliases.
- Imports date, odometer, liters, price or total cost, full/partial tank, station, note and external ID when present.
- Derives price from total/liters or total from price/liters when one value is missing.
- Adds source and external import ID to the local tank log.
- Duplicate-safe repeated imports using Spritmonitor ID or a deterministic fingerprint.
- Existing V0.4 database and all price history remain intact.

## Upgrade

Push the files to the existing repository, wait for GHCR, then pull/redeploy `latest` in Portainer. Keep the existing `/data` volume.

```bash
git add .
git commit -m "fix: deduplicate menu and add Spritmonitor CSV import"
git push origin main
git tag v0.4.1
git push origin v0.4.1
```

## Import workflow

1. Export the fuelings of one vehicle from Spritmonitor as CSV.
2. Open `Tankungen`.
3. Select the corresponding local vehicle and upload the CSV.
4. Check the detected columns and preview.
5. Confirm the import.

The same CSV can be uploaded again safely. Existing import keys are skipped.
