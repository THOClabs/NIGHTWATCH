"""
NIGHTWATCH Space Weather Client
NOAA SWPC data for geomagnetic storm awareness and aurora alerts.

Why this matters for NIGHTWATCH:
- G2+ geomagnetic storms affect telescope tracking (magnetic field fluctuations)
- Aurora alerts are observation opportunities at Nevada latitude
- Solar flare X-ray flux affects atmospheric transparency
- Proton events create increased sky background noise
- Equinox periods (like RIGHT NOW, March 2026) have enhanced coupling

API Documentation: https://www.swpc.noaa.gov/products-and-data
JSON feeds: https://services.swpc.noaa.gov/products/
"""

import aiohttp
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, List

logger = logging.getLogger("NIGHTWATCH.SpaceWeather")


class GeomagneticLevel(Enum):
    """NOAA Geomagnetic Storm Scale (G1-G5)."""
    QUIET = 0       # Kp 0-3
    UNSETTLED = 1   # Kp 4
    G1_MINOR = 5    # Kp 5
    G2_MODERATE = 6  # Kp 6
    G3_STRONG = 7   # Kp 7
    G4_SEVERE = 8   # Kp 8
    G5_EXTREME = 9  # Kp 9

    @classmethod
    def from_kp(cls, kp: float) -> 'GeomagneticLevel':
        """Convert Kp index to geomagnetic level."""
        if kp >= 9:
            return cls.G5_EXTREME
        elif kp >= 8:
            return cls.G4_SEVERE
        elif kp >= 7:
            return cls.G3_STRONG
        elif kp >= 6:
            return cls.G2_MODERATE
        elif kp >= 5:
            return cls.G1_MINOR
        elif kp >= 4:
            return cls.UNSETTLED
        return cls.QUIET

    @property
    def label(self) -> str:
        """Human-readable label."""
        labels = {
            0: "Quiet",
            1: "Unsettled",
            5: "G1 Minor Storm",
            6: "G2 Moderate Storm",
            7: "G3 Strong Storm",
            8: "G4 Severe Storm",
            9: "G5 Extreme Storm",
        }
        return labels.get(self.value, "Unknown")

    @property
    def affects_tracking(self) -> bool:
        """Whether this level may affect telescope magnetic tracking."""
        return self.value >= 6  # G2+

    @property
    def aurora_visible_at_latitude(self) -> float:
        """Approximate lowest latitude where aurora may be visible."""
        lat_map = {
            0: 70.0,
            1: 65.0,
            5: 60.0,
            6: 55.0,
            7: 50.0,
            8: 45.0,
            9: 40.0,
        }
        return lat_map.get(self.value, 70.0)


@dataclass
class KpReading:
    """A single Kp index reading."""
    timestamp: datetime
    kp: float
    observed: bool  # True = observed, False = predicted

    @property
    def level(self) -> GeomagneticLevel:
        return GeomagneticLevel.from_kp(self.kp)


@dataclass
class SolarWindReading:
    """Solar wind plasma data."""
    timestamp: datetime
    speed_km_s: float  # Solar wind speed
    density_p_cm3: float  # Proton density
    bz_nt: float  # IMF Bz component (negative = geoeffective)
    bt_nt: float  # IMF total field

    @property
    def is_geoeffective(self) -> bool:
        """Check if solar wind conditions favor geomagnetic activity."""
        return self.bz_nt < -5 and self.speed_km_s > 400

    @property
    def coupling_strength(self) -> str:
        """Qualitative solar wind-magnetosphere coupling."""
        if self.bz_nt < -20 and self.speed_km_s > 600:
            return "extreme"
        elif self.bz_nt < -10 and self.speed_km_s > 500:
            return "strong"
        elif self.bz_nt < -5 and self.speed_km_s > 400:
            return "moderate"
        elif self.bz_nt < 0:
            return "weak"
        return "none"


