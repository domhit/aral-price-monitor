from datetime import datetime,timezone,timedelta
import httpx
from . import config
from .db import connect
HEADERS={'User-Agent':'AralPriceMonitor/0.9.3 (self-hosted private fuel price tool)'}
def _key(*xs):return tuple(round(float(x),5) for x in xs)
def _cached(a,b,c,d,cutoff):
 with connect() as db:return db.execute('SELECT distance_km,duration_min FROM osrm_route_cache WHERE origin_lat=? AND origin_lng=? AND dest_lat=? AND dest_lng=? AND retrieved_at>=? ORDER BY retrieved_at DESC LIMIT 1',(a,b,c,d,cutoff)).fetchone()
def _save(a,b,c,d,km,minutes):
 with connect() as db:db.execute('INSERT INTO osrm_route_cache(origin_lat,origin_lng,dest_lat,dest_lng,distance_km,duration_min,retrieved_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(origin_lat,origin_lng,dest_lat,dest_lng) DO UPDATE SET distance_km=excluded.distance_km,duration_min=excluded.duration_min,retrieved_at=excluded.retrieved_at',(a,b,c,d,km,minutes,datetime.now(timezone.utc).isoformat()))
async def routes(origin_lat,origin_lng,destinations):
 """Return road routes for up to 10 destinations. Cached routes are reused; missing routes use one OSRM table request."""
 a,b=_key(origin_lat,origin_lng);cutoff=(datetime.now(timezone.utc)-timedelta(hours=config.OSRM_CACHE_HOURS)).isoformat();result={};missing=[]
 for d in destinations[:10]:
  c,e=_key(d['latitude'],d['longitude']);row=_cached(a,b,c,e,cutoff)
  if row:result[d['key']]={'distance_km':row['distance_km'],'duration_min':row['duration_min'],'cached':True}
  else:missing.append((d,c,e))
 if missing:
  coords=[f'{b},{a}']+[f'{e},{c}' for _,c,e in missing];url=f"{config.OSRM_BASE_URL.rstrip('/')}/table/v1/driving/"+';'.join(coords)
  params={'sources':'0','destinations':';'.join(str(i) for i in range(1,len(coords))),'annotations':'distance,duration'}
  async with httpx.AsyncClient(timeout=20,follow_redirects=True,headers=HEADERS) as client:
   r=await client.get(url,params=params);r.raise_for_status();body=r.json()
  if body.get('code')!='Ok':raise ValueError(f"OSRM table: {body.get('message') or body.get('code')}")
  distances=(body.get('distances') or [[]])[0];durations=(body.get('durations') or [[]])[0]
  for i,(d,c,e) in enumerate(missing):
   if i>=len(distances) or distances[i] is None or durations[i] is None:continue
   km=round(float(distances[i])/1000,2);mins=round(float(durations[i])/60,1);_save(a,b,c,e,km,mins);result[d['key']]={'distance_km':km,'duration_min':mins,'cached':False}
 return result
async def route(origin_lat,origin_lng,dest_lat,dest_lng):
 r=await routes(origin_lat,origin_lng,[{'key':'one','latitude':dest_lat,'longitude':dest_lng}])
 if 'one' not in r:raise ValueError('OSRM: keine Route')
 return r['one']
