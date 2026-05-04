# gee_engine.py - ULTRA SIMPLIFIED VERSION
import ee
import os
import sys
import logging
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
import requests

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

PROJECT_ID = 'flooddetectionfinal'

# ============================================
# CITY DATABASE WITH HISTORICAL FLOOD DATA
# ============================================
CITIES_DB = {
    "darbhanga": {
        "name": "Darbhanga", "state": "Bihar", "lat": 26.15, "lon": 85.90,
        "coastal": False, "population": 400000, "area_sqkm": 50,
        "flood_causes": "Kosi river overflow, heavy monsoon rainfall",
        "historical_floods": [
            {"date": "2024-07-15", "cause": "Kosi river overflow + heavy rainfall", "affected": 250000},
            {"date": "2020-08-10", "cause": "Kosi river breach", "affected": 180000}
        ]
    },
    "mumbai": {
        "name": "Mumbai", "state": "Maharashtra", "lat": 19.08, "lon": 72.88,
        "coastal": True, "population": 12400000, "area_sqkm": 600,
        "flood_causes": "High tide, storm surge, urban drainage failure",
        "historical_floods": [
            {"date": "2023-07-25", "cause": "Urban drainage failure + heavy rain", "affected": 500000},
            {"date": "2005-07-26", "cause": "Record rainfall (944mm)", "affected": 700000}
        ]
    },
    "chennai": {
        "name": "Chennai", "state": "Tamil Nadu", "lat": 13.08, "lon": 80.27,
        "coastal": True, "population": 7000000, "area_sqkm": 426,
        "flood_causes": "Cyclones, northeast monsoon, urban flooding",
        "historical_floods": [
            {"date": "2023-12-05", "cause": "Cyclone Michaung", "affected": 400000},
            {"date": "2015-12-01", "cause": "Record rainfall (500mm in 2 days)", "affected": 800000}
        ]
    },
    "kolkata": {
        "name": "Kolkata", "state": "West Bengal", "lat": 22.57, "lon": 88.36,
        "coastal": True, "population": 4500000, "area_sqkm": 205,
        "flood_causes": "Hooghly river overflow, cyclones, tidal surge",
        "historical_floods": [
            {"date": "2024-08-10", "cause": "Cyclone Remal", "affected": 350000}
        ]
    },
    "bangalore": {
        "name": "Bangalore", "state": "Karnataka", "lat": 12.97, "lon": 77.59,
        "coastal": False, "population": 8500000, "area_sqkm": 741,
        "flood_causes": "Poor urban drainage, lake overflow",
        "historical_floods": [
            {"date": "2024-09-05", "cause": "Bellandur lake overflow", "affected": 150000}
        ]
    },
    "delhi": {
        "name": "Delhi", "state": "Delhi", "lat": 28.61, "lon": 77.23,
        "coastal": False, "population": 16700000, "area_sqkm": 1484,
        "flood_causes": "Yamuna river overflow, urban flooding",
        "historical_floods": [
            {"date": "2023-07-13", "cause": "Yamuna river overflow", "affected": 200000}
        ]
    }
}

# ============================================
# EARTH ENGINE INITIALIZATION
# ============================================
def initialize_ee():
    import ssl
    import urllib3
    
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    ssl._create_default_https_context = ssl._create_unverified_context
    
    key_path = '/etc/secrets/ee-key.json'
    logger.info(f"Looking for key file at: {key_path}")
    logger.info(f"File exists: {os.path.exists(key_path)}")
    
    if os.path.exists(key_path):
        try:
            with open(key_path, 'r') as f:
                creds_dict = json.load(f)
            logger.info(f"JSON loaded. Keys: {list(creds_dict.keys())}")
            
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=['https://www.googleapis.com/auth/earthengine']
            )
            ee.Initialize(credentials, project=PROJECT_ID)
            logger.info("✅✅✅ Earth Engine initialized successfully! ✅✅✅")
            return True
        except Exception as e:
            logger.error(f"EE init error: {e}")
            return False
    else:
        logger.error(f"Key file NOT found at {key_path}")
        return False

INIT_SUCCESS = initialize_ee()

class FloodPredictor:
    def __init__(self):
        logger.info("🚀 Flood Predictor Initialized")
        if not INIT_SUCCESS:
            logger.warning("⚠️ Earth Engine not initialized!")
    
    def get_city_info(self, city_name):
        return CITIES_DB.get(city_name.lower().strip())
    
    def get_all_cities(self):
        return [{'name': data['name'], 'state': data['state'], 'lat': data['lat'], 'lon': data['lon'], 
                 'coastal': data.get('coastal', False)} for data in CITIES_DB.values()]
    
    def analyze_city_flood_risk(self, city_name):
        city_data = self.get_city_info(city_name)
        if not city_data:
            return {'error': f'City {city_name} not found'}
        
        lat, lon = city_data['lat'], city_data['lon']
        
        # Get flood data from GEE (if initialized)
        flooded_area = 0
        risk_level = "NORMAL"
        maps_data = {}
        
        if INIT_SUCCESS:
            try:
                roi = ee.Geometry.Point([lon, lat]).buffer(5000)
                
                # Get Sentinel-1 SAR
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
                
                sar = ee.ImageCollection('COPERNICUS/S1_GRD') \
                    .filterBounds(roi) \
                    .filterDate(start_date, end_date) \
                    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
                    .filter(ee.Filter.eq('instrumentMode', 'IW')) \
                    .select('VV').median()
                
                water = sar.lt(-15)
                
                # Calculate flooded area
                area = water.multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi,
                    scale=30,
                    maxPixels=1e9
                ).getInfo()
                
                flooded_area = (area.get('VV', 0) or 0) / 10000
                
                # Determine risk level
                if flooded_area > 100:
                    risk_level = "HIGH"
                elif flooded_area > 10:
                    risk_level = "MEDIUM"
                elif flooded_area > 0:
                    risk_level = "LOW"
                
                # Get map tile
                water_viz = water.getMapId({'palette': ['#FF0000'], 'min': 0, 'max': 1})
                maps_data = {'flood_map': {'mapid': water_viz['mapid'], 'token': water_viz.get('token', '')}}
                
                logger.info(f"✅ Flood analysis for {city_name}: {flooded_area} hectares, {risk_level} risk")
                
            except Exception as e:
                logger.error(f"GEE analysis error: {e}")
        else:
            logger.warning(f"GEE not initialized - using demo mode for {city_name}")
        
        # Calculate impact
        flood_percentage = min(100, (flooded_area / 100) / city_data.get('area_sqkm', 100) * 100)
        affected_population = int(city_data['population'] * (flood_percentage / 100))
        
        return {
            'status': 'success',
            'city': city_data['name'],
            'state': city_data['state'],
            'coastal': city_data.get('coastal', False),
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'flooded_area_hectares': flooded_area,
            'risk_level': risk_level,
            'flood_percentage': round(flood_percentage, 2),
            'affected_population': affected_population,
            'flood_causes': city_data.get('flood_causes', 'Unknown'),
            'historical_floods': city_data.get('historical_floods', []),
            'maps': maps_data,
            'message': 'Earth Engine ready' if INIT_SUCCESS else 'GEE needs authentication'
        }