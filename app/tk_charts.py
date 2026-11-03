from .db import rows
def top5(days=30):
 days=max(7,min(90,int(days)));rank=rows("SELECT station_external_id,station_name,place,AVG(price) avg_price FROM tankerkoenig_prices WHERE fuel_type='e10' AND datetime(retrieved_at)>=datetime('now',?) GROUP BY station_external_id,station_name,place ORDER BY avg_price LIMIT 5",(f'-{days} days',));out=[]
 for r in rank:out.append({**r,'points':[dict(x) for x in rows("SELECT retrieved_at x,price y FROM tankerkoenig_prices WHERE station_external_id=? AND fuel_type='e10' AND datetime(retrieved_at)>=datetime('now',?) ORDER BY retrieved_at",(r['station_external_id'],f'-{days} days'))]})
 return {'series':out,'days':days}
