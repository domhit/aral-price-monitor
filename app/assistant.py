from datetime import datetime,timezone
from . import config
from .db import connect,rows

async def refresh_tankerkoenig():
 if not config.TANKERKOENIG_ENABLED:return 0,[]
 fuels={str(v['price_fuel'] or '').lower() for v in rows("SELECT price_fuel FROM vehicles WHERE active=1 AND price_source='tankerkoenig'")};aliases={'super_e10':'e10','supere10':'e10','super_e5':'e5','supere5':'e5'};fuels={aliases.get(f,f) for f in fuels if f};ok=0;errors=[]
 from .tankerkoenig import search
 for fuel in sorted(fuels):
  if fuel not in ('e5','e10','diesel'):continue
  try:await search(fuel,config.TANKERKOENIG_LAT,config.TANKERKOENIG_LNG,config.TANKERKOENIG_RADIUS);ok+=1
  except Exception as e:errors.append(f'{fuel}: {e}')
 return ok,errors

async def run_assistant():
 start=datetime.now(timezone.utc).isoformat();errors=[]
 with connect() as c:rid=c.execute("INSERT INTO assistant_runs(started_at) VALUES(?)",(start,)).lastrowid
 tk_ok,te=await refresh_tankerkoenig();errors.extend(te)
 try:
  from .vehicle_prices import all_vehicle_prices
  items=await all_vehicle_prices(config.TANKERKOENIG_LAT,config.TANKERKOENIG_LNG)
  from .mqtt import publish_vehicle_assistant
  for x in items:
   try:publish_vehicle_assistant(x)
   except Exception as e:errors.append(f"MQTT {x.get('name')}: {e}")
 except Exception as e:items=[];errors.append(str(e))
 status='ok' if not errors else 'warning';finish=datetime.now(timezone.utc).isoformat()
 with connect() as c:c.execute('UPDATE assistant_runs SET finished_at=?,status=?,tk_ok=?,vehicles=?,errors=?,message=? WHERE id=?',(finish,status,tk_ok,len(items),len(errors),' | '.join(errors),rid))
 return {'status':status,'tk_ok':tk_ok,'vehicles':len(items),'errors':errors,'items':items}
