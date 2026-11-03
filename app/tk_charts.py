from .db import rows
def top5(days=30,fuel='e10'):
 days=max(7,min(90,int(days)));rank=rows("""SELECT station_external_id,station_name,AVG(price) avg_price,COUNT(*) samples FROM tankerkoenig_prices WHERE fuel_type=? AND datetime(retrieved_at)>=datetime('now',?) GROUP BY station_external_id,station_name HAVING COUNT(*)>0 ORDER BY avg_price LIMIT 5""",(fuel,f'-{days} days'));series=[]
 for r in rank:
  pts=rows("SELECT retrieved_at,price FROM tankerkoenig_prices WHERE station_external_id=? AND fuel_type=? AND datetime(retrieved_at)>=datetime('now',?) ORDER BY retrieved_at",(r['station_external_id'],fuel,f'-{days} days'));series.append({**r,'points':[{'x':p['retrieved_at'],'y':p['price']} for p in pts]})
 return {'days':days,'fuel':fuel,'definition':'Top 5 nach niedrigstem Durchschnittspreis im Zeitraum','series':series}
