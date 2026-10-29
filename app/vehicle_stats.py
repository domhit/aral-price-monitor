from .db import rows

def vehicle_stats(vehicle_id):
    vehicle=(rows('SELECT * FROM vehicles WHERE id=?',(vehicle_id,)) or [None])[0]
    if not vehicle:return None
    refuels=rows('''SELECT * FROM refuels WHERE vehicle_id=? AND COALESCE(tank_type,1)<>0 ORDER BY refueled_at,id''',(vehicle_id,))
    if not refuels:return {'vehicle':vehicle,'count':0,'liters':0,'fuel_cost':0,'avg_price':None,'first_odo':None,'last_odo':None,'distance':0,'avg_consumption':None,'cost_per_100':None,'series':[],'fuel_breakdown':[]}
    liters=sum(float(r.get('liters') or 0) for r in refuels);cost=sum(float(r.get('total_cost') or r.get('total') or 0) for r in refuels)
    prices=[float(r.get('price_per_liter') or r.get('price') or 0) for r in refuels if (r.get('price_per_liter') or r.get('price'))]
    odos=[float(r['odometer']) for r in refuels if r.get('odometer') is not None];first=min(odos) if odos else None;last=max(odos) if odos else None;distance=max(0,last-first) if first is not None and last is not None else 0
    # Prefer Spritmonitor-reported consumption for historic entries; fallback to liters/distance global approximation.
    cons=[float(r['reported_consumption']) for r in refuels if r.get('reported_consumption') and float(r['reported_consumption'])>0]
    avg_cons=sum(cons)/len(cons) if cons else (liters/distance*100 if distance>0 else None)
    cost100=(cost/distance*100) if distance>0 else None
    series=[{'date':r['refueled_at'][:10],'consumption':r.get('reported_consumption'),'price':r.get('price_per_liter') or r.get('price'),'odometer':r.get('odometer')} for r in refuels if r.get('reported_consumption') or r.get('price_per_liter') or r.get('price')]
    breakdown=rows('''SELECT COALESCE(spritmonitor_fuel_code,0) code,COUNT(*) count,SUM(liters) liters,SUM(COALESCE(total_cost,total,0)) cost FROM refuels WHERE vehicle_id=? GROUP BY COALESCE(spritmonitor_fuel_code,0) ORDER BY count DESC''',(vehicle_id,))
    return {'vehicle':vehicle,'count':len(refuels),'liters':liters,'fuel_cost':cost,'avg_price':sum(prices)/len(prices) if prices else None,'first_odo':first,'last_odo':last,'distance':distance,'avg_consumption':avg_cons,'cost_per_100':cost100,'series':series,'fuel_breakdown':breakdown}
