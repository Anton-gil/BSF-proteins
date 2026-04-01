"""
Weather Client

Fetches current weather data for the farm location.
Uses Open-Meteo API (free, no API key required) with file-based
caching and an offline default fallback.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


@dataclass
class WeatherData:
    """Current weather conditions."""
    temperature_c: float
    humidity_pct: float
    description: str
    timestamp: datetime
    source: str   # 'api' | 'cache' | 'default'


class WeatherClient:
    """
    Weather data client with caching and offline fallback.

    Uses the Open-Meteo free API — no API key required.

    Usage:
        client = WeatherClient(latitude=13.08, longitude=80.27)
        weather = client.get_current_weather()
        print(f"{weather.temperature_c}°C  {weather.humidity_pct}%")
    """

    def __init__(
        self,
        latitude: float = 13.0827,       # Default: Chennai, India
        longitude: float = 80.2707,
        cache_file: str = "data/weather_cache.json",
        cache_duration_hours: int = 1
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.cache_file = cache_file
        self.cache_duration = timedelta(hours=cache_duration_hours)

        # Offline defaults (tropical climate)
        self.default_temp = 28.0
        self.default_humidity = 70.0

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _load_cache(self) -> Optional[WeatherData]:
        """Return cached data if it is still within the TTL."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                timestamp = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - timestamp < self.cache_duration:
                    return WeatherData(
                        temperature_c=data['temperature_c'],
                        humidity_pct=data['humidity_pct'],
                        description=data['description'],
                        timestamp=timestamp,
                        source='cache'
                    )
        except Exception:
            pass
        return None

    def _save_cache(self, weather: WeatherData):
        """Persist weather data to disk."""
        try:
            os.makedirs(os.path.dirname(self.cache_file) or '.', exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'temperature_c': weather.temperature_c,
                    'humidity_pct': weather.humidity_pct,
                    'description': weather.description,
                    'timestamp': weather.timestamp.isoformat()
                }, f)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def _fetch_from_api(self) -> Optional[WeatherData]:
        """Query the Open-Meteo API for current conditions."""
        try:
            import requests
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={self.latitude}"
                f"&longitude={self.longitude}"
                f"&current=temperature_2m,relative_humidity_2m,weather_code"
            )
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            current = response.json().get('current', {})

            weather = WeatherData(
                temperature_c=float(current.get('temperature_2m', self.default_temp)),
                humidity_pct=float(current.get('relative_humidity_2m', self.default_humidity)),
                description=self._code_to_description(current.get('weather_code', 0)),
                timestamp=datetime.now(),
                source='api'
            )
            self._save_cache(weather)
            return weather

        except Exception as exc:
            print(f"Weather API unavailable: {exc}")
            return None

    @staticmethod
    def _code_to_description(code: int) -> str:
        """Map WMO weather code to English description."""
        mapping = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Icy fog",
            51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
            61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
            80: "Light showers", 81: "Showers", 82: "Heavy showers",
            95: "Thunderstorm",
        }
        return mapping.get(code, "Unknown")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current_weather(self, use_cache: bool = True) -> WeatherData:
        """
        Return current weather. Order of preference: cache → API → default.

        Args:
            use_cache: Whether to use cached data when available

        Returns:
            WeatherData instance
        """
        if use_cache:
            cached = self._load_cache()
            if cached:
                return cached

        api_data = self._fetch_from_api()
        if api_data:
            return api_data

        # Offline fallback
        return WeatherData(
            temperature_c=self.default_temp,
            humidity_pct=self.default_humidity,
            description="Default (offline)",
            timestamp=datetime.now(),
            source='default'
        )

    def get_forecast(self, days: int = 3) -> list:
        """
        Return a daily forecast for the next N days.

        Args:
            days: Number of forecast days

        Returns:
            List of dicts with 'date', 'temp_max', 'temp_min', 'humidity'
        """
        try:
            import requests
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={self.latitude}"
                f"&longitude={self.longitude}"
                f"&daily=temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean"
                f"&forecast_days={days}"
            )
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            daily = response.json().get('daily', {})

            dates = daily.get('time', [])
            return [
                {
                    'date': dates[i],
                    'temp_max': daily.get('temperature_2m_max', [])[i] if i < len(daily.get('temperature_2m_max', [])) else self.default_temp,
                    'temp_min': daily.get('temperature_2m_min', [])[i] if i < len(daily.get('temperature_2m_min', [])) else self.default_temp - 5,
                    'humidity': daily.get('relative_humidity_2m_mean', [])[i] if i < len(daily.get('relative_humidity_2m_mean', [])) else self.default_humidity,
                }
                for i in range(len(dates))
            ]
        except Exception as exc:
            print(f"Forecast API error: {exc}")
            return []

    def set_location(self, latitude: float, longitude: float):
        """Update farm location and clear cache."""
        self.latitude = latitude
        self.longitude = longitude
        # Remove stale cache for old location
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
            except Exception:
                pass
