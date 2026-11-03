import math
from .db import rows
def hav(a,b,c,d):
 R=6371000;p1,p2=math.radians(a),math.radians(c);dp=math.radians(c-a);dl=math.radians(d-b);x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2;return 2*R*math.asin(math.sqrt(x))
def match(lat,lng,vehicle_id):
 v=(rows('SELECT * FROM vehicles WHERE id=?',(vehicle_id,)) or [None])[0];fuel=str(v.get('price_fuel') or 'e10').lower() if v else 'e10';fuel={'super_e10':'e10','super_e5':'e5'}.get(fuel,fuel);q=rows('SELECT * FROM tankerkoenig_prices WHERE fuel_type=? AND latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY retrieved_at DESC',(fuel,));seen=set();cand=[]
 for x in q:
  if x['station_external_id'] in seen:continue
  seen.add(x['station_external_id']);dist=hav(lat,lng,x['latitude'],x['longitude']);cand.append({**x,'distance_m':round(dist,1)})
 cand.sort(key=lambda x:x['distance_m']);best=cand[0] if cand else None
 return {'match':best if best and best['distance_m']<=100 else None,'auto':bool(best and best['distance_m']<=50),'candidates':[x for x in cand[:5] if x['distance_m']<=100]}
