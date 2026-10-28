# Aral Price Monitor v0.1.0

Self-hosted Docker service for Aral fuel prices with SQLite history, a small web UI, MQTT Discovery for Home Assistant, and exact price-change timestamps from the Aral price API.

## V0.1 features

- Seven preconfigured stations
- Aral Ultimate 102 (`F00125`) and Aral SuperPlus (`F00114`)
- Audi RS3 and Audi S3 as initial vehicles
- Polling every five minutes
- Deduplicated price events using Aral's `last_price_update`
- SQLite in `/data`
- FastAPI web UI on port 8000
- Home Assistant MQTT Discovery
- Multi-architecture image for `linux/amd64` and `linux/arm64`
- GitHub Actions build and publish to GHCR

## GitHub and GHCR

1. Create a new GitHub repository named `aral-price-monitor`.
2. Upload this project and push it to `main`.
3. Open **Actions** and wait for `Build and publish Docker image`.
4. Open **Packages** in the repository/user profile and set the package visibility as needed.
5. Replace `DEIN_GITHUB_BENUTZER` in `docker-compose.yml` with the lowercase GitHub owner.

The workflow publishes:

- `ghcr.io/<owner>/aral-price-monitor:latest`
- version tags such as `ghcr.io/<owner>/aral-price-monitor:0.1.0`

## Portainer deployment

1. Create `/volume1/docker/aral-price-monitor/data` on the Synology.
2. In Portainer open **Stacks**, create a stack, and paste `docker-compose.yml`.
3. Adjust image owner, MQTT host, username, and password.
4. Deploy the stack.
5. Open `http://<NAS-IP>:8095`.

If the GHCR package is private, add a GHCR registry in Portainer using a GitHub personal access token with `read:packages`.

## Data persistence

All mutable data is stored in:

```text
/data/aral-price-monitor.db
```

Back up the mapped Synology directory. SQLite uses WAL mode. For a consistent live backup, use SQLite's backup command or briefly stop the container before copying the database and its possible `-wal`/`-shm` files.

## MQTT

The service publishes retained discovery and state messages. Example entity:

```text
sensor.neunkirchen_konigstrasse_aral_ultimate_102
```

Exact entity IDs are assigned by Home Assistant; stable `unique_id` values use station ID and fuel slug.

## Initial stations

### Ultimate 102
- 12141800 Neunkirchen Königstraße
- 28423400 St. Ingbert Saarbrücker Straße
- 28409400 Spiesen-Elversberg Lindenstraße 14
- 18052100 St. Wendel Mommstraße

### SuperPlus
- 28416400 Schiffweiler Kreisstraße
- 18056700 Spiesen-Elversberg Lindenstraße 7
- 28414400 Homburg Saarbrücker Straße

## Local development

```bash
docker compose up --build
```

Web UI: `http://localhost:8095`

## Release

```bash
git add .
git commit -m "feat: initial Aral Price Monitor v0.1.0"
git push origin main
git tag v0.1.0
git push origin v0.1.0
```

## V0.2 planned

- Today versus yesterday step charts
- 30-day median daily profile
- Expected daily low
- Refuel recommendation
- Separate Ultimate 102 and SuperPlus dashboards
