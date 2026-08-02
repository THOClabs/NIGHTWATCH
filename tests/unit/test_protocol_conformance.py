"""S4-4: Protocol-conformance tests binding the REAL service classes to the
Service Protocols declared in :mod:`nightwatch.orchestrator`.

This module is *purely additive* and *introspection-only*: it changes no product
code and instantiates no hardware. Every check is performed against the class
object via :func:`inspect.getattr_static`, so no ``__init__`` runs and no real or
simulated I/O is touched.

For each Protocol member we assert both (a) presence on the concrete class and
(b) the correct *kind*:

* ``property``        -> ``isinstance(getattr_static(cls, name), property)``
* ``async`` coroutine -> ``inspect.iscoroutinefunction``
* plain ``method``    -> callable and *not* a coroutine function

Where a real service does **not** currently conform (a missing member, a
method that the Protocol pins as a ``property``, or a sync method where the
Protocol implies an awaitable), the specific ``(class, member)`` case is marked
``xfail(strict=True)`` with a reason naming the later stage that owes the fix.
The xfail list below is therefore the *conformance backlog*: when a fixing stage
lands, the affected case flips to xpass and ``strict=True`` turns that into a
failure -- forcing the backlog entry to be pruned. Keep the reasons specific.
"""

from __future__ import annotations

import importlib
import inspect
from typing import Dict, Tuple

import pytest

from nightwatch import orchestrator as O


# ---------------------------------------------------------------------------
# Protocol -> concrete production class bindings.
#
# ``ServiceProtocol`` itself is the abstract lifecycle base and has no direct
# concrete implementation, so it is not bound on its own; its members
# (start/stop/is_running) are inherited into every subclass below and checked
# there against each real service.
#
# ``EphemerisServiceProtocol`` and ``AstrometryServiceProtocol`` /
# ``GuidingServiceProtocol`` etc. are bound to their concrete modules. If a
# Protocol had *no* production implementation it would simply be omitted here
# (none are omitted -- every Protocol below has a concrete class).
# ---------------------------------------------------------------------------
BINDINGS: Tuple[Tuple[str, str, str], ...] = (
    ("MountServiceProtocol", "services.mount_control.lx200", "LX200Client"),
    ("CatalogServiceProtocol", "services.catalog.catalog", "CatalogService"),
    ("EphemerisServiceProtocol", "services.ephemeris.skyfield_service", "EphemerisService"),
    ("WeatherServiceProtocol", "services.weather.unified", "UnifiedWeatherService"),
    # The Orchestrator binds SafetyMonitor as the safety service: its
    # ``register_callback`` is the ARCH-003 cancel-on-unsafe pipe named in the
    # SafetyServiceProtocol docstring. (NightwatchSafetySystem is a higher-level
    # wrapper with a different, also-nonconforming surface and is not the bound
    # SafetyServiceProtocol impl.)
    ("SafetyServiceProtocol", "services.safety_monitor.monitor", "SafetyMonitor"),
    ("CameraServiceProtocol", "services.camera.asi_camera", "ASICamera"),
    ("GuidingServiceProtocol", "services.guiding.phd2_client", "PHD2Client"),
    ("FocusServiceProtocol", "services.focus.focuser_service", "FocuserService"),
    ("AstrometryServiceProtocol", "services.astrometry.plate_solver", "PlateSolver"),
    ("AlertServiceProtocol", "services.alerts.alert_manager", "AlertManager"),
    ("PowerServiceProtocol", "services.power.power_manager", "PowerManager"),
    ("EnclosureServiceProtocol", "services.enclosure.roof_controller", "RoofController"),
)


