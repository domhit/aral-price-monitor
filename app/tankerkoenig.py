from datetime import datetime,timezone
import httpx
from . import config
from .db import connect,rows
BASE='https://creativecommons.tankerkoenig.de/api/v4'

def _fuel_price(st,fuel):
    # API v4 returns fuels as an array, not flat e10/e5/diesel fields.
    wanted=fuel.lower()
    for f in st.get('fuels') or []:
        name=str(f.get('name') or f.get('type') or f.get('shortName') or '').lower().replace(' ','')
        aliases={'e10':('e10','supere10'),'e5':('e5','supere5'),'diesel':('diesel',)}[wanted]
        if any(a in name for a in aliases):
            try:return float(f.get('price'))
            except (TypeError,ValueError):return None
    # compatibility if upstream ever returns legacy flat fields
    try:return float(st.get(wanted))
    except (TypeError,ValueError):return None

def _coords(st):
    c=st.get('coords') or {}
    return c.get('lat',st.get('lat')),c.get('lng',st.get('lng'))

async def search(fuel='e10',lat=None,lng=None,radius=None):
    if not config.TANKERKOENIG_ENABLED:raise ValueError('Tankerkönig ist deaktiviert')
    if not config.TANKERKOENIG_API_KEY:raise ValueError('TANKERKOENIG_API_KEY fehlt')
    lat=float(lat if lat is not None else config.TANKERKOENIG_LAT);lng=float(lng if lng is not None else config.TANKERKOENIG_LNG);radius=max(.1,min(25,float(radius if radius is not None else config.TANKERKOENIG_RADIUS)))
    if not (-90<=lat<=90 and -180<=lng<=180) or (lat==0 and lng==0):raise ValueError('Ungültige oder fehlende Koordinaten')
    fuel=fuel.lower()
    if fuel not in ('e5','e10','diesel'):raise ValueError('Kraftstoff muss e5, e10 oder diesel sein')
    params={'apikey':config.TANKERKOENIG_API_KEY,'lat':lat,'lng':lng,'rad':radius}
    async with httpx.AsyncClient(timeout=20,follow_redirects=True) as c:
        r=await c.get(BASE+'/stations/search',params=params)
        if r.status_code>=400:raise ValueError(f'Tankerkönig HTTP {r.status_code}: {r.text[:300]}')
        body=r.json()
    stations=body.get('stations') or []
    now=datetime.now(timezone.utc).isoformat();result=[]
    with connect() as db:
      for st in stations:
        price=_fuel_price(st,fuel)
        if price is None or not .5<=price<=5:continue
        slat,slng=_coords(st)
        item={'id':str(st.get('id') or ''),'name':st.get('name') or st.get('brand') or 'Tankstelle','brand':st.get('brand') or '','street':st.get('street') or '','place':st.get('place') or '','lat':slat,'lng':slng,'dist':st.get('dist'),'price':price,'isOpen':st.get('isOpen'),'fuel':fuel,'retrieved_at':now}
        result.append(item)
        db.execute('INSERT OR IGNORE INTO tankerkoenig_prices(station_external_id,station_name,brand,street,place,latitude,longitude,distance,fuel_type,price,is_open,retrieved_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(item['id'],item['name'],item['brand'],item['street'],item['place'],slat,slng,item['dist'],fuel,price,1 if item['isOpen'] is True else 0 if item['isOpen'] is False else None,now))
    return sorted(result,key=lambda x:(x['price'],x['dist'] if x['dist'] is not None else 999))

def latest(fuel='e10'):
    return rows('''SELECT p.* FROM tankerkoenig_prices p JOIN (SELECT station_external_id,MAX(retrieved_at) t FROM tankerkoenig_prices WHERE fuel_type=? GROUP BY station_external_id) x ON x.station_external_id=p.station_external_id AND x.t=p.retrieved_at WHERE p.fuel_type=? ORDER BY p.price,p.distance''',(fuel,fuel))
