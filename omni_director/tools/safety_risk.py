"""On-Set Stunt, Pyro/SFX, Rigging & Environmental Safety Risk Assessment Matrix / JSA Engine (PM-FEAT-026).

Pure-Python on-set production safety & Job Safety Analysis (JSA) suite implementing:
- Physics-based kinetic exclusion zone calculation (MoCo arm reach + E-stop braking distance,
  FAA Part 107 UAV standoff perimeter, and stunt vehicle stopping buffers)
- 5x5 Job Safety Analysis (JSA) hazard scoring with engineering controls, PPE, and CSATF
  Safety Bulletins (#1, #16, #25, #36, #40)
- Standby medical, fire safety officer, E-stop, and trauma response coordination (`CH-09 SAFETY`)
- 6-domain archetype safety calibrations across all commercial formats
- Safety Bulletin Markdown, JSA Matrix CSV, and Safety Risk JSON manifest export bundle
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omni_director.schemas import (
    DroneFlightPathSpec,
    MasterProductionBible,
    MasterSafetyRiskSpec,
    MocoRigSpec,
    RiskSeverityLevel,
    SafetyHazardCategory,
    SafetyHazardControlSpec,
    SafetySignoffStatus,
    ScenePromptSpec,
    SceneSafetyRiskSpec,
    StandbyMedicalAndEmergencySpec,
)


_DOMAIN_BASELINE_EXCLUSION_M: Dict[str, float] = {
    "automotive_robotics": 18.0,
    "kinetic_action": 10.0,
    "tech_hardware": 6.0,
    "luxury_fashion": 4.5,
    "architectural_sanctuary": 4.0,
    "culinary_asmr": 3.0,
}

_MOCO_ARM_REACH_M: Dict[str, float] = {
    "russian_arm": 7.5,
    "cablecam": 4.5,
    "technocrane": 4.5,
    "bolt_cinebot": 3.0,
    "motorized_dolly": 2.0,
}

_AERIAL_CUE_RE = re.compile(r"\b(?:drone|uav|aerial|fpv|flyover|quadcopter|helicopter)\b", re.IGNORECASE)
_MOCO_CUE_RE = re.compile(
    r"\b(?:moco|motion[- ]control|bolt|cinebot|russian\s+arm|technocrane|cablecam|robotic\s+arm)\b",
    re.IGNORECASE,
)
_VEHICLE_STUNT_RE = re.compile(
    r"\b(?:hypercar|supercar|stunt\s+vehicle|stunt\s+car|camera\s+car|motor\s+vehicle|"
    r"sports\s+car|pursuit\s+vehicle|vehicle\s+pursuit|russian\s+arm|automotive|motorsport|tarmac)\b",
    re.IGNORECASE,
)
_PYRO_SFX_RE = re.compile(
    r"\b(?:pyro|fire|flame|explosion|spark|haze|smoke|fog|condensation|airflow|wind\s+tunnel|torch)\b",
    re.IGNORECASE,
)
_LASER_CUE_RE = re.compile(r"\b(?:laser|lidar|optical\s+scan|violet\s+beam|class\s+[34]b?)\b", re.IGNORECASE)
_WET_ELEC_RE = re.compile(
    r"\b(?:wet|rain|cobblestone|puddle|reflection|water|mist|steam|dmx|hmi|led\s+volume|neon)\b",
    re.IGNORECASE,
)
_WIRE_HEIGHT_RE = re.compile(
    r"\b(?:wire|harness|rigging|truss|overhead|suspended|aerial|tension|catwalk|runway|elevated)\b",
    re.IGNORECASE,
)
_CULINARY_THERMAL_RE = re.compile(
    r"\b(?:knife|blade|cleaver|sear|sizzle|boil|oven|induction|flame|steam|hot\s+oil|culinary|allergen)\b",
    re.IGNORECASE,
)


def _normalize_domain(domain: Optional[str]) -> str:
    raw = str(domain or "architectural_sanctuary").strip().lower()
    if "automotive" in raw:
        return "automotive_robotics"
    if "culinary" in raw or "asmr" in raw:
        return "culinary_asmr"
    if "luxury" in raw or "fashion" in raw:
        return "luxury_fashion"
    if "kinetic" in raw or "action" in raw:
        return "kinetic_action"
    if "hardware" in raw or "tech" in raw:
        return "tech_hardware"
    return "architectural_sanctuary"


def _scene_corpus(scene: Optional[ScenePromptSpec]) -> str:
    if scene is None:
        return ""
    parts = [
        str(getattr(scene, "scene_title", "") or ""),
        str(getattr(scene, "omni_prose_prompt", "") or ""),
        " ".join(getattr(scene, "action_beats", []) or []),
        str(getattr(scene, "kinetic_contact_chain", "") or ""),
    ]
    craft = getattr(scene, "craft_camera", None)
    if craft is not None:
        parts.append(str(getattr(craft, "rig_type", "") or ""))
        parts.append(str(getattr(craft, "route", "") or ""))
    return " ".join(parts)


def calculate_kinetic_exclusion_zone_m(
    moco_rig: Optional[MocoRigSpec] = None,
    drone_flight: Optional[DroneFlightPathSpec] = None,
    scene: Optional[ScenePromptSpec] = None,
    domain: str = "architectural_sanctuary",
) -> float:
    """Compute physics-based safety exclusion perimeter in meters.

    Accounts for:
    - MoCo arm reach + E-stop braking distance (`max(2.5, arm_reach + v^2/(2*a) + 1.5)`)
    - FAA Part 107 UAV standoff altitude/velocity buffer (`max(10.0, ...)`)
    - High-speed stunt/vehicle braking envelope (`15.0 - 25.0m`)
    - Domain baseline safety perimeter floors
    """
    norm_domain = _normalize_domain(domain)
    zone_m = float(_DOMAIN_BASELINE_EXCLUSION_M.get(norm_domain, 4.0))
    corpus = _scene_corpus(scene)

    # 1. MoCo robotic rig reach + braking distance (a_decel = 6.0 m/s^2)
    eff_moco = moco_rig
    if eff_moco is None and scene is not None:
        candidate_moco = getattr(scene, "moco_rig", None)
        if candidate_moco is not None and (
            _MOCO_CUE_RE.search(corpus)
            or norm_domain in ("automotive_robotics", "kinetic_action", "tech_hardware")
        ):
            eff_moco = candidate_moco

    if eff_moco is not None:
        rig_key = (
            eff_moco.rig_type.value
            if hasattr(eff_moco.rig_type, "value")
            else str(eff_moco.rig_type)
        ).lower()
        arm_reach = _MOCO_ARM_REACH_M.get(rig_key, 2.8)
        vel = float(getattr(eff_moco, "max_velocity_mps", 2.5) or 2.5)
        braking_dist = (vel ** 2) / (2.0 * 6.0)
        moco_zone = max(2.5, round(arm_reach + braking_dist + 1.5, 2))
        zone_m = max(zone_m, moco_zone)

    # 2. Aerial UAV / Drone FAA Part 107 standoff buffer
    eff_drone = drone_flight
    drone_explicit = drone_flight is not None
    if eff_drone is None and scene is not None:
        candidate_drone = getattr(scene, "drone_flight", None)
        if candidate_drone is not None and _AERIAL_CUE_RE.search(corpus):
            eff_drone = candidate_drone

    if eff_drone is not None or _AERIAL_CUE_RE.search(corpus):
        max_alt = float(getattr(eff_drone, "max_altitude_agl_m", 20.0) or 20.0) if eff_drone else 20.0
        if drone_explicit or _AERIAL_CUE_RE.search(corpus) or max_alt > 5.0:
            uav_zone = max(10.0, round(min(30.0, 0.35 * max_alt + 5.0), 2))
            zone_m = max(zone_m, uav_zone)

    # 3. High-speed stunt / vehicle braking buffer (15.0 - 25.0m)
    if norm_domain == "automotive_robotics" or _VEHICLE_STUNT_RE.search(corpus):
        has_extreme_speed = bool(re.search(r"\b(?:drift|120\s*mph|high[- ]speed|pursuit|skid)\b", corpus, re.IGNORECASE))
        vehicle_zone = 21.0 if has_extreme_speed else 18.0
        zone_m = max(zone_m, vehicle_zone)

    return round(zone_m, 2)


def _severity_from_rating(rating: int) -> RiskSeverityLevel:
    if rating >= 15:
        return RiskSeverityLevel.CRITICAL
    if rating >= 10:
        return RiskSeverityLevel.HIGH
    if rating >= 5:
        return RiskSeverityLevel.MODERATE
    return RiskSeverityLevel.LOW


def _make_hazard(
    hazard_id: str,
    category: SafetyHazardCategory,
    description: str,
    likelihood: int,
    severity: int,
    exclusion_zone_m: float,
    engineering_controls: List[str],
    ppe_required: List[str],
    supervisor: str,
    notes: str,
) -> SafetyHazardControlSpec:
    rating = max(1, min(25, int(likelihood) * int(severity)))
    raw_level = _severity_from_rating(rating)
    residual = RiskSeverityLevel.MODERATE if raw_level in (RiskSeverityLevel.HIGH, RiskSeverityLevel.CRITICAL) else RiskSeverityLevel.LOW
    signoff = SafetySignoffStatus.CLEARED if raw_level == RiskSeverityLevel.LOW else SafetySignoffStatus.MITIGATED
    return SafetyHazardControlSpec(
        hazard_id=hazard_id,
        category=category,
        hazard_description=description,
        likelihood_score=likelihood,
        severity_score=severity,
        risk_rating=rating,
        risk_level=raw_level,
        residual_risk_level=residual,
        exclusion_zone_m=round(float(exclusion_zone_m), 2),
        engineering_controls=engineering_controls,
        ppe_required=ppe_required,
        responsible_supervisor=supervisor,
        mitigation_verified=True,
        signoff_status=signoff,
        notes=notes,
    )


def format_safety_prompt_token(
    spec: Union[SceneSafetyRiskSpec, MasterSafetyRiskSpec],
) -> str:
    """Emit standardized Gemini Omni prompt-auditable On-Set Safety JSA token."""
    risk_s = (
        spec.overall_risk_level.value
        if hasattr(spec.overall_risk_level, "value")
        else str(spec.overall_risk_level)
    ).lower()
    status_s = (
        spec.signoff_status.value
        if hasattr(spec.signoff_status, "value")
        else str(spec.signoff_status)
    ).upper()

    if isinstance(spec, SceneSafetyRiskSpec):
        excl_m = float(spec.max_exclusion_zone_m)
        hazard_cnt = len(spec.hazards)
    else:
        excl_m = max((float(ss.max_exclusion_zone_m) for ss in spec.scene_safety_specs), default=3.0)
        hazard_cnt = int(spec.total_hazards_identified or sum(len(ss.hazards) for ss in spec.scene_safety_specs))

    return f"[SAFETY_JSA: risk={risk_s} exclusion={excl_m:.1f}m hazards={hazard_cnt} status={status_s}]"


def assess_scene_hazards(
    scene: ScenePromptSpec,
    scene_index: int = 1,
    domain: str = "architectural_sanctuary",
    bible: Optional[MasterProductionBible] = None,
) -> SceneSafetyRiskSpec:
    """Inspect scene rigs, lighting, breakdown, and prompt cues to synthesize a CSATF-compliant JSA."""
    norm_domain = _normalize_domain(
        domain or (getattr(bible, "domain_archetype", None) if bible is not None else None)
    )
    eff_idx = int(scene_index or getattr(scene, "scene_index", 1) or 1)
    corpus = _scene_corpus(scene)

    breakdown = getattr(scene, "breakdown_sheet", None)
    if breakdown is not None and getattr(breakdown, "category_elements", None):
        bd_text = " ".join(
            " ".join(elems) for elems in breakdown.category_elements.values()
        )
        corpus = f"{corpus} {bd_text}"

    lighting_rig = getattr(scene, "lighting_rig", None)
    moco_rig = getattr(scene, "moco_rig", None)
    drone_flight = getattr(scene, "drone_flight", None)

    hazards: List[SafetyHazardControlSpec] = []
    h_num = 0

    def _next_id() -> str:
        nonlocal h_num
        h_num += 1
        return f"HAZ-S{eff_idx:02d}-{h_num:02d}"

    # 1. Domain-primary & kinetic hazards
    if norm_domain == "automotive_robotics" or _VEHICLE_STUNT_RE.search(corpus):
        veh_zone = calculate_kinetic_exclusion_zone_m(
            moco_rig=moco_rig, scene=scene, domain="automotive_robotics"
        )
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.STUNT_VEHICLE,
                description="High-speed tracking vehicle & Russian Arm gyro-stabilized crane pursuit envelope.",
                likelihood=3,
                severity=4,
                exclusion_zone_m=veh_zone,
                engineering_controls=[
                    "Closed-course perimeter barricades & spotter radio lock",
                    "Dual-channel hydraulic arm E-stop & speed governor",
                    "Tire pressure & brake thermal telemetry pre-check",
                ],
                ppe_required=[
                    "ANSI Class 3 high-visibility vest",
                    "Snell-rated stunt helmet (camera car crew)",
                    "Five-point harness & Hans restraint",
                ],
                supervisor="Stunt Coordinator & Precision Driver Lead",
                notes="CSATF Bulletin #1 (Stunt / Vehicle Safety) & CSATF Bulletin #40 (Camera Crane / Arm).",
            )
        )

    if norm_domain == "kinetic_action" or _MOCO_CUE_RE.search(corpus) or norm_domain == "tech_hardware":
        moco_zone = calculate_kinetic_exclusion_zone_m(
            moco_rig=moco_rig,
            scene=scene,
            domain=norm_domain if norm_domain in ("kinetic_action", "tech_hardware") else "kinetic_action",
        )
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.KINETIC_MOCO_ARM,
                description="High-acceleration robotic motion-control arm sweep and track pinch-point envelope.",
                likelihood=3,
                severity=3,
                exclusion_zone_m=moco_zone,
                engineering_controls=[
                    "SIL-3 hardware E-stop lanyard at Video Village & Rig Base",
                    "Optical LiDAR/laser perimeter safety curtain interlock",
                    "Dry-run kinematic envelope sweep at 25% velocity prior to talent entry",
                ],
                ppe_required=[
                    "Steel-toe stage footwear",
                    "ANSI Z87.1 impact eyewear",
                    "High-visibility floor spotter vest",
                ],
                supervisor="Lead MoCo Technician & Key Grip",
                notes="CSATF Bulletin #40 (Robotic Camera & Motion Control Safety).",
            )
        )

    if _AERIAL_CUE_RE.search(corpus):
        uav_zone = calculate_kinetic_exclusion_zone_m(drone_flight=drone_flight, scene=scene, domain=norm_domain)
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.AERIAL_UAV,
                description="Heavy-lift cinema UAV rotor wash, battery thermal load, and FAA Part 107 flight corridor.",
                likelihood=2,
                severity=4,
                exclusion_zone_m=uav_zone,
                engineering_controls=[
                    "FAA Part 107 airspace authorization & geofence ceiling lock",
                    "Dedicated Visual Observer (VO) and sterile launch/recovery pad",
                    "Dual-link RF telemetry fail-safe & return-to-home altitude lock",
                ],
                ppe_required=[
                    "ANSI Type II hard hat",
                    "High-visibility flight-line vest",
                    "ANSI Z87.1 debris eyewear",
                ],
                supervisor="FAA Part 107 Pilot in Command",
                notes="CSATF Bulletin #36 (Unmanned Aircraft Systems / Aerial Filming).",
            )
        )

    if _LASER_CUE_RE.search(corpus) or norm_domain == "tech_hardware":
        laser_zone = max(6.0, float(_DOMAIN_BASELINE_EXCLUSION_M.get(norm_domain, 6.0)))
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.LASER_OPTICAL,
                description="Class 3B/4 coherent optical scan & specular beam termination hazard (NOHD perimeter).",
                likelihood=2,
                severity=4,
                exclusion_zone_m=laser_zone,
                engineering_controls=[
                    "Certified Laser Safety Officer (LSO/RSO) beam-stop termination",
                    "Beam path elevated above/below eye level with matte baffles",
                    "Interlocked beam shutter & wavelength-specific viewing barrier",
                ],
                ppe_required=[
                    "OD 4+ wavelength-rated laser safety eyewear",
                    "Cleanroom lint-free ESD smock & gloves",
                ],
                supervisor="Laser Safety Officer (LSO) / Gaffer",
                notes="CSATF Bulletin #25 (Laser Safety) & ANSI Z136.1 NOHD clearance.",
            )
        )

    if _PYRO_SFX_RE.search(corpus) and norm_domain != "culinary_asmr":
        pyro_zone = max(8.0, float(_DOMAIN_BASELINE_EXCLUSION_M.get(norm_domain, 8.0)))
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.PYRO_ATMOSPHERIC_SFX,
                description="Atmospheric haze/smoke particulate dispersion, high-pressure air/SFX manifold, or thermal ignition.",
                likelihood=2,
                severity=3,
                exclusion_zone_m=pyro_zone,
                engineering_controls=[
                    "NFPA 160 / AHJ atmospheric SFX permit & CO2/smoke detector bypass watch",
                    "High-volume stage purge exhaust & air-quality particulate monitor",
                    "Whip-check safety cables on all pressurized pneumatic manifolds",
                ],
                ppe_required=[
                    "NIOSH N95 / P100 particulate respirator (SFX crew)",
                    "Hearing protection (NRR 26dB)",
                    "Nomex FR apron near ignition sources",
                ],
                supervisor="Licensed SFX Coordinator / Fire Safety Officer",
                notes="CSATF Bulletin #16 (Pyrotechnic Special Effects & Atmospheric Haze).",
            )
        )

    if norm_domain == "culinary_asmr" or _CULINARY_THERMAL_RE.search(corpus):
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.FOOD_ALLERGEN_THERMAL,
                description="Tabletop thermal cooking surfaces, boiling/searing liquids, sharp cutlery, and food allergen controls.",
                likelihood=2,
                severity=3,
                exclusion_zone_m=3.0,
                engineering_controls=[
                    "Class K wet-chemical & ABC fire extinguishers staged within 3.0m",
                    "Heat-resistant silicone surface mats & insulated induction zones",
                    "Dedicated allergen-free prep trays & food-safe temperature log",
                ],
                ppe_required=[
                    "Cut-resistant Kevlar food-styling glove (prep)",
                    "Heat-insulated nitrile/silicone mitts",
                    "Closed-toe non-slip kitchen footwear",
                ],
                supervisor="Culinary Food Stylist & 1st AD",
                notes="CSATF Bulletin #16 (Open Flame / Thermal) & studio food-safety allergen SOP.",
            )
        )

    if (
        norm_domain in ("automotive_robotics", "luxury_fashion", "architectural_sanctuary")
        or _WET_ELEC_RE.search(corpus)
        or (lighting_rig is not None and float(getattr(lighting_rig, "total_lux", 0.0) or 0.0) >= 3500.0)
    ):
        elec_zone = (
            3.0 if norm_domain == "culinary_asmr"
            else 4.5 if norm_domain == "luxury_fashion"
            else 4.0 if norm_domain == "architectural_sanctuary"
            else 5.0
        )
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.ELECTRICAL_DMX_WET,
                description="High-draw DMX/HMI lighting distribution near wet set surfaces, condensation, or metallic truss.",
                likelihood=2,
                severity=3,
                exclusion_zone_m=elec_zone,
                engineering_controls=[
                    "Class-A 5mA GFCI inline protection on all wet-area distribution drops",
                    "Elevated cable ramps, rubber matting, and bonded stage ground",
                    "IP65 weather-sealed DMX splitters & ballast isolation stands",
                ],
                ppe_required=[
                    "EH-rated insulated rubber-sole footwear",
                    "Insulated electrical handling gloves (Gaffer crew)",
                ],
                supervisor="Chief Lighting Technician (Gaffer)",
                notes="CSATF Bulletin #1 (General Safety) & CSATF Bulletin #22 (Electrical / Wet Location Safety).",
            )
        )

    if norm_domain in ("kinetic_action", "architectural_sanctuary", "luxury_fashion") or _WIRE_HEIGHT_RE.search(corpus):
        rig_zone = 10.0 if norm_domain == "kinetic_action" else (4.5 if norm_domain == "luxury_fashion" else 4.0)
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.WIRE_RIGGING_HEIGHT,
                description="Overhead truss/softbox rigging, tensioned wire/fabric loads, and elevated working-at-height perimeter.",
                likelihood=2,
                severity=3,
                exclusion_zone_m=rig_zone,
                engineering_controls=[
                    "Secondary rated steel safety cables on all overhead fixtures & truss points",
                    "Certified load-cell shackles with 5:1 working load limit (WLL) safety factor",
                    "Tool-tether lanyards and barricaded drop-zone beneath riggers",
                ],
                ppe_required=[
                    "ANSI Z89.1 climbing/rigging hard hat",
                    "Full-body fall-arrest harness (>1.8m elevation)",
                    "Steel-toe work boots",
                ],
                supervisor="Key Grip & Lead Stunt Rigger",
                notes="CSATF Bulletin #1 (Overhead Rigging / Fall Protection) & ANSI E1.6.",
            )
        )

    if not hazards:
        base_zone = calculate_kinetic_exclusion_zone_m(scene=scene, domain=norm_domain)
        hazards.append(
            _make_hazard(
                hazard_id=_next_id(),
                category=SafetyHazardCategory.WIRE_RIGGING_HEIGHT,
                description="Standard stage tripod/grip footprint, cable routing, and overhead fixture clearance.",
                likelihood=1,
                severity=2,
                exclusion_zone_m=base_zone,
                engineering_controls=[
                    "Safety chains on overhead stands and sandbagged C-stand bases",
                    "High-visibility gaffer tape & ADA-compliant cable ramps",
                ],
                ppe_required=[
                    "Closed-toe stage footwear",
                    "Work gloves (Grip & Electric)",
                ],
                supervisor="1st AD / Key Grip",
                notes="CSATF Bulletin #1 (General Stage & Set Safety).",
            )
        )

    spec = SceneSafetyRiskSpec(
        scene_index=eff_idx,
        scene_title=str(getattr(scene, "scene_title", f"Scene {eff_idx}")),
        hazards=hazards,
        safety_officer_name="1st AD / Certified Unit Safety Officer",
        jsa_notes=(
            f"Domain={norm_domain}; CSATF tailgate briefing completed prior to camera roll. "
            f"All {len(hazards)} hazard control(s) verified at residual risk <= MODERATE."
        ),
    )
    spec.prompt_token = format_safety_prompt_token(spec)
    return spec


def synthesize_default_safety_risk_spec(
    bible: MasterProductionBible,
    domain: Optional[str] = None,
) -> MasterSafetyRiskSpec:
    """Synthesize a Master On-Set Safety JSA Manifest from a MasterProductionBible."""
    norm_domain = _normalize_domain(domain or getattr(bible, "domain_archetype", None))
    scenes = list(getattr(bible, "scenes", []) or [])

    scene_specs: List[SceneSafetyRiskSpec] = []
    if scenes:
        for pos, sc in enumerate(scenes, start=1):
            s_idx = int(getattr(sc, "scene_index", pos) or pos)
            scene_specs.append(
                assess_scene_hazards(sc, scene_index=s_idx, domain=norm_domain, bible=bible)
            )
    else:
        fallback_sc = ScenePromptSpec(
            scene_index=1,
            timestamp_range="00:00 - 00:08",
            scene_title="Master Stage Setup",
            omni_prose_prompt=str(getattr(bible, "logline", "") or bible.project_title),
        )
        scene_specs.append(
            assess_scene_hazards(fallback_sc, scene_index=1, domain=norm_domain, bible=bible)
        )

    all_hazards = [h for ss in scene_specs for h in ss.hazards]
    has_pyro_or_thermal = any(
        h.category in (SafetyHazardCategory.PYRO_ATMOSPHERIC_SFX, SafetyHazardCategory.FOOD_ALLERGEN_THERMAL)
        for h in all_hazards
    )
    has_high_energy_stunt = any(
        h.category in (SafetyHazardCategory.STUNT_VEHICLE, SafetyHazardCategory.WIRE_RIGGING_HEIGHT)
        and h.risk_level in (RiskSeverityLevel.HIGH, RiskSeverityLevel.CRITICAL)
        for h in all_hazards
    )

    e_stops = ["Video Village Master Console", "Stage Door Alpha"]
    if norm_domain in ("automotive_robotics", "kinetic_action", "tech_hardware"):
        e_stops.insert(1, "MoCo / Crane Base Controller")
    if norm_domain == "culinary_asmr":
        e_stops.append("Culinary Prep Class-K Station")

    standby = StandbyMedicalAndEmergencySpec(
        set_medic_on_standby=True,
        medic_qualification="Certified Set Paramedic / EMT-P",
        fire_safety_officer_required=has_pyro_or_thermal,
        ambulance_on_standby=has_high_energy_stunt or norm_domain == "automotive_robotics",
        nearest_trauma_center="Regional Level-1 Trauma Center (<12 min EMS response)",
        emergency_muster_point="Exterior Stage North Gate Alpha",
        emergency_radio_channel="CH-09 SAFETY",
        e_stop_locations=e_stops,
        sds_sheets_staged=True,
        safety_briefing_time="07:00 Call Time Tailgate",
    )

    digest = hashlib.sha256(f"{bible.project_title}|{norm_domain}".encode("utf-8")).hexdigest()[:6].upper()
    master = MasterSafetyRiskSpec(
        project_title=bible.project_title,
        jsa_document_id=f"JSA-2026-{digest}",
        production_safety_officer="Certified 1st AD & CSATF Unit Safety Coordinator",
        standby_emergency=standby,
        scene_safety_specs=scene_specs,
        open_holds_count=0,
        all_hazards_mitigated=True,
        jsa_summary=(
            f"CSATF JSA cleared across {len(scene_specs)} scene(s) ({norm_domain}); "
            f"{len(all_hazards)} hazard(s) mitigated with verified engineering controls and PPE."
        ),
    )
    master.prompt_token = format_safety_prompt_token(master)
    return master


def _resolve_safety_spec(
    spec_or_bible: Union[MasterSafetyRiskSpec, MasterProductionBible],
) -> MasterSafetyRiskSpec:
    if isinstance(spec_or_bible, MasterSafetyRiskSpec):
        return spec_or_bible
    existing = (
        getattr(spec_or_bible, "master_safety_risk", None)
        or getattr(spec_or_bible, "safety_risk", None)
    )
    if isinstance(existing, MasterSafetyRiskSpec):
        return existing
    return synthesize_default_safety_risk_spec(spec_or_bible)


def generate_safety_bulletin_md(
    spec_or_bible: Union[MasterSafetyRiskSpec, MasterProductionBible],
) -> str:
    """Generate an executive On-Set Safety Bulletin & Job Safety Analysis (JSA) Markdown document."""
    spec = _resolve_safety_spec(spec_or_bible)
    em = spec.standby_emergency
    overall_s = (
        spec.overall_risk_level.value
        if hasattr(spec.overall_risk_level, "value")
        else str(spec.overall_risk_level)
    ).upper()
    status_s = (
        spec.signoff_status.value
        if hasattr(spec.signoff_status, "value")
        else str(spec.signoff_status)
    ).upper()

    lines = [
        f"# On-Set Safety Bulletin & JSA Matrix: {spec.project_title}",
        "",
        f"- **JSA Document ID**: `{spec.jsa_document_id}`",
        f"- **Safety Officer**: `{spec.production_safety_officer}`",
        f"- **Overall Risk Tier**: `{overall_s}` (Peak 5x5 Rating: `{spec.highest_risk_rating}/25`)",
        f"- **Signoff Status**: **`{status_s}`** (`Open Holds: {spec.open_holds_count}`)",
        f"- **Total Hazards Mitigated**: `{spec.total_hazards_identified}`",
        "",
        "## Standby Medical, Fire & Emergency Response",
        f"- **Emergency Radio Channel**: `{em.emergency_radio_channel}`",
        f"- **Set Medic On Standby**: `{'YES' if em.set_medic_on_standby else 'NO'}` ({em.medic_qualification})",
        f"- **Fire Safety Officer Required**: `{'YES' if em.fire_safety_officer_required else 'NO'}`",
        f"- **Standby Ambulance**: `{'YES' if em.ambulance_on_standby else 'NO'}`",
        f"- **Nearest Trauma Center**: {em.nearest_trauma_center}",
        f"- **Muster Point**: `{em.emergency_muster_point}` | **Tailgate Briefing**: `{em.safety_briefing_time}`",
        f"- **E-Stop Locations**: {', '.join(em.e_stop_locations)}",
        "",
        "## Per-Scene Exclusion Zones & Specialist Clearances",
        "| Scene | Title | Risk Tier | Peak Score | Exclusion Zone | Stunt / Pyro / LSO | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for ss in spec.scene_safety_specs:
        r_s = ss.overall_risk_level.value if hasattr(ss.overall_risk_level, "value") else str(ss.overall_risk_level)
        st_s = ss.signoff_status.value if hasattr(ss.signoff_status, "value") else str(ss.signoff_status)
        specialists = [
            tag
            for flag, tag in (
                (ss.stunt_coordinator_required, "Stunt"),
                (ss.pyro_permit_required, "Pyro"),
                (ss.rso_laser_clearance_required, "LSO"),
            )
            if flag
        ]
        spec_str = ", ".join(specialists) if specialists else "Standard"
        lines.append(
            f"| {ss.scene_index} | {ss.scene_title} | `{r_s.upper()}` | `{ss.max_risk_rating}/25` | "
            f"`{ss.max_exclusion_zone_m:.1f}m` | `{spec_str}` | `{st_s.upper()}` |"
        )

    lines.extend([
        "",
        "## Detailed Hazard Control & CSATF Bulletin Matrix",
        "| Hazard ID | Scene | Category | Rating | Residual | Zone (m) | Supervisor | CSATF Ref |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for ss in spec.scene_safety_specs:
        for hz in ss.hazards:
            cat_s = hz.category.value if hasattr(hz.category, "value") else str(hz.category)
            res_s = hz.residual_risk_level.value if hasattr(hz.residual_risk_level, "value") else str(hz.residual_risk_level)
            lines.append(
                f"| `{hz.hazard_id}` | {ss.scene_index} | `{cat_s}` | `{hz.risk_rating}/25` | "
                f"`{res_s.upper()}` | `{hz.exclusion_zone_m:.1f}m` | {hz.responsible_supervisor} | {hz.notes} |"
            )

    lines.extend(["", f"**Summary**: {spec.jsa_summary}", ""])
    return "\n".join(lines)


def generate_safety_jsa_csv(
    spec_or_bible: Union[MasterSafetyRiskSpec, MasterProductionBible],
) -> str:
    """Export all per-scene safety hazard controls into a structured JSA CSV matrix."""
    spec = _resolve_safety_spec(spec_or_bible)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "scene_index",
        "scene_title",
        "hazard_id",
        "category",
        "hazard_description",
        "likelihood_score",
        "severity_score",
        "risk_rating",
        "risk_level",
        "residual_risk_level",
        "exclusion_zone_m",
        "engineering_controls",
        "ppe_required",
        "responsible_supervisor",
        "mitigation_verified",
        "signoff_status",
        "notes",
    ])
    for ss in spec.scene_safety_specs:
        for hz in ss.hazards:
            cat_s = hz.category.value if hasattr(hz.category, "value") else str(hz.category)
            rl_s = hz.risk_level.value if hasattr(hz.risk_level, "value") else str(hz.risk_level)
            res_s = hz.residual_risk_level.value if hasattr(hz.residual_risk_level, "value") else str(hz.residual_risk_level)
            st_s = hz.signoff_status.value if hasattr(hz.signoff_status, "value") else str(hz.signoff_status)
            writer.writerow([
                ss.scene_index,
                ss.scene_title,
                hz.hazard_id,
                cat_s,
                hz.hazard_description,
                hz.likelihood_score,
                hz.severity_score,
                hz.risk_rating,
                rl_s,
                res_s,
                hz.exclusion_zone_m,
                "; ".join(hz.engineering_controls),
                "; ".join(hz.ppe_required),
                hz.responsible_supervisor,
                hz.mitigation_verified,
                st_s,
                hz.notes,
            ])
    return buf.getvalue()


def generate_safety_manifest_json(
    spec_or_bible: Union[MasterSafetyRiskSpec, MasterProductionBible],
) -> str:
    """Serialize the MasterSafetyRiskSpec into an indented JSON JSA manifest."""
    spec = _resolve_safety_spec(spec_or_bible)
    return json.dumps(spec.model_dump(mode="json"), indent=2)


def export_safety_bundle(
    spec_or_bible: Union[MasterSafetyRiskSpec, MasterProductionBible],
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Export all PM-FEAT-026 On-Set Safety & JSA artifacts into `output_dir`.

    Writes:
    - safety_bulletin.md
    - safety_jsa_matrix.csv
    - safety_risk_manifest.json
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    spec = _resolve_safety_spec(spec_or_bible)

    md_p = out_path / "safety_bulletin.md"
    csv_p = out_path / "safety_jsa_matrix.csv"
    json_p = out_path / "safety_risk_manifest.json"

    md_p.write_text(generate_safety_bulletin_md(spec), encoding="utf-8")
    csv_p.write_text(generate_safety_jsa_csv(spec), encoding="utf-8")
    json_p.write_text(generate_safety_manifest_json(spec), encoding="utf-8")

    return {
        "safety_md": str(md_p),
        "safety_csv": str(csv_p),
        "safety_json": str(json_p),
    }


__all__ = [
    "calculate_kinetic_exclusion_zone_m",
    "assess_scene_hazards",
    "synthesize_default_safety_risk_spec",
    "format_safety_prompt_token",
    "generate_safety_bulletin_md",
    "generate_safety_jsa_csv",
    "generate_safety_manifest_json",
    "export_safety_bundle",
]
