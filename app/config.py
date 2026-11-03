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
VERSION='0.7.5'

SPRITMONITOR_ENABLED=os.getenv("SPRITMONITOR_ENABLED","false").lower() in {"1","true","yes","on"}
SPRITMONITOR_APP_TOKEN=os.getenv("SPRITMONITOR_APP_TOKEN","")
SPRITMONITOR_BEARER_TOKEN=os.getenv("SPRITMONITOR_BEARER_TOKEN","")
SPRITMONITOR_SYNC_MODE=os.getenv("SPRITMONITOR_SYNC_MODE","read_only").lower()

TANKERKOENIG_ENABLED=os.getenv("TANKERKOENIG_ENABLED","false").lower() in {"1","true","yes","on"}
TANKERKOENIG_API_KEY=os.getenv("TANKERKOENIG_API_KEY","")
TANKERKOENIG_LAT=float(os.getenv("TANKERKOENIG_LAT","0") or 0)
TANKERKOENIG_LNG=float(os.getenv("TANKERKOENIG_LNG","0") or 0)
TANKERKOENIG_RADIUS=max(0.1,min(25.0,float(os.getenv("TANKERKOENIG_RADIUS","10") or 10)))

OSRM_BASE_URL=os.getenv("OSRM_BASE_URL","https://router.project-osrm.org")
OSRM_CACHE_HOURS=max(1,int(os.getenv("OSRM_CACHE_HOURS","24")))
OSRM_ROUTE_CANDIDATES=max(1,min(10,int(os.getenv("OSRM_ROUTE_CANDIDATES","5"))))
