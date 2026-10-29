import hashlib,json
from datetime import datetime,timezone
import httpx
from . import config
from .db import connect,rows
BASE='https://api.spritmonitor.de/v1'
TANK_TYPE={0:'invalid',1:'full',2:'notfull',3:'first'}
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
def vehicle_id(v):return str(pick(v,'id','vehicle_id','vehicleId') or '')
def vehicle_name(v):return str(pick(v,'name','vehicle','description','model') or f'Spritmonitor {vehicle_id(v)}')
def check_response(body):
 if not isinstance(body,dict):raise ValueError('Ungültige Spritmonitor-Antwort')
 if int(body.get('errors',0) or 0)>0:raise ValueError(json.dumps(body.get('errormessages') or body,ensure_ascii=False))
 return str(pick(body,'id','fueling_id','fuelingId') or pick(body.get('data',{}) if isinstance(body.get('data'),dict) else {},'id','fueling_id') or '') or None
def normalize(f):
 liters=num(pick(f,'quantity','liters','amount'));total=num(pick(f,'cost','costs','total_cost','total'));price=num(pick(f,'price','price_per_unit','unitprice'))
 if price is None and total is not None and liters:price=total/liters
 if total is None and price is not None and liters:total=price*liters
 return {'external_id':str(pick(f,'id','fueling_id','fuelingId') or '') or None,'refueled_at':str(pick(f,'date','datetime','timestamp') or '')[:16].replace(' ','T'),'odometer':num(pick(f,'odometer','mileage','km')),'liters':liters,'total_cost':total,'price_per_liter':price,'tank_type':pick(f,'type','tank_type','fueling_type'),'spritmonitor_fuel_code':pick(f,'fuelsortid','fuel','fuel_id','fuelType'),'station_brand':str(pick(f,'stationname','station','station_name','brand') or ''),'location':str(pick(f,'location','place','city') or '')}
def fp(vid,date,odo,liters,total):return hashlib.sha256(f'{vid}|{str(date or "")[:10]}|{odo}|{round(float(liters or 0),2)}|{round(float(total or 0),2)}'.encode()).hexdigest()
async def get_json(c,path,params=None):
 r=await c.get(BASE+path,headers=headers(),params=params,timeout=30);r.raise_for_status();return r.json()
async def list_vehicles():
 async with httpx.AsyncClient(follow_redirects=True) as c:return as_list(await get_json(c,'/vehicles.json'),'vehicles')
async def list_fuelings(remote_id):
 async with httpx.AsyncClient(follow_redirects=True) as c:return as_list(await get_json(c,f'/vehicle/{remote_id}/fuelings.json'),'fuelings')
def outbound_payload(r,m):
 date=str(r.get('refueled_at') or '')[:10]
 if not date:raise ValueError('Datum fehlt')
 d=datetime.fromisoformat(date)
 fuel=r.get('spritmonitor_fuel_code')
 if fuel in (None,''):raise ValueError('Kraftstoff/Spritmonitor-Code fehlt')
 payload={'date':d.strftime('%d.%m.%Y'),'odometer':r.get('odometer'),'trip':r.get('trip_km'),'quantity':r.get('liters'),'type':TANK_TYPE.get(int(r.get('tank_type') or 1),'full'),'price':r.get('price_per_liter') or r.get('price'),'currencyid':m.get('currency_id') or 1,'pricetype':1,'fuelsortid':fuel,'quantityunitid':m.get('quantity_unit_id') or 1,'note':r.get('note') or '','stationname':r.get('station_brand') or '','location':r.get('location') or '','country':r.get('country') or '','bc_consumption':r.get('bc_consumption'),'bc_quantity':r.get('bc_fuel_quantity'),'bc_speed':r.get('bc_speed'),'position_lat':r.get('latitude'),'position_long':r.get('longitude'),'attributes':r.get('attributes'),'streets':r.get('streets')}
 return {k:v for k,v in payload.items() if v not in (None,'')}
async def push_one(r,m,dry=False):
 payload=outbound_payload(r,m)
 if dry:return payload
 path=f"/vehicle/{m['spritmonitor_vehicle_id']}/tank/{m.get('tank_id') or '1'}/fueling.json"
 # Official API defines the add operation as GET with query parameters.
 async with httpx.AsyncClient(follow_redirects=True) as c:body=await get_json(c,path,payload)
 external=check_response(body);now=datetime.now(timezone.utc).isoformat()
 with connect() as db:db.execute("UPDATE refuels SET external_id=COALESCE(?,external_id),last_synced_at=?,sync_status='synced',sync_error=NULL WHERE id=?",(external,now,r['id']))
 return body
