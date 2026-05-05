# app.py
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

CITIES = {
    'chennai': {
        'name': 'Chennai', 'state': 'Tamil Nadu', 'lat': 13.08, 'lon': 80.27,
        'coastal': True, 'population': 7000000, 'area_sqkm': 426,
        'flood_causes': 'Cyclones, northeast monsoon, urban flooding',
        'avg_elevation_m': 6, 'avg_slope_deg': 0.5, 'drainage_score': 3, 'historical_flood_count': 4,
        'historical_floods': [
            {'date': '2023-12-05', 'cause': 'Cyclone Michaung', 'affected': 400000, 'severity': 'high'}
        ]
    },
    'mumbai': {
        'name': 'Mumbai', 'state': 'Maharashtra', 'lat': 19.08, 'lon': 72.88,
        'coastal': True, 'population': 12400000, 'area_sqkm': 600,
        'flood_causes': 'Urban drainage failure, high tide, extreme rainfall',
        'avg_elevation_m': 10, 'avg_slope_deg': 1.2, 'drainage_score': 2, 'historical_flood_count': 6,
        'historical_floods': [
            {'date': '2023-07-25', 'cause': 'Urban drainage failure', 'affected': 500000, 'severity': 'high'}
        ]
    },
    'darbhanga': {
        'name': 'Darbhanga', 'state': 'Bihar', 'lat': 26.15, 'lon': 85.90,
        'coastal': False, 'population': 400000, 'area_sqkm': 50,
        'flood_causes': 'Kosi river overflow, heavy monsoon rainfall',
        'avg_elevation_m': 45, 'avg_slope_deg': 0.3, 'drainage_score': 4, 'historical_flood_count': 5,
        'historical_floods': [
            {'date': '2024-07-15', 'cause': 'Kosi river overflow', 'affected': 250000, 'severity': 'high'}
        ]
    },
    'kolkata': {
        'name': 'Kolkata', 'state': 'West Bengal', 'lat': 22.57, 'lon': 88.36,
        'coastal': True, 'population': 4500000, 'area_sqkm': 205,
        'flood_causes': 'Hooghly river overflow, cyclones, tidal surge',
        'avg_elevation_m': 4, 'avg_slope_deg': 0.2, 'drainage_score': 3, 'historical_flood_count': 5,
        'historical_floods': []
    },
    'bangalore': {
        'name': 'Bangalore', 'state': 'Karnataka', 'lat': 12.97, 'lon': 77.59,
        'coastal': False, 'population': 8500000, 'area_sqkm': 741,
        'flood_causes': 'Poor urban drainage, lake overflow',
        'avg_elevation_m': 920, 'avg_slope_deg': 3.5, 'drainage_score': 3, 'historical_flood_count': 2,
        'historical_floods': []
    },
    'delhi': {
        'name': 'Delhi', 'state': 'Delhi', 'lat': 28.61, 'lon': 77.23,
        'coastal': False, 'population': 16700000, 'area_sqkm': 1484,
        'flood_causes': 'Yamuna river overflow, urban flooding',
        'avg_elevation_m': 216, 'avg_slope_deg': 1.5, 'drainage_score': 5, 'historical_flood_count': 3,
        'historical_floods': []
    }
}

try:
    from gee_engine import FloodPredictor, INIT_SUCCESS
    predictor = FloodPredictor() if INIT_SUCCESS else None
except Exception as e:
    print(f"Import error: {e}")
    predictor = None
    INIT_SUCCESS = False

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'ee_initialized': INIT_SUCCESS,
        'predictor_ready': predictor is not None,
        'cities_count': len(CITIES)
    })

@app.route('/api/cities')
def get_cities():
    return jsonify({'cities': list(CITIES.values())})

@app.route('/api/analyze/<city_name>')
def analyze(city_name):
    city_name = city_name.lower()
    if city_name not in CITIES:
        return jsonify({'error': 'City not found'}), 404
    
    if not predictor:
        return jsonify({'error': 'GEE not initialized', 'ee_initialized': INIT_SUCCESS}), 500
    
    result = predictor.analyze_city(city_name, CITIES[city_name])
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)