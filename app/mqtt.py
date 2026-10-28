import json
import paho.mqtt.client as mqtt
from . import config
_c=None
def client():
 global _c
 if not config.MQTT_ENABLED or not config.MQTT_HOST:return None
 if _c is None:
  c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="aral-price-monitor")
  if config.MQTT_USER:c.username_pw_set(config.MQTT_USER,config.MQTT_PASSWORD)
  c.connect(config.MQTT_HOST,config.MQTT_PORT,30);c.loop_start();_c=c
 return _c
def publish_station(s,f,price,changed,retrieved):
 c=client()
 if not c:return
 uid=f"aral_{s['aral_station_id']}_{f['slug']}"; state=f"{config.MQTT_BASE_TOPIC}/station/{s['aral_station_id']}/{f['slug']}/state"; avail=f"{config.MQTT_BASE_TOPIC}/status"
 disc=f"{config.MQTT_DISCOVERY_PREFIX}/sensor/{uid}/config"
 cfg={"name":f"{s['name']} {f['name']}","unique_id":uid,"state_topic":state,"value_template":"{{ value_json.price }}","unit_of_measurement":"€/L","state_class":"measurement","icon":"mdi:gas-station","availability_topic":avail,"json_attributes_topic":state,"device":{"identifiers":[f"aral_station_{s['aral_station_id']}"],"name":s['name'],"manufacturer":"Aral","model":"Price API"}}
 c.publish(disc,json.dumps(cfg,ensure_ascii=False),qos=1,retain=True);c.publish(state,json.dumps({"price":price,"fuel":f['name'],"fuel_id":f['aral_fuel_id'],"station_id":s['aral_station_id'],"last_price_change":changed,"retrieved_at":retrieved},ensure_ascii=False),qos=1,retain=True);c.publish(avail,"online",qos=1,retain=True)
