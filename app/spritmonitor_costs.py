import base64,csv,hashlib,io,re
from datetime import datetime
from .db import connect

COST_TYPES={1:'Wartung',2:'Reparatur',3:'Reifenwechsel',4:'Ölwechsel',5:'Versicherung',6:'Steuer',7:'HU/AU (TÜV)',8:'Tuning',9:'Zubehör',10:'Kaufpreis',11:'Sonstiges',12:'Wagenpflege',13:'Leasingrate',14:'Zulassung/Ummeldung',15:'Finanzierungsrate',16:'Erstattung',17:'Bußgeld',18:'Parkgebühr',19:'Maut',20:'Ersatzteile',21:'Ladegrundgebühr',22:'Digitale Dienste',23:'THG-Prämie'}
TYPE_BY_NAME={re.sub(r'[^a-z0-9]+','',v.lower().replace('ä','a').replace('ö','o').replace('ü','u').replace('ß','ss')):k for k,v in COST_TYPES.items()}
def key(v):return re.sub(r'[^a-z0-9]+',' ',str(v).lower().replace('ä','a').replace('ö','o').replace('ü','u').replace('ß','ss')).strip()
def number(v):
 s=str(v or '').strip().replace('\u00a0','').replace('€','').replace(' ','')
 if not s:return None
 if ',' in s and '.' in s:s=s.replace('.','').replace(',','.') if s.rfind(',')>s.rfind('.') else s.replace(',','')
 else:s=s.replace(',','.')
 s=re.sub(r'[^0-9.\-]','',s);return float(s) if s else None
def dateval(v):
 s=str(v or '').strip()
 for f in ('%d.%m.%Y','%Y-%m-%d'):
  try:return datetime.strptime(s,f).date().isoformat()
  except ValueError:pass
 raise ValueError('Unbekanntes Datum: '+s)
def decode(raw):
 for enc in ('utf-8-sig','utf-8','cp1252','iso-8859-1'):
  try:return raw.decode(enc),enc
  except UnicodeDecodeError:pass
 raise ValueError('CSV-Kodierung nicht unterstützt')
def get_dialect(text):
 try:return csv.Sniffer().sniff(text[:10000],delimiters=';,\t|')
 except csv.Error:
  class D(csv.excel):delimiter=';'
  return D
def cost_code(value):
 s=str(value or '').strip();n=number(s)
 if n is not None and int(n) in COST_TYPES:return int(n)
 normalized=re.sub(r'[^a-z0-9]+','',s.lower().replace('ä','a').replace('ö','o').replace('ü','u').replace('ß','ss'))
 if normalized in TYPE_BY_NAME:return TYPE_BY_NAME[normalized]
 raise ValueError('Unbekannte Kostenart: '+s)
def parse(raw):
 text,enc=decode(raw);d=get_dialect(text);reader=csv.DictReader(io.StringIO(text),dialect=d)
 if not reader.fieldnames:raise ValueError('Keine Kopfzeile')
 aliases={'datum':'cost_date','km stand':'odometer','tachostand':'odometer','distanz':'distance_km','kostenart':'cost_type_code','gesamtkosten':'total_cost','kosten':'total_cost','wahrung':'currency','bemerkung':'note','wiederholung':'recurrence_months','id':'external_id'}
 mapping={aliases[key(h)]:h for h in reader.fieldnames if key(h) in aliases}
 missing={'cost_date','cost_type_code','total_cost'}-set(mapping)
 if missing:raise ValueError('Pflichtspalten fehlen: '+', '.join(sorted(missing))+'; Kopfzeile: '+', '.join(reader.fieldnames))
 items=[];errors=[]
 for line,row in enumerate(reader,2):
  if not any(str(v or '').strip() for v in row.values()):continue
  try:
   x={'cost_date':dateval(row[mapping['cost_date']]),'odometer':number(row.get(mapping.get('odometer',''))),'distance_km':number(row.get(mapping.get('distance_km',''))),'cost_type_code':cost_code(row[mapping['cost_type_code']]),'total_cost':number(row[mapping['total_cost']]),'currency':str(row.get(mapping.get('currency',''),'EUR') or 'EUR').strip(),'note':str(row.get(mapping.get('note',''),'') or '').strip(),'recurrence_months':int(number(row.get(mapping.get('recurrence_months',''))) or 0),'external_id':str(row.get(mapping.get('external_id',''),'') or '').strip() or None}
   if x['total_cost'] is None:raise ValueError('Gesamtkosten fehlen')
   sig=f"{x['cost_date']}|{x.get('odometer')}|{x['cost_type_code']}|{x['total_cost']:.2f}|{x['note']}"
   x['import_key']='spritmonitor-cost:'+hashlib.sha256(sig.encode()).hexdigest()[:32];x['cost_type_name']=COST_TYPES[x['cost_type_code']];items.append(x)
  except Exception as e:errors.append({'line':line,'error':str(e)})
 return {'items':items,'errors':errors,'mapping':mapping,'encoding':enc,'delimiter':d.delimiter}
def encode(raw):return base64.b64encode(raw).decode()
def decode_token(s):return base64.b64decode(s.encode(),validate=True)
def import_csv(vehicle_id,raw):
 p=parse(raw);inserted=duplicates=0
 with connect() as c:
  known={r['import_key'] for r in c.execute('SELECT import_key FROM vehicle_costs WHERE import_key IS NOT NULL')}
  for x in p['items']:
   if x['import_key'] in known:duplicates+=1;continue
   c.execute('''INSERT INTO vehicle_costs(vehicle_id,cost_date,odometer,distance_km,cost_type_code,total_cost,currency,note,recurrence_months,source,external_id,import_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(vehicle_id,x['cost_date'],x['odometer'],x['distance_km'],x['cost_type_code'],x['total_cost'],x['currency'],x['note'],x['recurrence_months'],'spritmonitor_csv',x['external_id'],x['import_key']))
   known.add(x['import_key']);inserted+=1
 return inserted,duplicates,len(p['errors'])
