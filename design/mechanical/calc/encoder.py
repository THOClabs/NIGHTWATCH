"""
Tracking-error (pointing) budget — the SHARP proof of the whole mount.

The repo's headline aspiration is "< 1 arcsec RMS" tracking (Hedrick review,
``P.TRACKING_RMS_TARGET_ARCSEC``). This module asks the uncomfortable question:
does the *as-specified* encoder chain actually reach it? It does not — and that
is the point of the proof.

Two schemes are compared:

Baseline (as specified in the Build Package)
    A dual-encoder scheme: a fine AMT103 on the *motor* shaft (8192 PPR x100 =>
    ~1.58" to the axis) plus a cheap AS5600 12-bit absolute "on-axis" chip
    (~316" resolution). The servo can only close its loop on the motor encoder,
    because the AS5600's quantisation (~91" RMS) is 90x the entire error budget
    and is fit only for coarse homing, not tracking. So everything the motor
    encoder cannot *see* leaks straight into pointing:
      * harmonic-drive periodic error between motor and axis (PE residual), and
      * structural / drivetrain flexure between motor and star.
    Baseline RMS = RSS(motor_quant, PE_residual, flexure).

Proposed (v2)
    Close the servo loop on a genuine on-axis high-resolution *absolute* ring
    (Renishaw RESA-class, ``P.ENC_AXIS_RESA``, sub-arcsec LSB). Sitting on the
    axis, it observes and corrects the harmonic PE and every drivetrain/mount
    flexure *upstream* of the axis; only the servo following error and the
    residual OTA/mirror-cell flexure *downstream* of the ring survive.
    Proposed RMS = RSS(resa_quant, servo_following, residual_flexure).

Headline decision: the baseline chain FAILS < 1 arcsec (~5 arcsec RMS); an
on-axis high-resolution absolute encoder is REQUIRED to reach sub-arcsecond.
"""

from __future__ import annotations

import math

from . import params as P
from .budget import BudgetResult, verdict_from_sf

# --------------------------------------------------------------------------
# Modelled error terms. None of these exist in params.py, so they are defined
# and tagged here (DERIVED/ASSUMED) and echoed into result.assumptions.
# --------------------------------------------------------------------------

# Harmonic-drive periodic-error residual that the MOTOR encoder cannot observe.
# ASSUMED 4.0" RMS — consistent with the CSF units' 6-8" peak repeatability
# (P.RA_DRIVE.repeatability_arcsec = 6", P.DEC_DRIVE = 8"): a quasi-sinusoidal
# PE of ~6-8" peak-to-peak lands near ~4" RMS once the strain-wave 2/rev term
# and gravity-dependent lost motion are folded in. ASSUMED.
PE_RESIDUAL_ARCSEC = 4.0

# Drivetrain + mount flexure between the motor encoder and the star, none of it
# seen by a motor-side encoder. From a stated ~3" structural flexure budget
# (bearing preload, housing wall, harmonic wind-up). ASSUMED.
FLEXURE_ARCSEC = 3.0

# On-axis closed-loop servo following error once the loop is closed on a
# high-resolution axis encoder (finite loop bandwidth vs wind/seeing input).
# ASSUMED 0.2" RMS — routine for a stiff sub-kHz servo with a fine axis sensor.
SERVO_FOLLOWING_ARCSEC = 0.2

# Residual flexure that even an on-axis ring CANNOT correct: the OTA / focuser /
# mirror-cell flex that lies *downstream* of the encoder ring, between the axis
# and the focal plane. Much smaller than the full 3" chain flexure because the
# ring corrects everything upstream of the axis. ASSUMED 0.5" RMS.
FLEXURE_RESIDUAL_ARCSEC = 0.5


# --------------------------------------------------------------------------
# Pure helpers (the tests call these directly).
# --------------------------------------------------------------------------


def quant_rms_arcsec(enc: P.Encoder) -> float:
    """RMS error of an ideal uniform quantiser = LSB / sqrt(12) (arcsec)."""
    return enc.resolution_arcsec / math.sqrt(12.0)


def _rss(*terms: float) -> float:
    return math.sqrt(sum(t * t for t in terms))


def tracking_components(scheme: str = "baseline") -> dict[str, float]:
    """Return the RMS error terms (arcsec) that RSS into the tracking budget."""
    if scheme == "baseline":
        return {
            "quant": quant_rms_arcsec(P.ENC_MOTOR_AMT103),  # servo on motor encoder
            "pe_residual": PE_RESIDUAL_ARCSEC,              # unseen by motor encoder
            "flexure": FLEXURE_ARCSEC,                      # unseen by motor encoder
        }
    if scheme == "proposed":
        return {
            "quant": quant_rms_arcsec(P.ENC_AXIS_RESA),     # servo on on-axis ring
            "servo": SERVO_FOLLOWING_ARCSEC,                # finite-bandwidth following
            "flexure": FLEXURE_RESIDUAL_ARCSEC,             # OTA flex downstream of ring
        }
    raise ValueError(f"unknown scheme {scheme!r} (want 'baseline' or 'proposed')")


def tracking_rms_arcsec(scheme: str = "baseline") -> float:
    """Total pointing/tracking error (arcsec RMS) for a scheme, via RSS."""
    return _rss(*tracking_components(scheme).values())


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------


