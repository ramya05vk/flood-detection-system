# pipeline.py
import schedule
import time
from gee_engine import FloodPredictor
import ee
from datetime import datetime, timedelta
import requests
from twilio.rest import Client

# Configuration
HIGH_RISK_DISTRICTS = [
    {'name': 'Darbhanga', 'lat': 26.15, 'lon': 85.90},
    {'name': 'Katihar', 'lat': 25.55, 'lon': 87.58},
    {'name': 'Purnea', 'lat': 25.78, 'lon': 87.47},
    # Add more high-risk districts across India
]
RAIN_THRESHOLD_MM = 50

def check_and_predict():
    """Main function to check rainfall and run predictions"""
    print(f"\n--- Running pipeline at {datetime.now()} ---")
    
    for district in HIGH_RISK_DISTRICTS:
        # Check rainfall forecast
        rain = check_rainfall(district['lat'], district['lon'])
        
        if rain > RAIN_THRESHOLD_MM:
            print(f"⚠️ Rainfall threshold met for {district['name']}: {rain}mm")
            
            # Run flood prediction
            try:
                predictor = FloodPredictor()
                roi = ee.Geometry.Point([district['lon'], district['lat']]).buffer(10000)
                
                after_date = datetime.now().strftime('%Y-%m-%d')
                before_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                risk_map = predictor.predict_flood_risk(roi, before_date, after_date)
                
                # Process result and send alert if needed
                send_district_alert(district, risk_map)
                
            except Exception as e:
                print(f"Error processing {district['name']}: {e}")
        else:
            print(f"✅ Rainfall normal for {district['name']}: {rain}mm")

def check_rainfall(lat, lon):
    """Get rainfall forecast from Open-Meteo"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&forecast_days=1"
    response = requests.get(url).json()
    return response['daily']['precipitation_sum'][0]

def send_district_alert(district, risk_map):
    """Send SMS alert for high-risk districts"""
    # Extract flooded area from risk_map (simplified)
    # In production, you'd calculate actual area
    
    client = Client('YOUR_TWILIO_SID', 'YOUR_TWILIO_TOKEN')
    message = client.messages.create(
        body=f"⚠️ FLOOD WARNING for {district['name']}. Heavy rainfall predicted. Please stay alert.",
        from_='+12345678901',
        to='+919876543210'
    )
    print(f"Alert sent for {district['name']}: {message.sid}")

# Schedule the pipeline to run every 6 hours
schedule.every(6).hours.do(check_and_predict)

if __name__ == "__main__":
    print("Automated Flood Prediction Pipeline Started")
    print("Running scheduled checks every 6 hours...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute