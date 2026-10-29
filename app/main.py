import asyncio,re
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from fastapi import FastAPI,Request,Form,HTTPException,UploadFile,File
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .config import VERSION,POLL_INTERVAL
from .db import init_db,rows,connect
from .collector import collector_loop,collect_once
from .analytics import history_payload,all_recommendations,recommendation_for_fuel
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

@app.get("/analysis",response_class=HTMLResponse)
def analysis_page(request:Request):
 recs=all_recommendations()
 return tpl.TemplateResponse("analysis.html",{"request":request,"recs":recs,**common()})

@app.get("/api/recommendations")
def api_recommendations():
 return all_recommendations()
@app.get("/stations",response_class=HTMLResponse)
def stations_page(request:Request,edit:int|None=None):
 st=rows("SELECT s.*,GROUP_CONCAT(f.name,', ') fuels FROM stations s LEFT JOIN station_fuels sf ON sf.station_id=s.id LEFT JOIN fuels f ON f.id=sf.fuel_id GROUP BY s.id ORDER BY s.name");fuels=rows("SELECT * FROM fuels ORDER BY name");editing=rows("SELECT s.*,sf.fuel_id FROM stations s LEFT JOIN station_fuels sf ON sf.station_id=s.id WHERE s.id=?",(edit,))[0] if edit and rows("SELECT 1 FROM stations WHERE id=?",(edit,)) else None
 return tpl.TemplateResponse("stations.html",{"request":request,"stations":st,"fuels":fuels,"editing":editing,**common()})
@app.post("/stations/save")
def save_station(id:str=Form(""),url:str=Form(...),name:str=Form(...),address:str=Form(""),fuel_id:int=Form(...),active:str=Form("1"),extra_distance_km:float=Form(0)):
 m=re.search(r"/(\d{8})/?(?:\?.*)?$",url.strip())
 if not m:return RedirectResponse("/stations?error=Stations-ID+nicht+gefunden",303)
 sid=m.group(1);now=datetime.now(timezone.utc).isoformat();act=1 if active=="1" else 0
 with connect() as c:
  if id:
   c.execute("UPDATE stations SET aral_station_id=?,name=?,address=?,url=?,active=?,extra_distance_km=? WHERE id=?",(sid,name.strip(),address.strip(),url.strip(),act,extra_distance_km,int(id)));c.execute("DELETE FROM station_fuels WHERE station_id=?",(int(id),));c.execute("INSERT INTO station_fuels(station_id,fuel_id,active) VALUES(?,?,1)",(int(id),fuel_id))
  else:
   cur=c.execute("INSERT INTO stations(aral_station_id,name,address,url,active,created_at,extra_distance_km) VALUES(?,?,?,?,?,?,?)",(sid,name.strip(),address.strip(),url.strip(),act,now,extra_distance_km));c.execute("INSERT INTO station_fuels(station_id,fuel_id,active) VALUES(?,?,1)",(cur.lastrowid,fuel_id))
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

@app.get('/settings',response_class=HTMLResponse)
def settings_page(request:Request):
    from .admin import get_settings,db_stats
    settings=get_settings(); stats=db_stats(); last=(rows('SELECT * FROM collector_runs ORDER BY id DESC LIMIT 1') or [None])[0]
    return tpl.TemplateResponse('settings.html',{'request':request,'settings':settings,'stats':stats,'last':last,**common()})

@app.post('/settings')
def settings_save(analysis_days:int=Form(...),now_threshold_ct:float=Form(...),okay_threshold_ct:float=Form(...),wait_threshold_ct:float=Form(...),min_days:int=Form(...)):
    from .admin import save_settings
    save_settings({'analysis_days':max(7,min(90,analysis_days)),'now_threshold_ct':now_threshold_ct,'okay_threshold_ct':okay_threshold_ct,'wait_threshold_ct':wait_threshold_ct,'min_days':max(1,min(30,min_days))});return RedirectResponse('/settings?saved=1',303)

@app.get('/backup/database')
def backup_database():
    from .admin import make_backup
    from fastapi.responses import FileResponse
    stamp=datetime.now().strftime('%Y-%m-%d_%H%M%S');path=f'/tmp/aral-price-monitor-backup-{stamp}.db';make_backup(path);return FileResponse(path,media_type='application/vnd.sqlite3',filename=f'aral-price-monitor-backup-{stamp}.db')

@app.get('/backup/config')
def backup_config():
    from .admin import export_config
    from fastapi.responses import Response
    return Response(export_config(),media_type='application/x-yaml',headers={'Content-Disposition':'attachment; filename="aral-price-monitor-config.yaml"'})

