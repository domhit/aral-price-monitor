import json
import paho.mqtt.client as mqtt
from . import config
_c=None
def client():
 global _c
 if not config.MQTT_ENABLED or not config.MQTT_HOST:return None
 if _c is None:
  c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='aral-price-monitor')
  if config.MQTT_USER:c.username_pw_set(config.MQTT_USER,config.MQTT_PASSWORD)
  c.connect(config.MQTT_HOST,config.MQTT_PORT,30);c.loop_start();_c=c
 return _c
def _pub_sensor(uid,name,state,value_template='{{ value_json.value }}',unit=None,icon='mdi:gas-station',attrs=True):
 c=client()
 if not c:return
 topic=f'{config.MQTT_BASE_TOPIC}/{uid}/state';avail=f'{config.MQTT_BASE_TOPIC}/status';disc=f'{config.MQTT_DISCOVERY_PREFIX}/sensor/{uid}/config'
 cfg={'name':name,'unique_id':uid,'state_topic':topic,'value_template':value_template,'availability_topic':avail,'icon':icon,'device':{'identifiers':['aral_price_monitor'],'name':'Aral Price Monitor','manufacturer':'Self-hosted','model':'v0.9.0'}}
 if unit:cfg['unit_of_measurement']=unit
 if attrs:cfg['json_attributes_topic']=topic
 c.publish(disc,json.dumps(cfg,ensure_ascii=False),qos=1,retain=True);c.publish(topic,json.dumps(state,ensure_ascii=False),qos=1,retain=True);c.publish(avail,'online',qos=1,retain=True)
def publish_station(s,f,price,changed,retrieved):
 uid=f"aral_{s['aral_station_id']}_{f['slug']}";_pub_sensor(uid,f"{s['name']} {f['name']}",{'price':price,'fuel':f['name'],'fuel_id':f['aral_fuel_id'],'station_id':s['aral_station_id'],'last_price_change':changed,'retrieved_at':retrieved},'{{ value_json.price }}','€/L')
def publish_recommendation(r):
 slug=r['fuel']['slug'];attrs={'value':r['recommendation'],'current_price':r['current_price'],'best_station':r['best_station'],'expected_low':r['expected_low'],'remaining_ct':r['remaining_ct'],'saving_per_tank':r['saving_per_tank'],'tank_liters':r['tank_liters'],'best_window':r['best_window'],'confidence':r['confidence'],'data_days':r['data_days'],'economic_station':r['economic_station']['name']}
 _pub_sensor(f'{slug}_refuel_recommendation',f"{r['fuel']['name']} Tankempfehlung",attrs,icon='mdi:gas-station-outline')
 _pub_sensor(f'{slug}_best_price',f"{r['fuel']['name']} bester Preis",{'value':r['current_price'],'station':r['best_station']},unit='€/L')

def _slug(v):
 import re
 return re.sub(r'[^a-z0-9]+','_',str(v).lower()).strip('_')
def publish_vehicle_assistant(r):
 if not r.get('current'):return
 uid=_slug(r['name']);c=r['current'];base={'vehicle':r['name'],'price_source':r.get('price_source'),'fuel':r.get('price_fuel'),'station':c.get('station'),'price':c.get('price'),'distance_km':c.get('route_distance_km'),'duration_min':c.get('route_duration_min'),'refill_liters':r.get('fill_liters'),'fill_source':r.get('fill_source'),'fill_cost':c.get('fill_cost'),'travel_cost':c.get('trip_cost'),'effective_cost':c.get('effective_cost'),'advantage':r.get('advantage'),'recommendation':r.get('recommendation'),'notify_worthy':r.get('notify_worthy'),'price_age_min':c.get('price_age_min')}
 _pub_sensor(f'{uid}_fuel_recommendation',f"{r['name']} Tankempfehlung",{**base,'value':r['recommendation']},icon='mdi:gas-station-outline')
 _pub_sensor(f'{uid}_best_fuel_price',f"{r['name']} bester Preis",{**base,'value':c.get('price')},unit='€/L')
 _pub_sensor(f'{uid}_station_distance',f"{r['name']} Tankstelle Entfernung",{**base,'value':c.get('route_distance_km')},unit='km',icon='mdi:map-marker-distance')
 _pub_sensor(f'{uid}_effective_cost',f"{r['name']} effektive Tankkosten",{**base,'value':c.get('effective_cost')},unit='€',icon='mdi:cash')
 _pub_sensor(f'{uid}_station_advantage',f"{r['name']} Tankstellen-Vorteil",{**base,'value':r.get('advantage')},unit='€',icon='mdi:cash-plus')
