import os
DB_PATH=os.getenv('DATABASE_PATH','/data/aral-price-monitor.db')
POLL_INTERVAL=max(60,int(os.getenv('POLL_INTERVAL_SECONDS','300')))
API_URL=os.getenv('ARAL_API_URL','https://api.tankstelle.aral.de/api/v3/stations/{station_id}/prices')
MQTT_ENABLED=os.getenv('MQTT_ENABLED','true').lower() in {'1','true','yes','on'}
MQTT_HOST=os.getenv('MQTT_HOST','')
MQTT_PORT=int(os.getenv('MQTT_PORT','1883'))
MQTT_USER=os.getenv('MQTT_USER','')
MQTT_PASSWORD=os.getenv('MQTT_PASSWORD','')
MQTT_DISCOVERY_PREFIX=os.getenv('MQTT_DISCOVERY_PREFIX','homeassistant').strip('/')
MQTT_BASE_TOPIC=os.getenv('MQTT_BASE_TOPIC','aral_price_monitor').strip('/')
ANALYSIS_DAYS=max(7,min(90,int(os.getenv('ANALYSIS_DAYS','30'))))
VERSION='0.5.1'

SPRITMONITOR_ENABLED=os.getenv("SPRITMONITOR_ENABLED","false").lower() in {"1","true","yes","on"}
SPRITMONITOR_APP_TOKEN=os.getenv("SPRITMONITOR_APP_TOKEN","")
SPRITMONITOR_BEARER_TOKEN=os.getenv("SPRITMONITOR_BEARER_TOKEN","")
SPRITMONITOR_SYNC_INTERVAL=max(300,int(os.getenv("SPRITMONITOR_SYNC_INTERVAL","900")))
