import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import geopy.distance
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class CowMonitoringSystem:
    def __init__(self, channel_id, api_key):
        self.channel_id = channel_id
        self.api_key = api_key
        self.base_url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"
        self.alert_thresholds = {
            'temp_high': 39.5,      # °C
            'temp_low': 37.5,       # °C
            'temp_critical': 41.0,   # °C
            'motion_high': 2.0,     # g
            'motion_low': 0.1,      # g
            'speed_high': 20,       # km/h
            'speed_very_high': 30,  # km/h
            'battery_low': 20,      # %
            'battery_critical': 10, # %
            'inactivity_time': 60,  # minutes
            'rapid_temp_change': 1.5, # °C per hour
            'sustained_motion': 1.8,  # g for extended period
            'rest_period': 120,      # minutes without significant motion
            'grazing_threshold': 0.5, # g - typical grazing motion
            'jumping_threshold': 3.0  # g - sudden vertical acceleration
        }
        self.geofence = {
            'center': (23.0225, 72.5714),  # Ahmedabad coordinates
            'radius': 1.0,  # km
            'safe_zones': [
                {'name': 'Grazing Area 1', 'center': (23.0225, 72.5714), 'radius': 0.5},
                {'name': 'Water Source', 'center': (23.0230, 72.5720), 'radius': 0.1}
            ]
        }
        self.behavior_patterns = {
            'normal_grazing': {'start_time': '06:00', 'end_time': '18:00', 'min_motion': 0.3},
            'rest_period': {'start_time': '22:00', 'end_time': '04:00', 'max_motion': 0.2},
            'water_breaks': {'frequency': 6, 'duration': 15}  # minutes
        }

    def fetch_data(self, results=100):
        """Fetch data from ThingSpeak"""
        params = {
            'api_key': self.api_key,
            'results': results
        }
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()['feeds']
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

    def process_data(self, data):
        """Process raw data into structured format with enhanced metrics"""
        if not data:
            return None

        df = pd.DataFrame(data)
        
        # Convert timestamp
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Convert fields to numeric
        for i in range(1, 9):
            field = f'field{i}'
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')

        # Rename columns for clarity
        df = df.rename(columns={
            'field1': 'temperature',
            'field2': 'battery',
            'field3': 'latitude',
            'field4': 'longitude',
            'field5': 'motion_x',
            'field6': 'motion_y',
            'field7': 'motion_z',
            'field8': 'speed'
        })

        # Calculate additional metrics
        df['hour'] = df['created_at'].dt.hour
        df['is_daytime'] = (df['hour'] >= 6) & (df['hour'] <= 18)
        
        # Calculate temperature change rate
        df['temp_change'] = df['temperature'].diff() / df['created_at'].diff().dt.total_seconds() * 3600
        
        # Calculate vertical acceleration (for jumping detection)
        df['vertical_acc'] = df['motion_y'].abs()
        
        # Detect behavior patterns
        df['is_grazing'] = (
            (df['motion_magnitude'] > self.alert_thresholds['grazing_threshold']) & 
            (df['motion_magnitude'] < self.alert_thresholds['motion_high']) &
            df['is_daytime']
        )
        
        # Calculate rest periods
        df['is_resting'] = df['motion_magnitude'] < self.alert_thresholds['motion_low']
        df['rest_duration'] = None
        rest_start = None
        
        for idx, row in df.iterrows():
            if row['is_resting'] and rest_start is None:
                rest_start = row['created_at']
            elif not row['is_resting']:
                rest_start = None
            
            if rest_start is not None:
                df.at[idx, 'rest_duration'] = (row['created_at'] - rest_start).total_seconds() / 60

        return df

    def calculate_motion_metrics(self, df):
        """Enhanced motion metrics calculation"""
        if df is None or df.empty:
            return None

        # Basic motion magnitude
        df['motion_magnitude'] = np.sqrt(
            df['motion_x']**2 + 
            df['motion_y']**2 + 
            df['motion_z']**2
        )

        # Activity periods
        df['is_active'] = df['motion_magnitude'] > self.alert_thresholds['motion_low']
        df['activity_change'] = df['is_active'].astype(int).diff()
        
        # Calculate motion patterns
        window_size = 10  # 10 samples for pattern detection
        df['motion_std'] = df['motion_magnitude'].rolling(window=window_size).std()
        df['motion_mean'] = df['motion_magnitude'].rolling(window=window_size).mean()
        
        # Detect jumping
        df['is_jumping'] = df['vertical_acc'] > self.alert_thresholds['jumping_threshold']
        
        # Detect sustained motion
        df['sustained_motion'] = (
            df['motion_mean'] > self.alert_thresholds['sustained_motion']
        ).astype(int)
        
        # Calculate activity score (0-100)
        df['activity_score'] = (
            (df['motion_magnitude'] / self.alert_thresholds['motion_high']) * 100
        ).clip(0, 100)
        
        return df

    def detect_anomalies(self, df):
        """Detect unusual behavior using machine learning"""
        if df is None or df.empty:
            return None

        # Prepare features for anomaly detection
        features = ['temperature', 'motion_magnitude', 'speed']
        X = df[features].dropna()
        
        if len(X) < 2:
            return None

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Apply DBSCAN for anomaly detection
        dbscan = DBSCAN(eps=0.5, min_samples=3)
        df['anomaly'] = pd.Series(dbscan.fit_predict(X_scaled), index=X.index)
        df['is_anomaly'] = df['anomaly'] == -1

        return df

    def check_alerts(self, df):
        """Enhanced alert checking with more specific conditions"""
        if df is None or df.empty:
            return []

        alerts = []
        latest = df.iloc[-1]
        recent_data = df.tail(12)  # Last hour of data (assuming 5-minute intervals)

        # Temperature alerts with different severity levels
        if latest['temperature'] >= self.alert_thresholds['temp_critical']:
            alerts.append({
                'type': 'CRITICAL_TEMPERATURE',
                'value': latest['temperature'],
                'timestamp': latest['created_at'],
                'severity': 'critical',
                'message': 'Temperature critically high! Immediate action required.'
            })
        elif latest['temperature'] > self.alert_thresholds['temp_high']:
            alerts.append({
                'type': 'HIGH_TEMPERATURE',
                'value': latest['temperature'],
                'timestamp': latest['created_at'],
                'severity': 'high',
                'message': 'Temperature above normal range.'
            })
        elif latest['temperature'] < self.alert_thresholds['temp_low']:
            alerts.append({
                'type': 'LOW_TEMPERATURE',
                'value': latest['temperature'],
                'timestamp': latest['created_at'],
                'severity': 'high',
                'message': 'Temperature below normal range.'
            })

        # Rapid temperature change alert
        if abs(latest['temp_change']) > self.alert_thresholds['rapid_temp_change']:
            alerts.append({
                'type': 'RAPID_TEMPERATURE_CHANGE',
                'value': latest['temp_change'],
                'timestamp': latest['created_at'],
                'severity': 'high',
                'message': 'Rapid temperature change detected.'
            })

        # Motion-based alerts
        if latest['is_jumping']:
            alerts.append({
                'type': 'JUMPING_DETECTED',
                'value': latest['vertical_acc'],
                'timestamp': latest['created_at'],
                'severity': 'medium',
                'message': 'Unusual jumping activity detected.'
            })

        if latest['sustained_motion'] == 1:
            alerts.append({
                'type': 'SUSTAINED_MOTION',
                'value': latest['motion_mean'],
                'timestamp': latest['created_at'],
                'severity': 'medium',
                'message': 'Extended period of high activity detected.'
            })

        # Inactivity alert with context
        if latest['rest_duration'] and latest['rest_duration'] > self.alert_thresholds['inactivity_time']:
            if latest['is_daytime']:
                alerts.append({
                    'type': 'UNUSUAL_INACTIVITY',
                    'value': latest['rest_duration'],
                    'timestamp': latest['created_at'],
                    'severity': 'high',
                    'message': 'Unusual inactivity during daytime.'
                })

        # Battery alerts with different severity levels
        if latest['battery'] <= self.alert_thresholds['battery_critical']:
            alerts.append({
                'type': 'CRITICAL_BATTERY',
                'value': latest['battery'],
                'timestamp': latest['created_at'],
                'severity': 'critical',
                'message': 'Battery critically low! Immediate charging required.'
            })
        elif latest['battery'] <= self.alert_thresholds['battery_low']:
            alerts.append({
                'type': 'LOW_BATTERY',
                'value': latest['battery'],
                'timestamp': latest['created_at'],
                'severity': 'medium',
                'message': 'Battery level low.'
            })

        # Speed-based alerts
        if latest['speed'] > self.alert_thresholds['speed_very_high']:
            alerts.append({
                'type': 'CRITICAL_SPEED',
                'value': latest['speed'],
                'timestamp': latest['created_at'],
                'severity': 'critical',
                'message': 'Extremely high speed detected! Possible theft.'
            })
        elif latest['speed'] > self.alert_thresholds['speed_high']:
            alerts.append({
                'type': 'HIGH_SPEED',
                'value': latest['speed'],
                'timestamp': latest['created_at'],
                'severity': 'high',
                'message': 'Unusually high speed detected.'
            })

        # Enhanced geofencing alerts
        current_pos = (latest['latitude'], latest['longitude'])
        main_distance = geopy.distance.distance(self.geofence['center'], current_pos).km
        
        if main_distance > self.geofence['radius']:
            # Check if in any safe zone
            in_safe_zone = False
            for zone in self.geofence['safe_zones']:
                zone_distance = geopy.distance.distance(zone['center'], current_pos).km
                if zone_distance <= zone['radius']:
                    in_safe_zone = True
                    break
            
            if not in_safe_zone:
                alerts.append({
                    'type': 'GEOFENCE_BREACH',
                    'value': main_distance,
                    'timestamp': latest['created_at'],
                    'severity': 'critical',
                    'message': f'Cow has left the designated area. Distance: {main_distance:.2f}km'
                })

        # Behavior pattern alerts
        current_time = latest['created_at'].strftime('%H:%M')
        if (current_time >= self.behavior_patterns['normal_grazing']['start_time'] and 
            current_time <= self.behavior_patterns['normal_grazing']['end_time']):
            if not any(recent_data['is_grazing']):
                alerts.append({
                    'type': 'ABNORMAL_BEHAVIOR',
                    'value': latest['motion_magnitude'],
                    'timestamp': latest['created_at'],
                    'severity': 'medium',
                    'message': 'No grazing activity detected during normal grazing hours.'
                })

        return alerts

    def generate_report(self, df, report_type='daily'):
        """Generate statistical report"""
        if df is None or df.empty:
            return None

        report = {
            'period': report_type,
            'start_time': df['created_at'].min(),
            'end_time': df['created_at'].max(),
            'metrics': {
                'temperature': {
                    'avg': df['temperature'].mean(),
                    'min': df['temperature'].min(),
                    'max': df['temperature'].max()
                },
                'motion': {
                    'avg': df['motion_magnitude'].mean(),
                    'active_periods': len(df[df['activity_change'] == 1]),
                    'rest_periods': len(df[df['activity_change'] == -1])
                },
                'location': {
                    'total_distance': self.calculate_total_distance(df),
                    'avg_speed': df['speed'].mean()
                },
                'battery': {
                    'current': df['battery'].iloc[-1],
                    'avg_consumption': (df['battery'].iloc[0] - df['battery'].iloc[-1]) / len(df)
                }
            },
            'alerts': {
                'total': len(df[df['is_anomaly']]),
                'high_temp': len(df[df['temperature'] > self.alert_thresholds['temp_high']]),
                'low_temp': len(df[df['temperature'] < self.alert_thresholds['temp_low']]),
                'excessive_motion': len(df[df['motion_magnitude'] > self.alert_thresholds['motion_high']]),
                'no_motion': len(df[df['motion_magnitude'] < self.alert_thresholds['motion_low']])
            }
        }

        return report

    def calculate_total_distance(self, df):
        """Calculate total distance traveled"""
        if df is None or df.empty or len(df) < 2:
            return 0

        total_distance = 0
        prev_pos = None

        for _, row in df.iterrows():
            current_pos = (row['latitude'], row['longitude'])
            if prev_pos is not None:
                distance = geopy.distance.distance(prev_pos, current_pos).km
                total_distance += distance
            prev_pos = current_pos

        return total_distance

    def get_weather_data(self, lat, lon):
        """Fetch weather data for location"""
        weather_api_key = "YOUR_WEATHER_API_KEY"  # Replace with actual API key
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_api_key}&units=metric"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return None

    def get_recommendations(self, df, weather_data):
        """Enhanced recommendations with more context"""
        if df is None or df.empty or weather_data is None:
            return []

        recommendations = []
        latest = df.iloc[-1]
        recent_data = df.tail(12)  # Last hour of data

        # Temperature-based recommendations
        if latest['temperature'] > self.alert_thresholds['temp_high']:
            recommendations.append({
                'type': 'COOLING',
                'priority': 'high',
                'message': 'Move the cow to a shaded area and provide cooling measures',
                'actions': [
                    'Ensure access to fresh water',
                    'Provide shade or shelter',
                    'Consider using cooling fans',
                    'Monitor for heat stress symptoms'
                ]
            })

        # Weather-based recommendations
        if weather_data['main']['temp'] > 30:
            recommendations.append({
                'type': 'HYDRATION',
                'priority': 'high',
                'message': 'High environmental temperature detected',
                'actions': [
                    'Increase water availability',
                    'Add electrolytes to water',
                    'Monitor water consumption',
                    'Provide salt licks'
                ]
            })
        elif weather_data['main']['temp'] < 10:
            recommendations.append({
                'type': 'SHELTER',
                'priority': 'medium',
                'message': 'Cold weather conditions detected',
                'actions': [
                    'Provide warm shelter',
                    'Increase feed rations',
                    'Check for draft-free areas',
                    'Monitor body temperature'
                ]
            })

        # Activity-based recommendations
        if recent_data['motion_magnitude'].mean() < self.alert_thresholds['motion_low']:
            recommendations.append({
                'type': 'ACTIVITY',
                'priority': 'medium',
                'message': 'Low activity levels detected',
                'actions': [
                    'Check for signs of illness',
                    'Evaluate feed quality',
                    'Consider veterinary check-up',
                    'Monitor eating patterns'
                ]
            })

        # Grazing recommendations
        if not any(recent_data['is_grazing']) and latest['is_daytime']:
            recommendations.append({
                'type': 'GRAZING',
                'priority': 'medium',
                'message': 'Reduced grazing activity during normal hours',
                'actions': [
                    'Check pasture quality',
                    'Rotate grazing area',
                    'Evaluate feed supplements',
                    'Monitor for illness'
                ]
            })

        # Battery management
        if latest['battery'] < self.alert_thresholds['battery_low']:
            recommendations.append({
                'type': 'BATTERY',
                'priority': 'high',
                'message': 'Low battery level detected',
                'actions': [
                    'Charge device immediately',
                    'Check charging system',
                    'Consider backup device',
                    'Monitor charging pattern'
                ]
            })

        return recommendations