# ---------------------------------------------------------------------------
# Conformance backlog: (concrete class name, Protocol member) -> xfail reason.
#
# Every entry names the later stage that owes the fix. Membership here is the
# ONLY thing that marks a case xfail(strict=True); a case not listed here is
# expected to conform right now. Derived from static introspection of the real
# classes at S4-4 time -- see the PR body for the enumeration.
#
# Stage legend:
#   S4-3  -> make LX200Client mount motion async + expose parked/tracking as
#            properties and a canonical async slew_to_coordinates.
#   S4-1  -> wire-or-delete dormant subsystems: give every concrete service the
#            ServiceProtocol lifecycle (start/stop/is_running) and align the
#            method/property names the Protocols pin (naming + kind reconcile).
# ---------------------------------------------------------------------------
KNOWN_GAPS: Dict[Tuple[str, str], str] = {
    # --- MountServiceProtocol <- LX200Client -------------------------------
    # S4-3 FIXED (removed from backlog): slew_to_coordinates, park, unpark,
    # is_parked, is_tracking, stop now conform (async coroutines + properties).
    # Those parametrized cases must PASS now, not xfail.
    # S4-1a FIXED (removed from backlog): start, is_running lifecycle added.

    # --- CatalogServiceProtocol <- CatalogService --------------------------
    # S4-1a FIXED: start, stop, is_running lifecycle added (delegate to
    # initialize()/close()).

    # --- EphemerisServiceProtocol <- EphemerisService ----------------------
    # S4-1a FIXED: start, stop, is_running lifecycle added.
    # S4-1b (still owed): get_planet_position, get_twilight_times semantic aliases.
    ("EphemerisService", "get_planet_position"): (
        "S4-1b: EphemerisService exposes get_body_position(...); no get_planet_position(str)."
    ),
    ("EphemerisService", "get_twilight_times"): (
        "S4-1b: EphemerisService exposes get_twilight_phase(...); no get_twilight_times()."
    ),

    # --- WeatherServiceProtocol <- UnifiedWeatherService -------------------
    # S4-1a FIXED: start, stop, is_running lifecycle added.
    # S4-1b (still owed): is_safe/current_conditions kind + naming reconcile.
    ("UnifiedWeatherService", "is_safe"): (
        "S4-1b: UnifiedWeatherService.is_safe is an async coroutine; Protocol pins a "
        "synchronous property."
    ),
    ("UnifiedWeatherService", "current_conditions"): (
        "S4-1b: UnifiedWeatherService exposes async get_conditions(); no current_conditions property."
    ),

    # --- SafetyServiceProtocol <- SafetyMonitor ----------------------------
    # S4-1a FIXED: start (begin monitoring), stop (now async), is_running added.
    # S4-1b (still owed): is_safe/get_unsafe_reasons semantic aliases.
    ("SafetyMonitor", "is_safe"): (
        "S4-1b: SafetyMonitor exposes verdict via evaluate() -> SafetyStatus; no is_safe property."
    ),
    ("SafetyMonitor", "get_unsafe_reasons"): (
        "S4-1b: SafetyMonitor surfaces reasons on SafetyStatus; no get_unsafe_reasons() method."
    ),

    # --- CameraServiceProtocol <- ASICamera --------------------------------
    # S4-1a FIXED: start, stop, is_running lifecycle added.
    # S4-1b (still owed): capture/is_exposing semantic aliases.
    ("ASICamera", "capture"): (
        "S4-1b: ASICamera exposes capture_single/capture_frame; no capture(exposure, gain)."
    ),
    ("ASICamera", "is_exposing"): "S4-1b: ASICamera has no is_exposing property.",

    # --- GuidingServiceProtocol <- PHD2Client ------------------------------
    # S4-1a FIXED: start, stop, is_running lifecycle added.
    # S4-1b (still owed): is_guiding semantic alias.
    ("PHD2Client", "is_guiding"): (
        "S4-1b: PHD2Client exposes state -> GuideState property; no is_guiding bool property."
    ),

    # --- FocusServiceProtocol <- FocuserService ----------------------------
    # S4-1a FIXED: start, stop, is_running lifecycle added.

    # --- AstrometryServiceProtocol <- PlateSolver --------------------------
    # S4-1a FIXED: start, stop, is_running lifecycle added.

    # --- AlertServiceProtocol <- AlertManager ------------------------------
    # S4-1a FIXED: start, stop, is_running lifecycle added.
    # S4-1b (still owed): send_alert semantic alias.
    ("AlertManager", "send_alert"): (
        "S4-1b: AlertManager exposes raise_alert(Alert); no send_alert(level: str, message: str)."
    ),

    # --- PowerServiceProtocol <- PowerManager ------------------------------
    # S4-1a FIXED: is_running property added (start/stop already conformed).
    # S4-1b (still owed): on_battery/battery_percent semantic aliases.
    ("PowerManager", "on_battery"): "S4-1b: PowerManager has no on_battery property.",
    ("PowerManager", "battery_percent"): "S4-1b: PowerManager has no battery_percent property.",

    # --- EnclosureServiceProtocol <- RoofController ------------------------
    # S4-1a FIXED: start, is_running added (stop/open/close/is_open already conformed).
}


