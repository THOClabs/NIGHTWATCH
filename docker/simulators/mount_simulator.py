#!/usr/bin/env python3
"""
LX200 Protocol Mount Simulator for NIGHTWATCH (Step 503)

Simulates an OnStepX mount controller responding to LX200 commands over TCP.
Supports basic telescope operations: position queries, slewing, parking, tracking.

Protocol: Meade LX200 with OnStepX extensions
Port: 9999 (configurable via MOUNT_SIM_PORT)

Common commands:
  :GR#  - Get RA (returns HH:MM:SS#)
  :GD#  - Get Dec (returns sDD*MM:SS#)
  :GA#  - Get Altitude
  :GZ#  - Get Azimuth
  :Sr HH:MM:SS#  - Set target RA
  :Sd sDD*MM:SS# - Set target Dec
  :MS#  - Slew to target (returns 0 on success)
  :Q#   - Stop all motion
  :hP#  - Park mount
  :hR#  - Unpark mount (OnStepX)
  :GVP# - Get product name
"""

import asyncio
import logging
import math
import os
import time
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MountSimulator:
    """Simulated equatorial mount with LX200 protocol."""

    def __init__(self):
        # Configuration from environment
        self.port = int(os.environ.get('MOUNT_SIM_PORT', 9999))
        self.latitude = float(os.environ.get('MOUNT_SIM_LATITUDE', 39.0))
        self.longitude = float(os.environ.get('MOUNT_SIM_LONGITUDE', -117.0))
        self.timezone = float(os.environ.get('MOUNT_SIM_TIMEZONE', -8))
        self.slew_rate = float(os.environ.get('MOUNT_SIM_SLEW_RATE', 2.0))  # deg/sec
        self.track_rate = float(os.environ.get('MOUNT_SIM_TRACK_RATE', 0.004178))  # sidereal

        # Mount state
        self.ra_hours = float(os.environ.get('MOUNT_SIM_INIT_RA', 0.0))
        self.dec_degrees = float(os.environ.get('MOUNT_SIM_INIT_DEC', 90.0))
        self.target_ra = 0.0
        self.target_dec = 0.0
        self.is_parked = os.environ.get('MOUNT_SIM_PARKED', 'true').lower() == 'true'
        self.is_slewing = False
        self.is_tracking = False
        self.pier_side = 'E'  # East or West

        # Internal
        self._last_update = time.time()
        self._slew_task: Optional[asyncio.Task] = None

    def get_lst(self) -> float:
        """Calculate local sidereal time in hours."""
        # Simplified LST calculation
        now = datetime.utcnow()
        jd = 367 * now.year - int(7 * (now.year + int((now.month + 9) / 12)) / 4) + \
             int(275 * now.month / 9) + now.day + 1721013.5
        jd += (now.hour + now.minute / 60 + now.second / 3600) / 24

        t = (jd - 2451545.0) / 36525.0
        gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + \
               0.000387933 * t * t - t * t * t / 38710000.0
        gmst = gmst % 360

        lst = (gmst + self.longitude) / 15.0  # Convert to hours
        return lst % 24

    def ra_to_alt_az(self, ra: float, dec: float) -> tuple:
        """Convert RA/Dec to Alt/Az."""
        lst = self.get_lst()
        ha = (lst - ra) * 15  # Hour angle in degrees

        lat_rad = math.radians(self.latitude)
        dec_rad = math.radians(dec)
        ha_rad = math.radians(ha)

        # Calculate altitude
        sin_alt = math.sin(dec_rad) * math.sin(lat_rad) + \
                  math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad)
        alt = math.degrees(math.asin(max(-1, min(1, sin_alt))))

        # Calculate azimuth
        cos_az = (math.sin(dec_rad) - math.sin(math.radians(alt)) * math.sin(lat_rad)) / \
                 (math.cos(math.radians(alt)) * math.cos(lat_rad))
        cos_az = max(-1, min(1, cos_az))
        az = math.degrees(math.acos(cos_az))

        if math.sin(ha_rad) > 0:
            az = 360 - az

        return alt, az

    def update_tracking(self):
        """Update position for sidereal tracking."""
        if self.is_tracking and not self.is_slewing and not self.is_parked:
            now = time.time()
            dt = now - self._last_update
            # Sidereal tracking: RA increases to compensate for Earth rotation
            self.ra_hours += self.track_rate * dt / 3600 * 24  # Convert to hours
            self.ra_hours = self.ra_hours % 24
            self._last_update = now

    async def slew_to_target(self):
        """Simulate slewing to target coordinates."""
        self.is_slewing = True
        logger.info(f"Slewing to RA={self.target_ra:.4f}h, Dec={self.target_dec:.2f}°")

        while True:
            # Calculate angular distance
            ra_diff = self.target_ra - self.ra_hours
            if ra_diff > 12:
                ra_diff -= 24
            elif ra_diff < -12:
                ra_diff += 24
            ra_diff_deg = ra_diff * 15  # Convert to degrees

            dec_diff = self.target_dec - self.dec_degrees

            total_diff = math.sqrt(ra_diff_deg**2 + dec_diff**2)

            if total_diff < 0.01:  # Close enough
                self.ra_hours = self.target_ra
                self.dec_degrees = self.target_dec
                break

            # Move towards target
            step = min(self.slew_rate * 0.1, total_diff)  # 100ms update rate
            if total_diff > 0:
                self.ra_hours += (ra_diff_deg / total_diff) * step / 15
                self.dec_degrees += (dec_diff / total_diff) * step

            # Normalize RA
            self.ra_hours = self.ra_hours % 24

            await asyncio.sleep(0.1)

        self.is_slewing = False
        self.is_tracking = True
        self._last_update = time.time()
        logger.info("Slew complete, tracking started")

    def format_ra(self) -> str:
        """Format RA as HH:MM:SS."""
        hours = int(self.ra_hours)
        minutes = int((self.ra_hours - hours) * 60)
        seconds = int(((self.ra_hours - hours) * 60 - minutes) * 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def format_dec(self) -> str:
        """Format Dec as sDD*MM:SS."""
        sign = '+' if self.dec_degrees >= 0 else '-'
        dec = abs(self.dec_degrees)
        degrees = int(dec)
        minutes = int((dec - degrees) * 60)
        seconds = int(((dec - degrees) * 60 - minutes) * 60)
        return f"{sign}{degrees:02d}*{minutes:02d}:{seconds:02d}"

    def parse_ra(self, ra_str: str) -> float:
        """Parse RA from HH:MM:SS format."""
        parts = ra_str.replace('#', '').split(':')
        hours = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        seconds = float(parts[2]) if len(parts) > 2 else 0
        return hours + minutes / 60 + seconds / 3600

    def parse_dec(self, dec_str: str) -> float:
        """Parse Dec from sDD*MM:SS format."""
        dec_str = dec_str.replace('#', '').replace('*', ':').replace("'", ':')
        negative = dec_str.startswith('-')
        dec_str = dec_str.lstrip('+-')
        parts = dec_str.split(':')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        seconds = float(parts[2]) if len(parts) > 2 else 0
        result = degrees + minutes / 60 + seconds / 3600
        return -result if negative else result

    def process_command(self, cmd: str) -> str:
        """Process an LX200 command and return response."""
        cmd = cmd.strip()
        if not cmd.startswith(':'):
            return ""

        self.update_tracking()

        # Get commands
        if cmd == ':GR#':  # Get RA
            return f"{self.format_ra()}#"

        elif cmd == ':GD#':  # Get Dec
            return f"{self.format_dec()}#"

        elif cmd == ':GA#':  # Get Altitude
            alt, _ = self.ra_to_alt_az(self.ra_hours, self.dec_degrees)
            return f"{alt:+.1f}#"

        elif cmd == ':GZ#':  # Get Azimuth
            _, az = self.ra_to_alt_az(self.ra_hours, self.dec_degrees)
            return f"{az:.1f}#"

        elif cmd == ':GS#':  # Get sidereal time
            lst = self.get_lst()
            hours = int(lst)
            minutes = int((lst - hours) * 60)
            seconds = int(((lst - hours) * 60 - minutes) * 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}#"

        elif cmd == ':Gstat#':  # OnStepX status
            # Status: T=tracking, S=slewing, P=parked, N=not tracking
            if self.is_parked:
                return "P#"
            elif self.is_slewing:
                return "S#"
            elif self.is_tracking:
                return "T#"
            else:
                return "N#"

        elif cmd == ':GVP#':  # Product name
            return "OnStepX-Sim#"

        elif cmd == ':GVN#':  # Firmware version
            return "5.0.0#"

        # Set commands
        elif cmd.startswith(':Sr'):  # Set target RA
            ra_str = cmd[3:]
            try:
                self.target_ra = self.parse_ra(ra_str)
                return "1"
            except Exception:
                return "0"

        elif cmd.startswith(':Sd'):  # Set target Dec
            dec_str = cmd[3:]
            try:
                self.target_dec = self.parse_dec(dec_str)
                return "1"
            except Exception:
                return "0"

        # Motion commands
        elif cmd == ':MS#':  # Slew to target
            if self.is_parked:
                return "1Parked#"
            alt, _ = self.ra_to_alt_az(self.target_ra, self.target_dec)
            if alt < -10:
                return "1Below horizon#"
            # Start slew in background
            if self._slew_task:
                self._slew_task.cancel()
            self._slew_task = asyncio.create_task(self.slew_to_target())
            return "0"  # Success

        elif cmd == ':Q#':  # Stop all motion
            if self._slew_task:
                self._slew_task.cancel()
            self.is_slewing = False
            return ""

        elif cmd == ':hP#':  # Park
            self.is_tracking = False
            self.is_parked = True
            self.ra_hours = 0.0
            self.dec_degrees = 90.0
            logger.info("Mount parked")
            return "1"

        elif cmd == ':hR#':  # Unpark (OnStepX)
            self.is_parked = False
            self.is_tracking = True
            self._last_update = time.time()
            logger.info("Mount unparked")
            return "1"

        elif cmd == ':Te#':  # Enable tracking
            if not self.is_parked:
                self.is_tracking = True
                self._last_update = time.time()
            return "1"

        elif cmd == ':Td#':  # Disable tracking
            self.is_tracking = False
            return "1"

        elif cmd.startswith(':Sg'):  # Set longitude
            return "1"

        elif cmd.startswith(':St'):  # Set latitude
            return "1"

        elif cmd.startswith(':SG'):  # Set UTC offset
            return "1"

        else:
            logger.warning(f"Unknown command: {cmd}")
            return ""


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, mount: MountSimulator):
    """Handle a single client connection."""
    addr = writer.get_extra_info('peername')
    logger.info(f"New connection from {addr}")

    try:
        buffer = ""
        while True:
            data = await reader.read(1024)
            if not data:
                break

            buffer += data.decode('utf-8', errors='ignore')

            # Process complete commands (terminated by #)
            while '#' in buffer:
                cmd, buffer = buffer.split('#', 1)
                cmd = cmd + '#'

                response = mount.process_command(cmd)
                if response:
                    writer.write(response.encode())
                    await writer.drain()

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error handling client: {e}")
    finally:
        logger.info(f"Connection closed: {addr}")
        writer.close()
        await writer.wait_closed()


async def main():
    """Main entry point."""
    mount = MountSimulator()

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, mount),
        '0.0.0.0', mount.port
    )

    addr = server.sockets[0].getsockname()
    logger.info(f"LX200 Mount Simulator listening on {addr}")
    logger.info(f"Initial position: RA={mount.ra_hours:.2f}h, Dec={mount.dec_degrees:.2f}°")
    logger.info(f"Parked: {mount.is_parked}")

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
