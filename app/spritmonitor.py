import base64, csv, hashlib, io, re
from datetime import datetime
from .db import connect

ALIASES={
 'date':['datum','date','zeitpunkt','timestamp'],
 'odometer':['kilometerstand','km stand','odometer','mileage','km'],
 'liters':['liter','litres','liters','menge','quantity','fuel quantity'],
 'price':['preis/l','preis pro liter','literpreis','price/l','price per unit','price'],
 'total':['gesamtpreis','kosten','betrag','total price','total cost','cost'],
 'full':['vollgetankt','volltankung','full tank','full'],
 'partial':['teilbetankung','partial tank','partial'],
 'station':['tankstelle','station','place'],
 'note':['notiz','bemerkung','kommentar','note','comment'],
 'external_id':['id','betankungs-id','fueling id','entry id'],
}

def clean(v): return re.sub(r'[^a-z0-9äöüß]+',' ',str(v).strip().lower()).strip()
def norm_number(v):
 s=str(v or '').strip().replace('\u00a0','').replace('€','').replace(' ','')
 if not s:return None
 if ',' in s and '.' in s:
  if s.rfind(',')>s.rfind('.'):s=s.replace('.','').replace(',','.')
  else:s=s.replace(',','')
 else:s=s.replace(',','.')
 return float(re.sub(r'[^0-9.\-]','',s))
def norm_bool(v): return clean(v) in {'1','ja','yes','true','x','voll','full'}
def decode(raw):
 for enc in ('utf-8-sig','utf-8','cp1252','iso-8859-1'):
  try:return raw.decode(enc),enc
  except UnicodeDecodeError:pass
 raise ValueError('Zeichencodierung der CSV wird nicht unterstützt')
def sniff(text):
 sample=text[:10000]
 try:return csv.Sniffer().sniff(sample,delimiters=';,\t|')
 except csv.Error:
  class D(csv.excel):delimiter=';'
  return D
def mapping(headers):
 result={}; clean_headers={clean(h):h for h in headers}
 for target,names in ALIASES.items():
  for n in names:
   if clean(n) in clean_headers:result[target]=clean_headers[clean(n)];break
 return result
def parse_date(v):
 s=str(v or '').strip()
 for fmt in ('%d.%m.%Y %H:%M','%d.%m.%Y','%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M','%Y-%m-%d','%d/%m/%Y'):
  try:return datetime.strptime(s,fmt).isoformat(timespec='minutes')
  except ValueError:pass
 try:return datetime.fromisoformat(s.replace('Z','+00:00')).isoformat()
 except ValueError:raise ValueError(f'Unbekanntes Datum: {s}')
def preview(raw):
 text,encoding=decode(raw);dialect=sniff(text);reader=csv.DictReader(io.StringIO(text),dialect=dialect)
 if not reader.fieldnames:raise ValueError('CSV enthält keine Kopfzeile')
 mp=mapping(reader.fieldnames);required={'date','odometer','liters'}
 missing=required-set(mp)
 if missing:raise ValueError('Pflichtspalten nicht erkannt: '+', '.join(sorted(missing))+'. Erkannte Kopfzeile: '+', '.join(reader.fieldnames))
 items=[];errors=[]
 for no,row in enumerate(reader,2):
  if not any(str(x or '').strip() for x in row.values()):continue
  try:
   liters=norm_number(row.get(mp['liters'])); odo=norm_number(row.get(mp['odometer'])); price=norm_number(row.get(mp.get('price','')));total=norm_number(row.get(mp.get('total','')))
   if not liters or liters<=0:raise ValueError('Liter fehlt oder ist 0')
   if price is None and total is not None:price=total/liters
   if total is None and price is not None:total=liters*price
   if price is None:raise ValueError('Weder Literpreis noch Gesamtpreis vorhanden')
   date=parse_date(row.get(mp['date']))
   ext=str(row.get(mp.get('external_id',''),'') or '').strip()
   key='spritmonitor:'+ (ext if ext else hashlib.sha256(f'{date}|{odo}|{liters:.3f}|{price:.4f}'.encode()).hexdigest()[:24])
   items.append({'date':date,'odometer':odo,'liters':round(liters,3),'price':round(price,4),'total':round(total,2),'full_tank':norm_bool(row.get(mp.get('full',''))),'partial_tank':norm_bool(row.get(mp.get('partial',''))),'station':str(row.get(mp.get('station',''),'') or '').strip(),'note':str(row.get(mp.get('note',''),'') or '').strip(),'external_id':ext or None,'import_key':key})
  except Exception as e:errors.append({'line':no,'error':str(e)})
 return {'items':items,'errors':errors,'headers':reader.fieldnames,'mapping':mp,'encoding':encoding,'delimiter':dialect.delimiter}
def encode(raw):return base64.b64encode(raw).decode('ascii')
def decode_token(token):return base64.b64decode(token.encode('ascii'),validate=True)
def import_items(vehicle_id,raw):
 p=preview(raw);inserted=duplicates=0
 with connect() as c:
  existing={r['import_key'] for r in c.execute("SELECT import_key FROM refuels WHERE import_key IS NOT NULL")}
  for x in p['items']:
   if x['import_key'] in existing:duplicates+=1;continue
   station_id=None
   if x['station']:
    r=c.execute('SELECT id FROM stations WHERE lower(name) LIKE ? LIMIT 1',(f"%{x['station'].lower()}%",)).fetchone();station_id=r['id'] if r else None
   c.execute('''INSERT INTO refuels(vehicle_id,station_id,liters,price,total,refueled_at,odometer,full_tank,partial_tank,note,source,external_id,import_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(vehicle_id,station_id,x['liters'],x['price'],x['total'],x['date'],x['odometer'],int(x['full_tank']),int(x['partial_tank']),x['note'],'spritmonitor_csv',x['external_id'],x['import_key']))
   inserted+=1;existing.add(x['import_key'])
 return inserted,duplicates,len(p['errors'])
