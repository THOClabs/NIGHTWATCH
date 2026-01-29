"""
NIGHTWATCH Fireball Data Clients
NASA CNEOS and American Meteor Society APIs

Fetches real-time and historical fireball data for meteor tracking.
"""

import aiohttp
import asyncio
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List

logger = logging.getLogger("NIGHTWATCH.MeteorTracking")


@dataclass
class Fireball:
    """A detected fireball event from NASA CNEOS."""
    date: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    altitude_km: Optional[float]
    velocity_km_s: Optional[float]
    total_radiated_energy_j: Optional[float]
    calculated_total_impact_energy_kt: Optional[float]

    @property
    def magnitude_estimate(self) -> Optional[float]:
        """
        Estimate visual magnitude from radiated energy.
        Rough approximation: -2.5 * log10(energy_j / reference_energy)
        """
        if self.total_radiated_energy_j:
            return -2.5 * math.log10(self.total_radiated_energy_j / 1e10) - 10
        return None

    @property
    def coordinates_str(self) -> str:
        """Format coordinates as string."""
        if self.latitude is not None and self.longitude is not None:
            lat_dir = "N" if self.latitude >= 0 else "S"
            lon_dir = "W" if self.longitude < 0 else "E"
            return f"{abs(self.latitude):.1f}{lat_dir} {abs(self.longitude):.1f}{lon_dir}"
        return "coordinates-unknown"

    @property
    def fireball_id(self) -> str:
        """Generate unique ID for this fireball."""
        return f"{self.date.strftime('%Y%m%d%H%M%S')}_{self.latitude}_{self.longitude}"


@dataclass
class AMSFireball:
    """An observer-reported fireball event from AMS."""
    event_id: str
    date: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    magnitude: Optional[float]
    duration_seconds: Optional[float]
    num_reports: int
    direction: Optional[str]
    terminal_flash: bool
    fragmentation: bool
    sound_reported: bool

    @property
    def coordinates_str(self) -> str:
        """Format coordinates as string."""
        if self.latitude is not None and self.longitude is not None:
            lat_dir = "N" if self.latitude >= 0 else "S"
            lon_dir = "W" if self.longitude < 0 else "E"
            return f"{abs(self.latitude):.1f}{lat_dir} {abs(self.longitude):.1f}{lon_dir}"
        return "coordinates-unknown"

    @property
    def debris_likely(self) -> bool:
        """Estimate if meteorite debris is possible."""
        bright = self.magnitude is not None and self.magnitude < -8
        slow = self.duration_seconds is not None and self.duration_seconds > 3
        return (bright or slow) and (self.terminal_flash or self.fragmentation)


