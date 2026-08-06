"""
NIGHTWATCH mechanical-design parameters — the single source of truth.

Every budget module imports from here, so the numbers can no longer disagree
file-to-file the way they do across the repo today (MN76 vs MN78 mass, 2048 vs
8192 PPR, 10/15/20 deg horizon limits, temp in C vs F ...).

All values are SI (m, kg, s, N, Pa, K, rad). Imperial/astronomy figures from
the docs are converted on the way in via ``units``. Each field is tagged in
``PROVENANCE`` as:

    S = sourced  (stated in a repo file — path given)
    D = derived  (computed from sourced values)
    A = assumed  (repo silent — a stated engineering assumption)

The three ASSUMED structural load cases (survival wind, snow, seismic) and the
DGX thermal figure are the repo's governing voids; they are labelled so nothing
masquerades as measured or specified data.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import units as u

# ==========================================================================
# Materials  (E = Young's modulus Pa, sigma_y = yield Pa, rho = kg/m^3,
#             cte = 1/K, Sut for fatigue where relevant)
# ==========================================================================


@dataclass(frozen=True)
class Material:
    name: str
    E: float          # Young's modulus, Pa
    sigma_y: float    # yield strength, Pa
    rho: float        # density, kg/m^3
    cte: float        # coeff. thermal expansion, 1/K
    G: float = 0.0    # shear modulus, Pa (0 => derive as E/2.6)

    @property
    def shear_modulus(self) -> float:
        return self.G if self.G > 0 else self.E / 2.6


MATERIALS: dict[str, Material] = {
    # 6061-T6 aluminium — the frame material specified throughout the repo.
    "6061-T6": Material("6061-T6 aluminium", E=68.9e9, sigma_y=276e6, rho=2700.0, cte=23.6e-6, G=26.0e9),
    # 303 stainless — the counterweight shaft.
    "303-SS": Material("303 stainless", E=193e9, sigma_y=240e6, rho=8000.0, cte=17.3e-6, G=77.0e9),
    # A36 mild steel — pier top plate / steel-pier alternative.
    "A36-steel": Material("A36 steel", E=200e9, sigma_y=250e6, rho=7850.0, cte=11.7e-6, G=79.3e9),
    # 4000 psi fibre-reinforced concrete — the pier. Ec = 57000*sqrt(f'c[psi]) psi.
    "concrete-4ksi": Material("4000 psi concrete", E=24.86e9, sigma_y=27.6e6, rho=2400.0, cte=10.0e-6, G=10.4e9),
}


# ==========================================================================
# Optical tube assemblies — the unresolved MN76 / MN78 fork, both carried.
# ==========================================================================


@dataclass(frozen=True)
class OTA:
    name: str
    aperture_m: float
    focal_length_m: float
    f_ratio: float
    mass_kg: float
    tube_length_m: float
    tube_od_m: float          # outer tube diameter (for wind area & inertia)
    central_obstruction: float  # fraction of aperture diameter

    @property
    def cg_from_saddle_m(self) -> float:
        """
        CG height above the dovetail saddle plane. A closed Mak-Newt tube is
        roughly uniform, so CG ~ mid-tube; the saddle sits ~1/3 up the tube for
        balance, giving a modest lever arm. DERIVED (geometric estimate).
        """
        return 0.5 * self.tube_length_m - (self.tube_length_m / 3.0)


# Case A: MN76 as specified in NIGHTWATCH_Build_Package.md (primary spec table).
MN76 = OTA(
    name="Intes-Micro MN76 (f/6)",
    aperture_m=u.mm(178.0),
    focal_length_m=u.mm(1068.0),
    f_ratio=6.0,
    mass_kg=9.0,
    tube_length_m=u.mm(700.0),
    tube_od_m=u.mm(205.0),
    central_obstruction=0.25,
)

# Case B: MN78 as specified in docs/INTES_MICRO_HISTORY.md ("selected", f/8, 14 kg).
MN78 = OTA(
    name="Intes-Micro MN78 (f/8)",
    aperture_m=u.mm(180.0),
    focal_length_m=u.mm(1440.0),
    f_ratio=8.0,
    mass_kg=14.0,
    tube_length_m=u.mm(1400.0),
    tube_od_m=u.mm(210.0),
    central_obstruction=0.134,
)

OTA_CASES: dict[str, OTA] = {"MN76": MN76, "MN78": MN78}


@dataclass(frozen=True)
class ImagingTrain:
    """Lumped rear accessories: camera + ADC + Powermate + diagonal + focuser."""
    mass_kg: float = 4.0            # Musser load analysis (lumped)
    offset_behind_tube_m: float = u.mm(150.0)  # rear stack lever from tube back, DERIVED


IMAGING_TRAIN = ImagingTrain()


# ==========================================================================
# Harmonic (strain-wave) drives — Harmonic Drive LLC CSF series.
# ==========================================================================


@dataclass(frozen=True)
class HarmonicDrive:
    name: str
    ratio: float
    rated_torque_Nm: float      # continuous
    peak_torque_Nm: float       # momentary
    repeatability_arcsec: float
    backlash_arcmin: float
    mass_kg: float
    bore_m: float


RA_DRIVE = HarmonicDrive(
    name="CSF-32-100-2A-GR", ratio=100.0, rated_torque_Nm=127.0, peak_torque_Nm=343.0,
    repeatability_arcsec=6.0, backlash_arcmin=1.0, mass_kg=1.6, bore_m=u.mm(80.0),
)
DEC_DRIVE = HarmonicDrive(
    name="CSF-25-80-2A-GR", ratio=80.0, rated_torque_Nm=70.0, peak_torque_Nm=186.0,
    repeatability_arcsec=8.0, backlash_arcmin=1.0, mass_kg=1.0, bore_m=u.mm(64.0),
)


# ==========================================================================
# Motor / driver train (NEMA17 + planetary + harmonic).
# ==========================================================================


@dataclass(frozen=True)
class MotorDrive:
    step_angle_deg: float = 1.8       # NEMA17 full step
    microsteps: int = 16              # TMC5160
    planetary_ratio: float = 27.0     # StepperOnline planetary gearhead
    holding_torque_Nm: float = 0.45   # NEMA17 typical
    irun_A: float = 1.5               # TMC5160 run current
    igoto_A: float = 2.0              # TMC5160 goto current
    slew_rate_dps: float = 4.0        # firmware Config.h goto rate
    accel_dps2: float = 2.0           # firmware Config.h goto accel


MOTOR = MotorDrive()


def steps_per_degree(drive: HarmonicDrive, motor: MotorDrive = MOTOR) -> float:
    """Full mechanical resolution to the axis (steps/deg). DERIVED."""
    steps_per_motor_rev = (360.0 / motor.step_angle_deg) * motor.microsteps
    axis_ratio = motor.planetary_ratio * drive.ratio
    return steps_per_motor_rev * axis_ratio / 360.0


# ==========================================================================
# Encoder chains — the crux of the sub-arcsecond contradiction.
# ==========================================================================


@dataclass(frozen=True)
class Encoder:
    name: str
    counts_per_rev_native: float   # counts per revolution of the thing it's on
    on_axis: bool                  # True => already on the telescope axis
    upstream_ratio: float = 1.0    # gear ratio between encoder and axis (motor-side)

    @property
    def axis_counts_per_rev(self) -> float:
        return self.counts_per_rev_native * (self.upstream_ratio if not self.on_axis else 1.0)

    @property
    def resolution_arcsec(self) -> float:
        return u.ARCSEC_PER_REV / self.axis_counts_per_rev


# Baseline dual-encoder scheme from the Build Package / Hedrick review.
ENC_MOTOR_AMT103 = Encoder("AMT103-V motor-side", counts_per_rev_native=8192.0, on_axis=False, upstream_ratio=100.0)
ENC_AXIS_AS5600 = Encoder("AS5600 12-bit on-axis", counts_per_rev_native=4096.0, on_axis=True)

# Bold v2 proposal: on-axis absolute tape ring (Renishaw RESA-class) sized for sub-arcsec.
# A ~200 mm ring (circumference pi*200 = 628 mm) at ~15 um signal pitch gives ~41,900
# periods, and Renishaw x5000-class interpolation yields ~2.3e8 counts/rev (~0.0055
# arcsec/LSB). We use that delivered figure and let the encoder budget check it.
ENC_AXIS_RESA = Encoder("Renishaw RESA ring on-axis (proposed)", counts_per_rev_native=234_000_000.0, on_axis=True)


# ==========================================================================
# Frame housings (6061-T6, CNC).  Dimensions from the Build Package table.
# ==========================================================================


@dataclass(frozen=True)
class Housing:
    name: str
    outer_x_m: float
    outer_y_m: float
    depth_m: float          # along the axis => sets bearing separation
    wall_m: float           # structural wall thickness
    material_key: str = "6061-T6"

    @property
    def material(self) -> Material:
        return MATERIALS[self.material_key]


# Baseline walls 8 mm (Hedrick min); bold review raised to 12 mm.
RA_HOUSING = Housing("RA housing", outer_x_m=u.inch(8), outer_y_m=u.inch(8), depth_m=u.inch(3), wall_m=u.mm(8))
DEC_HOUSING = Housing("DEC housing", outer_x_m=u.inch(6), outer_y_m=u.inch(6), depth_m=u.inch(2.5), wall_m=u.mm(8))
RA_HOUSING_12MM = Housing("RA housing (12 mm wall)", outer_x_m=u.inch(8), outer_y_m=u.inch(8), depth_m=u.inch(3), wall_m=u.mm(12))
DEC_HOUSING_12MM = Housing("DEC housing (12 mm wall)", outer_x_m=u.inch(6), outer_y_m=u.inch(6), depth_m=u.inch(2.5), wall_m=u.mm(12))


# ==========================================================================
# Bearings (deep-groove values; repo labels them "angular contact" — flagged).
# C = dynamic load rating (N), C0 = static (N).
# ==========================================================================


@dataclass(frozen=True)
class Bearing:
    name: str
    bore_m: float
    od_m: float
    C_dynamic_N: float
    C0_static_N: float


BRG_RA_6008 = Bearing("6008-2RS (RA output)", bore_m=u.mm(40), od_m=u.mm(68), C_dynamic_N=16_800.0, C0_static_N=11_600.0)
BRG_DEC_6006 = Bearing("6006-2RS (DEC output)", bore_m=u.mm(30), od_m=u.mm(55), C_dynamic_N=13_300.0, C0_static_N=8_300.0)


# ==========================================================================
# Counterweight system (303 SS shaft + weights).
# ==========================================================================


@dataclass(frozen=True)
class CounterweightSystem:
    shaft_dia_m: float = u.inch(1.25)
    shaft_len_m: float = u.inch(18.0)
    weights_available_kg: float = 12.5   # 2x5 + 1x2.5 kg
    material_key: str = "303-SS"

    @property
    def material(self) -> Material:
        return MATERIALS[self.material_key]


COUNTERWEIGHTS = CounterweightSystem()


# ==========================================================================
# Pier (concrete Sonotube) + steel top plate.
# ==========================================================================


@dataclass(frozen=True)
class Pier:
    diameter_m: float = u.inch(12.0)
    height_above_m: float = u.inch(36.0)
    embed_depth_m: float = u.inch(36.0)
    fc_Pa: float = u.psi(4000.0)
    material_key: str = "concrete-4ksi"
    top_plate_thk_m: float = u.inch(0.375)
    top_plate_side_m: float = u.inch(12.0)

    @property
    def material(self) -> Material:
        return MATERIALS[self.material_key]


PIER = Pier()


# ==========================================================================
# Enclosure (roll-off roof).
# ==========================================================================


@dataclass(frozen=True)
class Enclosure:
    kind: str = "roll-off-roof"
    open_time_s: float = 45.0        # POS sim
    close_time_s: float = 45.0
    motor_timeout_s: float = 60.0
    # Roof geometry is unspecified in the repo -> assumed footprint for load calcs.
    roof_span_m: float = 3.0         # ASSUMED
    roof_length_m: float = 3.0       # ASSUMED
    roof_mass_kg: float = 180.0      # ASSUMED (framed + panelled roll-off roof)
    track_incline_deg: float = 0.0


ENCLOSURE = Enclosure()


# ==========================================================================
# Site & environment.
# ==========================================================================


@dataclass(frozen=True)
class Site:
    latitude_deg: float = 38.9
    longitude_deg: float = -117.4
    elevation_m: float = 1800.0

    @property
    def air_density(self) -> float:
        return u.isa_air_density(self.elevation_m)


SITE = Site()


@dataclass(frozen=True)
class Environment:
    # --- operational interlocks (SOURCED: safety monitor / constants) ---
    wind_park_ms: float = u.mph(25.0)          # park threshold
    wind_gust_close_ms: float = u.mph(35.0)    # emergency close
    temp_min_c: float = u.f_to_c(20.0)         # code TEMP_MIN_F
    temp_max_c: float = u.f_to_c(100.0)        # code TEMP_MAX_F
    humidity_max_pct: float = 85.0
    diurnal_swing_c: float = (40.0 - 0.0) * 5.0 / 9.0  # "30-40 F swing" -> ~22 C, DERIVED
    # --- structural survival loads (ASSUMED — repo is silent) ---
    survival_wind_ms: float = u.mph(105.0)     # ASCE 7 basic wind, central NV, Risk Cat I
    ground_snow_load_Pa: float = u.psf(25.0)   # ASSUMED high-desert @ 6000 ft
    seismic_sds_g: float = 0.50                # ASSUMED S_DS, Walker Lane vicinity
    # --- aerodynamics ---
    cd_cylinder: float = 1.1                   # tube broadside drag coefficient
    roof_uplift_gcp: float = 0.9               # ASCE net uplift coefficient (windward)


ENV = Environment()


# ==========================================================================
# Optical / focus (for the thermal budget).
# ==========================================================================


@dataclass(frozen=True)
class Optical:
    wavelength_m: float = 0.55e-6              # visual band
    astrositall_cte: float = 1.5e-7           # +/- over -60..+60 C (mirror substrate)


OPTICAL = Optical()


# ==========================================================================
# Tracking requirement (the "< 1 arcsec RMS" aspiration made a hard target).
# ==========================================================================
TRACKING_RMS_TARGET_ARCSEC = 1.0     # SOURCED aspiration (Hedrick review)
DEFLECTION_TARGET_ARCSEC = 5.0       # SOURCED target (Hedrick review)
NATURAL_FREQ_TARGET_HZ = 10.0        # SOURCED target (Hedrick review)


# ==========================================================================
# Provenance registry — keyed by dotted path; feeds the report's honesty table.
# ==========================================================================
PROVENANCE: dict[str, tuple[u.Provenance, str]] = {
    "MN76.mass_kg": (u.Provenance.SOURCED, "NIGHTWATCH_Build_Package.md spec table"),
    "MN78.mass_kg": (u.Provenance.SOURCED, "docs/INTES_MICRO_HISTORY.md ('selected')"),
    "OTA.cg_from_saddle_m": (u.Provenance.DERIVED, "geometric mid-tube estimate"),
    "IMAGING_TRAIN.mass_kg": (u.Provenance.SOURCED, "pos/agents/05_walton_musser.md load analysis"),
    "RA_DRIVE": (u.Provenance.SOURCED, "Build_Package.md / Musser (CSF-32-100)"),
    "DEC_DRIVE": (u.Provenance.SOURCED, "Build_Package.md / Musser (CSF-25-80)"),
    "MOTOR.slew_rate_dps": (u.Provenance.SOURCED, "firmware/onstepx_config/Config.h"),
    "ENC_MOTOR_AMT103": (u.Provenance.SOURCED, "Build_Package.md / Hedrick (8192 PPR x100)"),
    "ENC_AXIS_AS5600": (u.Provenance.SOURCED, "Build_Package.md / Hedrick (12-bit on-axis)"),
    "ENC_AXIS_RESA": (u.Provenance.ASSUMED, "proposed on-axis ring to meet sub-arcsec"),
    "RA_HOUSING.wall_m": (u.Provenance.SOURCED, "Hedrick min 8 mm (12 mm bold review)"),
    "BRG_RA_6008": (u.Provenance.SOURCED, "Build_Package.md bearing table (deep-groove C ratings)"),
    "COUNTERWEIGHTS": (u.Provenance.SOURCED, "Build_Package.md counterweight table"),
    "PIER": (u.Provenance.SOURCED, "Build_Package.md concrete pier spec"),
    "ENCLOSURE.roof_mass_kg": (u.Provenance.ASSUMED, "roof geometry unspecified in repo"),
    "SITE": (u.Provenance.SOURCED, "config.py / Config.h (central Nevada, 1800 m)"),
    "SITE.air_density": (u.Provenance.DERIVED, "ISA at 1800 m"),
    "ENV.wind_park_ms": (u.Provenance.SOURCED, "services/safety_monitor/monitor.py"),
    "ENV.survival_wind_ms": (u.Provenance.ASSUMED, "ASCE 7 basic wind speed, central NV"),
    "ENV.ground_snow_load_Pa": (u.Provenance.ASSUMED, "high-desert @ 6000 ft"),
    "ENV.seismic_sds_g": (u.Provenance.ASSUMED, "Walker Lane seismicity"),
    "TRACKING_RMS_TARGET_ARCSEC": (u.Provenance.SOURCED, "Hedrick '< 1 arcsec RMS'"),
    "DEFLECTION_TARGET_ARCSEC": (u.Provenance.SOURCED, "Hedrick '< 5 arcsec @ 25 kg'"),
    "NATURAL_FREQ_TARGET_HZ": (u.Provenance.SOURCED, "Hedrick '> 10 Hz'"),
}
