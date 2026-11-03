# Aral Price Monitor v0.7.5

## First public release

v0.7.5 is the first release-ready version of Aral Price Monitor and the stable baseline for future development.

### What it does

Aral Price Monitor combines live/current fuel prices, vehicle refueling history and road-routing costs to answer a practical question: **which available station is the most economical place to refuel right now?**

### Highlights

- Aral station price monitoring.
- Tankerkönig API v4 support for E5, E10 and Diesel.
- Spritmonitor vehicle/refueling synchronization.
- Vehicle dashboards with consumption, fuel-price and cost history.
- Per-vehicle price-source selection.
- OSRM road routing instead of straight-line distance.
- Default/home location plus optional mobile browser geolocation.
- Effective station cost calculation: current refill cost + driving cost.
- Average refill quantity derived from 10+ valid historical fuelings; 90% tank capacity otherwise.
- SQLite backup/export and MQTT foundation.

### Economic comparison

v0.7.5 compares stations using current data:

```text
fill cost      = current price × expected refill liters
travel cost    = round trip km × vehicle l/100 km × common current reference price
effective cost = fill cost + travel cost
```

The winning station is the station with the lowest effective cost. Historical 7/30-day prices are shown only as context.

### Before upgrading or deploying

1. Back up `/data/aral-price-monitor.db`.
2. Keep API keys/tokens out of Git.
3. Verify persistent `/data` storage.
4. After startup, confirm v0.7.5 in the UI.
5. Smoke-test Tankerkönig, Spritmonitor Sync, Aral station routing and Fahrzeugpreise.

### License

The application source code is released under the MIT License. External APIs, routing data and fuel-price data remain subject to their respective terms and licenses.

### External services

This release integrates Tankerkönig/MTS-K, Spritmonitor and OSRM/OpenStreetMap. Users are responsible for obtaining required credentials and following the respective service/data terms and attribution requirements.

### Known limitations

- No built-in authentication. Recommended deployment is LAN/VPN or behind an authenticated reverse proxy.
- Mileage charts are based on refueling odometer data, not GPS telemetry.
- Routing assumes an out-and-back refueling trip.
- External APIs are availability/rate-limit dependencies.

### Next direction

Planned post-release work includes automated Tankerkönig collection, Home Assistant/MQTT recommendation entities and later Traccar-based real mileage and route-deviation analysis.
