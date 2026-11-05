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
 
 try:
  from .analytics import all_recommendations
  from .mqtt import publish_recommendation
  for rec in all_recommendations(): publish_recommendation(rec)
 except Exception as e: msgs.append(f"Analytics/MQTT: {e}")
 return {"ok":ok,"errors":err,"messages":msgs}
async def collector_loop(stop):
 while not stop.is_set():
  try:await collect_once()
  except Exception as e:print("Collector:",e,flush=True)
  try:await asyncio.wait_for(stop.wait(),timeout=POLL_INTERVAL)
  except asyncio.TimeoutError:pass

async def tankerkoenig_collect_once():
 from . import config
 if not config.TANKERKOENIG_ENABLED:return {'ok':0,'errors':['Tankerkönig deaktiviert']}
 from .tankerkoenig import search
 aliases={'super_e10':'e10','supere10':'e10','super_e5':'e5','supere5':'e5'}
 fuels={aliases.get(str(v['price_fuel'] or '').lower(),str(v['price_fuel'] or '').lower()) for v in __import__('app.db',fromlist=['rows']).rows("SELECT DISTINCT price_fuel FROM vehicles WHERE active=1 AND price_source='tankerkoenig'")}
 ok=0;errors=[]
 for fuel in sorted(fuels):
  if fuel not in ('e5','e10','diesel'):continue
  try:await search(fuel,config.TANKERKOENIG_LAT,config.TANKERKOENIG_LNG,config.TANKERKOENIG_RADIUS);ok+=1
  except Exception as e:errors.append(f'{fuel}: {e}')
 return {'ok':ok,'errors':errors}

async def tankerkoenig_loop(stop):
 # Immediate initial refresh so dashboards work without opening the Tankerkönig page.
 while not stop.is_set():
  try:await tankerkoenig_collect_once()
  except Exception as e:print('Tankerkönig Collector:',e,flush=True)
  try:await asyncio.wait_for(stop.wait(),timeout=600)
  except asyncio.TimeoutError:pass

async def spritmonitor_loop(stop):
 from . import config
 # Let startup migrations and collectors settle before the first automatic read sync.
 try:await asyncio.wait_for(stop.wait(),timeout=60)
 except asyncio.TimeoutError:pass
 while not stop.is_set():
  try:
   from .db import rows
   cfg={x['key']:x['value'] for x in rows('SELECT key,value FROM settings')}
   enabled=config.SPRITMONITOR_ENABLED and config.SPRITMONITOR_AUTO_SYNC and str(cfg.get('spritmonitor_auto_sync','1')).lower() in ('1','true','yes','on')
   minutes=max(60,int(cfg.get('spritmonitor_sync_interval_minutes',1440)))
   if enabled:
    from .spritmonitor_sync import sync
    result=await sync('read_only')
    print('Spritmonitor Auto-Sync:',result,flush=True)
  except Exception as e:print('Spritmonitor Auto-Sync:',e,flush=True)
  try:await asyncio.wait_for(stop.wait(),timeout=max(3600,minutes*60))
  except asyncio.TimeoutError:pass
