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
 cfg={'name':name,'unique_id':uid,'state_topic':topic,'value_template':value_template,'availability_topic':avail,'icon':icon,'device':{'identifiers':['aral_price_monitor'],'name':'Aral Price Monitor','manufacturer':'Self-hosted','model':'v0.3'}}
 if unit:cfg['unit_of_measurement']=unit
 if attrs:cfg['json_attributes_topic']=topic
 c.publish(disc,json.dumps(cfg,ensure_ascii=False),qos=1,retain=True);c.publish(topic,json.dumps(state,ensure_ascii=False),qos=1,retain=True);c.publish(avail,'online',qos=1,retain=True)
def publish_station(s,f,price,changed,retrieved):
 uid=f"aral_{s['aral_station_id']}_{f['slug']}";_pub_sensor(uid,f"{s['name']} {f['name']}",{'price':price,'fuel':f['name'],'fuel_id':f['aral_fuel_id'],'station_id':s['aral_station_id'],'last_price_change':changed,'retrieved_at':retrieved},'{{ value_json.price }}','€/L')
def publish_recommendation(r):
 slug=r['fuel']['slug'];attrs={'value':r['recommendation'],'current_price':r['current_price'],'best_station':r['best_station'],'expected_low':r['expected_low'],'remaining_ct':r['remaining_ct'],'saving_per_tank':r['saving_per_tank'],'tank_liters':r['tank_liters'],'best_window':r['best_window'],'confidence':r['confidence'],'data_days':r['data_days'],'economic_station':r['economic_station']['name']}
 _pub_sensor(f'{slug}_refuel_recommendation',f"{r['fuel']['name']} Tankempfehlung",attrs,icon='mdi:gas-station-outline')
 _pub_sensor(f'{slug}_best_price',f"{r['fuel']['name']} bester Preis",{'value':r['current_price'],'station':r['best_station']},unit='€/L')
