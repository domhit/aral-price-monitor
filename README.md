# Aral Price Monitor

Self-hosted fuel-price and refueling dashboard for Docker/Portainer. Version **0.7.4** is the first public release and the current stable baseline.

## Highlights

- Aral price monitoring for configured stations and fuel types.
- Tankerkönig API v4 integration for Super E5, Super E10 and Diesel.
- Spritmonitor synchronization for vehicle/refueling history, including consumption and fueling metadata.
- Per-vehicle price source and fuel configuration.
- Vehicle dashboards with consumption, price, cost and refueling history.
- OSRM road routing for real driving distance and duration.
- Current station comparison based on effective trip cost.
- Mobile location search using browser geolocation.
- SQLite persistence, backup/export and MQTT support.
- Multi-architecture container build for `linux/amd64` and `linux/arm64` via GitHub Actions.

## How the station comparison works

For each currently available station:

```text
refill amount = average historical refill amount, if at least 10 valid fuelings exist
                otherwise 90% of configured tank capacity

fill cost      = current station price × refill amount
travel cost    = round-trip road distance × vehicle consumption / 100 × shared reference fuel price
effective cost = fill cost + travel cost
```

Stations are ranked by effective cost. The displayed advantage is the difference between the best and the second-best current station. The 7-day and 30-day averages are informational only and do not select the winner.

## Quick start

### 1. Create persistent data directory

Example on Synology:

```bash
mkdir -p /volume1/docker/aral-price-monitor/data
```

### 2. Configure Docker/Portainer

Use `docker-compose.yml` as a starting point. At minimum, verify the image name and persistent volume.

Recommended environment variables:

```yaml
DATABASE_PATH: /data/aral-price-monitor.db
POLL_INTERVAL_SECONDS: 300
TZ: Europe/Berlin

SPRITMONITOR_ENABLED: "true"
SPRITMONITOR_APP_TOKEN: ""
SPRITMONITOR_BEARER_TOKEN: ""
SPRITMONITOR_SYNC_MODE: "read_only"

TANKERKOENIG_ENABLED: "true"
TANKERKOENIG_API_KEY: ""
TANKERKOENIG_LAT: "49.000000"
TANKERKOENIG_LNG: "7.000000"
TANKERKOENIG_RADIUS: "10"

OSRM_BASE_URL: "https://router.project-osrm.org"
OSRM_CACHE_HOURS: "24"
OSRM_ROUTE_CANDIDATES: "5"
```

Do not commit real API keys or tokens.

### 3. Deploy

```bash
docker compose pull
docker compose up -d
```

Default example port from the supplied compose file:

```text
http://<docker-host>:8095
```

### 4. Initial setup

1. Open **Fahrzeuge** and verify vehicles, tank capacities and price sources.
2. Add/verify **Aral stations** and their fuel assignments.
3. Configure **Tankerkönig** and run a first location search so station data is cached locally.
4. Add coordinates to Aral stations. They can be assigned from cached Tankerkönig station data or entered manually.
5. Configure **Spritmonitor Sync**, map each local vehicle to the correct remote vehicle/tank, then perform a read sync.
6. Open **Fahrzeugpreise** and verify route distance, refill quantity and effective station costs.
7. Create a SQLite backup after initial setup.

## Updating

Before every update, download a SQLite backup from the settings page or copy `/data/aral-price-monitor.db` while the application is stopped.

For a tagged release:

```bash
docker compose pull
docker compose up -d
```

Then verify the version shown in the UI and perform a quick smoke test of Dashboard, Fahrzeugpreise, Tankerkönig and Spritmonitor Sync.

## External services and attribution

### Tankerkönig / MTS-K

Tankerkönig supplies current German E5, E10 and Diesel station data sourced from the Markttransparenzstelle für Kraftstoffe (MTS-K). The public API requires an API key, limits radius searches to 25 km and is offered on a best-effort basis. Observe Tankerkönig/MTS-K usage conditions and attribution requirements.

### Spritmonitor

Spritmonitor is used for vehicle and refueling-history synchronization. This project is independent from Spritmonitor. You need your own Spritmonitor API credentials.

### OSRM / OpenStreetMap

Road distance and duration are calculated with OSRM. The default configuration uses the public OSRM endpoint; routing is cached and limited to a small number of station candidates. For heavier use, configure `OSRM_BASE_URL` to a suitable/self-hosted OSRM service. Routing data is based on OpenStreetMap; retain applicable OpenStreetMap/ODbL attribution.

## Data and security

- Database: SQLite under `/data` by default.
- Secrets: environment variables only, never commit credentials.
- The app has no built-in authentication layer in this release. Keep it behind a trusted LAN/VPN or add a reverse proxy with authentication before exposing it publicly.
- Browser geolocation is used only when explicitly requested by the user.

## Known limitations

- Monthly vehicle mileage is inferred from refueling odometer progression, not GPS telemetry.
- The station comparison assumes a dedicated out-and-back trip to the station.
- Aral station coordinates must be available for OSRM routing; they can be matched from cached Tankerkönig data or entered manually.
- Public third-party APIs may be unavailable or rate-limited.
- Notification automation and Traccar-based real driving/route analysis are not part of v0.7.5.

## License

The application source code is released under the **MIT License**. See `LICENSE`. External data and services remain subject to their own terms and licenses.


## v0.9.2
Consolidated navigation, a home/current-location overview, per-vehicle analysis, Tankerkönig E10 Top-5 charts, vehicle KPIs, GPS station matching for refueling entry and configurable update intervals.
