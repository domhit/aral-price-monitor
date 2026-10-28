import asyncio, re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .config import VERSION, POLL_INTERVAL
from .db import init_db, rows, connect
from .collector import collector_loop, collect_once

stop_event = asyncio.Event()
collector_task = None

@asynccontextmanager
async def lifespan(app):
    global collector_task
    init_db()
    stop_event.clear()
    collector_task = asyncio.create_task(collector_loop(stop_event))
    yield
    stop_event.set()
    if collector_task: await collector_task

app = FastAPI(title="Aral Price Monitor", version=VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def dashboard_data():
    states = rows("""SELECT s.name station_name,s.aral_station_id,s.address,f.name fuel_name,f.slug,ss.price,ss.price_changed_at,ss.retrieved_at
      FROM station_state ss JOIN stations s ON s.id=ss.station_id JOIN fuels f ON f.id=ss.fuel_id ORDER BY f.name,ss.price""")
    stations = rows("""SELECT s.*, group_concat(f.name, ', ') fuels FROM stations s LEFT JOIN station_fuels sf ON sf.station_id=s.id LEFT JOIN fuels f ON f.id=sf.fuel_id GROUP BY s.id ORDER BY s.name""")
    vehicles = rows("""SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id ORDER BY v.name""")
    last_run = rows("SELECT * FROM collector_runs ORDER BY id DESC LIMIT 1")
    return states, stations, vehicles, last_run[0] if last_run else None

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    states, stations, vehicles, last_run = dashboard_data()
    return templates.TemplateResponse("dashboard.html", {"request":request,"states":states,"stations":stations,"vehicles":vehicles,"last_run":last_run,"version":VERSION,"poll":POLL_INTERVAL})

@app.get("/stations", response_class=HTMLResponse)
def station_page(request: Request):
    stations = rows("""SELECT s.*,group_concat(f.name, ', ') fuels FROM stations s LEFT JOIN station_fuels sf ON sf.station_id=s.id LEFT JOIN fuels f ON f.id=sf.fuel_id GROUP BY s.id ORDER BY s.name""")
    fuels = rows("SELECT * FROM fuels ORDER BY name")
    return templates.TemplateResponse("stations.html", {"request":request,"stations":stations,"fuels":fuels,"version":VERSION})

@app.post("/stations")
def add_station(url: str=Form(...), name: str=Form(...), fuel_id: int=Form(...)):
    match = re.search(r"/(\d{8})/?(?:\?.*)?$", url.strip())
    if not match: return RedirectResponse("/stations?error=Die+Stations-ID+konnte+nicht+aus+der+URL+gelesen+werden", status_code=303)
    sid = match.group(1); now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        con.execute("INSERT INTO stations(aral_station_id,name,url,active,created_at) VALUES(?,?,?,1,?) ON CONFLICT(aral_station_id) DO UPDATE SET name=excluded.name,url=excluded.url,active=1", (sid,name.strip(),url.strip(),now))
        con.execute("INSERT OR IGNORE INTO station_fuels(station_id,fuel_id,active) SELECT id,?,1 FROM stations WHERE aral_station_id=?", (fuel_id,sid))
    return RedirectResponse("/stations", status_code=303)

@app.post("/stations/{station_id}/toggle")
def toggle_station(station_id: int):
    with connect() as con: con.execute("UPDATE stations SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (station_id,))
    return RedirectResponse("/stations", status_code=303)

@app.get("/vehicles", response_class=HTMLResponse)
def vehicle_page(request: Request):
    vehicles = rows("SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id ORDER BY v.name")
    fuels = rows("SELECT * FROM fuels ORDER BY name")
    return templates.TemplateResponse("vehicles.html", {"request":request,"vehicles":vehicles,"fuels":fuels,"version":VERSION})

@app.post("/vehicles")
def add_vehicle(name: str=Form(...), fuel_id: int=Form(...), consumption: float=Form(...), tank_capacity: str=Form(""), season_start: str=Form(...), season_end: str=Form(...)):
    tank = float(tank_capacity) if tank_capacity.strip() else None
    with connect() as con: con.execute("INSERT INTO vehicles(name,fuel_id,consumption,tank_capacity,season_start,season_end,active) VALUES(?,?,?,?,?,?,1)", (name.strip(),fuel_id,consumption,tank,season_start,season_end))
    return RedirectResponse("/vehicles", status_code=303)

@app.post("/collect")
async def collect_now():
    await collect_once(); return RedirectResponse("/", status_code=303)

@app.get("/health")
def health():
    last = rows("SELECT * FROM collector_runs ORDER BY id DESC LIMIT 1")
    return {"status":"ok","version":VERSION,"last_run":last[0] if last else None}
