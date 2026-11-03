from datetime import datetime,timezone
from .db import rows
from . import config
MIN_REFUELS_FOR_AVERAGE=10
DEFAULT_FILL_RATIO=.90

def _fuel(v):
 raw=str(v.get('price_fuel') or '').lower().replace('-','_');return {'super_e10':'e10','supere10':'e10','super_e5':'e5','supere5':'e5'}.get(raw,raw)
def _settings():return {x['key']:x['value'] for x in rows('SELECT key,value FROM settings')}
def _usual_fill(v):
 vals=[float(x['liters']) for x in rows('SELECT liters FROM refuels WHERE vehicle_id=? AND liters>0 AND COALESCE(tank_type,1)<>0',(v['id'],))];cap=float(v.get('tank_capacity') or 50);fallback=cap*.9
 if len(vals)<10:return fallback,'90 % Tankvolumen',len(vals)
 avg=sum(vals)/len(vals);return (avg,'Ø Nachfüllmenge',len(vals)) if 0<avg<=cap*1.1 else (fallback,'90 % Tankvolumen',len(vals))
def _avg(v,days):
 q=rows("SELECT price FROM tankerkoenig_prices WHERE fuel_type=? AND datetime(retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{days} days')) if v['price_source']=='tankerkoenig' else rows("SELECT pe.price FROM price_events pe JOIN fuels f ON f.id=pe.fuel_id WHERE f.slug=? AND datetime(pe.retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{days} days'))
 a=[float(x['price']) for x in q];return sum(a)/len(a) if a else None
def _aral(v):return rows('SELECT s.name station,ss.price,ss.retrieved_at,s.latitude,s.longitude,s.extra_distance_km FROM station_state ss JOIN stations s ON s.id=ss.station_id JOIN fuels f ON f.id=ss.fuel_id WHERE f.slug=? AND s.active=1 ORDER BY ss.price',(_fuel(v),))
def _tk(v):
 q=rows('SELECT station_external_id,station_name station,price,retrieved_at,distance,latitude,longitude,place,street,is_open FROM tankerkoenig_prices WHERE fuel_type=? ORDER BY retrieved_at DESC,price ASC',(_fuel(v),))
 if not q:return []
 newest=q[0]['retrieved_at'];return [x for x in q if x['retrieved_at']==newest and x.get('is_open')!=0]
def _age(ts):
 try:return max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(str(ts).replace('Z','+00:00'))).total_seconds()/60)
 except:return None
async def vehicle_price(v,lat=None,lng=None):
 cfg=_settings();candidates=_tk(v) if v['price_source']=='tankerkoenig' else _aral(v);fill,source,count=_usual_fill(v)
 if not candidates:return {**v,'current':None,'candidates':[],'recommendation':'Keine Preisdaten','level':'learning','fill_liters':fill,'fill_source':source,'refuel_count':count}
 avg7=_avg(v,7);avg30=_avg(v,30);cons=float(v.get('consumption') or 0);olat=float(lat if lat is not None else config.TANKERKOENIG_LAT);olng=float(lng if lng is not None else config.TANKERKOENIG_LNG);ref=sum(float(x['price']) for x in candidates)/len(candidates);limit=int(cfg.get('osrm_route_candidates',5));out=[]
 for i,c in enumerate(sorted(candidates,key=lambda x:float(x['price']))):
  x={**c};route=None
  if i<limit and olat and olng and c.get('latitude') is not None and c.get('longitude') is not None:
   try:
    from .osrm import route;route=await route(olat,olng,c['latitude'],c['longitude'])
   except Exception as e:x['route_error']=str(e)
  if not route:
   x.update(route_distance_km=None,route_duration_min=None,eligible=False,trip_cost=None,fill_cost=round(float(c['price'])*fill,2),effective_cost=None,price_age_min=_age(c.get('retrieved_at')));out.append(x);continue
  rt=route['distance_km']*2;trip=rt*cons/100*ref;fc=float(c['price'])*fill;age=_age(c.get('retrieved_at'));fresh=age is None or age<=int(cfg.get('max_price_age_min',60))
  x.update(route_distance_km=route['distance_km'],route_duration_min=route['duration_min'],roundtrip_km=round(rt,2),trip_cost=round(trip,2),fill_cost=round(fc,2),effective_cost=round(fc+trip,2),price_age_min=round(age,1) if age is not None else None,eligible=fresh);out.append(x)
 eligible=sorted([x for x in out if x['eligible'] and x['effective_cost'] is not None],key=lambda x:x['effective_cost'])
 if not eligible:return {**v,'current':None,'candidates':out,'recommendation':'Keine belastbare Route','level':'bad','fill_liters':fill,'fill_source':source,'refuel_count':count}
 cur=eligible[0];base=eligible[1] if len(eligible)>1 else cur;adv=max(0,base['effective_cost']-cur['effective_cost']);threshold=float(v.get('notify_min_advantage') or config.TANK_ASSISTANT_DEFAULT_MIN_ADVANTAGE);maxdist=float(v.get('notify_max_distance_km') or config.TANK_ASSISTANT_DEFAULT_MAX_DISTANCE);worthy=bool(v.get('notify_enabled',1)) and adv>=threshold and cur['route_distance_km']<=maxdist
 # historical hints from existing Aral analytics when available
 expected=min([float(x['price']) for x in candidates],default=float(cur['price']));remaining=max(0,float(cur['price'])-expected)*100
 return {**v,'current':cur,'baseline':base,'candidates':sorted(out,key=lambda x:(x['effective_cost'] is None,x['effective_cost'] or 999)),'advantage':round(adv,2),'avg7':avg7,'avg30':avg30,'fill_liters':round(fill,2),'fill_source':source,'refuel_count':count,'reference_price':round(ref,3),'notify_worthy':worthy,'notify_threshold':threshold,'recommendation':'Tanken lohnt sich' if worthy else 'Beste aktuelle Wahl','level':'good' if worthy else 'okay','expected_low':expected,'remaining_ct':round(remaining,1),'best_window':'Abends meist günstiger'}
async def all_vehicle_prices(lat=None,lng=None):return [await vehicle_price(v,lat,lng) for v in rows('SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id WHERE v.active=1 ORDER BY v.name')]
