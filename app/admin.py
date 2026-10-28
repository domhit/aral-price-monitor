import csv, io, os, sqlite3, tempfile, yaml
from datetime import datetime, timezone
from .config import DB_PATH
from .db import connect, rows

def get_settings():
    defaults={'analysis_days':'30','now_threshold_ct':'1.0','okay_threshold_ct':'2.0','wait_threshold_ct':'4.0','min_days':'7'}
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        for k,v in defaults.items():c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))
        return {r['key']:r['value'] for r in c.execute('SELECT key,value FROM settings')}

def save_settings(values):
    with connect() as c:
        for k,v in values.items():c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,str(v)))

def db_stats():
    size=os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    with connect() as c:
        events=c.execute('SELECT COUNT(*) n,MIN(price_changed_at) oldest,MAX(price_changed_at) newest FROM price_events').fetchone()
        return {'size_bytes':size,'events':events['n'],'oldest':events['oldest'],'newest':events['newest'],'stations':c.execute('SELECT COUNT(*) n FROM stations').fetchone()['n'],'vehicles':c.execute('SELECT COUNT(*) n FROM vehicles').fetchone()['n']}

def make_backup(path):
    src=sqlite3.connect(DB_PATH); dst=sqlite3.connect(path)
    try: src.backup(dst)
    finally: dst.close();src.close()

def check_database(path):
    c=sqlite3.connect(path)
    try:
        integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required={'stations','fuels','vehicles','price_events','station_state'}
        return integrity=='ok' and required.issubset(tables),integrity,tables
    finally:c.close()

def export_config():
    data={'version':1,'exported_at':datetime.now(timezone.utc).isoformat(),'settings':get_settings(),'stations':rows('''SELECT s.aral_station_id,s.name,s.address,s.url,s.active,s.extra_distance_km,f.aral_fuel_id fuel FROM stations s LEFT JOIN station_fuels sf ON sf.station_id=s.id LEFT JOIN fuels f ON f.id=sf.fuel_id ORDER BY s.name'''),'vehicles':rows('''SELECT v.name,f.aral_fuel_id fuel,v.consumption,v.tank_capacity,v.season_start,v.season_end,v.active FROM vehicles v JOIN fuels f ON f.id=v.fuel_id ORDER BY v.name''')}
    return yaml.safe_dump(data,allow_unicode=True,sort_keys=False)

def import_config(text):
    d=yaml.safe_load(text)
    if not isinstance(d,dict) or 'stations' not in d:raise ValueError('Ungültige Konfigurationsdatei')
    with connect() as c:
        now=datetime.now(timezone.utc).isoformat()
        for s in d.get('stations',[]):
            fuel=c.execute('SELECT id FROM fuels WHERE aral_fuel_id=?',(s['fuel'],)).fetchone()
            if not fuel:continue
            c.execute('''INSERT INTO stations(aral_station_id,name,address,url,active,created_at,extra_distance_km) VALUES(?,?,?,?,?,?,?) ON CONFLICT(aral_station_id) DO UPDATE SET name=excluded.name,address=excluded.address,url=excluded.url,active=excluded.active,extra_distance_km=excluded.extra_distance_km''',(s['aral_station_id'],s['name'],s.get('address',''),s.get('url',''),int(s.get('active',1)),now,float(s.get('extra_distance_km') or 0)))
            sid=c.execute('SELECT id FROM stations WHERE aral_station_id=?',(s['aral_station_id'],)).fetchone()['id'];c.execute('DELETE FROM station_fuels WHERE station_id=?',(sid,));c.execute('INSERT INTO station_fuels(station_id,fuel_id,active) VALUES(?,?,1)',(sid,fuel['id']))
        for v in d.get('vehicles',[]):
            fuel=c.execute('SELECT id FROM fuels WHERE aral_fuel_id=?',(v['fuel'],)).fetchone()
            if not fuel:continue
            old=c.execute('SELECT id FROM vehicles WHERE name=?',(v['name'],)).fetchone()
            vals=(fuel['id'],float(v['consumption']),v.get('tank_capacity'),v['season_start'],v['season_end'],int(v.get('active',1)))
            if old:c.execute('UPDATE vehicles SET fuel_id=?,consumption=?,tank_capacity=?,season_start=?,season_end=?,active=? WHERE id=?',(*vals,old['id']))
            else:c.execute('INSERT INTO vehicles(name,fuel_id,consumption,tank_capacity,season_start,season_end,active) VALUES(?,?,?,?,?,?,?)',(v['name'],*vals))
    if d.get('settings'):save_settings(d['settings'])

def csv_history(days=30,fuel_id=None,station_id=None):
    clauses=["datetime(pe.price_changed_at) >= datetime('now', ?)"]; params=[f'-{int(days)} days']
    if fuel_id:clauses.append('f.id=?');params.append(fuel_id)
    if station_id:clauses.append('s.id=?');params.append(station_id)
    q='''SELECT s.name station,s.aral_station_id station_id,f.name fuel,f.aral_fuel_id fuel_id,pe.price,pe.price_changed_at,pe.retrieved_at FROM price_events pe JOIN stations s ON s.id=pe.station_id JOIN fuels f ON f.id=pe.fuel_id WHERE '''+' AND '.join(clauses)+' ORDER BY pe.price_changed_at'
    out=io.StringIO();w=csv.writer(out,delimiter=';');w.writerow(['station','station_id','fuel','fuel_id','price','price_changed_at','retrieved_at'])
    for r in rows(q,tuple(params)):w.writerow([r[k] for k in ['station','station_id','fuel','fuel_id','price','price_changed_at','retrieved_at']])
    return out.getvalue()

def add_refuel(vehicle_id,station_id,liters,price,refueled_at,odometer=None):
    total=round(liters*price,2)
    with connect() as c:c.execute('INSERT INTO refuels(vehicle_id,station_id,liters,price,total,refueled_at,odometer) VALUES(?,?,?,?,?,?,?)',(vehicle_id,station_id,liters,price,total,refueled_at,odometer))
