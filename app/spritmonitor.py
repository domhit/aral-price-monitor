import base64,csv,hashlib,io,re
from datetime import datetime
from .db import connect
MAP={'datum':'refueled_at','km stand':'odometer','teil km':'trip_km','spritmenge':'liters','kosten':'total_cost','wahrung':'currency','tankart':'tank_type','reifen':'tire_code','strecken':'route_code','fahrweise':'driving_style_code','kraftstoff':'spritmonitor_fuel_code','bemerkung':'note','verbrauch':'reported_consumption','bc verbrauch':'bc_consumption','bc spritmenge':'bc_fuel_quantity','bc geschwindigkeit':'bc_speed','tankstelle':'station_brand','land':'country','grossraum':'region','ort':'location','breitengrad':'latitude','langengrad':'longitude'}
def k(s):return re.sub(r'[^a-z0-9]+',' ',str(s).lower().translate(str.maketrans('äöüß','aous'))).strip()
def n(v):
 s=str(v or '').strip().replace(' ','').replace('€','');
 if not s:return None
 s=s.replace('.','').replace(',','.') if ',' in s else s
 s=re.sub(r'[^0-9.\-]','',s);return float(s) if s else None
def dt(v):
 for f in ('%d.%m.%Y','%d.%m.%Y %H:%M','%Y-%m-%d'):
  try:return datetime.strptime(str(v).strip(),f).isoformat(timespec='minutes')
  except ValueError:pass
 raise ValueError('Datum ungültig: '+str(v))
def parse(raw):
 text=None;enc=''
 for e in ('utf-8-sig','utf-8','cp1252','iso-8859-1'):
  try:text=raw.decode(e);enc=e;break
  except UnicodeDecodeError:pass
 d=csv.Sniffer().sniff(text[:10000],delimiters=';,\t|');r=csv.DictReader(io.StringIO(text),dialect=d);mp={MAP[k(h)]:h for h in r.fieldnames if k(h) in MAP};items=[];errors=[]
 for line,row in enumerate(r,2):
  try:
   x={f:(n(row[h]) if f not in ('refueled_at','currency','note','station_brand','country','region','location') else str(row[h] or '').strip()) for f,h in mp.items()};x['refueled_at']=dt(x['refueled_at']);x['tank_type']=int(x.get('tank_type') or 0);x['price_per_liter']=round(x['total_cost']/x['liters'],4);x['currency']=x.get('currency') or 'EUR';sig=f"{x['refueled_at']}|{x.get('odometer')}|{x['liters']}|{x['total_cost']}";x['import_key']='spritmonitor:'+hashlib.sha256(sig.encode()).hexdigest()[:32];items.append(x)
  except Exception as e:errors.append({'line':line,'error':str(e)})
 return {'items':items,'errors':errors,'mapping':mp,'encoding':enc,'delimiter':d.delimiter}
def encode(raw):return base64.b64encode(raw).decode()
def decode_token(s):return base64.b64decode(s)
def import_csv(vehicle_id,raw):
 p=parse(raw);i=d=0;fields=['refueled_at','odometer','trip_km','liters','price_per_liter','total_cost','currency','tank_type','tire_code','route_code','driving_style_code','spritmonitor_fuel_code','note','reported_consumption','bc_consumption','bc_fuel_quantity','bc_speed','station_brand','country','region','location','latitude','longitude']
 with connect() as c:
  known={r['import_key'] for r in c.execute('select import_key from refuels where import_key is not null')}
  for x in p['items']:
   if x['import_key'] in known:d+=1;continue
   vals=[x.get(f) for f in fields];c.execute(f"insert into refuels(vehicle_id,{','.join(fields)},price,total,source,import_key,sync_status) values(?{',?'*(len(fields)+5)})",[vehicle_id,*vals,x['price_per_liter'],x['total_cost'],'spritmonitor_csv',x['import_key'],'imported']);i+=1
 return i,d,len(p['errors'])
