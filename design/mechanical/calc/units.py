"""
Units, physical constants, and provenance tagging for the NIGHTWATCH
mechanical-design calculator.

Everything in this package computes in **SI base units** (metre, kilogram,
second, newton, pascal, kelvin, radian). Conversion helpers below turn the
imperial / astronomy figures quoted in the repo's docs into SI so there is a
single internal system and the numbers can no longer disagree file-to-file.

Provenance
----------
Every input parameter in ``params.py`` is tagged with a ``Provenance`` so the
report can honestly separate what the repo actually specifies from what we
derived or had to assume (the repo is silent on survival wind, snow, seismic,
and DGX power — those are ASSUMED and labelled as such).
"""

from __future__ import annotations

import enum
import math

# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


class Provenance(enum.Enum):
    """Where a parameter's value comes from."""

    SOURCED = "sourced"   # stated in the repo (a doc, config, or firmware file)
    DERIVED = "derived"   # computed from sourced values inside this package
    ASSUMED = "assumed"   # repo is silent; a stated engineering assumption

    @property
    def marker(self) -> str:
        return {"sourced": "S", "derived": "D", "assumed": "A"}[self.value]


# --------------------------------------------------------------------------
# Length
# --------------------------------------------------------------------------
IN_TO_M = 0.0254
FT_TO_M = 0.3048
MM_TO_M = 1.0e-3


def inch(x: float) -> float:
    return x * IN_TO_M


def foot(x: float) -> float:
    return x * FT_TO_M


def mm(x: float) -> float:
    return x * MM_TO_M


# --------------------------------------------------------------------------
# Mass / force
# --------------------------------------------------------------------------
LB_TO_KG = 0.45359237
G0 = 9.80665  # m/s^2, standard gravity


def lb(x: float) -> float:
    return x * LB_TO_KG


def weight_N(mass_kg: float) -> float:
    """Gravitational force (newtons) of a mass at standard gravity."""
    return mass_kg * G0


# --------------------------------------------------------------------------
# Speed
# --------------------------------------------------------------------------
MPH_TO_MS = 0.44704


def mph(x: float) -> float:
    return x * MPH_TO_MS


# --------------------------------------------------------------------------
# Pressure
# --------------------------------------------------------------------------
PSI_TO_PA = 6894.757
PSF_TO_PA = 47.880259  # pounds per square foot -> pascal


def psi(x: float) -> float:
    return x * PSI_TO_PA


def psf(x: float) -> float:
    return x * PSF_TO_PA


# --------------------------------------------------------------------------
# Angle (astronomy)
# --------------------------------------------------------------------------
ARCSEC_PER_REV = 360.0 * 3600.0           # 1_296_000
ARCSEC_PER_RAD = 180.0 * 3600.0 / math.pi  # ~206264.806


def rad_to_arcsec(theta_rad: float) -> float:
    return theta_rad * ARCSEC_PER_RAD


def arcsec_to_rad(theta_arcsec: float) -> float:
    return theta_arcsec / ARCSEC_PER_RAD


def deg_to_rad(deg: float) -> float:
    return math.radians(deg)


# --------------------------------------------------------------------------
# Temperature
# --------------------------------------------------------------------------
def f_to_c(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


def c_to_k(c: float) -> float:
    return c + 273.15


# --------------------------------------------------------------------------
# Atmosphere (International Standard Atmosphere, troposphere)
# --------------------------------------------------------------------------
def isa_air_density(altitude_m: float, sea_level_density: float = 1.225) -> float:
    """
    ISA air density (kg/m^3) at a geopotential altitude. Central Nevada sits at
    ~1800 m, where air is ~17% thinner than sea level — this materially reduces
    wind drag and is normally ignored in amateur mount design. DERIVED.
    """
    # rho = rho0 * (1 - L*h/T0)^(g*M/(R*L) - 1), troposphere lapse form.
    return sea_level_density * (1.0 - 2.25577e-5 * altitude_m) ** 4.25588


__all__ = [
    "Provenance",
    "IN_TO_M", "FT_TO_M", "MM_TO_M", "inch", "foot", "mm",
    "LB_TO_KG", "G0", "lb", "weight_N",
    "MPH_TO_MS", "mph",
    "PSI_TO_PA", "PSF_TO_PA", "psi", "psf",
    "ARCSEC_PER_REV", "ARCSEC_PER_RAD",
    "rad_to_arcsec", "arcsec_to_rad", "deg_to_rad",
    "f_to_c", "c_to_k", "isa_air_density",
]
