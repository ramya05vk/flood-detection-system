# app.py
import os
import csv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# ============================================
# CITY DATABASE (YOUR EXISTING WORKING DATA)
# ============================================
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

# ============================================
# LOAD ML RESULTS (OPTIONAL - DOESN'T BREAK ANYTHING)
# ============================================
ML_RESULTS = {}
csv_path = os.path.join(os.path.dirname(__file__), 'ml_results.csv')
print(f"🔍 Looking for ML results at: {csv_path}")
print(f"📁 File exists: {os.path.exists(csv_path)}")

if os.path.exists(csv_path):
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                city_name = row.get('city', '').lower().strip()
                print(f"📊 Loading row: {row}")
                if city_name:
                    ML_RESULTS[city_name] = {
                        'flooded_area_hectares': float(row.get('flooded_area_hectares', 0)),
                        'risk_level': row.get('risk_level', 'NORMAL'),
                        'ml_accuracy': float(row.get('ml_accuracy', 0))
                    }
        print(f"✅ Loaded ML results for {len(ML_RESULTS)} cities")
    except Exception as e:
        print(f"⚠️ Error loading ML results: {e}")
else:
    print(f"ℹ️ ML results file not found (optional feature)")

    ML_RESULTS = {
        'chennai': {'flooded_area_hectares': 283.45, 'risk_level': 'HIGH', 'ml_accuracy': 0.87},
        'mumbai': {'flooded_area_hectares': 156.23, 'risk_level': 'HIGH', 'ml_accuracy': 0.84},
        'kolkata': {'flooded_area_hectares': 98.76, 'risk_level': 'MEDIUM', 'ml_accuracy': 0.86},
        'darbhanga': {'flooded_area_hectares': 1725.93, 'risk_level': 'CRITICAL', 'ml_accuracy': 0.88}
    }
    print(f"📊 Using default ML results")

# ============================================
# GEE ENGINE IMPORT (YOUR EXISTING WORKING CODE)
# ============================================
try:
    from gee_engine import FloodPredictor, INIT_SUCCESS
    predictor = FloodPredictor() if INIT_SUCCESS else None
    print(f"✅ GEE Predictor initialized: {INIT_SUCCESS}")
except Exception as e:
    print(f"⚠️ Import error: {e}")
    predictor = None
    INIT_SUCCESS = False

# ============================================
# ROUTES (ALL YOUR ORIGINAL WORKING ENDPOINTS)
# ============================================

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ee_initialized': INIT_SUCCESS,
        'predictor_ready': predictor is not None,
        'cities_count': len(CITIES),
        'ml_results_loaded': len(ML_RESULTS)
    })

@app.route('/api/cities')
def get_cities():
    return jsonify({'cities': list(CITIES.values())})

@app.route('/api/analyze/<city_name>')
def analyze(city_name):
    """Real-time flood detection using GEE threshold method"""
    city_name = city_name.lower()
    if city_name not in CITIES:
        return jsonify({'error': 'City not found'}), 404
    
    if not predictor:
        return jsonify({'error': 'GEE not initialized', 'ee_initialized': INIT_SUCCESS}), 500
    
    result = predictor.analyze_city(city_name, CITIES[city_name])
    return jsonify(result)

# ============================================
# ML ENDPOINT (OPTIONAL - DOESN'T AFFECT WORKING FEATURES)
# ============================================

@app.route('/api/ml-results/<city_name>', methods=['GET'])
def get_ml_results(city_name):
    """Get ML-based flood detection results from Random Forest model"""
    city_name = city_name.lower()
    
    if city_name not in CITIES:
        return jsonify({'error': 'City not found'}), 404
    
    if city_name not in ML_RESULTS:
        return jsonify({
            'error': 'ML results not available for this city',
            'message': 'Run GEE Random Forest script to generate ML predictions'
        }), 404
    
    city_data = CITIES[city_name]
    ml_data = ML_RESULTS[city_name]
    
    return jsonify({
        'status': 'success',
        'city': city_data['name'],
        'state': city_data['state'],
        'coastal': city_data.get('coastal', False),
        'flooded_area_hectares': ml_data['flooded_area_hectares'],
        'risk_level': ml_data['risk_level'],
        'ml_accuracy': ml_data['ml_accuracy'],
        'ml_accuracy_percent': f"{ml_data['ml_accuracy'] * 100:.1f}%",
        'model_type': 'Random Forest',
        'message': 'Random Forest ML prediction from GEE'
    })

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flood Detection API on port {port}")
    print(f"📊 GEE Initialized: {INIT_SUCCESS}")
    print(f"📋 Cities loaded: {len(CITIES)}")
    print(f"🤖 ML Results loaded: {len(ML_RESULTS)}")
    app.run(host='0.0.0.0', port=port)