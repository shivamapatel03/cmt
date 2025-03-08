from flask import Flask, jsonify, request
from cow_monitor import CowMonitoringSystem
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Initialize the monitoring system
monitor = CowMonitoringSystem(
    channel_id="2864424",
    api_key="5J2F0XY1N3FO6GZF"
)

# Global variables to store cached data
cached_data = {
    'current_status': None,
    'alerts': [],
    'report': None,
    'recommendations': [],
    'historical_data': [],
    'behavior_analysis': None,
    'health_status': None,
    'last_updated': None
}

def update_cache():
    """Enhanced background task to update cached data"""
    while True:
        try:
            # Fetch and process data
            raw_data = monitor.fetch_data(results=100)
            if raw_data:
                df = monitor.process_data(raw_data)
                df = monitor.calculate_motion_metrics(df)
                df = monitor.detect_anomalies(df)

                # Update current status with enhanced metrics
                latest = df.iloc[-1]
                cached_data['current_status'] = {
                    'temperature': float(latest['temperature']),
                    'battery': float(latest['battery']),
                    'motion_level': float(latest['motion_magnitude']),
                    'speed': float(latest['speed']),
                    'latitude': float(latest['latitude']),
                    'longitude': float(latest['longitude']),
                    'activity_score': float(latest['activity_score']),
                    'is_grazing': bool(latest['is_grazing']),
                    'is_resting': bool(latest['is_resting']),
                    'timestamp': latest['created_at'].isoformat()
                }

                # Update alerts with enhanced detection
                cached_data['alerts'] = monitor.check_alerts(df)

                # Update report
                cached_data['report'] = monitor.generate_report(df)

                # Update weather-based recommendations
                weather_data = monitor.get_weather_data(
                    latest['latitude'],
                    latest['longitude']
                )
                cached_data['recommendations'] = monitor.get_recommendations(df, weather_data)

                # Update historical data
                cached_data['historical_data'] = df.tail(24).to_dict('records')  # Last 2 hours

                # Calculate health status
                cached_data['health_status'] = calculate_health_status(df)

                # Analyze behavior patterns
                cached_data['behavior_analysis'] = analyze_behavior_patterns(df)

                # Update timestamp
                cached_data['last_updated'] = time.time()

        except Exception as e:
            print(f"Error updating cache: {e}")

        # Wait for 15 seconds before next update
        time.sleep(15)

def calculate_health_status(df):
    """Calculate overall health status based on multiple metrics"""
    if df is None or df.empty:
        return None

    latest = df.iloc[-1]
    recent = df.tail(12)  # Last hour

    # Calculate various health indicators
    temp_normal = 37.5 <= latest['temperature'] <= 39.5
    activity_normal = 0.1 <= recent['motion_magnitude'].mean() <= 2.0
    rest_periods = len(recent[recent['is_resting']]) / len(recent)
    grazing_periods = len(recent[recent['is_grazing']]) / len(recent)

    # Calculate health score (0-100)
    health_score = 100

    # Temperature impact
    if not temp_normal:
        health_score -= 20
    
    # Activity impact
    if not activity_normal:
        health_score -= 15

    # Rest patterns impact
    if rest_periods < 0.2 or rest_periods > 0.8:  # Abnormal rest patterns
        health_score -= 10

    # Grazing patterns impact
    if grazing_periods < 0.3 and latest['is_daytime']:  # Low grazing during day
        health_score -= 10

    # Battery impact
    if latest['battery'] < 20:
        health_score -= 5

    return {
        'score': max(0, health_score),
        'temperature_status': 'normal' if temp_normal else 'abnormal',
        'activity_status': 'normal' if activity_normal else 'abnormal',
        'rest_ratio': float(rest_periods),
        'grazing_ratio': float(grazing_periods),
        'timestamp': latest['created_at'].isoformat()
    }

def analyze_behavior_patterns(df):
    """Analyze behavioral patterns over time"""
    if df is None or df.empty:
        return None

    # Calculate time-based metrics
    hourly_activity = df.groupby(df['created_at'].dt.hour)['motion_magnitude'].mean().to_dict()
    grazing_periods = df[df['is_grazing']]['created_at'].dt.hour.value_counts().to_dict()
    rest_periods = df[df['is_resting']]['created_at'].dt.hour.value_counts().to_dict()

    # Analyze motion patterns
    motion_patterns = {
        'avg_daily_activity': float(df['motion_magnitude'].mean()),
        'peak_activity_hour': max(hourly_activity.items(), key=lambda x: x[1])[0],
        'main_grazing_hours': [hour for hour, count in grazing_periods.items() if count > len(df) / 48],
        'main_rest_hours': [hour for hour, count in rest_periods.items() if count > len(df) / 48]
    }

    return {
        'hourly_activity': hourly_activity,
        'grazing_patterns': grazing_periods,
        'rest_patterns': rest_periods,
        'motion_patterns': motion_patterns,
        'timestamp': df.iloc[-1]['created_at'].isoformat()
    }

@app.route('/api/status')
def get_status():
    """Get enhanced current status of the cow"""
    return jsonify(cached_data['current_status'])

@app.route('/api/alerts')
def get_alerts():
    """Get active alerts with filtering options"""
    severity = request.args.get('severity')
    alert_type = request.args.get('type')
    
    alerts = cached_data['alerts']
    
    if severity:
        alerts = [a for a in alerts if a['severity'] == severity]
    if alert_type:
        alerts = [a for a in alerts if a['type'] == alert_type]
        
    return jsonify(alerts)

@app.route('/api/report')
def get_report():
    """Get statistical report with time range option"""
    time_range = request.args.get('range', 'daily')  # daily, weekly, monthly
    return jsonify(cached_data['report'])

@app.route('/api/recommendations')
def get_recommendations():
    """Get current recommendations with priority filtering"""
    priority = request.args.get('priority')
    
    recommendations = cached_data['recommendations']
    
    if priority:
        recommendations = [r for r in recommendations if r['priority'] == priority]
        
    return jsonify(recommendations)

@app.route('/api/health')
def get_health_status():
    """Get detailed health status"""
    return jsonify(cached_data['health_status'])

@app.route('/api/behavior')
def get_behavior_analysis():
    """Get behavior analysis results"""
    return jsonify(cached_data['behavior_analysis'])

@app.route('/api/historical')
def get_historical_data():
    """Get historical data with time range and metric filtering"""
    hours = int(request.args.get('hours', 2))
    metrics = request.args.get('metrics', '').split(',')
    
    data = cached_data['historical_data']
    
    if metrics and metrics[0]:  # If specific metrics requested
        data = [{k: v for k, v in record.items() if k in metrics} for record in data]
    
    return jsonify(data[-hours*12:])  # Assuming 5-minute intervals

@app.route('/api/summary')
def get_summary():
    """Get a comprehensive summary of all monitoring aspects"""
    return jsonify({
        'status': cached_data['current_status'],
        'health': cached_data['health_status'],
        'active_alerts': len([a for a in cached_data['alerts'] if a['severity'] in ['high', 'critical']]),
        'behavior': cached_data['behavior_analysis'],
        'last_updated': cached_data['last_updated']
    })

@app.route('/api/all')
def get_all_data():
    """Get all monitoring data"""
    return jsonify(cached_data)

def start_background_tasks():
    """Start background tasks"""
    update_thread = threading.Thread(target=update_cache, daemon=True)
    update_thread.start()

if __name__ == '__main__':
    start_background_tasks()
    app.run(debug=True, port=5000) 