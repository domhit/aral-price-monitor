import asyncio
from datetime import datetime, timezone
import httpx
from .config import API_URL, POLL_INTERVAL
from .db import connect
from .mqtt import publish_station

HEADERS = {"Accept": "application/json", "User-Agent": "AralPriceMonitor/0.1 (+self-hosted)"}

async def fetch(client, station_id):
    r = await client.get(API_URL.format(station_id=station_id), headers=HEADERS, timeout=20)
    r.raise_for_status()
    body = r.json()
    data = body.get("data", body)
    if not isinstance(data.get("prices"), dict): raise ValueError("API response contains no prices object")
    return data

async def collect_once():
    started = datetime.now(timezone.utc).isoformat()
    ok = errors = 0
    messages = []
    with connect() as con:
        run_id = con.execute("INSERT INTO collector_runs(started_at) VALUES(?)", (started,)).lastrowid
        targets = [dict(r) for r in con.execute("""SELECT s.*, f.id AS fuel_db_id, f.aral_fuel_id, f.name AS fuel_name, f.slug
          FROM stations s JOIN station_fuels sf ON sf.station_id=s.id JOIN fuels f ON f.id=sf.fuel_id
          WHERE s.active=1 AND sf.active=1 ORDER BY s.name""").fetchall()]
    async with httpx.AsyncClient(follow_redirects=True) as http:
        station_cache = {}
        for t in targets:
            try:
                data = station_cache.get(t['aral_station_id'])
                if data is None:
                    data = await fetch(http, t['aral_station_id']); station_cache[t['aral_station_id']] = data
                raw = data['prices'].get(t['aral_fuel_id'])
                if raw is None: raise ValueError(f"No price for {t['aral_fuel_id']}")
                price = round(float(raw) / 100.0, 3)
                if not 0.5 <= price <= 5.0: raise ValueError(f"Implausible price {price}")
                changed = data.get('last_price_update') or started
                retrieved = datetime.now(timezone.utc).isoformat()
                with connect() as con:
                    con.execute("INSERT OR IGNORE INTO price_events(station_id,fuel_id,price,price_changed_at,retrieved_at) VALUES(?,?,?,?,?)", (t['id'],t['fuel_db_id'],price,changed,retrieved))
                    con.execute("""INSERT INTO station_state(station_id,fuel_id,price,price_changed_at,retrieved_at) VALUES(?,?,?,?,?)
                      ON CONFLICT(station_id,fuel_id) DO UPDATE SET price=excluded.price,price_changed_at=excluded.price_changed_at,retrieved_at=excluded.retrieved_at""", (t['id'],t['fuel_db_id'],price,changed,retrieved))
                publish_station(t, {"slug":t['slug'],"name":t['fuel_name'],"aral_fuel_id":t['aral_fuel_id']}, price, changed, retrieved)
                ok += 1
            except Exception as e:
                errors += 1; messages.append(f"{t['name']}/{t['fuel_name']}: {e}")
    finished = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        con.execute("UPDATE collector_runs SET finished_at=?,ok_count=?,error_count=?,message=? WHERE id=?", (finished,ok,errors," | ".join(messages),run_id))
    return {"ok":ok,"errors":errors,"messages":messages}

async def collector_loop(stop_event):
    while not stop_event.is_set():
        try: await collect_once()
        except Exception as e: print(f"Collector error: {e}", flush=True)
        try: await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL)
        except asyncio.TimeoutError: pass