def evaluate(scheme: str = "compare") -> BudgetResult:
    target = P.TRACKING_RMS_TARGET_ARCSEC

    base = tracking_rms_arcsec("baseline")
    prop = tracking_rms_arcsec("proposed")
    base_sf = target / base   # >1 => meets target with margin
    prop_sf = target / prop

    base_c = tracking_components("baseline")
    prop_c = tracking_components("proposed")

    base_verdict = verdict_from_sf(base_sf, pass_at=1.5, marginal_at=1.0)
    prop_verdict = verdict_from_sf(prop_sf, pass_at=1.5, marginal_at=1.0)

    if scheme == "baseline":
        verdict, sf = base_verdict, base_sf
        headline = (
            f"Baseline dual-encoder chain: {base:.2f} arcsec RMS vs {target:.1f} arcsec "
            f"target (SF {base_sf:.2f}) — FAILS; the motor encoder cannot see harmonic "
            f"PE or mount flexure."
        )
    elif scheme == "proposed":
        verdict, sf = prop_verdict, prop_sf
        headline = (
            f"On-axis RESA ring closed loop: {prop:.2f} arcsec RMS vs {target:.1f} arcsec "
            f"target (SF {prop_sf:.2f}) — MEETS sub-arcsecond."
        )
    elif scheme == "compare":
        # The design AS SPECIFIED is the baseline, so the honest module verdict
        # is the baseline's: it FAILS, and the proposed ring is the remedy.
        verdict, sf = base_verdict, base_sf
        headline = (
            f"Baseline dual-encoder chain reaches only {base:.2f} arcsec RMS, FAILING the "
            f"{target:.1f} arcsec target; the on-axis RESA ring reaches {prop:.2f} arcsec RMS. "
            f"An on-axis high-resolution absolute encoder is REQUIRED to reach sub-arcsecond."
        )
    else:
        raise ValueError(f"unknown scheme {scheme!r}")

    res = BudgetResult(
        key="encoder",
        title="Tracking-error (pointing) budget",
        verdict=verdict,
        headline=headline,
        target=f"Tracking error < {target:.1f} arcsec RMS (P.TRACKING_RMS_TARGET_ARCSEC)",
        safety_factor=sf,
    )

    # --- Encoder resolutions (LSB to the axis) ---
    res.add("AMT103 motor-side resolution (to axis)", P.ENC_MOTOR_AMT103.resolution_arcsec,
            "arcsec/LSB", "8192 PPR x100 upstream ratio")
    res.add("AS5600 on-axis resolution", P.ENC_AXIS_AS5600.resolution_arcsec,
            "arcsec/LSB", "12-bit => quant RMS 91\", homing-grade only")
    res.add("RESA on-axis resolution (proposed)", P.ENC_AXIS_RESA.resolution_arcsec,
            "arcsec/LSB", "absolute ring, sub-arcsec")

    # --- Baseline chain (servo locked to the motor encoder) ---
    res.add("Baseline: motor quant RMS", base_c["quant"], "arcsec", "res/sqrt(12)")
    res.add("Baseline: harmonic PE residual", base_c["pe_residual"], "arcsec", "unseen by motor enc")
    res.add("Baseline: drivetrain/mount flexure", base_c["flexure"], "arcsec", "unseen by motor enc")
    res.add("Baseline total tracking RMS", base, "arcsec", "RSS of the three")
    res.add("Baseline margin (target/achieved)", base_sf, "x", "<1 => fails")

    # --- Proposed chain (servo locked to the on-axis ring) ---
    res.add("Proposed: RESA quant RMS", prop_c["quant"], "arcsec", "res/sqrt(12)")
    res.add("Proposed: servo following error", prop_c["servo"], "arcsec", "on-axis closed loop")
    res.add("Proposed: residual OTA flexure", prop_c["flexure"], "arcsec", "downstream of ring")
    res.add("Proposed total tracking RMS", prop, "arcsec", "RSS of the three")
    res.add("Proposed margin (target/achieved)", prop_sf, "x", ">1 => meets")

    res.assumptions = [
        "Quantisation RMS = LSB/sqrt(12) (ideal uniform quantiser).",
        f"Baseline servo closes on the MOTOR encoder ({P.ENC_MOTOR_AMT103.resolution_arcsec:.2f}\" "
        f"to axis); the AS5600's {quant_rms_arcsec(P.ENC_AXIS_AS5600):.0f}\" quant RMS makes it "
        f"a homing reference only, so harmonic PE and mount flexure leak into pointing. SOURCED chain.",
        f"Harmonic PE residual = {PE_RESIDUAL_ARCSEC:.1f}\" RMS (ASSUMED), consistent with CSF "
        f"repeatability P.RA_DRIVE={P.RA_DRIVE.repeatability_arcsec:.0f}\" / "
        f"P.DEC_DRIVE={P.DEC_DRIVE.repeatability_arcsec:.0f}\".",
        f"Drivetrain + mount flexure = {FLEXURE_ARCSEC:.1f}\" RMS (ASSUMED, stated structural budget), "
        f"entirely upstream of the axis and thus invisible to a motor encoder.",
        f"Proposed on-axis ring corrects everything upstream of the axis; only servo following "
        f"({SERVO_FOLLOWING_ARCSEC:.1f}\" RMS, ASSUMED) and residual OTA/focuser flexure "
        f"({FLEXURE_RESIDUAL_ARCSEC:.1f}\" RMS, ASSUMED) downstream of the ring remain.",
        "Terms combine in RSS (independent, zero-mean error sources).",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
