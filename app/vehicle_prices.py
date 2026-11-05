from datetime import datetime,timezone
from .db import rows
from . import config
def _fuel(v):
 raw=str(v.get('price_fuel') or '').lower().replace('-','_');return {'super_e10':'e10','supere10':'e10','super_e5':'e5','supere5':'e5'}.get(raw,raw)
def _settings():return {x['key']:x['value'] for x in rows('SELECT key,value FROM settings')}
def _fill(v):
 vals=[float(x['liters']) for x in rows('SELECT liters FROM refuels WHERE vehicle_id=? AND liters>0 AND COALESCE(tank_type,1)<>0',(v['id'],))];cap=float(v.get('tank_capacity') or 50);fallback=cap*.9
 if len(vals)<10:return fallback,'90 % Tankvolumen',len(vals)
 avg=sum(vals)/len(vals);return (avg,'Ø Nachfüllmenge',len(vals)) if 0<avg<=cap*1.1 else (fallback,'90 % Tankvolumen',len(vals))
def _avg(v,days):
 q=rows("SELECT price FROM tankerkoenig_prices WHERE fuel_type=? AND datetime(retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{days} days')) if v['price_source']=='tankerkoenig' else rows("SELECT pe.price FROM price_events pe JOIN fuels f ON f.id=pe.fuel_id WHERE f.slug=? AND datetime(pe.retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{days} days'));a=[float(x['price']) for x in q];return sum(a)/len(a) if a else None
def _aral(v):return rows('SELECT s.name station,s.address place,ss.price,ss.retrieved_at,s.latitude,s.longitude,0 distance FROM station_state ss JOIN stations s ON s.id=ss.station_id JOIN fuels f ON f.id=ss.fuel_id WHERE f.slug=? AND s.active=1 ORDER BY ss.price',(_fuel(v),))
def _tk(v):
 q=rows('SELECT station_external_id,station_name station,brand,street,place,price,retrieved_at,distance,latitude,longitude,is_open FROM tankerkoenig_prices WHERE fuel_type=? ORDER BY retrieved_at DESC,price ASC',(_fuel(v),))
 if not q:return []
 newest=q[0]['retrieved_at'];return [x for x in q if x['retrieved_at']==newest and x.get('is_open')!=0]
def _age(ts):
 try:return max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(str(ts).replace('Z','+00:00'))).total_seconds()/60)
 except:return None
def _select_candidates(items,limit=10):
 """Union of five cheapest and five nearest, then fill to requested limit by estimated effective cost."""
 cheapest=sorted(items,key=lambda x:float(x['price']))[:5];nearest=sorted(items,key=lambda x:float(x.get('distance') or 999))[:5];chosen=[];seen=set()
 for x in cheapest+nearest:
  key=x.get('station_external_id') or x.get('station')
  if key not in seen:seen.add(key);chosen.append(x)
 estimated=sorted(items,key=lambda x:float(x['price'])+float(x.get('distance') or 0)*.002)
 for x in estimated:
  key=x.get('station_external_id') or x.get('station')
  if key not in seen:seen.add(key);chosen.append(x)
  if len(chosen)>=limit:break
 return chosen[:limit]
async def vehicle_price(v,lat=None,lng=None):
 cfg=_settings();all_items=_tk(v) if v['price_source']=='tankerkoenig' else _aral(v);fill,source,count=_fill(v)
 if not all_items:return {**v,'current':None,'candidates':[],'recommendation':'Keine Preisdaten','level':'learning','fill_liters':fill,'fill_source':source,'refuel_count':count}
 olat=float(lat if lat is not None else config.TANKERKOENIG_LAT);olng=float(lng if lng is not None else config.TANKERKOENIG_LNG);limit=max(2,min(10,int(cfg.get('osrm_route_candidates',10))));selected=_select_candidates(all_items,limit);ref=sum(float(x['price']) for x in all_items)/len(all_items);cons=float(v.get('consumption') or 0)
 destinations=[]
 for i,x in enumerate(selected):
  if x.get('latitude') is not None and x.get('longitude') is not None:destinations.append({'key':str(i),'latitude':x['latitude'],'longitude':x['longitude']})
 route_map={}
 if destinations and olat and olng:
  try:
   from .osrm import routes;route_map=await routes(olat,olng,destinations)
  except Exception:route_map={}
 out=[]
 for i,c in enumerate(selected):
  x={**c};r=route_map.get(str(i));fc=float(c['price'])*fill;age=_age(c.get('retrieved_at'))
  if not r:x.update(route_distance_km=None,route_duration_min=None,fill_cost=round(fc,2),trip_cost=None,effective_cost=None,eligible=False,price_age_min=age);out.append(x);continue
  trip=r['distance_km']*2*cons/100*ref;fresh=age is None or age<=int(cfg.get('max_price_age_min',60));x.update(route_distance_km=r['distance_km'],route_duration_min=r['duration_min'],fill_cost=round(fc,2),trip_cost=round(trip,2),effective_cost=round(fc+trip,2),eligible=fresh,price_age_min=round(age,1) if age is not None else None);out.append(x)
 good=sorted([x for x in out if x['eligible'] and x['effective_cost'] is not None],key=lambda x:x['effective_cost'])
 if not good:return {**v,'current':None,'candidates':out,'recommendation':'Keine belastbare Route','level':'bad','fill_liters':fill,'fill_source':source,'refuel_count':count}
 cur=good[0];base=good[1] if len(good)>1 else cur;adv=max(0,base['effective_cost']-cur['effective_cost']);a7,a30=_avg(v,7),_avg(v,30);expected=min(float(x['price']) for x in all_items)
 return {**v,'current':cur,'baseline':base,'candidates':sorted(out,key=lambda x:(x['effective_cost'] is None,x['effective_cost'] or 999)),'advantage':round(adv,2),'avg7':a7,'avg30':a30,'fill_liters':round(fill,2),'fill_source':source,'refuel_count':count,'recommendation':'Beste aktuelle Wahl','level':'okay','expected_low':expected,'remaining_ct':round(max(0,float(cur['price'])-expected)*100,1),'best_window':'Abends meist günstiger','candidate_strategy':'5 günstigste + 5 nächste'}
async def all_vehicle_prices(lat=None,lng=None,season_only=True):
 vehicles=rows('SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id WHERE v.active=1 ORDER BY v.name')
 if season_only:
  from .seasons import seasonal_vehicles
  vehicles=seasonal_vehicles(vehicles)
 return [await vehicle_price(v,lat,lng) for v in vehicles]
