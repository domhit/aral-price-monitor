import hashlib
from datetime import datetime,timezone
import httpx
from . import config
from .db import connect,rows
BASE='https://api.spritmonitor.de/v1'

def headers():
 if not config.SPRITMONITOR_APP_TOKEN or not config.SPRITMONITOR_BEARER_TOKEN:raise ValueError('Spritmonitor APP_TOKEN oder BEARER_TOKEN fehlt')
 return {'APPLICATION-ID':config.SPRITMONITOR_APP_TOKEN,'Authorization':f'Bearer {config.SPRITMONITOR_BEARER_TOKEN}','Accept':'application/json'}
def _list(payload,*keys):
 if isinstance(payload,list):return payload
 if isinstance(payload,dict):
  for k in keys:
   if isinstance(payload.get(k),list):return payload[k]
  if isinstance(payload.get('data'),list):return payload['data']
 return []
def _get(d,*keys):
 for k in keys:
  if isinstance(d,dict) and d.get(k) not in (None,''):return d[k]
 return None
def _num(v):
 try:return float(str(v).replace(',','.')) if v not in (None,'') else None
 except:return None
def _date(v):return str(v or '')[:16].replace(' ','T')
def remote_vehicle_id(v):return str(_get(v,'id','vehicle_id','vehicleId') or '')
def remote_vehicle_name(v):return str(_get(v,'name','vehicle','description','model') or f"Spritmonitor {remote_vehicle_id(v)}")
def normalize_fueling(f):
 fid=str(_get(f,'id','fueling_id','fuelingId') or '')
 date=_date(_get(f,'date','datetime','timestamp'))
 odo=_num(_get(f,'odometer','mileage','km'))
 liters=_num(_get(f,'quantity','liters','amount'))
 total=_num(_get(f,'cost','costs','total_cost','total'))
 price=_num(_get(f,'price','price_per_unit','unitprice'))
 if price is None and total is not None and liters:price=total/liters
 if total is None and price is not None and liters:total=price*liters
 return {'external_id':fid or None,'refueled_at':date,'odometer':odo,'liters':liters,'total_cost':total,'price_per_liter':price,'tank_type':_get(f,'type','tank_type','fueling_type'),'spritmonitor_fuel_code':_get(f,'fuel','fuel_id','fuelType'),'station_brand':str(_get(f,'station','station_name','brand') or ''),'location':str(_get(f,'location','place','city') or '')}
def fingerprint(vehicle_id,x):
 return hashlib.sha256(f"{vehicle_id}|{x.get('refueled_at','')[:10]}|{x.get('odometer')}|{round(x.get('liters') or 0,2)}|{round(x.get('total_cost') or 0,2)}".encode()).hexdigest()
def local_fingerprint(vehicle_id,r):
 return hashlib.sha256(f"{vehicle_id}|{str(r.get('refueled_at') or '')[:10]}|{r.get('odometer')}|{round(float(r.get('liters') or 0),2)}|{round(float(r.get('total_cost') or r.get('total') or 0),2)}".encode()).hexdigest()
async def get_json(client,path):
 r=await client.get(BASE+path,headers=headers(),timeout=30);r.raise_for_status();return r.json()
async def list_vehicles():
 async with httpx.AsyncClient(follow_redirects=True) as c:return _list(await get_json(c,'/vehicles.json'),'vehicles')
async def list_fuelings(remote_id):
 async with httpx.AsyncClient(follow_redirects=True) as c:return _list(await get_json(c,f'/vehicle/{remote_id}/fuelings.json'),'fuelings')
async def sync_readonly():
 started=datetime.now(timezone.utc).isoformat();linked=inserted=errors=remote_count=0;messages=[]
 with connect() as c:run=c.execute("INSERT INTO sync_runs(started_at,status) VALUES(?,'running')",(started,)).lastrowid
 maps=rows('SELECT m.*,v.name local_name FROM spritmonitor_vehicle_map m JOIN vehicles v ON v.id=m.local_vehicle_id ORDER BY v.name')
 for m in maps:
  try:
   remote=await list_fuelings(m['spritmonitor_vehicle_id']);remote_count+=len(remote)
   local=rows('SELECT * FROM refuels WHERE vehicle_id=?',(m['local_vehicle_id'],));byid={str(r['external_id']):r for r in local if r.get('external_id')};byfp={local_fingerprint(m['local_vehicle_id'],r):r for r in local}
   for raw in remote:
    x=normalize_fueling(raw);existing=byid.get(str(x['external_id'])) if x['external_id'] else None
    if existing:
     with connect() as c:c.execute("UPDATE refuels SET last_synced_at=?,sync_status='synced' WHERE id=?",(datetime.now(timezone.utc).isoformat(),existing['id']))
     continue
    match=byfp.get(fingerprint(m['local_vehicle_id'],x))
    if match:
     with connect() as c:c.execute("UPDATE refuels SET external_id=?,last_synced_at=?,sync_status='synced' WHERE id=?",(x['external_id'],datetime.now(timezone.utc).isoformat(),match['id']))
     linked+=1;continue
    if not x['liters'] or not x['refueled_at']:messages.append(f"{m['local_name']}: remote Tankung ohne Datum/Liter übersprungen");errors+=1;continue
    price=x['price_per_liter'] or 0;total=x['total_cost'] or round(x['liters']*price,2)
    with connect() as c:c.execute('''INSERT INTO refuels(vehicle_id,liters,price,total,refueled_at,odometer,price_per_liter,total_cost,tank_type,spritmonitor_fuel_code,station_brand,location,source,external_id,last_synced_at,sync_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'synced')''',(m['local_vehicle_id'],x['liters'],price,total,x['refueled_at'],x['odometer'],price,total,x['tank_type'],x['spritmonitor_fuel_code'],x['station_brand'],x['location'],'spritmonitor_api',x['external_id'],datetime.now(timezone.utc).isoformat()))
    inserted+=1
  except Exception as e:errors+=1;messages.append(f"{m['local_name']}: {e}")
 finished=datetime.now(timezone.utc).isoformat();status='ok' if errors==0 else 'warning'
 with connect() as c:
  c.execute('UPDATE sync_runs SET finished_at=?,status=?,vehicles=?,remote_fuelings=?,linked=?,inserted=?,errors=?,message=? WHERE id=?',(finished,status,len(maps),remote_count,linked,inserted,errors,' | '.join(messages),run))
  for m in maps:c.execute('UPDATE spritmonitor_vehicle_map SET last_synced_at=? WHERE local_vehicle_id=?',(finished,m['local_vehicle_id']))
 return {'status':status,'vehicles':len(maps),'remote_fuelings':remote_count,'linked':linked,'inserted':inserted,'errors':errors,'messages':messages}
