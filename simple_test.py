def test_monitoring_config():
    """Test the monitoring system configuration"""
    # Alert thresholds
    alert_thresholds = {
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
    
    # Geofence settings
    geofence = {
        'center': (23.0225, 72.5714),  # Ahmedabad coordinates
        'radius': 1.0,  # km
        'safe_zones': [
            {'name': 'Grazing Area 1', 'center': (23.0225, 72.5714), 'radius': 0.5},
            {'name': 'Water Source', 'center': (23.0230, 72.5720), 'radius': 0.1}
        ]
    }
    
    # Behavior patterns
    behavior_patterns = {
        'normal_grazing': {'start_time': '06:00', 'end_time': '18:00', 'min_motion': 0.3},
        'rest_period': {'start_time': '22:00', 'end_time': '04:00', 'max_motion': 0.2},
        'water_breaks': {'frequency': 6, 'duration': 15}  # minutes
    }
    
    # Print configurations
    print("Cow Monitoring System Configuration Test")
    print("======================================")
    
    print("\nAlert Thresholds:")
    for key, value in alert_thresholds.items():
        print(f"{key}: {value}")
    
    print("\nGeofence Settings:")
    print(f"Center: {geofence['center']}")
    print(f"Radius: {geofence['radius']} km")
    print("\nSafe Zones:")
    for zone in geofence['safe_zones']:
        print(f"- {zone['name']}: center={zone['center']}, radius={zone['radius']}km")
    
    print("\nBehavior Patterns:")
    for key, value in behavior_patterns.items():
        print(f"{key}: {value}")

def test_alert_scenarios():
    """Test various alert scenarios"""
    print("\nTesting Alert Scenarios")
    print("======================")
    
    # Test temperature alerts
    temp = 40.0
    print(f"\nTemperature: {temp}°C")
    if temp >= 41.0:
        print("ALERT: Critical temperature!")
    elif temp > 39.5:
        print("ALERT: High temperature")
    elif temp < 37.5:
        print("ALERT: Low temperature")
    else:
        print("Temperature is normal")
    
    # Test motion alerts
    motion = 2.5
    print(f"\nMotion: {motion}g")
    if motion > 3.0:
        print("ALERT: Jumping detected!")
    elif motion > 2.0:
        print("ALERT: Excessive motion")
    elif motion < 0.1:
        print("ALERT: No motion detected")
    else:
        print("Motion is normal")
    
    # Test battery alerts
    battery = 15
    print(f"\nBattery: {battery}%")
    if battery <= 10:
        print("ALERT: Critical battery level!")
    elif battery <= 20:
        print("ALERT: Low battery")
    else:
        print("Battery level is normal")

if __name__ == "__main__":
    test_monitoring_config()
    test_alert_scenarios()
