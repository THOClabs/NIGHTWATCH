# 04 — Inspection & Test Plan (ITP)

**Document:** BP-00 / 04 — Inspection & Test Plan, Rev A
**Status:** **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**
**Units:** mm primary, [inch] in brackets.

This ITP sets **acceptance criteria and hold/witness points** for each trade. The
deliverable reports named here are a **condition of acceptance and payment** and shall
be priced into every bid (see `00_instructions_to_bidders.md` §4). Verification
methods reference the standards register (`02_standards_register.md`).

**Point types:** **H = Hold point** (work shall not proceed past this point until the
Owner/PE releases it) · **W = Witness point** (Owner may attend; contractor gives
notice, work may proceed if Owner declines) · **R = Review of records** (documentation
only) · **S = Surveillance** (contractor's own QC, records retained).

---

## 1. BP-01 — Mount head machining (6061-T6, CNC)

Parts: NW-MH-001 (RA housing), NW-MH-002 (DEC housing + saddle), NW-MH-003 (clamp bar).

| # | Characteristic | Acceptance criterion | Method / standard | Point |
|:-:|---|---|---|:-:|
| 1.1 | Material | 6061-T6 per ASTM B209 / AMS-QQ-A-250/11 | **Mill certificate** (heat/lot traceable) | R |
| 1.2 | Bearing seat bore — RA | Ø **68.0 mm [2.677 in] H7** (+0.030/0), for 7008 pair | **CMM** dimensional report | **H** |
| 1.3 | Bearing seat bore — DEC | Ø **55.0 mm [2.165 in] H7** (+0.030/0), for 7006 pair | **CMM** dimensional report | **H** |
| 1.4 | Drive register bores | RA Ø **80.0 mm [3.150 in]** (CSF-32); DEC Ø **64.0 mm [2.520 in]** (CSF-25) | CMM | W |
| 1.5 | Flange bolt patterns | RA 8× on **104 mm [4.094 in]** PCD; DEC on **83 mm [3.268 in]** PCD; true position per Y14.5 | CMM | W |
| 1.6 | Flange face flatness | **0.05 mm [0.002 in]** flat | CMM / surface plate | W |
| 1.7 | General tolerances | ISO 2768-mK | Calipers/micrometer, first-article | S |
| 1.8 | Surface finish | **Ra 1.6 µm** (NW-MH-001/002), **Ra 3.2 µm** (NW-MH-003) | Profilometer per **ASME B46.1** | W |
| 1.9 | Finish | Type III hardcoat anodize, **0.002 in [0.051 mm]**, MIL-A-8625F Class 1 | Coating-thickness gauge; anodizer **CoC** | R |

**First-Article Inspection (FAI):** full CMM report on the first RA and DEC housing is
a **hold point** before running the balance of the lot / releasing to anodize.

## 2. BP-02 — Precision turned parts (303 SS, turned)

Parts: NW-TP-001 (CW shaft — *optional, counterweighted variant only*), NW-TP-002 (RA
spindle), NW-TP-003 (DEC spindle).

| # | Characteristic | Acceptance criterion | Method / standard | Point |
|:-:|---|---|---|:-:|
| 2.1 | Material | 303 stainless per ASTM A582 | **Mill certificate** | R |
| 2.2 | Bearing journals | RA j6 Ø **40.0 mm [1.575 in]** (7008); DEC j6 Ø **30.0 mm [1.181 in]** (7006) | **CMM / air gauge** | **H** |
| 2.3 | Concentricity | **0.02 mm [0.0008 in] TIR** journal-to-register | Between-centres runout / CMM | **H** |
| 2.4 | Drive registers | RA **80.0 mm [3.150 in]** (CSF-32); DEC **64.0 mm [2.520 in]** (CSF-25) | CMM | W |
| 2.5 | Bolt patterns | 8× M4 on RA **104 mm [4.094 in]** / DEC **83 mm [3.268 in]** PCD | CMM | W |
| 2.6 | General tolerances | ISO 2768-mK; journals h6/j6 per ISO 286 | First-article gauge | S |
| 2.7 | Surface finish | **Ra 0.8 µm** journals | Profilometer per ASME B46.1 | W |
| 2.8 | Finish | Passivate per ASTM A967 (nitric) | Passivation **CoC**; optional copper-sulphate / water-immersion test | R |

## 3. BP-03 — Pier & foundation (RC + steel). **PE-STAMP GATE.**

Parts: NW-PF-001 (RC pier), NW-PF-002 (steel top plate), NW-PF-003 (Al adapter),
NW-PF-004 (anchor set + template).

| # | Characteristic | Acceptance criterion | Method / standard | Point |
|:-:|---|---|---|:-:|
| 3.1 | **Foundation design** | PE-stamped rebar/anchor design vs confirmed **ASCE 7** loads (survival-wind uplift ~9.2 kN, seismic) | Stamped calc + drawings, **ACI 318 Ch. 17** | **H** |
| 3.2 | Concrete mix | f′c = **4000 psi [27.6 MPa]** per ACI 301 | Approved mix design | **H** |
| 3.3 | Rebar cage | 6× #4 vertical + #3 ties @ 12 in oc (A615 Gr60) — *ASSUMED, PE-to-confirm* | Placement inspection **before pour** | **H** |
| 3.4 | Anchor template / setting | 4× Ø **19.05 mm [0.750 in]** F1554, embedment **304.8 mm [12.000 in]**, projection **50 mm [1.969 in]**; template hole tol **0.02 mm** | Survey of bolt pattern **before pour** | **H** |
| 3.5 | Concrete strength | Cylinder breaks meet f′c at 28 days (and 7-day check) | **ACI cylinder break** test (4 cylinders/pour min) | **H** |
| 3.6 | Pier geometry | Ø **304.8 mm [12.000 in]**; height above grade **914.4 mm [36.000 in]**; embedment > frost line; plumb **1:200**; top level **0.5°**; isolated from any slab | Survey / level | W |
| 3.7 | Top plate NW-PF-002 | **304.8 mm [12.000 in]** sq × **9.5 mm [0.375 in]**; hole pattern ±0.25 mm | Dimensional; **A123** galvanize CoC | W |
| 3.8 | Adapter NW-PF-003 | **254.0 mm [10.000 in]** sq × **19.05 mm [0.750 in]**; latitude-38.9° orientation | CMM; anodize CoC | W |
| 3.9 | Grout / seating | Non-shrink grout under top plate, full bearing | Visual | W |

**Hold:** no concrete pour until 3.1, 3.3, and 3.4 are released. The pier is
**construction-gated on the PE stamp** (`02_standards_register.md` §7).

## 4. BP-04 — Roll-off roof (structural steel, AWS D1.1)

Parts: NW-RR-001 (frame), NW-RR-002 (rafters/purlins ×5), NW-RR-003 (rails ×2),
NW-RR-004 (wheel brackets ×8), NW-RR-005 (drive bracket ×4), NW-RR-006 (hold-down ×4).

| # | Characteristic | Acceptance criterion | Method / standard | Point |
|:-:|---|---|---|:-:|
| 4.1 | Weld procedures & personnel | Qualified **WPS / PQR** and current **welder qualifications** | Records review, **AWS D1.1** | **H** |
| 4.2 | **Member sizing** | Roof member sizes vs confirmed **ASCE 7** snow (10.8 kN closed-roof case) + wind — *ASSUMED, PE-to-confirm* | PE-stamped submittal | **H** |
| 4.3 | Material | HSS **ASTM A500 Gr B** (NW-RR-001/002); plate **ASTM A36** (NW-RR-003…006) | Mill certificates | R |
| 4.4 | Weld quality | **Visual (VT) 100%** per AWS D1.1; **NDE** (MT/UT) on critical/CJP joints per PE-set extent — *weld sizes ASSUMED, PE-to-confirm* | VT + MT/UT, symbols per **AWS A2.4** | **H** |
| 4.5 | Frame geometry | Square **3 mm/m**, diagonal **5 mm**; gauge (rail spacing) matches roof span | Tape/laser measure | W |
| 4.6 | Rail straightness | **3 mm [0.118 in]** over run; gauge **2 mm**; rail run = 2× roof length so roof clears aperture | Survey / string line | W |
| 4.7 | Wheel brackets | 8×, bore for Ø4 in V-groove wheel (NW-CO-010), M16 axle; sized ≥ 4× roof + snow | Dimensional; load rating check | W |
| 4.8 | **Wind hold-down brackets NW-RR-006** | 4×, Ø **19.05 mm [0.750 in]** F1554 anchor, capacity **≥ 2 klbf each** → survival SF 3.9 (**MANDATORY** wind remediation) | Dimensional; anchor pull-test per **ACI 318 Ch.17** | **H** |
| 4.9 | Drive & interlocks | Gate-operator (NW-CO-011) mounted; hard end stops; **snow + wind interlocks** functional | Function test (open/close, interlock trip) | **H** |
| 4.10 | Finish | Hot-dip galvanize per **ASTM A123** | Coating-thickness gauge; galvanizer **CoC** | R |

## 5. BP-05 — COTS procurement

| # | Characteristic | Acceptance criterion | Method | Point |
|:-:|---|---|---|:-:|
| 5.1 | Item conformance | Each NW-CO-xxx matches specified part/rating on the COTS schedule | **Certificate of Conformance** + datasheet | R |
| 5.2 | Remediation items | 7008/7006 angular-contact **DB** pairs (NW-CO-003/004); on-axis absolute encoder (NW-CO-005); temp-comp focuser (NW-CO-008); 48 V pack (NW-CO-013) supplied **as specified** (no deep-groove/homing-grade substitution) | Datasheet verification | **H** |
| 5.3 | Bearings | 7008 bore Ø40 / OD Ø68 mm; 7006 bore Ø30 / OD Ø55 mm; back-to-back preload set | Manufacturer data; incoming dimensional check | W |
| 5.4 | Fasteners | A574 SHCS; F1554 Gr36 anchors, galvanized | Mill certs / CoC | R |
| 5.5 | Incoming inspection | No transit damage; quantities per schedule | Visual + count | S |

**No substitution** of the five proof-out remediation items without written Owner/PE
approval — each closes a documented FAIL and a like-for-like commercial swap is not
equivalent.

## 6. Documentation package (all trades)

At delivery the contractor shall provide, per package:

1. Material certificates / mill certs (traceable to heat/lot).
2. First-Article Inspection and **CMM reports** (BP-01/BP-02 dimensional).
3. **Weld records** — WPS/PQR, welder quals, VT/NDE reports (BP-04).
4. **Concrete records** — mix design, placement logs, **cylinder-break** results,
   pre-pour rebar/anchor inspection sign-offs (BP-03).
5. **Finish certificates** — anodize (MIL-A-8625F), galvanize (A123), passivation
   (A967) CoCs with thickness/verification data.
6. **Certificates of Conformance** for all COTS (BP-05).
7. As-built notes on any RFI-resolved ASSUMED design-intent value.

Acceptance is conditional on a complete documentation package; a shortfall is grounds
to withhold acceptance of the affected line items.

---

*Hold points marked **H** require Owner/PE release; the contractor shall give the
notice period stated in the awarded contract before proceeding. All ASSUMED
design-intent values (weld sizes, roof member sizing, rebar/anchor sizing, GD&T
values, surface finish, rail/drive product) remain **bidder/PE to confirm** and are
verified against the PE-stamped, released-for-construction data — not this bid issue.*
