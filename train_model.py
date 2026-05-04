# train_model.py
import ee
import geemap
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# Initialize GEE
ee.Initialize(project='your-gcp-project-id')

# Define multiple flood events across India
flood_events = [
    {'region': 'Bihar', 'start': '2021-07-15', 'end': '2021-08-15', 'roi': ee.Geometry.Rectangle([83.5, 25.0, 88.0, 27.5])},
    {'region': 'Assam', 'start': '2022-06-20', 'end': '2022-07-10', 'roi': ee.Geometry.Rectangle([89.5, 26.0, 96.0, 28.0])},
    {'region': 'Gujarat', 'start': '2022-08-10', 'end': '2022-08-25', 'roi': ee.Geometry.Rectangle([68.0, 20.5, 74.5, 24.5])},
    # Add more events for better generalization
]

def create_training_data(flood_event):
    """Extract features and labels for a single flood event"""
    predictor = FloodPredictor()
    
    # Extract features
    features = predictor.extract_features(
        flood_event['roi'], 
        flood_event['start'], 
        flood_event['end']
    )
    
    # Create labels (1 = flooded, 0 = not flooded)
    # Using Sentinel-1 to identify actual flooded areas
    post_water = predictor.get_sentinel1_collection(
        flood_event['end'], flood_event['end'], flood_event['roi']
    )
    labels = post_water.lt(-15).rename('flooded')  # Water appears dark in SAR
    
    # Sample points for training
    training_data = features.addBands(labels).stratifiedSample(
        numPoints=5000,
        classBand='flooded',
        region=flood_event['roi'],
        scale=100,
        seed=42
    )
    return training_data

# Collect training data from all events
all_training_data = ee.FeatureCollection([])
for event in flood_events:
    data = create_training_data(event)
    all_training_data = all_training_data.merge(data)

# Train Random Forest classifier
classifier = ee.Classifier.smileRandomForest(numberOfTrees=100).train(
    features=all_training_data,
    classProperty='flooded',
    inputProperties=['water_change', 'rainfall', 'elevation', 'slope']
)

# Export the trained classifier
# Note: For local use, you'd convert the ee.Classifier to a format joblib can save
# The geemap library provides utilities for this conversion [13†L4-L8]
joblib.dump(classifier, 'flood_risk_model.pkl')
print("Model training complete and saved as flood_risk_model.pkl")