def main():
    # Initialize the monitoring system
    channel_id = "2864424"  # Your ThingSpeak channel ID
    api_key = "5J2F0XY1N3FO6GZF"  # Your ThingSpeak API key
    
    monitor = CowMonitoringSystem(channel_id, api_key)
    
    # Fetch and process data
    raw_data = monitor.fetch_data(results=100)
    if raw_data:
        # Process the data
        df = monitor.process_data(raw_data)
        df = monitor.calculate_motion_metrics(df)
        df = monitor.detect_anomalies(df)
        
        # Check for alerts
        alerts = monitor.check_alerts(df)
        
        # Generate report
        report = monitor.generate_report(df)
        
        # Get weather data and recommendations
        if not df.empty:
            weather_data = monitor.get_weather_data(
                df['latitude'].iloc[-1],
                df['longitude'].iloc[-1]
            )
            recommendations = monitor.get_recommendations(df, weather_data)
            
            # Print some results
            print("\n=== Current Status ===")
            print(f"Temperature: {df['temperature'].iloc[-1]:.1f}°C")
            print(f"Battery: {df['battery'].iloc[-1]:.1f}%")
            print(f"Motion Level: {df['motion_magnitude'].iloc[-1]:.2f}")
            
            print("\n=== Active Alerts ===")
            for alert in alerts:
                print(f"{alert['type']}: {alert['value']} ({alert['severity']})")
            
            print("\n=== Recommendations ===")
            for rec in recommendations:
                print(f"{rec['type']}: {rec['message']}")

if __name__ == "__main__":
    main() 