def pending_rows():return rows("""SELECT r.*,v.name local_name,m.spritmonitor_vehicle_id,m.tank_id,m.currency_id,m.quantity_unit_id FROM refuels r JOIN vehicles v ON v.id=r.vehicle_id JOIN spritmonitor_vehicle_map m ON m.local_vehicle_id=r.vehicle_id WHERE r.external_id IS NULL AND r.source='manual' AND COALESCE(r.sync_status,'local') IN ('local','pending','sync_error') ORDER BY r.refueled_at""")
async def pull_all():
 linked=inserted=errors=remote_count=0;messages=[];maps=rows('SELECT m.*,v.name local_name FROM spritmonitor_vehicle_map m JOIN vehicles v ON v.id=m.local_vehicle_id')
 for m in maps:
  try:
   remote=await list_fuelings(m['spritmonitor_vehicle_id']);remote_count+=len(remote);local=rows('SELECT * FROM refuels WHERE vehicle_id=?',(m['local_vehicle_id'],));byid={str(r['external_id']):r for r in local if r.get('external_id')};byfp={fp(m['local_vehicle_id'],r.get('refueled_at'),r.get('odometer'),r.get('liters'),r.get('total_cost') or r.get('total')):r for r in local}
   for raw in remote:
    x=normalize(raw);now=datetime.now(timezone.utc).isoformat();existing=byid.get(str(x['external_id'])) if x['external_id'] else None
    if existing:
     with connect() as c:c.execute("UPDATE refuels SET last_synced_at=?,sync_status='synced',sync_error=NULL WHERE id=?",(now,existing['id']))
     continue
    match=byfp.get(fp(m['local_vehicle_id'],x['refueled_at'],x['odometer'],x['liters'],x['total_cost']))
    if match:
     with connect() as c:c.execute("UPDATE refuels SET external_id=?,last_synced_at=?,sync_status='synced',sync_error=NULL WHERE id=?",(x['external_id'],now,match['id']))
     linked+=1;continue
    if not x['liters'] or not x['refueled_at']:errors+=1;continue
    price=x['price_per_liter'] or 0;total=x['total_cost'] or round(x['liters']*price,2)
    with connect() as c:c.execute("INSERT INTO refuels(vehicle_id,liters,price,total,refueled_at,odometer,price_per_liter,total_cost,tank_type,spritmonitor_fuel_code,station_brand,location,source,external_id,last_synced_at,sync_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'synced')",(m['local_vehicle_id'],x['liters'],price,total,x['refueled_at'],x['odometer'],price,total,x['tank_type'],x['spritmonitor_fuel_code'],x['station_brand'],x['location'],'spritmonitor_api',x['external_id'],now));inserted+=1
  except Exception as e:errors+=1;messages.append(f"{m['local_name']}: {e}")
 return {'vehicles':len(maps),'remote':remote_count,'linked':linked,'inserted':inserted,'errors':errors,'messages':messages}
async def sync(mode=None):
 mode=mode or config.SPRITMONITOR_SYNC_MODE;start=datetime.now(timezone.utc).isoformat();pushed=0
 with connect() as c:run=c.execute('INSERT INTO sync_runs(started_at,status,mode) VALUES(?,?,?)',(start,'running',mode)).lastrowid
 result=await pull_all()
 if mode in ('create_only','bidirectional'):
  for r in pending_rows():
   try:await push_one(r,r);pushed+=1
   except Exception as e:
    result['errors']+=1;result['messages'].append(f"Tankung {r['id']}: {e}")
    with connect() as c:c.execute("UPDATE refuels SET sync_status='sync_error',sync_error=? WHERE id=?",(str(e),r['id']))
 status='ok' if result['errors']==0 else 'warning';finish=datetime.now(timezone.utc).isoformat()
 with connect() as c:c.execute('UPDATE sync_runs SET finished_at=?,status=?,vehicles=?,remote_fuelings=?,linked=?,inserted=?,pushed=?,errors=?,message=? WHERE id=?',(finish,status,result['vehicles'],result['remote'],result['linked'],result['inserted'],pushed,result['errors'],' | '.join(result['messages']),run))
 return {**result,'pushed':pushed,'status':status}
