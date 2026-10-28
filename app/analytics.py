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

def active_in_season(v,day=None):
    day=day or date.today(); md=day.strftime('%m-%d'); a=v['season_start']; b=v['season_end']
    return (a<=md<=b) if a<=b else (md>=a or md<=b)

def recommendation_for_fuel(slug,days=30):
    base=history_payload(slug,days)
    if not base:return None
    fuel=base['fuel']; states=rows('''SELECT s.id,s.name,s.aral_station_id,s.extra_distance_km,ss.price,ss.price_changed_at
      FROM station_state ss JOIN stations s ON s.id=ss.station_id WHERE ss.fuel_id=? AND s.active=1 ORDER BY ss.price''',(fuel['id'],))
    if not states:return {**base,'recommendation':'Keine aktuellen Preise','level':'unknown'}
    vehicles=rows('SELECT * FROM vehicles WHERE fuel_id=? AND active=1 ORDER BY id',(fuel['id'],)); vehicle=next((v for v in vehicles if active_in_season(v)),vehicles[0] if vehicles else None)
    current=min(states,key=lambda x:x['price']); now=datetime.now(TZ); q=min(95,max(0,int((now.hour*60+now.minute)/15)))
    profile=[p['y'] for p in base['median'] if p['x']>=q/4]
    expected_low=min(profile) if profile else current['price']; remaining=max(0,current['price']-expected_low)
    tank=vehicle['tank_capacity'] if vehicle and vehicle['tank_capacity'] else 50.0; saving_tank=remaining*tank
    # economic station accounts for configured extra round-trip distance
    econ=[]
    for s in states:
        trip_cost=0
        if vehicle: trip_cost=(s['extra_distance_km'] or 0)*vehicle['consumption']/100*s['price']
        fill_cost=s['price']*tank; econ.append({**s,'trip_cost':round(trip_cost,2),'effective_cost':round(fill_cost+trip_cost,2)})
    economic=min(econ,key=lambda x:x['effective_cost'])
    ct=remaining*100
    if base['data_days']<7:level,label='learning','Daten sammeln'
    elif ct<=1.0:level,label='good','Jetzt tanken'
    elif ct<=2.0:level,label='okay','Tanken okay'
    elif ct<=4.0:level,label='wait','Eher warten'
    else:level,label='bad','Warten lohnt sich wahrscheinlich'
    # best median window: points within 0.5 ct/l of profile minimum
    med=base['median']; low=min((p['y'] for p in med),default=None); good=[p['x'] for p in med if low is not None and p['y']<=low+.005]
    def hm(h):return f'{int(h):02d}:{int(round((h-int(h))*60)):02d}'
    window=f'{hm(min(good))}–{hm(min(24,max(good)+.25))}' if good else 'Noch keine Daten'
    confidence=min(100,round(base['data_days']/max(1,base['target_days'])*100))
    return {**base,'current_price':current['price'],'best_station':current['name'],'expected_low':round(expected_low,3),'remaining_per_liter':round(remaining,3),'remaining_ct':round(ct,1),'saving_per_tank':round(saving_tank,2),'tank_liters':tank,'recommendation':label,'level':level,'best_window':window,'confidence':confidence,'vehicle':vehicle,'economic_station':economic,'stations':econ}

def all_recommendations(days=30):
    fuels=rows('SELECT DISTINCT f.slug FROM fuels f JOIN station_fuels sf ON sf.fuel_id=f.id WHERE sf.active=1 ORDER BY f.name')
    return [r for r in (recommendation_for_fuel(f['slug'],days) for f in fuels) if r]
