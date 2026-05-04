# app.py
import os
import sys
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    from gee_engine import FloodPredictor, INIT_SUCCESS
except Exception as e:
    logger.error(f"Failed to import: {e}")
    INIT_SUCCESS = False

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

predictor = None
if True:  # Always try to create predictor
    try:
        predictor = FloodPredictor()
        logger.info("FloodPredictor created")
    except Exception as e:
        logger.error(f"Failed: {e}")

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ee_initialized': INIT_SUCCESS,
        'predictor_ready': predictor is not None,
        'cities_count': len(predictor.get_all_cities()) if predictor else 0
    })

@app.route('/api/cities', methods=['GET'])
def get_cities():
    if not predictor:
        return jsonify({'error': 'Predictor not initialized'}), 500
    return jsonify({'cities': predictor.get_all_cities()})

@app.route('/api/analyze/<city_name>', methods=['GET'])
def analyze_city(city_name):
    if not predictor:
        return jsonify({'error': 'Predictor not initialized'}), 500
    result = predictor.analyze_city_flood_risk(city_name)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=False, host='0.0.0.0', port=port)