# ---------------------------------------------------------------------------
# Introspection helpers.
# ---------------------------------------------------------------------------
_NON_MEMBER_ATTRS = frozenset({"_is_protocol", "_abc_impl"})


def protocol_members(proto: type) -> Dict[str, str]:
    """Return ``{member_name: expected_kind}`` declared on a Protocol.

    Walks the Protocol MRO so inherited ServiceProtocol members
    (start/stop/is_running) are included, skipping dunders and the
    typing/abc bookkeeping attributes. ``expected_kind`` is one of
    ``"property"``, ``"async"`` or ``"method"``.
    """
    members: Dict[str, str] = {}
    for klass in proto.__mro__:
        if klass.__name__ in ("Protocol", "object", "Generic"):
            continue
        for name, value in vars(klass).items():
            if name.startswith("__") or name in _NON_MEMBER_ATTRS:
                continue
            if name in members:
                continue
            if isinstance(value, property):
                members[name] = "property"
            elif inspect.iscoroutinefunction(value):
                members[name] = "async"
            elif callable(value):
                members[name] = "method"
            # non-callable, non-property class vars are not part of the
            # behavioural interface we assert; ignore them.
    return members


def actual_kind(cls: type, name: str) -> str:
    """Classify how ``name`` is defined on ``cls`` *statically* (no instance).

    Returns ``"property"``, ``"async"``, ``"method"``, or ``"MISSING"``.
    Uses :func:`inspect.getattr_static` so descriptors are inspected without
    triggering them and no ``__init__`` runs.
    """
    try:
        value = inspect.getattr_static(cls, name)
    except AttributeError:
        return "MISSING"
    if isinstance(value, (staticmethod, classmethod)):
        value = value.__func__
    if isinstance(value, property):
        return "property"
    if inspect.iscoroutinefunction(value):
        return "async"
    if callable(value):
        return "method"
    return "MISSING"


def _build_cases():
    """Yield ``pytest.param(proto, cls, member, expected)`` for every
    (Protocol, real class, member) triple, xfail-marking known gaps."""
    cases = []
    for proto_name, module_path, class_name in BINDINGS:
        proto = getattr(O, proto_name)
        cls = getattr(importlib.import_module(module_path), class_name)
        for member, expected in protocol_members(proto).items():
            marks = ()
            reason = KNOWN_GAPS.get((class_name, member))
            if reason is not None:
                marks = (pytest.mark.xfail(reason=reason, strict=True),)
            cases.append(
                pytest.param(
                    proto,
                    cls,
                    member,
                    expected,
                    id=f"{class_name}.{member}",
                    marks=marks,
                )
            )
    return cases


CASES = _build_cases()


@pytest.mark.parametrize("proto, cls, member, expected_kind", CASES)
def test_real_service_conforms_to_protocol(proto, cls, member, expected_kind):
    """Each Protocol member must be present on the bound real class with the
    correct kind (property vs plain method vs async coroutine).

    Cases listed in ``KNOWN_GAPS`` are xfail(strict=True): they document a
    real conformance gap and will flip to a failure (xpass) once the owning
    stage fixes them -- that is the signal to remove the backlog entry.
    """
    got = actual_kind(cls, member)
    assert got == expected_kind, (
        f"{cls.__name__}.{member}: Protocol {proto.__name__} declares "
        f"'{expected_kind}' but concrete class provides '{got}'"
    )


def test_every_protocol_is_bound_to_a_concrete_class():
    """Guard: every Service Protocol subclass declared in the orchestrator is
    covered by exactly one production binding here (so no Protocol silently
    escapes conformance tracking). ``ServiceProtocol`` itself is the abstract
    base and is intentionally excluded."""
    declared = {
        name
        for name, obj in vars(O).items()
        if isinstance(obj, type)
        and name.endswith("ServiceProtocol")
        and name != "ServiceProtocol"
        and getattr(obj, "_is_protocol", False)
    }
    bound = {proto_name for proto_name, _, _ in BINDINGS}
    missing = declared - bound
    assert not missing, f"Service Protocols with no conformance binding: {sorted(missing)}"
