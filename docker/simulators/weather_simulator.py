#!/usr/bin/env python3
"""
Ecowitt Weather Simulator for NIGHTWATCH (Step 505)

Simulates an Ecowitt GW1000/GW2000 gateway HTTP API for testing.
Returns realistic weather data in Ecowitt JSON format.

Endpoint: GET /get_livedata_info

Response format matches Ecowitt gateway live data API.
"""

import asyncio
import json
import logging
import math
import os
import random
import time
from datetime import datetime

from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WeatherSimulator:
    """Simulated weather station generating realistic data."""

    def __init__(self):
        # Configuration from environment
        self.port = int(os.environ.get('WEATHER_SIM_PORT', 8080))
        self.base_temp_f = float(os.environ.get('WEATHER_SIM_TEMP_F', 55.0))
        self.base_humidity = float(os.environ.get('WEATHER_SIM_HUMIDITY', 45.0))
        self.base_wind_mph = float(os.environ.get('WEATHER_SIM_WIND_MPH', 5.0))
        self.base_pressure = float(os.environ.get('WEATHER_SIM_PRESSURE_HPA', 1013.25))
        self.events_enabled = os.environ.get('WEATHER_SIM_EVENTS_ENABLED', 'false').lower() == 'true'
        self.update_interval = int(os.environ.get('WEATHER_SIM_UPDATE_INTERVAL', 10))

        # Current state
        self._start_time = time.time()
        self._rain_event = False
        self._rain_start = None

    def _calculate_diurnal_temp(self) -> float:
        """Calculate temperature variation based on time of day."""
        hour = datetime.now().hour
        # Temperature peaks at 3pm (15:00), lowest at 5am
        # Variation of about ±10°F
        phase = (hour - 5) * (2 * math.pi / 24)
        variation = -10 * math.cos(phase)
        return self.base_temp_f + variation

    def _calculate_humidity(self, temp_f: float) -> float:
        """Calculate humidity (inversely related to temperature)."""
        temp_variation = temp_f - self.base_temp_f
        humidity_variation = -temp_variation * 1.5  # Humidity drops as temp rises
        humidity = self.base_humidity + humidity_variation + random.gauss(0, 2)
        return max(20, min(100, humidity))

    def _calculate_dewpoint(self, temp_f: float, humidity: float) -> float:
        """Calculate dew point using Magnus formula."""
        temp_c = (temp_f - 32) * 5 / 9
        a = 17.27
        b = 237.7
        alpha = (a * temp_c / (b + temp_c)) + math.log(humidity / 100)
        dewpoint_c = b * alpha / (a - alpha)
        return dewpoint_c * 9 / 5 + 32

    def _calculate_wind(self) -> tuple:
        """Calculate wind speed and direction with variability."""
        # Add some randomness to wind
        speed = self.base_wind_mph + random.gauss(0, 2)
        speed = max(0, speed)

        # Occasional gusts
        gust = speed
        if random.random() < 0.3:  # 30% chance of gust
            gust = speed * random.uniform(1.3, 1.8)

        # Wind direction varies slowly
        elapsed = time.time() - self._start_time
        base_direction = (elapsed / 60) * 5 % 360  # Slowly rotating
        direction = base_direction + random.gauss(0, 15)
        direction = direction % 360

        return speed, gust, direction

    def _get_wind_direction_str(self, degrees: float) -> str:
        """Convert wind direction degrees to compass string."""
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        idx = int((degrees + 11.25) / 22.5) % 16
        return directions[idx]

    def _check_rain_event(self) -> tuple:
        """Check for simulated rain events."""
        if not self.events_enabled:
            return 0.0, False

        # Random rain events
        if not self._rain_event and random.random() < 0.001:  # Low probability
            self._rain_event = True
            self._rain_start = time.time()
            logger.info("Rain event started!")

        if self._rain_event:
            # Rain lasts 5-30 minutes
            rain_duration = time.time() - self._rain_start
            if rain_duration > random.uniform(300, 1800):
                self._rain_event = False
                self._rain_start = None
                logger.info("Rain event ended")
                return 0.0, False

            # Variable rain rate
            rain_rate = random.uniform(1.0, 20.0)  # mm/hr
            return rain_rate, True

        return 0.0, False

    def get_live_data(self) -> dict:
        """Generate current weather data in Ecowitt format."""
        # Calculate current conditions
        temp_f = self._calculate_diurnal_temp() + random.gauss(0, 0.5)
        humidity = self._calculate_humidity(temp_f)
        dewpoint_f = self._calculate_dewpoint(temp_f, humidity)
        wind_speed, wind_gust, wind_dir = self._calculate_wind()
        rain_rate, is_raining = self._check_rain_event()

        # Pressure varies slightly
        pressure = self.base_pressure + random.gauss(0, 0.5)

        # Solar radiation (daytime only)
        hour = datetime.now().hour
        if 6 <= hour <= 18:
            solar_rad = max(0, 800 * math.sin((hour - 6) * math.pi / 12) + random.gauss(0, 50))
        else:
            solar_rad = 0

        # UV index (proportional to solar radiation)
        uv_index = min(11, max(0, solar_rad / 100))

        # Build response matching Ecowitt API format
        data = {
            "common_list": [
                {"id": "0x02", "val": f"{temp_f:.1f}", "unit": "℉"},
                {"id": "0x07", "val": f"{humidity:.0f}", "unit": "%"},
                {"id": "0x03", "val": f"{dewpoint_f:.1f}", "unit": "℉"},
                {"id": "0x0B", "val": f"{wind_dir:.0f}", "unit": ""},
                {"id": "0x0C", "val": f"{wind_speed:.1f}", "unit": "mph"},
                {"id": "0x0D", "val": f"{wind_gust:.1f}", "unit": "mph"},
            ],
            "rain": {
                "rain_rate": {"val": f"{rain_rate:.2f}", "unit": "mm/hr"},
                "daily": {"val": f"{rain_rate * 0.1:.2f}", "unit": "mm"},
                "event": {"val": f"{rain_rate * 0.05:.2f}", "unit": "mm"},
                "hourly": {"val": f"{rain_rate * 0.5:.2f}", "unit": "mm"},
                "weekly": {"val": "0.00", "unit": "mm"},
                "monthly": {"val": "0.00", "unit": "mm"},
                "yearly": {"val": "0.00", "unit": "mm"},
            },
            "wh25": [
                {"id": "0x02", "val": f"{temp_f:.1f}", "unit": "℉"},
                {"id": "0x07", "val": f"{humidity:.0f}", "unit": "%"},
                {"id": "0x09", "val": f"{pressure:.2f}", "unit": "hPa"},
            ],
            "wh90": [
                {"id": "0x02", "val": f"{temp_f:.1f}", "unit": "℉"},
                {"id": "0x07", "val": f"{humidity:.0f}", "unit": "%"},
                {"id": "0x0B", "val": f"{wind_dir:.0f}", "unit": ""},
                {"id": "0x0C", "val": f"{wind_speed:.1f}", "unit": "mph"},
                {"id": "0x0D", "val": f"{wind_gust:.1f}", "unit": "mph"},
                {"id": "0x17", "val": f"{solar_rad:.0f}", "unit": "W/m²"},
                {"id": "0x15", "val": f"{uv_index:.0f}", "unit": ""},
            ],
            # Additional fields for compatibility
            "temperature_f": temp_f,
            "humidity_percent": humidity,
            "wind_speed_mph": wind_speed,
            "wind_gust_mph": wind_gust,
            "wind_direction_deg": wind_dir,
            "wind_direction_str": self._get_wind_direction_str(wind_dir),
            "pressure_hpa": pressure,
            "rain_rate_mmhr": rain_rate,
            "rain_detected": is_raining,
            "dewpoint_f": dewpoint_f,
            "solar_radiation_wm2": solar_rad,
            "uv_index": uv_index,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        return data


async def handle_livedata(request: web.Request) -> web.Response:
    """Handle GET /get_livedata_info requests."""
    simulator = request.app['simulator']
    data = simulator.get_live_data()
    return web.json_response(data)


async def handle_health(request: web.Request) -> web.Response:
    """Handle health check requests."""
    return web.json_response({"status": "ok", "service": "weather-simulator"})


async def handle_root(request: web.Request) -> web.Response:
    """Handle root path requests."""
    return web.Response(
        text="Ecowitt Weather Simulator\n\nEndpoints:\n"
             "  GET /get_livedata_info - Get current weather data\n"
             "  GET /health - Health check\n",
        content_type='text/plain'
    )


def create_app() -> web.Application:
    """Create and configure the web application."""
    app = web.Application()
    app['simulator'] = WeatherSimulator()

    app.router.add_get('/', handle_root)
    app.router.add_get('/get_livedata_info', handle_livedata)
    app.router.add_get('/health', handle_health)

    return app


def main():
    """Main entry point."""
    app = create_app()
    port = app['simulator'].port

    logger.info(f"Weather Simulator starting on port {port}")
    logger.info(f"Base conditions: {app['simulator'].base_temp_f}°F, "
                f"{app['simulator'].base_humidity}% humidity, "
                f"{app['simulator'].base_wind_mph} mph wind")
    logger.info(f"Weather events enabled: {app['simulator'].events_enabled}")

    web.run_app(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