@app.get('/export/history.csv')
def export_history(days:int=30,fuel_id:int|None=None,station_id:int|None=None):
    from .admin import csv_history
    from fastapi.responses import Response
    return Response(csv_history(days,fuel_id,station_id),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="aral-price-history.csv"'})

@app.post('/database/vacuum')
def vacuum_database():
    import sqlite3
    from .config import DB_PATH
    c=sqlite3.connect(DB_PATH);c.execute('VACUUM');c.close();return RedirectResponse('/settings?vacuum=1',303)

@app.get('/refuels',response_class=HTMLResponse)
def refuels_page(request:Request,edit:int|None=None):
 from .refuel_meta import TANK_TYPES,DRIVING,FUELS,route_name
 vehicles=rows('SELECT * FROM vehicles ORDER BY name');stations=rows('SELECT * FROM stations WHERE active=1 ORDER BY name')
 history=rows('SELECT r.*,v.name vehicle_name,s.name station_name FROM refuels r JOIN vehicles v ON v.id=r.vehicle_id LEFT JOIN stations s ON s.id=r.station_id ORDER BY r.refueled_at DESC,r.id DESC LIMIT 500')
 editing=(rows('SELECT * FROM refuels WHERE id=?',(edit,)) or [None])[0] if edit else None
 for r in history:
  r['tank_type_name']=TANK_TYPES.get(r.get('tank_type'),'–');r['fuel_name']=FUELS.get(r.get('spritmonitor_fuel_code'),'–');r['driving_name']=DRIVING.get(r.get('driving_style_code'),'–');r['route_name']=route_name(r.get('route_code'))
 return tpl.TemplateResponse('refuels.html',{'request':request,'vehicles':vehicles,'stations':stations,'history':history,'editing':editing,'tank_types':TANK_TYPES,'fuel_types':FUELS,**common()})

@app.post('/refuels/save')
def refuel_save(id:str=Form(''),vehicle_id:int=Form(...),station_id:str=Form(''),liters:float=Form(...),price:float=Form(...),refueled_at:str=Form(...),odometer:str=Form(''),trip_km:str=Form(''),tank_type:int=Form(1),spritmonitor_fuel_code:str=Form(''),station_brand:str=Form(''),location:str=Form(''),note:str=Form('')):
 total=round(liters*price,2);sid=int(station_id) if station_id else None;vals=(vehicle_id,sid,liters,price,total,refueled_at,float(odometer) if odometer else None,float(trip_km) if trip_km else None,tank_type,int(spritmonitor_fuel_code) if spritmonitor_fuel_code else None,station_brand.strip(),location.strip(),note.strip())
 with connect() as c:
  if id:
   c.execute("UPDATE refuels SET vehicle_id=?,station_id=?,liters=?,price=?,total=?,refueled_at=?,odometer=?,trip_km=?,tank_type=?,spritmonitor_fuel_code=?,station_brand=?,location=?,note=?,price_per_liter=?,total_cost=?,sync_status='modified',updated_at=CURRENT_TIMESTAMP WHERE id=?",(*vals,price,total,int(id)))
  else:
   c.execute("INSERT INTO refuels(vehicle_id,station_id,liters,price,total,refueled_at,odometer,trip_km,tank_type,spritmonitor_fuel_code,station_brand,location,note,price_per_liter,total_cost,source,sync_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'manual','local')",(*vals,price,total))
 return RedirectResponse('/refuels',303)

@app.post('/refuels/{id}/delete')
def refuel_delete(id:int):
 with connect() as c:c.execute('DELETE FROM refuels WHERE id=?',(id,))
 return RedirectResponse('/refuels?deleted=1',303)

@app.post('/refuels/import/preview',response_class=HTMLResponse)
async def import_preview(request:Request,vehicle_id:int=Form(...),file:UploadFile=File(...)):
 from .spritmonitor import parse,encode
 raw=await file.read()
 try:data=parse(raw)
 except Exception as e:return RedirectResponse('/refuels?import_error='+str(e).replace(' ','+'),303)
 vehicle=(rows('SELECT * FROM vehicles WHERE id=?',(vehicle_id,)) or [None])[0]
 return tpl.TemplateResponse('import_preview.html',{'request':request,'data':data,'vehicle':vehicle,'token':encode(raw),**common()})

@app.post('/refuels/import/confirm')
def import_confirm(vehicle_id:int=Form(...),token:str=Form(...)):
 from .spritmonitor import import_csv,decode_token
 try:i,d,e=import_csv(vehicle_id,decode_token(token))
 except Exception as ex:return RedirectResponse('/refuels?import_error='+str(ex).replace(' ','+'),303)
 return RedirectResponse(f'/refuels?imported={i}&duplicates={d}&errors={e}',303)

@app.get('/costs',response_class=HTMLResponse)
def costs_page(request:Request):
 costs=rows('SELECT c.*,v.name vehicle_name FROM vehicle_costs c JOIN vehicles v ON v.id=c.vehicle_id ORDER BY c.cost_date DESC')
 return tpl.TemplateResponse('costs.html',{'request':request,'costs':costs,**common()})
