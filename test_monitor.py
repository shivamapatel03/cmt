from cow_monitor import CowMonitoringSystem

def test_thresholds():
    """Test the alert thresholds configuration"""
    monitor = CowMonitoringSystem(channel_id="test", api_key="test")
    
    # Print alert thresholds
    print("\nAlert Thresholds:")
    for key, value in monitor.alert_thresholds.items():
        print(f"{key}: {value}")
    
    # Print geofence settings
    print("\nGeofence Settings:")
    print(f"Center: {monitor.geofence['center']}")
    print(f"Radius: {monitor.geofence['radius']} km")
    print("\nSafe Zones:")
    for zone in monitor.geofence['safe_zones']:
        print(f"- {zone['name']}: center={zone['center']}, radius={zone['radius']}km")
    
    # Print behavior patterns
    print("\nBehavior Patterns:")
    for key, value in monitor.behavior_patterns.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    print("Testing Cow Monitoring System Configuration")
    print("=========================================")
    test_thresholds() 