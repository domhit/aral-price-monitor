import json, re
import paho.mqtt.client as mqtt
from . import config

_client = None

def slug(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

def client():
    global _client
    if not config.MQTT_ENABLED or not config.MQTT_HOST:
        return None
    if _client is None:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="aral-price-monitor")
        if config.MQTT_USER:
            c.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
        c.connect(config.MQTT_HOST, config.MQTT_PORT, 30)
        c.loop_start()
        _client = c
    return _client

def publish_station(station, fuel, price, changed_at, retrieved_at):
    c = client()
    if c is None: return
    uid = f"aral_{station['aral_station_id']}_{fuel['slug']}"
    state_topic = f"{config.MQTT_BASE_TOPIC}/station/{station['aral_station_id']}/{fuel['slug']}/state"
    availability_topic = f"{config.MQTT_BASE_TOPIC}/status"
    discovery_topic = f"{config.MQTT_DISCOVERY_PREFIX}/sensor/{uid}/config"
    payload = {
        "name": f"{station['name']} {fuel['name']}", "unique_id": uid,
        "state_topic": state_topic, "value_template": "{{ value_json.price }}",
        "unit_of_measurement": "€/L", "state_class": "measurement", "icon": "mdi:gas-station",
        "availability_topic": availability_topic,
        "json_attributes_topic": state_topic,
        "device": {"identifiers": [f"aral_station_{station['aral_station_id']}"], "name": station['name'], "manufacturer": "Aral", "model": "Price API"}
    }
    c.publish(discovery_topic, json.dumps(payload, ensure_ascii=False), qos=1, retain=True)
    c.publish(state_topic, json.dumps({"price": price, "fuel": fuel['name'], "fuel_id": fuel['aral_fuel_id'], "station_id": station['aral_station_id'], "last_price_change": changed_at, "retrieved_at": retrieved_at}, ensure_ascii=False), qos=1, retain=True)
    c.publish(availability_topic, "online", qos=1, retain=True)

def publish_offline():
    c = client()
    if c: c.publish(f"{config.MQTT_BASE_TOPIC}/status", "offline", qos=1, retain=True)
