from collections import defaultdict
from datetime import date, datetime
from .db import rows

def _f(v):
    try:return float(v) if v not in (None,'') else None
    except:return None

def vehicle_stats(vehicle_id):
    vehicle=(rows('SELECT * FROM vehicles WHERE id=?',(vehicle_id,)) or [None])[0]
    if not vehicle:return None
    refuels=rows('''SELECT * FROM refuels WHERE vehicle_id=? AND COALESCE(tank_type,1)<>0 ORDER BY refueled_at,id''',(vehicle_id,))
    empty={'vehicle':vehicle,'count':0,'liters':0,'fuel_cost':0,'avg_price':None,'first_odo':None,'last_odo':None,'distance':0,'avg_consumption':None,'avg_consumption_12m':None,'min_consumption':None,'max_consumption':None,'cost_per_100':None,'series':[],'fuel_breakdown':[],'monthly':[],'recent':[]}
    if not refuels:return empty
    liters=sum(_f(r.get('liters')) or 0 for r in refuels);cost=sum(_f(r.get('total_cost') or r.get('total')) or 0 for r in refuels)
    prices=[_f(r.get('price_per_liter') or r.get('price')) for r in refuels if _f(r.get('price_per_liter') or r.get('price'))]
    odos=[_f(r.get('odometer')) for r in refuels if _f(r.get('odometer')) is not None];first=min(odos) if odos else None;last=max(odos) if odos else None;distance=max(0,last-first) if first is not None and last is not None else 0
    cons=[_f(r.get('reported_consumption')) for r in refuels if (_f(r.get('reported_consumption')) or 0)>0]
    avg_cons=sum(cons)/len(cons) if cons else (liters/distance*100 if distance>0 else None)
    today=date.today();cut=(today.year-1,today.month,today.day)
    cons12=[]
    for r in refuels:
        c=_f(r.get('reported_consumption')); ds=str(r.get('refueled_at') or '')[:10]
        try:d=datetime.fromisoformat(ds).date()
        except:continue
        if c and (d.year,d.month,d.day)>=cut:cons12.append(c)
    series=[];window=[]
    for r in refuels:
        c=_f(r.get('reported_consumption')); p=_f(r.get('price_per_liter') or r.get('price')); d=str(r.get('refueled_at') or '')[:10]
        if c:window.append(c)
        ma5=sum(window[-5:])/len(window[-5:]) if window else None
        series.append({'date':d,'consumption':c,'consumption_ma5':ma5,'price':p,'odometer':_f(r.get('odometer')),'cost100':(c*p if c and p else None)})
    monthly=defaultdict(lambda:{'distance':0.0,'cost':0.0,'liters':0.0})
    prev=None
    for r in refuels:
        ds=str(r.get('refueled_at') or '')[:7]; odo=_f(r.get('odometer'))
        if ds:
            monthly[ds]['cost']+=_f(r.get('total_cost') or r.get('total')) or 0;monthly[ds]['liters']+=_f(r.get('liters')) or 0
            if odo is not None and prev is not None and odo>=prev:monthly[ds]['distance']+=odo-prev
        if odo is not None:prev=odo
    monthly=[{'month':k,**v} for k,v in sorted(monthly.items())]
    breakdown=rows('''SELECT COALESCE(spritmonitor_fuel_code,0) code,COUNT(*) count,SUM(liters) liters,SUM(COALESCE(total_cost,total,0)) cost FROM refuels WHERE vehicle_id=? GROUP BY COALESCE(spritmonitor_fuel_code,0) ORDER BY count DESC''',(vehicle_id,))
    recent=list(reversed(refuels[-12:]))
    return {'vehicle':vehicle,'count':len(refuels),'liters':liters,'fuel_cost':cost,'avg_price':sum(prices)/len(prices) if prices else None,'first_odo':first,'last_odo':last,'distance':distance,'avg_consumption':avg_cons,'avg_consumption_12m':sum(cons12)/len(cons12) if cons12 else None,'min_consumption':min(cons) if cons else None,'max_consumption':max(cons) if cons else None,'cost_per_100':(cost/distance*100) if distance>0 else None,'series':series,'fuel_breakdown':breakdown,'monthly':monthly,'recent':recent}
