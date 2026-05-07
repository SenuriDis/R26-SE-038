def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit"""
    return (celsius * 9/5) + 32


def fahrenheit_to_celsius(fahrenheit):
    """Convert Fahrenheit to Celsius"""
    return (fahrenheit - 32) * 5/9


def heat_index(temp_celsius, humidity):
    """Calculate heat index (feels like temperature)"""
    if temp_celsius < 27:
        return temp_celsius
    
    # Simplified heat index formula
    hi = temp_celsius + (humidity / 100) * 0.5
    return round(hi, 1)


def wind_chill(temp_celsius, wind_speed_kmh):
    """Calculate wind chill temperature"""
    if temp_celsius > 10 or wind_speed_kmh < 4.8:
        return temp_celsius
    
    # Wind chill formula for Celsius
    wc = 13.12 + 0.6215 * temp_celsius - 11.37 * (wind_speed_kmh ** 0.16) + 0.3965 * temp_celsius * (wind_speed_kmh ** 0.16)
    return round(wc, 1)


def calculate_uv_index(ozone, angle, cloud_cover):
    """Calculate UV index based on ozone, sun angle, and cloud cover"""
    base_uv = ozone / 300 * 10
    
    if angle > 90:
        angle = 90
    
    angle_factor = angle / 90
    uv = base_uv * angle_factor
    
    cloud_factor = 1 - (cloud_cover / 100) * 0.5
    uv = uv * cloud_factor
    
    return round(max(0, uv), 1)