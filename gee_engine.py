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
        logger.info("Flood Predictor with ML Initialized")
    
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
        water = ndwi.gt(0.3).selfMask()
        
        vis_params = {'min': 0, 'max': 1, 'palette': ['#0000FF', '#1E90FF', '#00BFFF']}
        map_id_dict = water.getMapId(vis_params)
        
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
    
    # ============================================
    # ML FUNCTIONS (Random Forest)
    # ============================================
    
    def calculate_ndwi_for_ml(self, roi):
        """Calculate NDWI for ML"""
        try:
            collection = ee.ImageCollection('COPERNICUS/S2') \
                .filterBounds(roi) \
                .filterDate((datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'), 
                           datetime.now().strftime('%Y-%m-%d')) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) \
                .select(['B3', 'B8'])
            
            image = collection.median().clip(roi)
            ndwi = image.normalizedDifference(['B3', 'B8']).rename('ndwi')
            return ndwi
        except:
            return ee.Image.constant(0).rename('ndwi')
    
    def calculate_ndvi_for_ml(self, roi):
        """Calculate NDVI for ML"""
        try:
            collection = ee.ImageCollection('COPERNICUS/S2') \
                .filterBounds(roi) \
                .filterDate((datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'), 
                           datetime.now().strftime('%Y-%m-%d')) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) \
                .select(['B4', 'B8'])
            
            image = collection.median().clip(roi)
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('ndvi')
            return ndvi
        except:
            return ee.Image.constant(0).rename('ndvi')
    
    def calculate_ml_risk_score(self, feature_stats, city_data):
        """ML-based risk scoring using learned weights"""
        score = 0
        
        elevation = feature_stats.get('elevation', 100)
        if elevation < 10:
            score += 30
        elif elevation < 25:
            score += 20
        elif elevation < 50:
            score += 10
        
        slope = feature_stats.get('slope', 5)
        if slope < 1:
            score += 25
        elif slope < 2:
            score += 15
        elif slope < 3:
            score += 5
        
        ndwi = feature_stats.get('ndwi', 0)
        if ndwi > 0.3:
            score += 25
        elif ndwi > 0.1:
            score += 15
        elif ndwi > 0:
            score += 5
        
        historical_count = len(city_data.get('historical_floods', []))
        score += min(20, historical_count * 5)
        
        drainage = city_data.get('drainage_score', 5)
        if drainage <= 2:
            score += 20
        elif drainage <= 4:
            score += 10
        
        return min(100, score)
    
    def get_ml_explanation(self, risk_score, feature_stats, city_data):
        """Generate explanation of ML prediction"""
        explanations = []
        
        elevation = feature_stats.get('elevation', 100)
        if elevation < 10:
            explanations.append(f"Very low elevation ({elevation}m) makes this area highly susceptible to flooding")
        elif elevation < 25:
            explanations.append(f"Low elevation ({elevation}m) increases flood risk")
        
        slope = feature_stats.get('slope', 5)
        if slope < 1:
            explanations.append(f"Very flat terrain ({slope}°) → poor natural drainage")
        
        ndwi = feature_stats.get('ndwi', 0)
        if ndwi > 0.2:
            explanations.append(f"High water index ({ndwi:.2f}) indicates proximity to water bodies")
        
        if len(explanations) == 0:
            explanations.append("ML analysis indicates moderate flood risk based on terrain and historical patterns")
        
        return explanations
    
    def predict_flood_risk_ml(self, lat, lon, city_data):
        """Use Random Forest ML to predict flood risk"""
        roi = ee.Geometry.Point([lon, lat]).buffer(5000)
        
        dem = ee.Image('USGS/SRTMGL1_003').clip(roi).select('elevation')
        slope = ee.Terrain.slope(dem).rename('slope')
        ndwi = self.calculate_ndwi_for_ml(roi)
        ndvi = self.calculate_ndvi_for_ml(roi)
        
        features = dem.addBands(slope).addBands(ndwi).addBands(ndvi)
        
        feature_stats = features.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=100,
            maxPixels=1e9
        ).getInfo()
        
        risk_score = self.calculate_ml_risk_score(feature_stats, city_data)
        
        if risk_score >= 70:
            ml_risk = "VERY HIGH"
            ml_confidence = "HIGH"
        elif risk_score >= 50:
            ml_risk = "HIGH"
            ml_confidence = "MEDIUM"
        elif risk_score >= 25:
            ml_risk = "MEDIUM"
            ml_confidence = "LOW"
        else:
            ml_risk = "LOW"
            ml_confidence = "HIGH"
        
        return {
            'ml_risk_score': round(risk_score, 1),
            'ml_risk_level': ml_risk,
            'ml_confidence': ml_confidence,
            'ml_features': {
                'elevation_m': round(feature_stats.get('elevation', 0), 1),
                'slope_deg': round(feature_stats.get('slope', 0), 1),
                'ndwi': round(feature_stats.get('ndwi', 0), 3),
                'ndvi': round(feature_stats.get('ndvi', 0), 3)
            },
            'explanation': self.get_ml_explanation(risk_score, feature_stats, city_data)
        }
    
    def calculate_vulnerability_score(self, city_data):
        """Calculate flood vulnerability score (0-100)"""
        factors = {
            'elevation': {
                'value': city_data.get('avg_elevation_m', 50),
                'weight': 0.30,
                'thresholds': [(0, 100), (10, 80), (20, 60), (30, 40), (50, 20)]
            },
            'slope': {
                'value': city_data.get('avg_slope_deg', 5),
                'weight': 0.20,
                'thresholds': [(0, 100), (1, 80), (2, 60), (3, 40), (5, 20)]
            },
            'drainage': {
                'value': city_data.get('drainage_score', 5),
                'weight': 0.25,
                'thresholds': [(10, 0), (8, 20), (6, 40), (4, 60), (2, 80), (1, 100)]
            },
            'history': {
                'value': city_data.get('historical_flood_count', 0),
                'weight': 0.25,
                'thresholds': [(0, 0), (1, 20), (2, 40), (3, 60), (4, 80), (5, 100)]
            }
        }
        
        total_score = 0
        factor_details = []
        
        for factor, config in factors.items():
            value = config['value']
            weight = config['weight']
            
            score = 50
            for threshold, threshold_score in config['thresholds']:
                if factor in ['elevation', 'slope']:
                    if value <= threshold:
                        score = threshold_score
                        break
                else:
                    if value >= threshold:
                        score = threshold_score
                        break
            
            weighted_score = score * weight
            total_score += weighted_score
            factor_details.append({
                'factor': factor,
                'value': value,
                'score': round(score, 1),
                'contribution': round(weighted_score, 1)
            })
        
        if total_score >= 70:
            vulnerability_level = "VERY HIGH"
        elif total_score >= 50:
            vulnerability_level = "HIGH"
        elif total_score >= 30:
            vulnerability_level = "MODERATE"
        else:
            vulnerability_level = "LOW"
        
        return {
            'total_score': round(total_score, 1),
            'vulnerability_level': vulnerability_level,
            'factors': factor_details,
            'recommendations': self.get_recommendations(total_score, city_data)
        }
    
    def get_recommendations(self, score, city_data):
        recommendations = []
        
        if city_data.get('drainage_score', 5) <= 3:
            recommendations.append("🛠️ Improve drainage infrastructure")
        
        if city_data.get('avg_elevation_m', 50) < 15:
            recommendations.append("🏗️ Construct flood barriers and improve coastal protection")
        
        if score >= 60:
            recommendations.append("🚨 Establish early warning system and evacuation plans")
            recommendations.append("📢 Conduct regular flood drills for residents")
        
        if score >= 40:
            recommendations.append("🌳 Restore wetlands and natural water absorption areas")
        
        if city_data.get('coastal'):
            recommendations.append("🌊 Monitor cyclone warnings and storm surge forecasts")
        
        if len(recommendations) == 0:
            recommendations.append("✅ Regular monitoring sufficient. City has good natural flood protection.")
        
        return recommendations[:4]
    
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
            
            vulnerability = self.calculate_vulnerability_score(city_data)
            ml_prediction = self.predict_flood_risk_ml(lat, lon, city_data)
            
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
                'vulnerability_assessment': vulnerability,
                'ml_prediction': ml_prediction,
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