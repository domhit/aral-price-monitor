from datetime import datetime,date,time,timedelta
from zoneinfo import ZoneInfo
from statistics import median
from .db import rows
TZ=ZoneInfo("Europe/Berlin")
def parse_dt(v):
 d=datetime.fromisoformat(v.replace("Z","+00:00"));return d.astimezone(TZ)
def day_bounds(day):
 a=datetime.combine(day,time.min,TZ);return a,a+timedelta(days=1)
def station_series(station_id,fuel_id,day):
 start,end=day_bounds(day)
 prior=rows("SELECT price,price_changed_at FROM price_events WHERE station_id=? AND fuel_id=? AND price_changed_at<? ORDER BY price_changed_at DESC LIMIT 1",(station_id,fuel_id,start.isoformat()))
 ev=rows("SELECT price,price_changed_at FROM price_events WHERE station_id=? AND fuel_id=? AND price_changed_at>=? AND price_changed_at<? ORDER BY price_changed_at",(station_id,fuel_id,start.isoformat(),end.isoformat()))
 points=[]
 if prior:points.append({"x":0,"y":prior[0]['price']})
 for e in ev:
  d=parse_dt(e['price_changed_at']);points.append({"x":round((d-start).total_seconds()/3600,3),"y":e['price']})
 return points
def value_at(points,hour):
 value=None
 for p in points:
  if p['x']<=hour:value=p['y']
  else:break
 return value
def history_payload(slug,days=30):
 fuel=rows("SELECT * FROM fuels WHERE slug=?",(slug,))
 if not fuel:return None
 f=fuel[0]; stations=rows("SELECT s.* FROM stations s JOIN station_fuels sf ON sf.station_id=s.id WHERE sf.fuel_id=? AND sf.active=1 ORDER BY s.name",(f['id'],))
 today=date.today();yesterday=today-timedelta(days=1);colors=['#0064cc','#e6502e','#169c5b','#8c52cc','#d99b00','#008c99']
 datasets=[]
 for i,s in enumerate(stations):
  datasets.append({"label":s['name']+" heute","station":s['name'],"period":"today","color":colors[i%len(colors)],"points":station_series(s['id'],f['id'],today)})
  datasets.append({"label":s['name']+" gestern","station":s['name'],"period":"yesterday","color":colors[i%len(colors)],"points":station_series(s['id'],f['id'],yesterday)})
 # Fuel-wide 15-minute median across all stations and completed days
 profiles=[]
 for offset in range(1,days+1):
  d=today-timedelta(days=offset)
  station_points=[station_series(s['id'],f['id'],d) for s in stations]
  row=[]
  for q in range(96):
   h=q/4;vals=[value_at(p,h) for p in station_points];vals=[v for v in vals if v is not None]
   row.append(median(vals) if vals else None)
  if any(v is not None for v in row):profiles.append(row)
 med=[]
 for q in range(96):
  vals=[r[q] for r in profiles if r[q] is not None]
  if vals:med.append({"x":q/4,"y":round(median(vals),3)})
 first=rows("SELECT MIN(price_changed_at) first FROM price_events WHERE fuel_id=?",(f['id'],))[0]['first']
 available_days=0
 if first:available_days=min(days,max(1,(today-parse_dt(first).date()).days+1))
 return {"fuel":f,"datasets":datasets,"median":med,"data_days":available_days,"target_days":days}
