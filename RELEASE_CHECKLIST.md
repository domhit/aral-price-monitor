# v0.7.5 Release Checklist

## Repository
- [ ] Confirm working tree starts from tested v0.7.5 code.
- [ ] Review README.md, CHANGELOG.md and RELEASE_NOTES_v0.7.5.md.
- [x] MIT License added as `LICENSE`.
- [ ] Confirm no API keys, bearer tokens, database files or backups are tracked.

## Validation
- [ ] `python -m compileall -q app`
- [ ] Build Docker image locally or let GitHub Actions build it.
- [ ] Open `/health` and verify version 0.7.4.
- [ ] Verify Aral collector/dashboard.
- [ ] Verify Tankerkönig E10/E5/Diesel query.
- [ ] Verify Spritmonitor read synchronization.
- [ ] Verify Fahrzeugpreise including OSRM route distance and effective cost.
- [ ] Verify SQLite backup download.

## Git/GitHub
```bash
git add README.md CHANGELOG.md RELEASE_NOTES_v0.7.5.md RELEASE_CHECKLIST.md app/
git commit -m "release: prepare v0.7.5 first public release"
git push origin main

git tag -a v0.7.5 -m "Aral Price Monitor v0.7.5 - first stable release"
git push origin v0.7.5
```

The existing GitHub Actions workflow builds tags matching `v*.*.*` and publishes semver image tags to GHCR.

## GitHub Release
1. Open GitHub > Releases > Draft a new release.
2. Select tag `v0.7.5`.
3. Title: `Aral Price Monitor v0.7.5 - First Stable Release`.
4. Paste `RELEASE_NOTES_v0.7.5.md` into the release description.
5. Optionally attach the source ZIP.
6. Publish the release.

## After publication
- [ ] Pull the tagged image in Portainer/Synology.
- [ ] Confirm UI version 0.7.4.
- [ ] Keep v0.7.5 as the rollback tag before starting v0.9 development.
