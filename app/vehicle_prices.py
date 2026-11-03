from .db import rows
from . import config

def _fuel(v):
    raw=str(v.get('price_fuel') or '').strip().lower().replace('-','_')
    return {'super_e10':'e10','supere10':'e10','super_e5':'e5','supere5':'e5'}.get(raw,raw)

def _avg(v,days):
    if v['price_source']=='tankerkoenig':q=rows("SELECT price FROM tankerkoenig_prices WHERE fuel_type=? AND datetime(retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{days} days'))
    else:q=rows("SELECT pe.price FROM price_events pe JOIN fuels f ON f.id=pe.fuel_id WHERE f.slug=? AND datetime(pe.retrieved_at)>=datetime('now',?)",(_fuel(v),f'-{days} days'))
    vals=[float(x['price']) for x in q];return sum(vals)/len(vals) if vals else None

def _aral_candidates(v):
    return rows('''SELECT s.name station,ss.price,ss.retrieved_at,s.distance_km route_distance_km,s.extra_distance_km FROM station_state ss JOIN stations s ON s.id=ss.station_id JOIN fuels f ON f.id=ss.fuel_id WHERE f.slug=? AND s.active=1 ORDER BY ss.price''',(_fuel(v),))

def _tk_candidates(v):
    allrows=rows('''SELECT station_external_id,station_name station,price,retrieved_at,distance,latitude,longitude,place,street FROM tankerkoenig_prices WHERE fuel_type=? ORDER BY retrieved_at DESC,price ASC''',(_fuel(v),))
    if not allrows:return []
    newest=allrows[0]['retrieved_at'];return [x for x in allrows if x['retrieved_at']==newest]

async def vehicle_price(v,lat=None,lng=None,use_routing=True):
    candidates=_tk_candidates(v) if v['price_source']=='tankerkoenig' else _aral_candidates(v)
    if not candidates:return {**v,'current':None,'recommendation':'Keine Preisdaten','level':'learning','candidates':[]}
    avg7=_avg(v,7);avg30=_avg(v,30);tank=float(v.get('tank_capacity') or 50);cons=float(v.get('consumption') or 0)
    olat=float(lat if lat is not None else config.TANKERKOENIG_LAT);olng=float(lng if lng is not None else config.TANKERKOENIG_LNG)
    # Route only the cheapest few Tankerkoenig candidates to keep demo-server load low.
    enriched=[]
    for i,c in enumerate(sorted(candidates,key=lambda x:float(x['price']))):
        x={**c};route=None
        if v['price_source']=='tankerkoenig' and use_routing and i<config.OSRM_ROUTE_CANDIDATES and olat and olng and c.get('latitude') is not None and c.get('longitude') is not None:
            try:
                from .osrm import route as osrm_route
                route=await osrm_route(olat,olng,c['latitude'],c['longitude'])
            except Exception as e:x['route_error']=str(e)
        one_way=route['distance_km'] if route else (float(c.get('distance') or 0) if v['price_source']=='tankerkoenig' else float(c.get('extra_distance_km') or 0)/2)
        roundtrip=one_way*2;trip_cost=roundtrip*cons/100*float(c['price'])
        gross=max(0,(avg30-float(c['price']))*tank) if avg30 else 0
        x.update({'route_distance_km':route['distance_km'] if route else None,'route_duration_min':route['duration_min'] if route else None,'roundtrip_km':round(roundtrip,2),'trip_cost':round(trip_cost,2),'gross_saving':round(gross,2),'net_saving':round(gross-trip_cost,2)})
        enriched.append(x)
    current=min(enriched,key=lambda x:(float(x['price'])*tank+x['trip_cost']))
    price=float(current['price']);delta=(price-avg30)*100 if avg30 else None
    if delta is None:level,label='learning','Daten sammeln'
    elif current['net_saving']>=2 and delta<=-3:level,label='good','Jetzt tanken'
    elif current['net_saving']>0 and delta<=0:level,label='okay','Tanken lohnt sich'
    elif delta<=2:level,label='wait','Normal'
    else:level,label='bad','Eher warten'
    return {**v,'current':current,'avg7':avg7,'avg30':avg30,'delta_ct':delta,'saving_full_tank':max(0,(avg30-price)*tank) if avg30 else None,'net_saving':current['net_saving'],'recommendation':label,'level':level,'candidates':enriched,'origin_lat':olat,'origin_lng':olng}

async def all_vehicle_prices(lat=None,lng=None,use_routing=True):
    vs=rows('SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id WHERE v.active=1 ORDER BY v.name')
    out=[]
    for v in vs:out.append(await vehicle_price(v,lat,lng,use_routing))
    return out
