# Aral Price Monitor v0.4.2

V0.4.2 adds a complete vehicle-cost ledger and Spritmonitor costs CSV import while preserving every V0.4.1 function.

## New

- New `Kosten` navigation page.
- Add, edit and delete vehicle costs manually.
- Per-vehicle cost totals and entry counts.
- Spritmonitor costs CSV preview and import.
- Supports numeric cost codes and German cost names.
- Imports date, odometer, distance, cost type, total cost, currency, multi-line notes and recurrence interval in months.
- All Spritmonitor cost types 1–23 are included.
- Duplicate-safe repeated CSV imports.
- Persistent `vehicle_costs` SQLite table with automatic migration.

## Spritmonitor cost types

1 Wartung, 2 Reparatur, 3 Reifenwechsel, 4 Ölwechsel, 5 Versicherung, 6 Steuer, 7 HU/AU, 8 Tuning, 9 Zubehör, 10 Kaufpreis, 11 Sonstiges, 12 Wagenpflege, 13 Leasingrate, 14 Zulassung/Ummeldung, 15 Finanzierungsrate, 16 Erstattung, 17 Bußgeld, 18 Parkgebühr, 19 Maut, 20 Ersatzteile, 21 Ladegrundgebühr, 22 Digitale Dienste, 23 THG-Prämie.

## Upgrade

Keep the existing `/data` volume and redeploy the GHCR `latest` image after pushing this project.

```bash
git add .
git commit -m "feat: add vehicle costs and Spritmonitor costs import"
git push origin main
git tag v0.4.2
git push origin v0.4.2
```