@dataclass
class SpaceWeatherSummary:
    """Complete space weather summary for NIGHTWATCH decision-making."""
    timestamp: datetime
    current_kp: Optional[KpReading] = None
    kp_forecast_24h: List[KpReading] = field(default_factory=list)
    solar_wind: Optional[SolarWindReading] = None
    geomagnetic_level: GeomagneticLevel = GeomagneticLevel.QUIET
    aurora_possible_at_site: bool = False
    tracking_affected: bool = False
    alerts: List[str] = field(default_factory=list)

    def to_lexicon(self) -> str:
        """Format as Lexicon-style space weather report."""
        lines = ["nightwatch-space-weather."]
        lines.append(f"varek: {self.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

        if self.current_kp:
            lines.append(f"kp-index: {self.current_kp.kp:.1f} ({self.geomagnetic_level.label})")

        if self.solar_wind:
            lines.append(f"solar-wind: {self.solar_wind.speed_km_s:.0f} km/s")
            lines.append(f"imf-bz: {self.solar_wind.bz_nt:.1f} nT")
            if self.solar_wind.is_geoeffective:
                lines.append(f"coupling: {self.solar_wind.coupling_strength}")

        if self.aurora_possible_at_site:
            lines.append("")
            lines.append("aurora-possible: yes-at-site")

        if self.tracking_affected:
            lines.append("")
            lines.append("tracking-warning: magnetic-interference-possible")

        if self.alerts:
            lines.append("")
            for alert in self.alerts:
                lines.append(f"alert: {alert}")

        lines.append("")
        if self.geomagnetic_level.value >= 5:
            lines.append("presa-storm.")
        else:
            lines.append("sky-quiet.")

        return "\n".join(lines)

    @property
    def observation_impact(self) -> str:
        """Assessment of impact on observation quality."""
        if self.geomagnetic_level.value >= 8:
            return "SEVERE - Consider closing. Magnetic interference likely."
        elif self.geomagnetic_level.value >= 7:
            return "SIGNIFICANT - Tracking may drift. Monitor closely."
        elif self.geomagnetic_level.value >= 6:
            return "MODERATE - Possible tracking perturbations. Aurora opportunity."
        elif self.geomagnetic_level.value >= 5:
            return "MINOR - Slight tracking effects possible. Check for aurora."
        return "NONE - Clear for observation."


class SpaceWeatherClient:
    """
    Async client for NOAA SWPC space weather data.

    Data sources:
    - Planetary Kp index (3-hour values)
    - DSCOVR solar wind real-time data
    - Geomagnetic storm alerts
    """

    # NOAA SWPC JSON data feeds
    KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    KP_FORECAST_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
    SOLAR_WIND_URL = "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json"
    MAG_URL = "https://services.swpc.noaa.gov/products/solar-wind/mag-7-day.json"
    ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"

    def __init__(
        self,
        site_latitude: float = 38.9,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.site_latitude = site_latitude
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={'User-Agent': 'NIGHTWATCH/1.0 (observatory-space-weather)'}
            )
        return self._session

    async def close(self):
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def get_summary(self) -> SpaceWeatherSummary:
        """
        Get complete space weather summary for NIGHTWATCH.

        Combines Kp index, solar wind data, and alerts into
        a single actionable summary.
        """
        summary = SpaceWeatherSummary(timestamp=datetime.now(timezone.utc))

        # Fetch Kp index
        kp_readings = await self._fetch_kp()
        if kp_readings:
            summary.current_kp = kp_readings[-1]
            summary.geomagnetic_level = summary.current_kp.level

        # Fetch Kp forecast
        summary.kp_forecast_24h = await self._fetch_kp_forecast()

        # Fetch solar wind
        summary.solar_wind = await self._fetch_solar_wind()

        # Fetch alerts
        summary.alerts = await self._fetch_alerts()

        # Determine site-specific impacts
        if summary.geomagnetic_level != GeomagneticLevel.QUIET:
            min_aurora_lat = summary.geomagnetic_level.aurora_visible_at_latitude
            summary.aurora_possible_at_site = self.site_latitude >= min_aurora_lat - 5
            summary.tracking_affected = summary.geomagnetic_level.affects_tracking

        return summary

    async def get_current_kp(self) -> Optional[KpReading]:
        """Get the most recent Kp index value."""
        readings = await self._fetch_kp()
        return readings[-1] if readings else None

    async def _fetch_kp(self) -> List[KpReading]:
        """Fetch recent Kp index values."""
        try:
            session = await self._get_session()
            async with session.get(
                self.KP_URL,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_kp_data(data)

        except aiohttp.ClientError as e:
            logger.error(f"SWPC Kp API error: {e}")
            return []

    async def _fetch_kp_forecast(self) -> List[KpReading]:
        """Fetch Kp index forecast."""
        try:
            session = await self._get_session()
            async with session.get(
                self.KP_FORECAST_URL,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_kp_forecast(data)

        except aiohttp.ClientError as e:
            logger.error(f"SWPC Kp forecast API error: {e}")
            return []

    async def _fetch_solar_wind(self) -> Optional[SolarWindReading]:
        """Fetch latest solar wind data from DSCOVR."""
        try:
            session = await self._get_session()

            # Fetch plasma data (speed, density)
            plasma_data = None
            async with session.get(
                self.SOLAR_WIND_URL,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 200:
                    plasma_data = await response.json()

            # Fetch magnetic field data (Bz, Bt)
            mag_data = None
            async with session.get(
                self.MAG_URL,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 200:
                    mag_data = await response.json()

            return self._parse_solar_wind(plasma_data, mag_data)

        except aiohttp.ClientError as e:
            logger.error(f"SWPC solar wind API error: {e}")
            return None

    async def _fetch_alerts(self) -> List[str]:
        """Fetch active SWPC alerts."""
        try:
            session = await self._get_session()
            async with session.get(
                self.ALERTS_URL,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                return self._parse_alerts(data)

        except aiohttp.ClientError as e:
            logger.error(f"SWPC alerts API error: {e}")
            return []

    def _parse_kp_data(self, data: list) -> List[KpReading]:
        """Parse Kp index JSON data."""
        readings = []
        if not data or len(data) < 2:
            return readings

        # First row is headers, rest is data
        for row in data[1:]:
            try:
                timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                kp = float(row[1])
                readings.append(KpReading(
                    timestamp=timestamp,
                    kp=kp,
                    observed=True,
                ))
            except (ValueError, IndexError) as e:
                logger.debug(f"Kp parse error: {e}")
                continue

        return readings

    def _parse_kp_forecast(self, data: list) -> List[KpReading]:
        """Parse Kp forecast JSON data."""
        readings = []
        if not data or len(data) < 2:
            return readings

        for row in data[1:]:
            try:
                timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                kp = float(row[1])
                # Only include future predictions
                if timestamp > datetime.now(timezone.utc):
                    readings.append(KpReading(
                        timestamp=timestamp,
                        kp=kp,
                        observed=False,
                    ))
            except (ValueError, IndexError) as e:
                logger.debug(f"Kp forecast parse error: {e}")
                continue

        return readings[:8]  # Next 24 hours (8 x 3-hour windows)

    def _parse_solar_wind(
        self,
        plasma_data: Optional[list],
        mag_data: Optional[list],
    ) -> Optional[SolarWindReading]:
        """Parse solar wind plasma and magnetic field data."""
        speed = 400.0
        density = 5.0
        bz = 0.0
        bt = 5.0
        timestamp = datetime.now(timezone.utc)
        plasma_found = False
        mag_found = False

        # Get latest plasma reading
        if plasma_data and len(plasma_data) > 1:
            for row in reversed(plasma_data[1:]):
                try:
                    s = float(row[2]) if row[2] else None
                    d = float(row[1]) if row[1] else None
                    if s is not None and d is not None:
                        speed = s
                        density = d
                        timestamp = datetime.strptime(
                            row[0], '%Y-%m-%d %H:%M:%S.%f'
                        ).replace(tzinfo=timezone.utc)
                        plasma_found = True
                        break
                except (ValueError, IndexError):
                    continue

        # Get latest magnetic field reading
        if mag_data and len(mag_data) > 1:
            for row in reversed(mag_data[1:]):
                try:
                    bz_val = float(row[3]) if row[3] else None
                    bt_val = float(row[6]) if row[6] else None
                    if bz_val is not None and bt_val is not None:
                        bz = bz_val
                        bt = bt_val
                        mag_found = True
                        break
                except (ValueError, IndexError):
                    continue

        if not plasma_found or not mag_found:
            # Defaults describe quiet conditions; a partial feed outage must
            # not silently masquerade as a quiet sun.
            logger.warning(
                "Solar wind feed incomplete (plasma=%s, mag=%s); "
                "quiet-condition defaults substituted for missing values",
                plasma_found, mag_found,
            )

        return SolarWindReading(
            timestamp=timestamp,
            speed_km_s=speed,
            density_p_cm3=density,
            bz_nt=bz,
            bt_nt=bt,
        )

    def _parse_alerts(self, data: list) -> List[str]:
        """Parse SWPC alerts into summary strings."""
        alerts = []
        if not isinstance(data, list):
            return alerts

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)

        for item in data[:10]:  # Check last 10 alerts
            try:
                msg = item.get('message', '')
                issue_time = item.get('issue_datetime', '')

                # Parse issue time
                try:
                    issued = datetime.strptime(issue_time, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                    if issued < cutoff:
                        continue
                except ValueError:
                    pass

                # Extract key info from alert message
                if 'WARNING' in msg or 'WATCH' in msg or 'ALERT' in msg:
                    # Get first meaningful line
                    for line in msg.split('\n'):
                        line = line.strip()
                        if line and ('Warning' in line or 'Watch' in line
                                     or 'Alert' in line or 'Storm' in line
                                     or 'Geomagnetic' in line):
                            alerts.append(line[:120])
                            break

            except (KeyError, TypeError) as e:
                logger.debug(f"Alert parse error: {e}")
                continue

        return alerts[:5]  # Max 5 active alerts


async def get_space_weather_summary(
    site_latitude: float = 38.9,
) -> SpaceWeatherSummary:
    """Convenience function to get current space weather summary."""
    client = SpaceWeatherClient(site_latitude=site_latitude)
    try:
        return await client.get_summary()
    finally:
        await client.close()