class CNEOSClient:
    """
    Async client for NASA CNEOS Fireball API.

    API Documentation: https://ssd-api.jpl.nasa.gov/doc/fireball.html
    """

    BASE_URL = "https://ssd-api.jpl.nasa.gov/fireball.api"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={'User-Agent': 'NIGHTWATCH/1.0 (observatory-meteor-tracking)'}
            )
        return self._session

    async def close(self):
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def fetch_fireballs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_energy_kt: Optional[float] = None,
        limit: int = 100
    ) -> List[Fireball]:
        """
        Fetch fireball events from CNEOS API.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)
            min_energy_kt: Minimum calculated impact energy in kilotons
            limit: Maximum number of results

        Returns:
            List of Fireball objects
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()

        params = {
            'date-min': start_date.strftime('%Y-%m-%d'),
            'date-max': end_date.strftime('%Y-%m-%d'),
            'limit': limit,
            'sort': '-date'
        }

        if min_energy_kt:
            params['energy-min'] = min_energy_kt

        try:
            session = await self._get_session()
            async with session.get(self.BASE_URL, params=params, timeout=30) as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_fireballs(data)

        except aiohttp.ClientError as e:
            logger.error(f"CNEOS API error: {e}")
            return []

    def _parse_fireballs(self, data: dict) -> List[Fireball]:
        """Parse API response into Fireball objects."""
        fireballs = []

        if 'data' not in data or 'fields' not in data:
            return fireballs

        fields = data['fields']
        field_map = {field: idx for idx, field in enumerate(fields)}

        for row in data['data']:
            try:
                fireball = Fireball(
                    date=self._parse_datetime(row[field_map.get('date', 0)]),
                    latitude=self._parse_float(row[field_map.get('lat', -1)] if 'lat' in field_map else None),
                    longitude=self._parse_float(row[field_map.get('lon', -1)] if 'lon' in field_map else None),
                    altitude_km=self._parse_float(row[field_map.get('alt', -1)] if 'alt' in field_map else None),
                    velocity_km_s=self._parse_float(row[field_map.get('vel', -1)] if 'vel' in field_map else None),
                    total_radiated_energy_j=self._parse_energy(row[field_map.get('energy', -1)] if 'energy' in field_map else None),
                    calculated_total_impact_energy_kt=self._parse_float(row[field_map.get('impact-e', -1)] if 'impact-e' in field_map else None)
                )
                fireballs.append(fireball)
            except (IndexError, KeyError, ValueError) as e:
                logger.debug(f"Parse error for fireball row: {e}")
                continue

        return fireballs

    def _parse_datetime(self, date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return datetime.utcnow()

    def _parse_float(self, value) -> Optional[float]:
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_energy(self, value) -> Optional[float]:
        if value is None or value == '':
            return None
        try:
            return float(value) * 1e10  # API gives energy in 10^10 joules
        except (ValueError, TypeError):
            return None


class AMSClient:
    """
    Async client for American Meteor Society fireball data.

    Note: AMS API access may require registration for full features.
    """

    BASE_URL = "https://www.amsmeteors.org/members/imo_view/api"

    def __init__(
        self,
        api_key: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None
    ):
        self.api_key = api_key
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={'User-Agent': 'NIGHTWATCH/1.0 (observatory-meteor-tracking)'}
            )
        return self._session

    async def close(self):
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def fetch_fireballs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_reports: int = 2,
        limit: int = 100
    ) -> List[AMSFireball]:
        """
        Fetch fireball events from AMS.

        Args:
            start_date: Start of date range
            end_date: End of date range
            min_reports: Minimum number of observer reports
            limit: Maximum number of results

        Returns:
            List of AMSFireball objects
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=7)
        if end_date is None:
            end_date = datetime.utcnow()

        params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'min_reports': min_reports,
            'format': 'json'
        }

        if self.api_key:
            params['api_key'] = self.api_key

        try:
            session = await self._get_session()
            async with session.get(
                f"{self.BASE_URL}/get_events",
                params=params,
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_fireballs(data)
                else:
                    logger.warning(f"AMS API returned status {response.status}")
                    return []

        except aiohttp.ClientError as e:
            logger.error(f"AMS API error: {e}")
            return []

    def _parse_fireballs(self, data: dict) -> List[AMSFireball]:
        """Parse API response into AMSFireball objects."""
        fireballs = []
        events = data.get('events', data.get('data', []))

        for event in events:
            try:
                fireball = AMSFireball(
                    event_id=str(event.get('id', event.get('event_id', 'unknown'))),
                    date=self._parse_datetime(event.get('date', event.get('event_date', ''))),
                    latitude=self._parse_float(event.get('lat', event.get('latitude'))),
                    longitude=self._parse_float(event.get('lon', event.get('longitude'))),
                    magnitude=self._parse_float(event.get('magnitude', event.get('brightness'))),
                    duration_seconds=self._parse_float(event.get('duration', event.get('duration_seconds'))),
                    num_reports=int(event.get('reports', event.get('num_reports', 1))),
                    direction=event.get('direction', event.get('trajectory')),
                    terminal_flash=bool(event.get('terminal_flash', False)),
                    fragmentation=bool(event.get('fragmentation', event.get('fragmented', False))),
                    sound_reported=bool(event.get('sound', event.get('sonic_boom', False)))
                )
                fireballs.append(fireball)
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Parse error for AMS event: {e}")
                continue

        return fireballs

    def _parse_datetime(self, date_str: str) -> datetime:
        formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return datetime.utcnow()

    def _parse_float(self, value) -> Optional[float]:
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


async def fetch_recent_fireballs(days: int = 7) -> List[Fireball]:
    """Convenience function to fetch recent fireballs from CNEOS."""
    client = CNEOSClient()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        return await client.fetch_fireballs(start_date=start_date)
    finally:
        await client.close()
