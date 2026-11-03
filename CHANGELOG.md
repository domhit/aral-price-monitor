# Changelog

All notable project changes are summarized here.

## [0.9.2] - 2026-11-03
- Consolidated UI and navigation.
- Home/current-location overview and per-vehicle analysis.
- Tankerkönig E10 Top-5 history by lowest average price for 7/30/90 days.
- Vehicle KPIs merged into vehicle management.
- GPS-based Tankerkönig station/price suggestion within 50/100 m on refueling entry.
- Update intervals moved to settings.
- Closed, stale and unroutable stations excluded from recommendation.


## [0.7.5] - 2026-11-03

First public release. Functionally based on the previously tested stable baseline, with release documentation and MIT licensing finalized.

### Added
- Current station comparison using effective total cost.
- Vehicle-specific typical refill quantity based on historical fuelings when at least 10 valid entries are available.
- 90% tank-capacity fallback for vehicles with fewer than 10 valid fuelings.
- OSRM road-route distance and duration in the station comparison.
- Aral station coordinates via cached Tankerkönig matching or manual entry.
- Default-location and browser-geolocation workflows.

### Changed
- Station recommendation now compares current alternatives instead of using the 30-day average as the economic advantage.
- Travel costs use a shared current reference price across candidates.
- 7-day and 30-day price averages remain informational.

## [0.7.3]
- Added Aral coordinates and OSRM routing for Aral stations.

## [0.7.2]
- Added OSRM routing, location-aware recommendations, route caching and source attribution.

## [0.7.1]
- Restored enhanced vehicle dashboards and fixed Tankerkönig `super_e10` / `super_e5` mapping.

## [0.7.0]
- Added per-vehicle price source and fuel configuration plus vehicle price recommendations.

## [0.6.2]
- Fixed Tankerkönig API v4 `fuels`/`coords` parsing and added browser-location search.

## [0.6.0]
- Added enhanced vehicle analytics dashboards.

## [0.5.9]
- Completed Spritmonitor fueling detail import and synchronization.

## [0.5.6]
- Added Spritmonitor synchronization diagnostics and conflict handling.
