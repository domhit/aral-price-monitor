import asyncio
from datetime import datetime,timezone
import httpx
from .config import API_URL,POLL_INTERVAL
from .db import connect
from .mqtt import publish_station
HEADERS={"Accept":"application/json","User-Agent":"AralPriceMonitor/0.2"}
async def fetch(c,sid):
 r=await c.get(API_URL.format(station_id=sid),headers=HEADERS,timeout=20);r.raise_for_status();b=r.json();d=b.get("data",b)
 if not isinstance(d.get("prices"),dict):raise ValueError("API-Antwort enthält keine Preise")
 return d
async def collect_once():
 started=datetime.now(timezone.utc).isoformat();ok=err=0;msgs=[]
 with connect() as c:
  rid=c.execute("INSERT INTO collector_runs(started_at) VALUES(?)",(started,)).lastrowid
  targets=[dict(x) for x in c.execute("SELECT s.*,f.id fuel_db_id,f.aral_fuel_id,f.name fuel_name,f.slug FROM stations s JOIN station_fuels sf ON sf.station_id=s.id JOIN fuels f ON f.id=sf.fuel_id WHERE s.active=1 AND sf.active=1 ORDER BY s.name").fetchall()]
 async with httpx.AsyncClient(follow_redirects=True) as h:
  cache={}
  for t in targets:
   try:
    d=cache.get(t['aral_station_id'])
    if d is None:d=await fetch(h,t['aral_station_id']);cache[t['aral_station_id']]=d
    raw=d['prices'].get(t['aral_fuel_id'])
    if raw is None:raise ValueError(f"Kein Preis für {t['aral_fuel_id']}")
    price=round(float(raw)/100,3); changed=d.get('last_price_update') or started;retrieved=datetime.now(timezone.utc).isoformat()
    if not .5<=price<=5:raise ValueError(f"Unplausibler Preis {price}")
    with connect() as c:
     c.execute("INSERT OR IGNORE INTO price_events(station_id,fuel_id,price,price_changed_at,retrieved_at) VALUES(?,?,?,?,?)",(t['id'],t['fuel_db_id'],price,changed,retrieved))
     c.execute("INSERT INTO station_state(station_id,fuel_id,price,price_changed_at,retrieved_at) VALUES(?,?,?,?,?) ON CONFLICT(station_id,fuel_id) DO UPDATE SET price=excluded.price,price_changed_at=excluded.price_changed_at,retrieved_at=excluded.retrieved_at",(t['id'],t['fuel_db_id'],price,changed,retrieved))
    publish_station(t,{"slug":t['slug'],"name":t['fuel_name'],"aral_fuel_id":t['aral_fuel_id']},price,changed,retrieved);ok+=1
   except Exception as e:err+=1;msgs.append(f"{t['name']}/{t['fuel_name']}: {e}")
 with connect() as c:c.execute("UPDATE collector_runs SET finished_at=?,ok_count=?,error_count=?,message=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),ok,err," | ".join(msgs),rid))
 return {"ok":ok,"errors":err,"messages":msgs}
async def collector_loop(stop):
 while not stop.is_set():
  try:await collect_once()
  except Exception as e:print("Collector:",e,flush=True)
  try:await asyncio.wait_for(stop.wait(),timeout=POLL_INTERVAL)
  except asyncio.TimeoutError:pass
