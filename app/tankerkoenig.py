from datetime import datetime,timezone
import httpx
from . import config
from .db import connect,rows
BASE='https://creativecommons.tankerkoenig.de/api/v4'
FUEL_FIELDS={'e5':'e5','e10':'e10','diesel':'diesel'}
async def search(fuel='e10'):
    if not config.TANKERKOENIG_ENABLED:raise ValueError('Tankerkönig ist deaktiviert')
    if not config.TANKERKOENIG_API_KEY:raise ValueError('TANKERKOENIG_API_KEY fehlt')
    if not config.TANKERKOENIG_LAT or not config.TANKERKOENIG_LNG:raise ValueError('Tankerkönig LAT/LNG fehlen')
    fuel=fuel.lower()
    if fuel not in FUEL_FIELDS:raise ValueError('Kraftstoff muss e5, e10 oder diesel sein')
    params={'apikey':config.TANKERKOENIG_API_KEY,'lat':config.TANKERKOENIG_LAT,'lng':config.TANKERKOENIG_LNG,'rad':config.TANKERKOENIG_RADIUS}
    async with httpx.AsyncClient(timeout=15,follow_redirects=True) as c:r=await c.get(BASE+'/stations/search',params=params);r.raise_for_status();body=r.json()
    stations=body.get('stations') or body.get('data') or []
    now=datetime.now(timezone.utc).isoformat();result=[]
    with connect() as db:
      for st in stations:
        price=st.get(fuel)
        try:price=float(price)
        except:continue
        if not .5<=price<=5:continue
        item={'id':str(st.get('id') or ''),'name':st.get('name') or st.get('brand') or 'Tankstelle','brand':st.get('brand') or '','street':st.get('street') or '','place':st.get('place') or '','lat':st.get('lat'),'lng':st.get('lng'),'dist':st.get('dist'),'price':price,'isOpen':st.get('isOpen'),'fuel':fuel,'retrieved_at':now}
        result.append(item)
        db.execute('INSERT OR IGNORE INTO tankerkoenig_prices(station_external_id,station_name,brand,street,place,latitude,longitude,distance,fuel_type,price,is_open,retrieved_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(item['id'],item['name'],item['brand'],item['street'],item['place'],item['lat'],item['lng'],item['dist'],fuel,price,1 if item['isOpen'] is True else 0 if item['isOpen'] is False else None,now))
    return sorted(result,key=lambda x:(x['price'],x['dist'] if x['dist'] is not None else 999))
def latest(fuel='e10'):
    return rows('''SELECT p.* FROM tankerkoenig_prices p JOIN (SELECT station_external_id,MAX(retrieved_at) t FROM tankerkoenig_prices WHERE fuel_type=? GROUP BY station_external_id) x ON x.station_external_id=p.station_external_id AND x.t=p.retrieved_at WHERE p.fuel_type=? ORDER BY p.price,p.distance''',(fuel,fuel))
