from datetime import datetime,timezone
from .db import rows
from . import config
def _fuel(v):
 raw=str(v.get('price_fuel') or '').lower().replace('-','_');return {'super_e10':'e10','supere10':'e10','super_e5':'e5','supere5':'e5'}.get(raw,raw)
def _cfg():return {x['key']:x['value'] for x in rows('SELECT key,value FROM settings')}
def _fill(v):
 vals=[float(x['liters']) for x in rows('SELECT liters FROM refuels WHERE vehicle_id=? AND liters>0 AND COALESCE(tank_type,1)<>0',(v['id'],))];cap=float(v.get('tank_capacity') or 50);fb=cap*.9
 if len(vals)<10:return fb,'90 % Tankvolumen',len(vals)
 a=sum(vals)/len(vals);return (a,'Ø Nachfüllmenge',len(vals)) if 0<a<=cap*1.1 else (fb,'90 % Tankvolumen',len(vals))
def _avg(v,d):
 q=rows("SELECT price FROM tankerkoenig_prices WHERE fuel_type=? AND datetime(retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{d} days')) if v['price_source']=='tankerkoenig' else rows("SELECT pe.price FROM price_events pe JOIN fuels f ON f.id=pe.fuel_id WHERE f.slug=? AND datetime(pe.retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{d} days'));a=[float(x['price']) for x in q];return sum(a)/len(a) if a else None
def _aral(v):return rows('SELECT s.name station,s.address place,ss.price,ss.retrieved_at,s.latitude,s.longitude FROM station_state ss JOIN stations s ON s.id=ss.station_id JOIN fuels f ON f.id=ss.fuel_id WHERE f.slug=? AND s.active=1 ORDER BY ss.price',(_fuel(v),))
def _tk(v):
 q=rows('SELECT station_external_id,station_name station,brand,street,place,price,retrieved_at,distance,latitude,longitude,is_open FROM tankerkoenig_prices WHERE fuel_type=? ORDER BY retrieved_at DESC,price ASC',(_fuel(v),));
 if not q:return []
 newest=q[0]['retrieved_at'];return [x for x in q if x['retrieved_at']==newest and x.get('is_open')!=0]
def _age(s):
 try:return (datetime.now(timezone.utc)-datetime.fromisoformat(str(s).replace('Z','+00:00'))).total_seconds()/60
 except:return None
async def vehicle_price(v,lat=None,lng=None):
 cfg=_cfg();cs=_tk(v) if v['price_source']=='tankerkoenig' else _aral(v);fill,fs,n=_fill(v)
 if not cs:return {**v,'current':None,'candidates':[],'recommendation':'Keine Preisdaten','level':'learning','fill_liters':fill,'fill_source':fs,'refuel_count':n}
 ref=sum(float(x['price']) for x in cs)/len(cs);cons=float(v.get('consumption') or 0);olat=float(lat if lat is not None else config.TANKERKOENIG_LAT);olng=float(lng if lng is not None else config.TANKERKOENIG_LNG);out=[]
 for i,c in enumerate(sorted(cs,key=lambda x:float(x['price']))):
  x={**c};route=None
  if i<int(cfg.get('osrm_route_candidates',5)) and olat and olng and c.get('latitude') is not None:
   try:
    from .osrm import route;route=await route(olat,olng,c['latitude'],c['longitude'])
   except Exception as e:x['route_error']=str(e)
  fc=float(c['price'])*fill;age=_age(c.get('retrieved_at'))
  if not route:x.update(route_distance_km=None,route_duration_min=None,fill_cost=round(fc,2),trip_cost=None,effective_cost=None,eligible=False,price_age_min=age);out.append(x);continue
  trip=route['distance_km']*2*cons/100*ref;fresh=age is None or age<=int(cfg.get('max_price_age_min',60));x.update(route_distance_km=route['distance_km'],route_duration_min=route['duration_min'],fill_cost=round(fc,2),trip_cost=round(trip,2),effective_cost=round(fc+trip,2),eligible=fresh,price_age_min=age);out.append(x)
 good=sorted([x for x in out if x['eligible'] and x['effective_cost'] is not None],key=lambda x:x['effective_cost'])
 if not good:return {**v,'current':None,'candidates':out,'recommendation':'Keine belastbare Route','level':'bad','fill_liters':fill,'fill_source':fs,'refuel_count':n}
 cur=good[0];base=good[1] if len(good)>1 else cur;adv=max(0,base['effective_cost']-cur['effective_cost']);a7,a30=_avg(v,7),_avg(v,30);expected=min(float(x['price']) for x in cs)
 return {**v,'current':cur,'baseline':base,'candidates':sorted(out,key=lambda x:(x['effective_cost'] is None,x['effective_cost'] or 999)),'advantage':round(adv,2),'avg7':a7,'avg30':a30,'fill_liters':round(fill,2),'fill_source':fs,'refuel_count':n,'recommendation':'Beste aktuelle Wahl','level':'okay','expected_low':expected,'remaining_ct':round(max(0,float(cur['price'])-expected)*100,1),'best_window':'Abends meist günstiger'}
async def all_vehicle_prices(lat=None,lng=None):return [await vehicle_price(v,lat,lng) for v in rows('SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id WHERE v.active=1 ORDER BY v.name')]
