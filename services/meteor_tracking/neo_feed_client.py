"""
NIGHTWATCH NASA NEO Feed API Client
Secondary data source via api.nasa.gov/neo/rest/v1/feed.

Complements the CAD API in close_approach_client.py:
- CAD API: CNEOS close approach predictions (no auth needed)
- NEO Feed: NASA NeoWs with PHA flags and diameter estimates (DEMO_KEY or API key)

The NEO Feed provides the is_potentially_hazardous_asteroid flag directly,
which the CAD API does not include. Combining both gives more complete data.

API Documentation: https://api.nasa.gov/ (NeoWs section)
"""

import aiohttp
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Optional, List

from .close_approach_client import CloseApproach, ThreatLevel

logger = logging.getLogger("NIGHTWATCH.MeteorTracking")


# Conversion constants
AU_TO_KM = 149_597_870.7
LD_TO_AU = 0.00257


class NEOFeedClient:
    """
    Async client for NASA NEO Feed API (NeoWs).

    Provides near-Earth object data with official PHA classification.
    Requires API key (DEMO_KEY available for low-rate testing).

    API: https://api.nasa.gov/neo/rest/v1/feed
    Rate limit: 30 req/hour (DEMO_KEY), 1000 req/hour (registered key)
    """

    BASE_URL = "https://api.nasa.gov/neo/rest/v1/feed"

    def __init__(
        self,
        api_key: str = "DEMO_KEY",
        session: Optional[aiohttp.ClientSession] = None
    ):
        self.api_key = api_key
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={'User-Agent': 'NIGHTWATCH/1.0 (observatory-neo-tracking)'}
            )
        return self._session

    async def close(self):
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def fetch_neo_feed(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[CloseApproach]:
        """
        Fetch NEO feed data from NASA API.

        Note: Feed API limited to 7-day windows.

        Args:
            start_date: Start date (default: today)
            end_date: End date (default: 7 days from start, max 7 day span)

        Returns:
            List of CloseApproach objects (same type as CAD client)
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=7)

        # API limits to 7-day windows
        if (end_date - start_date).days > 7:
            end_date = start_date + timedelta(days=7)

        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'api_key': self.api_key,
        }

        try:
            session = await self._get_session()
            async with session.get(
                self.BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 429:
                    logger.warning("NEO Feed API rate limit exceeded")
                    return []
                response.raise_for_status()
                data = await response.json()
                return self._parse_neo_feed(data)

        except aiohttp.ClientError as e:
            logger.error(f"NEO Feed API error: {e}")
            return []

    def _parse_neo_feed(self, data: dict) -> List[CloseApproach]:
        """Parse NEO Feed API response into CloseApproach objects."""
        approaches = []
        neo_objects = data.get('near_earth_objects', {})

        for date_str, objects in neo_objects.items():
            for obj in objects:
                try:
                    approach = self._parse_neo_object(obj)
                    if approach:
                        approaches.append(approach)
                except (KeyError, ValueError, TypeError) as e:
                    logger.debug(f"Parse error for NEO object: {e}")
                    continue

        approaches.sort(key=lambda a: a.close_approach_date)
        return approaches

    def _parse_neo_object(self, obj: dict) -> Optional[CloseApproach]:
        """Parse a single NEO object from the feed."""
        close_approach_data = obj.get('close_approach_data', [])
        if not close_approach_data:
            return None

        ca = close_approach_data[0]

        # Diameter estimates
        diameter = obj.get('estimated_diameter', {})
        meters = diameter.get('meters', {})
        d_min = meters.get('estimated_diameter_min')
        d_max = meters.get('estimated_diameter_max')

        # Distance
        miss_distance = ca.get('miss_distance', {})
        dist_au = float(miss_distance.get('astronomical', 0))
        dist_km = float(miss_distance.get('kilometers', 0))
        dist_ld = dist_au / LD_TO_AU if dist_au else 0

        # Velocity
        rel_velocity = ca.get('relative_velocity', {})
        v_km_s = float(rel_velocity.get('kilometers_per_second', 0))

        return CloseApproach(
            designation=obj.get('neo_reference_id', 'unknown'),
            close_approach_date=self._parse_datetime(
                ca.get('close_approach_date_full', ca.get('close_approach_date', ''))
            ),
            distance_au=dist_au,
            distance_ld=dist_ld,
            distance_km=dist_km,
            relative_velocity_km_s=v_km_s,
            absolute_magnitude_h=obj.get('absolute_magnitude_h'),
            estimated_diameter_m_min=d_min,
            estimated_diameter_m_max=d_max,
            is_potentially_hazardous=obj.get('is_potentially_hazardous_asteroid', False),
            orbit_id=None,
            fullname=obj.get('name', ''),
        )

    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse NEO Feed date formats."""
        formats = [
            '%Y-%b-%d %H:%M',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return datetime.utcnow()
