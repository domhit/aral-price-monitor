import hashlib
from datetime import datetime,timezone
import httpx
from . import config
from .db import connect,rows
BASE='https://api.spritmonitor.de/v1'
def headers():
 if not config.SPRITMONITOR_APP_TOKEN or not config.SPRITMONITOR_BEARER_TOKEN:raise ValueError('Spritmonitor APP_TOKEN oder BEARER_TOKEN fehlt')
 return {'APPLICATION-ID':config.SPRITMONITOR_APP_TOKEN,'Authorization':f'Bearer {config.SPRITMONITOR_BEARER_TOKEN}','Accept':'application/json'}
def as_list(p,*keys):
 if isinstance(p,list):return p
 if isinstance(p,dict):
  for k in keys:
   if isinstance(p.get(k),list):return p[k]
  if isinstance(p.get('data'),list):return p['data']
 return []
def pick(d,*keys):
 for k in keys:
  if isinstance(d,dict) and d.get(k) not in (None,''):return d[k]
def num(v):
 try:return float(str(v).replace(',','.')) if v not in (None,'') else None
 except:return None
def rid(v):return str(pick(v,'id','vehicle_id','vehicleId') or '')
def rname(v):return str(pick(v,'name','vehicle','description','model') or f'Spritmonitor {rid(v)}')
def normalize(f):
 liters=num(pick(f,'quantity','liters','amount'));total=num(pick(f,'cost','costs','total_cost','total'));price=num(pick(f,'price','price_per_unit','unitprice'))
 if price is None and total is not None and liters:price=total/liters
 if total is None and price is not None and liters:total=price*liters
 return {'external_id':str(pick(f,'id','fueling_id','fuelingId') or '') or None,'refueled_at':str(pick(f,'date','datetime','timestamp') or '')[:16].replace(' ','T'),'odometer':num(pick(f,'odometer','mileage','km')),'liters':liters,'total_cost':total,'price_per_liter':price,'tank_type':pick(f,'type','tank_type','fueling_type'),'spritmonitor_fuel_code':pick(f,'fuel','fuel_id','fuelType'),'station_brand':str(pick(f,'station','station_name','brand') or ''),'location':str(pick(f,'location','place','city') or '')}
def fp(vid,date,odo,liters,total):return hashlib.sha256(f'{vid}|{str(date or "")[:10]}|{odo}|{round(float(liters or 0),2)}|{round(float(total or 0),2)}'.encode()).hexdigest()
async def get_json(c,path):
 r=await c.get(BASE+path,headers=headers(),timeout=30);r.raise_for_status();return r.json()
async def list_vehicles():
 async with httpx.AsyncClient(follow_redirects=True) as c:return as_list(await get_json(c,'/vehicles.json'),'vehicles')
async def list_fuelings(remote_id):
 async with httpx.AsyncClient(follow_redirects=True) as c:return as_list(await get_json(c,f'/vehicle/{remote_id}/fuelings.json'),'fuelings')
async def sync_readonly():
 start=datetime.now(timezone.utc).isoformat();linked=inserted=errors=remote_count=0;messages=[]
 with connect() as c:run=c.execute("INSERT INTO sync_runs(started_at,status) VALUES(?,'running')",(start,)).lastrowid
 maps=rows('SELECT m.*,v.name local_name FROM spritmonitor_vehicle_map m JOIN vehicles v ON v.id=m.local_vehicle_id')
 for m in maps:
  try:
   remote=await list_fuelings(m['spritmonitor_vehicle_id']);remote_count+=len(remote);local=rows('SELECT * FROM refuels WHERE vehicle_id=?',(m['local_vehicle_id'],));byid={str(r['external_id']):r for r in local if r.get('external_id')};byfp={fp(m['local_vehicle_id'],r.get('refueled_at'),r.get('odometer'),r.get('liters'),r.get('total_cost') or r.get('total')):r for r in local}
   for raw in remote:
    x=normalize(raw);now=datetime.now(timezone.utc).isoformat();existing=byid.get(str(x['external_id'])) if x['external_id'] else None
    if existing:
     with connect() as c:c.execute("UPDATE refuels SET last_synced_at=?,sync_status='synced' WHERE id=?",(now,existing['id']))
     continue
    match=byfp.get(fp(m['local_vehicle_id'],x['refueled_at'],x['odometer'],x['liters'],x['total_cost']))
    if match:
     with connect() as c:c.execute("UPDATE refuels SET external_id=?,last_synced_at=?,sync_status='synced' WHERE id=?",(x['external_id'],now,match['id']))
     linked+=1;continue
    if not x['liters'] or not x['refueled_at']:errors+=1;continue
    price=x['price_per_liter'] or 0;total=x['total_cost'] or round(x['liters']*price,2)
    with connect() as c:c.execute("INSERT INTO refuels(vehicle_id,liters,price,total,refueled_at,odometer,price_per_liter,total_cost,tank_type,spritmonitor_fuel_code,station_brand,location,source,external_id,last_synced_at,sync_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'synced')",(m['local_vehicle_id'],x['liters'],price,total,x['refueled_at'],x['odometer'],price,total,x['tank_type'],x['spritmonitor_fuel_code'],x['station_brand'],x['location'],'spritmonitor_api',x['external_id'],now));inserted+=1
  except Exception as e:errors+=1;messages.append(f"{m['local_name']}: {e}")
 finish=datetime.now(timezone.utc).isoformat();status='ok' if errors==0 else 'warning'
 with connect() as c:c.execute('UPDATE sync_runs SET finished_at=?,status=?,vehicles=?,remote_fuelings=?,linked=?,inserted=?,errors=?,message=? WHERE id=?',(finish,status,len(maps),remote_count,linked,inserted,errors,' | '.join(messages),run))
 return {'status':status}
