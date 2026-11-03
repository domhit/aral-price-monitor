from .db import rows
from . import config
MIN_REFUELS_FOR_AVERAGE=10
DEFAULT_FILL_RATIO=0.90

def _fuel(v):
 raw=str(v.get('price_fuel') or '').strip().lower().replace('-','_')
 return {'super_e10':'e10','supere10':'e10','super_e5':'e5','supere5':'e5'}.get(raw,raw)

def _avg(v,days):
 if v['price_source']=='tankerkoenig':q=rows("SELECT price FROM tankerkoenig_prices WHERE fuel_type=? AND datetime(retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{days} days'))
 else:q=rows("SELECT pe.price FROM price_events pe JOIN fuels f ON f.id=pe.fuel_id WHERE f.slug=? AND datetime(pe.retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{days} days'))
 vals=[float(x['price']) for x in q];return sum(vals)/len(vals) if vals else None

def _usual_fill(v):
 vals=[float(x['liters']) for x in rows('SELECT liters FROM refuels WHERE vehicle_id=? AND liters>0 AND COALESCE(tank_type,1)<>0 ORDER BY refueled_at DESC,id DESC',(v['id'],))]
 capacity=float(v.get('tank_capacity') or 50);fallback=capacity*DEFAULT_FILL_RATIO
 if len(vals)<10:return fallback,'90 % Tankvolumen',len(vals)
 avg=sum(vals)/len(vals)
 return (avg,'Ø Nachfüllmenge aus Tankhistorie',len(vals)) if 0<avg<=capacity*1.10 else (fallback,'90 % Tankvolumen',len(vals))

def _aral(v):return rows('SELECT s.id station_id,s.name station,s.address,ss.price,ss.retrieved_at,s.latitude,s.longitude,s.extra_distance_km FROM station_state ss JOIN stations s ON s.id=ss.station_id JOIN fuels f ON f.id=ss.fuel_id WHERE f.slug=? AND s.active=1 ORDER BY ss.price',(_fuel(v),))
def _tk(v):
 q=rows('SELECT station_external_id,station_name station,price,retrieved_at,distance,latitude,longitude,place,street FROM tankerkoenig_prices WHERE fuel_type=? ORDER BY retrieved_at DESC,price ASC',(_fuel(v),))
 if not q:return []
 newest=q[0]['retrieved_at'];return [x for x in q if x['retrieved_at']==newest]

async def vehicle_price(v,lat=None,lng=None):
 candidates=_tk(v) if v['price_source']=='tankerkoenig' else _aral(v);fill_liters,fill_source,refuel_count=_usual_fill(v)
 if not candidates:return {**v,'current':None,'recommendation':'Keine Preisdaten','level':'learning','candidates':[],'fill_liters':fill_liters,'fill_source':fill_source,'refuel_count':refuel_count}
 avg7=_avg(v,7);avg30=_avg(v,30);cons=float(v.get('consumption') or 0);olat=float(lat if lat is not None else config.TANKERKOENIG_LAT);olng=float(lng if lng is not None else config.TANKERKOENIG_LNG);reference_price=sum(float(x['price']) for x in candidates)/len(candidates)
 out=[]
 for i,c in enumerate(sorted(candidates,key=lambda x:float(x['price']))):
  x={**c};route=None
  if i<config.OSRM_ROUTE_CANDIDATES and olat and olng and c.get('latitude') is not None and c.get('longitude') is not None:
   try:
    from .osrm import route as osrm_route;route=await osrm_route(olat,olng,c['latitude'],c['longitude'])
   except Exception as e:x['route_error']=str(e)
  fallback=float(c.get('distance') or 0) if v['price_source']=='tankerkoenig' else float(c.get('extra_distance_km') or 0)/2;oneway=route['distance_km'] if route else fallback;roundtrip=oneway*2;trip_liters=roundtrip*cons/100;trip_cost=trip_liters*reference_price;fill_cost=float(c['price'])*fill_liters;effective=fill_cost+trip_cost
  x.update(gross_saving=max(0,round((avg30-float(c['price']))*fill_liters,2)) if avg30 else 0,net_saving=round((max(0,(avg30-float(c['price']))*fill_liters) if avg30 else 0)-trip_cost,2),route_distance_km=route['distance_km'] if route else None,route_duration_min=route['duration_min'] if route else None,roundtrip_km=round(roundtrip,2),trip_cost=round(trip_cost,2),fill_cost=round(fill_cost,2),effective_cost=round(effective,2));out.append(x)
 out.sort(key=lambda x:x['effective_cost']);current=out[0];baseline=out[1] if len(out)>1 else out[0];adv=max(0,baseline['effective_cost']-current['effective_cost'])
 return {**v,'current':current,'baseline':baseline,'advantage':round(adv,2),'avg7':avg7,'avg30':avg30,'delta_ct':((float(current['price'])-avg30)*100 if avg30 else None),'recommendation':'Beste Wahl' if adv>=2 else 'Leichter Vorteil' if adv>=.5 else 'Nahezu gleich teuer','level':'good' if adv>=2 else 'okay' if adv>=.5 else 'wait','candidates':out,'fill_liters':round(fill_liters,2),'fill_source':fill_source,'refuel_count':refuel_count,'reference_price':round(reference_price,3)}
async def all_vehicle_prices(lat=None,lng=None):
 return [await vehicle_price(v,lat,lng) for v in rows('SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id WHERE v.active=1 ORDER BY v.name')]
