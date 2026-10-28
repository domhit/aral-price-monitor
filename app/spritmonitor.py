import base64,csv,hashlib,io,re
from datetime import datetime
from .db import connect

COLUMNS={'datum':'refueled_at','km stand':'odometer','teil km':'trip_km','spritmenge':'liters','kosten':'total_cost','wahrung':'currency','tankart':'tank_type','reifen':'tire_code','strecken':'route_code','fahrweise':'driving_style_code','kraftstoff':'spritmonitor_fuel_code','bemerkung':'note','verbrauch':'reported_consumption','bc verbrauch':'bc_consumption','bc spritmenge':'bc_fuel_quantity','bc geschwindigkeit':'bc_speed','tankstelle':'station_brand','land':'country','grossraum':'region','ort':'location','breitengrad':'latitude','langengrad':'longitude'}
def ck(s):return re.sub(r'[^a-z0-9]+',' ',str(s).lower().replace('ä','a').replace('ö','o').replace('ü','u').replace('ß','ss')).strip()
def num(v):
 s=str(v or '').strip().replace('\u00a0','').replace('€','').replace(' ','')
 if not s:return None
 if ',' in s and '.' in s:s=s.replace('.','').replace(',','.') if s.rfind(',')>s.rfind('.') else s.replace(',','')
 else:s=s.replace(',','.')
 s=re.sub(r'[^0-9.\-]','',s);return float(s) if s else None
def integer(v):
 n=num(v);return int(n) if n is not None else None
def dateval(v):
 s=str(v or '').strip()
 for f in ('%d.%m.%Y','%d.%m.%Y %H:%M','%Y-%m-%d','%Y-%m-%d %H:%M:%S'):
  try:return datetime.strptime(s,f).isoformat(timespec='minutes')
  except ValueError:pass
 raise ValueError('Unbekanntes Datum: '+s)
def decode(raw):
 for enc in ('utf-8-sig','utf-8','cp1252','iso-8859-1'):
  try:return raw.decode(enc),enc
  except UnicodeDecodeError:pass
 raise ValueError('CSV-Kodierung nicht unterstützt')
def dialect(text):
 try:return csv.Sniffer().sniff(text[:10000],delimiters=';,\t|')
 except csv.Error:
  class D(csv.excel):delimiter=';'
  return D
def parse(raw):
 text,enc=decode(raw);d=dialect(text);r=csv.DictReader(io.StringIO(text),dialect=d)
 if not r.fieldnames:raise ValueError('Keine Kopfzeile')
 mp={COLUMNS[ck(h)]:h for h in r.fieldnames if ck(h) in COLUMNS}
 miss={'refueled_at','odometer','liters','total_cost'}-set(mp)
 if miss:raise ValueError('Pflichtspalten fehlen: '+', '.join(sorted(miss))+'; Kopfzeile: '+', '.join(r.fieldnames))
 numeric={'odometer','trip_km','liters','total_cost','reported_consumption','bc_consumption','bc_fuel_quantity','bc_speed','latitude','longitude'}
 codes={'tank_type','tire_code','route_code','driving_style_code','spritmonitor_fuel_code'}
 items=[];errors=[]
 for line,row in enumerate(r,2):
  if not any(str(v or '').strip() for v in row.values()):continue
  try:
   x={}
   for target,header in mp.items():
    value=row.get(header)
    x[target]=num(value) if target in numeric else integer(value) if target in codes else str(value or '').strip()
   x['refueled_at']=dateval(row[mp['refueled_at']]); liters=x['liters'];total=x['total_cost']
   if not liters or liters<=0:raise ValueError('Spritmenge fehlt/ungültig')
   if total is None:raise ValueError('Kosten fehlen')
   x['price_per_liter']=round(total/liters,4);x['currency']=x.get('currency') or 'EUR'
   if x.get('tank_type') not in (0,1,2,3):raise ValueError('Tankart muss 0, 1, 2 oder 3 sein')
   sig=f"{x['refueled_at']}|{x.get('odometer')}|{liters:.3f}|{total:.2f}"
   x['import_key']='spritmonitor:'+hashlib.sha256(sig.encode()).hexdigest()[:32];items.append(x)
  except Exception as e:errors.append({'line':line,'error':str(e)})
 return {'items':items,'errors':errors,'headers':r.fieldnames,'mapping':mp,'encoding':enc,'delimiter':d.delimiter}
def encode(raw):return base64.b64encode(raw).decode()
def decode_token(s):return base64.b64decode(s.encode(),validate=True)
def import_csv(vehicle_id,raw):
 p=parse(raw);inserted=duplicates=0
 fields=['refueled_at','odometer','trip_km','liters','price_per_liter','total_cost','currency','tank_type','tire_code','route_code','driving_style_code','spritmonitor_fuel_code','note','reported_consumption','bc_consumption','bc_fuel_quantity','bc_speed','station_brand','country','region','location','latitude','longitude']
 with connect() as c:
  known={r['import_key'] for r in c.execute('SELECT import_key FROM refuels WHERE import_key IS NOT NULL')}
  for x in p['items']:
   if x['import_key'] in known:duplicates+=1;continue
   vals=[x.get(f) for f in fields]
   c.execute(f"INSERT INTO refuels(vehicle_id,{','.join(fields)},price,total,source,import_key) VALUES(?{',?'*(len(fields)+4)})",[vehicle_id,*vals,x['price_per_liter'],x['total_cost'],'spritmonitor_csv',x['import_key']])
   inserted+=1;known.add(x['import_key'])
 return inserted,duplicates,len(p['errors'])
