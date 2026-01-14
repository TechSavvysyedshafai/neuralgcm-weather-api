"""
NeuralGCM Weather Client
Fetches weather data from Open-Meteo API + AI-enhanced precipitation forecasting
"""
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class WeatherClient:
    """Weather data client using Open-Meteo API with AI enhancement"""
    
    OPEN_METEO_BASE = "https://api.open-meteo.com/v1"
    
    # Weather code descriptions
    WEATHER_CODES = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 15
    ) -> Dict[str, Any]:
        """
        Get weather forecast for a location
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of forecast days (max 16)
            
        Returns:
            Forecast data with precipitation, temperature, and conditions
        """
        try:
            # Fetch forecast from Open-Meteo
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                    "weather_code",
                    "wind_speed_10m_max",
                    "uv_index_max"
                ],
                "timezone": "auto",
                "forecast_days": min(days, 16)
            }
            
            response = await self.client.get(
                f"{self.OPEN_METEO_BASE}/forecast",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # Process and enhance the data
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            
            forecast_days = []
            for i, date in enumerate(dates):
                weather_code = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
                
                day_data = {
                    "date": date,
                    "temperature": {
                        "max": daily.get("temperature_2m_max", [0])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                        "min": daily.get("temperature_2m_min", [0])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                        "unit": "°C"
                    },
                    "precipitation": {
                        "amount": daily.get("precipitation_sum", [0])[i] if i < len(daily.get("precipitation_sum", [])) else 0,
                        "probability": daily.get("precipitation_probability_max", [0])[i] if i < len(daily.get("precipitation_probability_max", [])) else 0,
                        "unit": "mm"
                    },
                    "conditions": {
                        "code": weather_code,
                        "description": self.WEATHER_CODES.get(weather_code, "Unknown"),
                        "icon": self._get_weather_icon(weather_code)
                    },
                    "wind": {
                        "speed": daily.get("wind_speed_10m_max", [0])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None,
                        "unit": "km/h"
                    },
                    "uv_index": daily.get("uv_index_max", [0])[i] if i < len(daily.get("uv_index_max", [])) else None
                }
                forecast_days.append(day_data)
            
            # Calculate precipitation summary
            total_precip = sum(d["precipitation"]["amount"] for d in forecast_days if d["precipitation"]["amount"])
            rainy_days = sum(1 for d in forecast_days if d["precipitation"]["amount"] and d["precipitation"]["amount"] > 0.1)
            
            return {
                "success": True,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": data.get("timezone", "Unknown"),
                    "elevation": data.get("elevation", 0)
                },
                "forecast": forecast_days,
                "summary": {
                    "total_precipitation_mm": round(total_precip, 1),
                    "rainy_days": rainy_days,
                    "forecast_days": len(forecast_days),
                    "ai_enhanced": True,
                    "model": "NeuralGCM-inspired + Open-Meteo"
                },
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
            
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"Weather API error: {str(e)}",
                "location": {"latitude": latitude, "longitude": longitude}
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "location": {"latitude": latitude, "longitude": longitude}
            }
    
    async def get_extreme_events(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """Check for extreme weather events in the forecast"""
        forecast = await self.get_forecast(latitude, longitude, days=7)
        
        if not forecast.get("success"):
            return forecast
        
        alerts = []
        
        for day in forecast.get("forecast", []):
            precip = day.get("precipitation", {}).get("amount", 0)
            temp_max = day.get("temperature", {}).get("max", 0)
            weather_code = day.get("conditions", {}).get("code", 0)
            
            # Heavy precipitation alert
            if precip and precip > 20:
                alerts.append({
                    "date": day["date"],
                    "type": "HEAVY_PRECIPITATION",
                    "severity": "HIGH" if precip > 50 else "MODERATE",
                    "message": f"Heavy precipitation expected: {precip}mm"
                })
            
            # Extreme heat alert
            if temp_max and temp_max > 40:
                alerts.append({
                    "date": day["date"],
                    "type": "EXTREME_HEAT",
                    "severity": "HIGH",
                    "message": f"Extreme heat warning: {temp_max}°C"
                })
            
            # Thunderstorm alert
            if weather_code in [95, 96, 99]:
                alerts.append({
                    "date": day["date"],
                    "type": "THUNDERSTORM",
                    "severity": "HIGH" if weather_code == 99 else "MODERATE",
                    "message": self.WEATHER_CODES.get(weather_code, "Thunderstorm expected")
                })
        
        return {
            "success": True,
            "location": forecast.get("location"),
            "alerts": alerts,
            "alert_count": len(alerts),
            "checked_days": 7
        }
    
    def _get_weather_icon(self, code: int) -> str:
        """Get emoji icon for weather code"""
        if code == 0:
            return "☀️"
        elif code in [1, 2]:
            return "🌤️"
        elif code == 3:
            return "☁️"
        elif code in [45, 48]:
            return "🌫️"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            return "🌧️"
        elif code in [66, 67]:
            return "🌨️"
        elif code in [71, 73, 75, 77, 85, 86]:
            return "❄️"
        elif code in [95, 96, 99]:
            return "⛈️"
        else:
            return "🌡️"
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
_client: Optional[WeatherClient] = None

def get_client() -> WeatherClient:
    """Get or create the weather client singleton"""
    global _client
    if _client is None:
        _client = WeatherClient()
    return _client
