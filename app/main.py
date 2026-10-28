import asyncio,re
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from fastapi import FastAPI,Request,Form,HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .config import VERSION,POLL_INTERVAL
from .db import init_db,rows,connect
from .collector import collector_loop,collect_once
from .analytics import history_payload
stop=asyncio.Event();task=None
@asynccontextmanager
async def lifespan(app):
 global task
 init_db();stop.clear();task=asyncio.create_task(collector_loop(stop));yield;stop.set()
 if task:await task
app=FastAPI(title="Aral Price Monitor",version=VERSION,lifespan=lifespan);app.mount("/static",StaticFiles(directory="app/static"),name="static");tpl=Jinja2Templates(directory="app/templates")
def common():return {"version":VERSION}
@app.get("/",response_class=HTMLResponse)
def dashboard(request:Request):
 states=rows("SELECT s.name station_name,s.address,f.name fuel_name,f.slug,ss.price,ss.price_changed_at FROM station_state ss JOIN stations s ON s.id=ss.station_id JOIN fuels f ON f.id=ss.fuel_id ORDER BY f.name,ss.price")
 last=rows("SELECT * FROM collector_runs ORDER BY id DESC LIMIT 1")
 return tpl.TemplateResponse("dashboard.html",{"request":request,"states":states,"last_run":last[0] if last else None,"poll":POLL_INTERVAL,**common()})
@app.get("/charts",response_class=HTMLResponse)
def charts(request:Request):
 fuels=rows("SELECT DISTINCT f.* FROM fuels f JOIN station_fuels sf ON sf.fuel_id=f.id WHERE sf.active=1 ORDER BY f.name")
 return tpl.TemplateResponse("charts.html",{"request":request,"fuels":fuels,**common()})
@app.get("/api/history/{slug}")
def api_history(slug:str,days:int=30):
 p=history_payload(slug,max(1,min(days,90)))
 if not p:raise HTTPException(404,"Kraftstoff nicht gefunden")
 return p
@app.get("/stations",response_class=HTMLResponse)
def stations_page(request:Request,edit:int|None=None):
 st=rows("SELECT s.*,GROUP_CONCAT(f.name,', ') fuels FROM stations s LEFT JOIN station_fuels sf ON sf.station_id=s.id LEFT JOIN fuels f ON f.id=sf.fuel_id GROUP BY s.id ORDER BY s.name");fuels=rows("SELECT * FROM fuels ORDER BY name");editing=rows("SELECT s.*,sf.fuel_id FROM stations s LEFT JOIN station_fuels sf ON sf.station_id=s.id WHERE s.id=?",(edit,))[0] if edit and rows("SELECT 1 FROM stations WHERE id=?",(edit,)) else None
 return tpl.TemplateResponse("stations.html",{"request":request,"stations":st,"fuels":fuels,"editing":editing,**common()})
@app.post("/stations/save")
def save_station(id:str=Form(""),url:str=Form(...),name:str=Form(...),address:str=Form(""),fuel_id:int=Form(...),active:str=Form("1")):
 m=re.search(r"/(\d{8})/?(?:\?.*)?$",url.strip())
 if not m:return RedirectResponse("/stations?error=Stations-ID+nicht+gefunden",303)
 sid=m.group(1);now=datetime.now(timezone.utc).isoformat();act=1 if active=="1" else 0
 with connect() as c:
  if id:
   c.execute("UPDATE stations SET aral_station_id=?,name=?,address=?,url=?,active=? WHERE id=?",(sid,name.strip(),address.strip(),url.strip(),act,int(id)));c.execute("DELETE FROM station_fuels WHERE station_id=?",(int(id),));c.execute("INSERT INTO station_fuels(station_id,fuel_id,active) VALUES(?,?,1)",(int(id),fuel_id))
  else:
   cur=c.execute("INSERT INTO stations(aral_station_id,name,address,url,active,created_at) VALUES(?,?,?,?,?,?)",(sid,name.strip(),address.strip(),url.strip(),act,now));c.execute("INSERT INTO station_fuels(station_id,fuel_id,active) VALUES(?,?,1)",(cur.lastrowid,fuel_id))
 return RedirectResponse("/stations",303)
@app.post("/stations/{id}/toggle")
def toggle_station(id:int):
 with connect() as c:c.execute("UPDATE stations SET active=1-active WHERE id=?",(id,))
 return RedirectResponse("/stations",303)
@app.post("/stations/{id}/delete")
def delete_station(id:int):
 with connect() as c:c.execute("DELETE FROM stations WHERE id=?",(id,))
 return RedirectResponse("/stations",303)
@app.get("/vehicles",response_class=HTMLResponse)
def vehicles_page(request:Request,edit:int|None=None):
 vs=rows("SELECT v.*,f.name fuel_name FROM vehicles v JOIN fuels f ON f.id=v.fuel_id ORDER BY v.name");fuels=rows("SELECT * FROM fuels ORDER BY name");editing=rows("SELECT * FROM vehicles WHERE id=?",(edit,))[0] if edit and rows("SELECT 1 FROM vehicles WHERE id=?",(edit,)) else None
 return tpl.TemplateResponse("vehicles.html",{"request":request,"vehicles":vs,"fuels":fuels,"editing":editing,**common()})
@app.post("/vehicles/save")
def save_vehicle(id:str=Form(""),name:str=Form(...),fuel_id:int=Form(...),consumption:float=Form(...),tank_capacity:str=Form(""),season_start:str=Form(...),season_end:str=Form(...),active:str=Form("1")):
 tank=float(tank_capacity) if tank_capacity.strip() else None;act=1 if active=="1" else 0
 with connect() as c:
  if id:c.execute("UPDATE vehicles SET name=?,fuel_id=?,consumption=?,tank_capacity=?,season_start=?,season_end=?,active=? WHERE id=?",(name.strip(),fuel_id,consumption,tank,season_start,season_end,act,int(id)))
  else:c.execute("INSERT INTO vehicles(name,fuel_id,consumption,tank_capacity,season_start,season_end,active) VALUES(?,?,?,?,?,?,?)",(name.strip(),fuel_id,consumption,tank,season_start,season_end,act))
 return RedirectResponse("/vehicles",303)
@app.post("/vehicles/{id}/delete")
def delete_vehicle(id:int):
 with connect() as c:c.execute("DELETE FROM vehicles WHERE id=?",(id,))
 return RedirectResponse("/vehicles",303)
@app.post("/collect")
async def collect():await collect_once();return RedirectResponse("/",303)
@app.get("/health")
def health():return {"status":"ok","version":VERSION,"last_run":(rows("SELECT * FROM collector_runs ORDER BY id DESC LIMIT 1") or [None])[0]}
