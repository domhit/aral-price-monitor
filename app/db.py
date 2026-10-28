import sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone
from .config import DB_PATH
SCHEMA="""
PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS fuels(id INTEGER PRIMARY KEY AUTOINCREMENT,aral_fuel_id TEXT NOT NULL UNIQUE,name TEXT NOT NULL,slug TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS stations(id INTEGER PRIMARY KEY AUTOINCREMENT,aral_station_id TEXT NOT NULL UNIQUE,name TEXT NOT NULL,address TEXT NOT NULL DEFAULT '',url TEXT NOT NULL DEFAULT '',active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS station_fuels(station_id INTEGER NOT NULL,fuel_id INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(station_id,fuel_id),FOREIGN KEY(station_id) REFERENCES stations(id) ON DELETE CASCADE,FOREIGN KEY(fuel_id) REFERENCES fuels(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,fuel_id INTEGER NOT NULL,consumption REAL NOT NULL,tank_capacity REAL,season_start TEXT NOT NULL,season_end TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,FOREIGN KEY(fuel_id) REFERENCES fuels(id));
CREATE TABLE IF NOT EXISTS price_events(id INTEGER PRIMARY KEY AUTOINCREMENT,station_id INTEGER NOT NULL,fuel_id INTEGER NOT NULL,price REAL NOT NULL,price_changed_at TEXT NOT NULL,retrieved_at TEXT NOT NULL,UNIQUE(station_id,fuel_id,price_changed_at),FOREIGN KEY(station_id) REFERENCES stations(id) ON DELETE CASCADE,FOREIGN KEY(fuel_id) REFERENCES fuels(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_price_events_lookup ON price_events(fuel_id,station_id,price_changed_at);
CREATE TABLE IF NOT EXISTS station_state(station_id INTEGER NOT NULL,fuel_id INTEGER NOT NULL,price REAL NOT NULL,price_changed_at TEXT NOT NULL,retrieved_at TEXT NOT NULL,PRIMARY KEY(station_id,fuel_id),FOREIGN KEY(station_id) REFERENCES stations(id) ON DELETE CASCADE,FOREIGN KEY(fuel_id) REFERENCES fuels(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS collector_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,started_at TEXT NOT NULL,finished_at TEXT,ok_count INTEGER NOT NULL DEFAULT 0,error_count INTEGER NOT NULL DEFAULT 0,message TEXT NOT NULL DEFAULT '');
"""
@contextmanager
def connect():
 c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON")
 try: yield c; c.commit()
 finally: c.close()
def rows(q,p=()):
 with connect() as c:return [dict(x) for x in c.execute(q,p).fetchall()]
def init_db():
 with connect() as c:c.executescript(SCHEMA);seed(c)
 migrate_v03()
 migrate_v04()
def seed(c):
 fuels=[("F00125","Aral Ultimate 102","ultimate_102"),("F00114","Aral SuperPlus","superplus_98"),("F00400","Aral Diesel","diesel"),("F00426","Aral Ultimate Diesel","ultimate_diesel"),("F00104","Aral Super E5","super_e5"),("F00113","Aral Super 95 E10","super_e10")]
 c.executemany("INSERT OR IGNORE INTO fuels(aral_fuel_id,name,slug) VALUES(?,?,?)",fuels)
 now=datetime.now(timezone.utc).isoformat()
 stations=[("12141800","Neunkirchen Königstraße","Königstraße 32, 66538 Neunkirchen","https://tankstelle.aral.de/neunkirchen/koenigstrasse-32/12141800","F00125"),("28423400","St. Ingbert Saarbrücker Straße","Saarbrücker Straße 6a, St. Ingbert","https://tankstelle.aral.de/st-ingbert/saarbruecker-strasse-6-a/28423400","F00125"),("28409400","Spiesen-Elversberg Lindenstraße 14","Lindenstraße 14, Spiesen-Elversberg","https://tankstelle.aral.de/spiesen-elversberg/lindenstrasse-14/28409400","F00125"),("18052100","St. Wendel Mommstraße","Mommstraße 1a, St. Wendel","https://tankstelle.aral.de/st-wendel/mommstrasse-1-a/18052100","F00125"),("28416400","Schiffweiler Kreisstraße","Kreisstraße 26, Schiffweiler","https://tankstelle.aral.de/schiffweiler/kreisstrasse-26/28416400","F00114"),("18056700","Spiesen-Elversberg Lindenstraße 7","Lindenstraße 7, Spiesen-Elversberg","https://tankstelle.aral.de/spiesen-elversberg/lindenstrasse-7/18056700","F00114"),("28414400","Homburg Saarbrücker Straße","Saarbrücker Straße 100, Homburg","https://tankstelle.aral.de/homburg/saarbruecker-strasse-100/28414400","F00114")]
 for sid,n,a,u,f in stations:
  c.execute("INSERT OR IGNORE INTO stations(aral_station_id,name,address,url,active,created_at) VALUES(?,?,?,?,1,?)",(sid,n,a,u,now))
  c.execute("INSERT OR IGNORE INTO station_fuels(station_id,fuel_id,active) SELECT s.id,f.id,1 FROM stations s,fuels f WHERE s.aral_station_id=? AND f.aral_fuel_id=?",(sid,f))
 for n,f,co,ss,se in [("Audi RS3","F00125",11.7,"04-01","10-31"),("Audi S3","F00114",10.1,"11-01","03-31")]:
  if not c.execute("SELECT 1 FROM vehicles WHERE name=?",(n,)).fetchone():c.execute("INSERT INTO vehicles(name,fuel_id,consumption,tank_capacity,season_start,season_end,active) SELECT ?,id,?,NULL,?,?,1 FROM fuels WHERE aral_fuel_id=?",(n,co,ss,se,f))

def migrate_v03():
    with connect() as c:
        cols={r['name'] for r in c.execute('PRAGMA table_info(stations)').fetchall()}
        if 'distance_km' not in cols:c.execute('ALTER TABLE stations ADD COLUMN distance_km REAL')
        if 'extra_distance_km' not in cols:c.execute('ALTER TABLE stations ADD COLUMN extra_distance_km REAL NOT NULL DEFAULT 0')
        c.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        defaults={'analysis_days':'30','max_remaining_ct':'1.0','okay_remaining_ct':'2.0'}
        for k,v in defaults.items():c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))

def migrate_v04():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        c.execute('''CREATE TABLE IF NOT EXISTS refuels(id INTEGER PRIMARY KEY AUTOINCREMENT,vehicle_id INTEGER NOT NULL,station_id INTEGER,liters REAL NOT NULL,price REAL NOT NULL,total REAL NOT NULL,refueled_at TEXT NOT NULL,odometer REAL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,FOREIGN KEY(station_id) REFERENCES stations(id) ON DELETE SET NULL)''')
