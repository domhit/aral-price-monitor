from datetime import datetime,timezone,timedelta
from .db import rows

def _fuel(v):
    raw=str(v.get('price_fuel') or '').strip().lower().replace('-','_')
    return {'super_e10':'e10','supere10':'e10','super_e5':'e5','supere5':'e5'}.get(raw,raw)

def _aral(v):
    q=rows('''SELECT s.name station,ss.price,ss.price_changed_at,ss.retrieved_at FROM station_state ss JOIN stations s ON s.id=ss.station_id JOIN fuels f ON f.id=ss.fuel_id WHERE f.slug=? AND s.active=1 ORDER BY ss.price LIMIT 1''',(_fuel(v),))
    return q[0] if q else None

def _tk(v):
    q=rows('''SELECT station_name station,price,retrieved_at,distance FROM tankerkoenig_prices WHERE fuel_type=? ORDER BY retrieved_at DESC,price ASC''',(_fuel(v),))
    if not q:return None
    newest=q[0]['retrieved_at'];same=[x for x in q if x['retrieved_at']==newest];return min(same,key=lambda x:x['price'])

def _history(v,days=30):
    if v['price_source']=='tankerkoenig':
        q=rows("SELECT price FROM tankerkoenig_prices WHERE fuel_type=? AND retrieved_at>=datetime('now',?)",(_fuel(v),f'-{days} days'))
    else:
        q=rows("SELECT pe.price FROM price_events pe JOIN fuels f ON f.id=pe.fuel_id WHERE f.slug=? AND pe.retrieved_at>=datetime('now',?)",(_fuel(v),f'-{days} days'))
    return [float(x['price']) for x in q]

def vehicle_price(v):
    cur=_tk(v) if v['price_source']=='tankerkoenig' else _aral(v);hist=_history(v)
    if not cur:return {**v,'current':None,'recommendation':'Keine Preisdaten','level':'learning'}
    avg=sum(hist)/len(hist) if hist else None;price=float(cur['price']);delta=(price-avg)*100 if avg else None
    if delta is None:level,label='learning','Daten sammeln'
    elif delta<=-5:level,label='good','Jetzt tanken'
    elif delta<=-2:level,label='okay','Günstig'
    elif delta<=2:level,label='wait','Normal'
    else:level,label='bad','Eher warten'
    tank=float(v.get('tank_capacity') or 50);saving=max(0,(avg-price)*tank) if avg else None
    return {**v,'current':cur,'avg30':avg,'delta_ct':delta,'saving_full_tank':saving,'recommendation':label,'level':level}

def all_vehicle_prices():
    vs=rows('SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id WHERE v.active=1 ORDER BY v.name')
    return [vehicle_price(v) for v in vs]
