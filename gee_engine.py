# gee_engine.py
import ee
import os
import logging
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PROJECT_ID = 'flooddetectionfinal'

def initialize_ee():
    key_path = '/etc/secrets/ee-key.json'
    
    if os.path.exists(key_path):
        try:
            with open(key_path, 'r') as f:
                creds_dict = json.load(f)
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=['https://www.googleapis.com/auth/earthengine']
            )
            ee.Initialize(credentials, project=PROJECT_ID)
            logger.info("✅ Earth Engine initialized!")
            return True
        except Exception as e:
            logger.error(f"EE init error: {e}")
            return False
    else:
        logger.error("Key file not found")
        return False

INIT_SUCCESS = initialize_ee()

class FloodPredictor:
    def __init__(self):
        logger.info("Flood Predictor Initialized")
    
    def get_tile_url(self, mapid):
        """Generate the correct tile URL without token"""
        return f"https://earthengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/maps/{mapid}/tiles/{{z}}/{{x}}/{{y}}"
    
    def get_true_color(self, lat, lon):
        roi = ee.Geometry.Point([lon, lat]).buffer(5000)
        collection = ee.ImageCollection('COPERNICUS/S2') \
            .filterBounds(roi) \
            .filterDate('2024-01-01', datetime.now().strftime('%Y-%m-%d')) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .select(['B4', 'B3', 'B2'])
        
        image = collection.median().clip(roi)
        vis_params = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}
        map_id_dict = image.getMapId(vis_params)
        
        return {
            'mapid': map_id_dict['mapid'],
            'tile_url': self.get_tile_url(map_id_dict['mapid'])
        }
    
    def get_water_bodies(self, lat, lon):
        roi = ee.Geometry.Point([lon, lat]).buffer(5000)
        collection = ee.ImageCollection('COPERNICUS/S2') \
            .filterBounds(roi) \
            .filterDate('2024-01-01', datetime.now().strftime('%Y-%m-%d')) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .select(['B3', 'B8'])
        
        image = collection.median().clip(roi)
        ndwi = image.normalizedDifference(['B3', 'B8'])
        vis_params = {'min': -0.2, 'max': 0.5, 'palette': ['#8B4513', '#FFFFFF', '#0000FF']}
        map_id_dict = ndwi.getMapId(vis_params)
        
        return {
            'mapid': map_id_dict['mapid'],
            'tile_url': self.get_tile_url(map_id_dict['mapid'])
        }
    
    def get_sar_before(self, lat, lon):
        roi = ee.Geometry.Point([lon, lat]).buffer(5000)
        end_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
        
        collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
            .filterBounds(roi) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .select('VV')
        
        image = collection.median().clip(roi)
        vis_params = {'min': -25, 'max': 5, 'palette': ['black', 'white']}
        map_id_dict = image.getMapId(vis_params)
        
        return {
            'mapid': map_id_dict['mapid'],
            'tile_url': self.get_tile_url(map_id_dict['mapid'])
        }
    
    def get_sar_current(self, lat, lon):
        roi = ee.Geometry.Point([lon, lat]).buffer(5000)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        
        collection = ee.ImageCollection('COPERNICUS/S1_GRD') \
            .filterBounds(roi) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .select('VV')
        
        image = collection.median().clip(roi)
        vis_params = {'min': -25, 'max': 5, 'palette': ['black', 'white']}
        map_id_dict = image.getMapId(vis_params)
        
        return {
            'mapid': map_id_dict['mapid'],
            'tile_url': self.get_tile_url(map_id_dict['mapid'])
        }
    
    def get_flood_extent(self, lat, lon):
        roi = ee.Geometry.Point([lon, lat]).buffer(5000)
        
        current = ee.ImageCollection('COPERNICUS/S1_GRD') \
            .filterBounds(roi) \
            .filterDate((datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .select('VV').median()
        
        baseline = ee.ImageCollection('COPERNICUS/S1_GRD') \
            .filterBounds(roi) \
            .filterDate((datetime.now() - timedelta(days=105)).strftime('%Y-%m-%d'), (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .select('VV').median()
        
        current_water = current.lt(-15)
        baseline_water = baseline.lt(-15)
        flood = current_water.updateMask(current_water.And(baseline_water.Not()))
        
        area = flood.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=roi, scale=30, maxPixels=1e9
        ).getInfo()
        flooded_area = (area.get('VV', 0) or 0) / 10000
        
        vis_params = {'palette': ['#FF0000'], 'min': 0, 'max': 1}
        map_id_dict = flood.getMapId(vis_params)
        
        return {
            'flooded_area': flooded_area,
            'map': {
                'mapid': map_id_dict['mapid'],
                'tile_url': self.get_tile_url(map_id_dict['mapid'])
            }
        }
    
    def analyze_city(self, city_name, city_data):
        lat, lon = city_data['lat'], city_data['lon']
        
        try:
            true_color = self.get_true_color(lat, lon)
            water_bodies = self.get_water_bodies(lat, lon)
            sar_before = self.get_sar_before(lat, lon)
            sar_current = self.get_sar_current(lat, lon)
            flood = self.get_flood_extent(lat, lon)
            
            if flood['flooded_area'] > 1000:
                risk_level = "CRITICAL"
            elif flood['flooded_area'] > 100:
                risk_level = "HIGH"
            elif flood['flooded_area'] > 10:
                risk_level = "MEDIUM"
            elif flood['flooded_area'] > 0:
                risk_level = "LOW"
            else:
                risk_level = "NORMAL"
            
            area_sqkm = city_data.get('area_sqkm', 100)
            flood_percentage = min(100, (flood['flooded_area'] / 100) / area_sqkm * 100)
            affected_population = int(city_data['population'] * (flood_percentage / 100))
            
            return {
                'status': 'success',
                'city': city_data['name'],
                'state': city_data['state'],
                'coastal': city_data.get('coastal', False),
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'flooded_area_hectares': round(flood['flooded_area'], 2),
                'risk_level': risk_level,
                'affected_population': affected_population,
                'flood_causes': city_data.get('flood_causes', 'Unknown'),
                'historical_floods': city_data.get('historical_floods', []),
                'maps': {
                    'true_color': true_color,
                    'water_bodies': water_bodies,
                    'sar_before': sar_before,
                    'sar_current': sar_current,
                    'flood_extent': flood['map']
                }
            }
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return {'status': 'error', 'message': str(e)}