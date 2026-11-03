from datetime import datetime,timezone,timedelta
import httpx
from . import config
from .db import connect
HEADERS={'User-Agent':'AralPriceMonitor/0.7.3 (self-hosted private fuel price tool)'}
def _key(*xs):return tuple(round(float(x),5) for x in xs)
async def route(origin_lat,origin_lng,dest_lat,dest_lng):
 a,b,c,d=_key(origin_lat,origin_lng,dest_lat,dest_lng);cutoff=(datetime.now(timezone.utc)-timedelta(hours=config.OSRM_CACHE_HOURS)).isoformat()
 with connect() as db:
  row=db.execute('SELECT distance_km,duration_min FROM osrm_route_cache WHERE origin_lat=? AND origin_lng=? AND dest_lat=? AND dest_lng=? AND retrieved_at>=? ORDER BY retrieved_at DESC LIMIT 1',(a,b,c,d,cutoff)).fetchone()
  if row:return {'distance_km':row['distance_km'],'duration_min':row['duration_min'],'cached':True}
 url=f"{config.OSRM_BASE_URL.rstrip('/')}/route/v1/driving/{b},{a};{d},{c}"
 async with httpx.AsyncClient(timeout=15,follow_redirects=True,headers=HEADERS) as client:
  r=await client.get(url,params={'overview':'false','steps':'false','alternatives':'false'});r.raise_for_status();body=r.json()
 if body.get('code')!='Ok' or not body.get('routes'):raise ValueError(f"OSRM: {body.get('message') or body.get('code') or 'keine Route'}")
 best=body['routes'][0];distance=round(float(best['distance'])/1000,2);duration=round(float(best['duration'])/60,1);now=datetime.now(timezone.utc).isoformat()
 with connect() as db:db.execute('INSERT INTO osrm_route_cache(origin_lat,origin_lng,dest_lat,dest_lng,distance_km,duration_min,retrieved_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(origin_lat,origin_lng,dest_lat,dest_lng) DO UPDATE SET distance_km=excluded.distance_km,duration_min=excluded.duration_min,retrieved_at=excluded.retrieved_at',(a,b,c,d,distance,duration,now))
 return {'distance_km':distance,'duration_min':duration,'cached':False}
