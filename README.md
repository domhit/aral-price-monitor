# Aral Price Monitor v0.5.2

V0.5.2 keeps the V0.4.4 vehicle dashboards and V0.5 read-only sync, and fixes fuel/station/location display.

- Spritmonitor code 22 at Aral is displayed as **Ultimate 102**.
- Code 22 at other brands remains **Premium Benzin 100+**.
- Fuel, station and location are separate columns.

```bash
git add .
git commit -m "fix: show fuel station and location in vehicle dashboards"
git push origin main
git tag v0.5.2
git push origin v0.5.2
```
