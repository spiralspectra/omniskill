"""AICP Commercial Production Bid & Budget Breakdown Top Sheet Engine (PM-FEAT-020).

Provides AICP Chart of Accounts line items calculation, union labor tiers & day rates,
payroll fringes (23.5%), production insurance (3.2%), production company markup (18%),
contingency reserve (10%), C-suite executive Top Sheet summary math, Cost-Per-Second (CPS),
per-scene budget allocations, Showbiz/Hot Budget compatible CSV bid sheets, and JSON manifests.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    AicpLineItemSpec,
    AicpSectionCode,
    AicpTopSheetSummarySpec,
    CrewLaborTier,
    MasterAicpBidSpec,
    MasterProductionBible,
)

# Standard union commercial day rates (USD / 10-hour day)
UNION_DAY_RATES: Dict[str, float] = {
    "DGA_DIRECTOR": 15000.0,
    "IATSE_600_DP": 4500.0,
    "DGA_1ST_AD": 2800.0,
    "IATSE_728_GAFFER": 1600.0,
    "IATSE_80_KEY_GRIP": 1600.0,
    "IATSE_695_SOUND_MIXER": 1800.0,
    "IATSE_600_DIT": 1900.0,
    "FAA_PART_107_PILOT": 2500.0,
}

# Standard commercial markup & fringe rates
DEFAULT_FRINGE_RATE_PCT: float = 23.5  # 23.5% payroll fringes & union health/pension
DEFAULT_INSURANCE_RATE_PCT: float = 3.2  # 3.2% comprehensive production insurance
DEFAULT_PRODUCTION_FEE_PCT: float = 18.0  # 18.0% production company markup
DEFAULT_CONTINGENCY_PCT: float = 10.0  # 10.0% production contingency reserve

# AICP Standard Section Descriptions (Sections A through K core, plus L, M, N)
AICP_SECTION_NAMES: Dict[str, str] = {
    "A": "Pre-Production & Wrap Crew",
    "B": "Shooting Production Crew Labor",
    "C": "Location & Travel Expenses",
    "D": "Props, Wardrobe & Sets",
    "E": "Equipment Rental (Camera/Grip/Electric/Drone)",
    "F": "Studio Soundstage & Facilities",
    "G": "Production Expenses & Catering",
    "H": "Talent Labor (SAG-AFTRA)",
    "I": "Talent Travel & Expenses",
    "J": "Post-Production Offline Editorial",
    "K": "Post Finishing, Color Grade & VFX",
    "L": "Sound Design & Final Mix",
    "M": "Production Insurance & Payroll Fringes",
    "N": "Production Fee & Contingency",
}


def calculate_aicp_top_sheet(
    line_items: List[AicpLineItemSpec],
    production_fee_pct: float = DEFAULT_PRODUCTION_FEE_PCT,
    contingency_pct: float = DEFAULT_CONTINGENCY_PCT,
    insurance_rate_pct: float = DEFAULT_INSURANCE_RATE_PCT,
    fringe_rate_pct: float = DEFAULT_FRINGE_RATE_PCT,
    total_runtime_seconds: float = 60.0,
) -> AicpTopSheetSummarySpec:
    """Calculates standardized AICP Top Sheet section totals, markups, fringes, insurance, and grand total."""
    section_totals: Dict[str, float] = {}

    for code in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]:
        section_totals[code] = 0.0

    total_labor_subtotal = 0.0
    total_fringes = 0.0

    for item in line_items:
        sec_str = item.section.value if hasattr(item.section, "value") else str(item.section)
        sec_key = sec_str.upper()
        if sec_key not in section_totals:
            section_totals[sec_key] = 0.0

        # Calculate base subtotal
        qty = item.units_count if item.units_count > 0 else item.days_or_qty
        rate = item.unit_rate_usd if item.unit_rate_usd > 0 else item.rate
        base_subtotal = round(qty * rate, 2)
        item.subtotal = base_subtotal

        # Identify labor vs non-labor
        is_labor = item.category.lower() == "labor" or sec_key in ("A", "B", "H")
        if is_labor:
            total_labor_subtotal = round(total_labor_subtotal + base_subtotal, 2)
            fringe_p = item.fringes_pct if item.fringes_pct > 0 else fringe_rate_pct
            fringe_amt = round(base_subtotal * (fringe_p / 100.0), 2)
            item.fringes_pct = fringe_p
            item.fringe_pct = fringe_p
            item.fringe_amount = fringe_amt
            total_cost = round(base_subtotal + fringe_amt, 2)
            total_fringes = round(total_fringes + fringe_amt, 2)
        else:
            item.fringe_amount = 0.0
            total_cost = base_subtotal

        item.total_cost_usd = total_cost
        item.total = total_cost
        section_totals[sec_key] = round(section_totals[sec_key] + total_cost, 2)

    # Above-The-Line (ATL) vs Below-The-Line (BTL)
    atl_subtotal = round(section_totals.get("A", 0.0) + section_totals.get("H", 0.0), 2)
    btl_subtotal = round(
        sum(section_totals.get(c, 0.0) for c in ["B", "C", "D", "E", "F", "G", "I", "J", "K", "L"]), 2
    )

    gross_production = round(sum(section_totals.get(c, 0.0) for c in ["A", "B", "C", "D", "E", "F", "G"]), 2)
    talent_costs = round(sum(section_totals.get(c, 0.0) for c in ["H", "I"]), 2)
    post_costs = round(sum(section_totals.get(c, 0.0) for c in ["J", "K", "L"]), 2)

    # Production Insurance (3.2% of direct production subtotal)
    direct_prod_subtotal = round(gross_production + talent_costs + post_costs, 2)
    insurance_usd = round(direct_prod_subtotal * (insurance_rate_pct / 100.0), 2)
    section_totals["M"] = round(insurance_usd + total_fringes, 2)

    # Subtotal Direct Costs
    subtotal_direct = round(direct_prod_subtotal + insurance_usd, 2)

    # Production Company Markup (18%)
    markup_usd = round(subtotal_direct * (production_fee_pct / 100.0), 2)

    # Contingency (10% of subtotal direct + markup)
    contingency_basis = subtotal_direct + markup_usd
    contingency_usd = round(contingency_basis * (contingency_pct / 100.0), 2)

    section_totals["N"] = round(markup_usd + contingency_usd, 2)

    grand_total = round(subtotal_direct + markup_usd + contingency_usd, 2)

    # Cost-Per-Second (CPS)
    runtime = max(1.0, float(total_runtime_seconds))
    cps = round(grand_total / runtime, 2)

    return AicpTopSheetSummarySpec(
        section_totals=section_totals,
        gross_production_costs_usd=gross_production,
        talent_costs_usd=talent_costs,
        post_production_costs_usd=post_costs,
        insurance_and_fringes_usd=section_totals["M"],
        subtotal_direct_costs_usd=subtotal_direct,
        direct_subtotal=subtotal_direct,
        atl_subtotal=atl_subtotal,
        btl_subtotal=btl_subtotal,
        fringe_rate=round(fringe_rate_pct / 100.0, 4),
        total_fringes=total_fringes,
        insurance_rate=round(insurance_rate_pct / 100.0, 4),
        total_insurance=insurance_usd,
        insurance_usd=insurance_usd,
        production_fee_pct=production_fee_pct,
        markup_rate=round(production_fee_pct / 100.0, 4),
        production_fee_usd=markup_usd,
        total_markup=markup_usd,
        contingency_pct=contingency_pct,
        contingency_rate=round(contingency_pct / 100.0, 4),
        contingency_usd=contingency_usd,
        total_contingency=contingency_usd,
        grand_total_bid_usd=grand_total,
        grand_total=grand_total,
        grand_total_bid=grand_total,
        cost_per_second=cps,
    )


def allocate_scene_budgets(
    grand_total_bid_usd: float,
    scenes: Optional[List[Any]] = None,
    total_runtime_seconds: float = 60.0,
) -> List[Dict[str, Any]]:
    """Allocates commercial production budget proportionally across scenes based on duration and complexity."""
    if not scenes:
        # Default single scene allocation
        return [{
            "scene_index": 1,
            "scene_title": "Primary Commercial Narrative",
            "runtime_seconds": total_runtime_seconds,
            "allocated_budget_usd": grand_total_bid_usd,
            "cost_per_second": round(grand_total_bid_usd / max(1.0, total_runtime_seconds), 2),
            "percentage_of_budget": 100.0,
        }]

    # Calculate duration per scene
    scene_durations: List[float] = []
    for sc in scenes:
        dur = 0.0
        if isinstance(sc, dict):
            dur = float(sc.get("duration_seconds", sc.get("duration", 5.0)))
        else:
            dur = float(getattr(sc, "duration_seconds", getattr(sc, "duration", 5.0)))
        scene_durations.append(max(1.0, dur))

    total_dur = sum(scene_durations)
    if total_dur <= 0.0:
        total_dur = max(1.0, total_runtime_seconds)

    allocations: List[Dict[str, Any]] = []
    accumulated_usd = 0.0

    for idx, (sc, dur) in enumerate(zip(scenes, scene_durations)):
        is_last = (idx == len(scenes) - 1)
        title = ""
        if isinstance(sc, dict):
            title = sc.get("title", sc.get("scene_title", f"Scene {idx + 1}"))
        else:
            title = getattr(sc, "title", getattr(sc, "scene_title", f"Scene {idx + 1}"))

        ratio = dur / total_dur
        if is_last:
            allocated = round(grand_total_bid_usd - accumulated_usd, 2)
        else:
            allocated = round(grand_total_bid_usd * ratio, 2)
            accumulated_usd += allocated

        alloc_cps = round(allocated / max(0.1, dur), 2)
        pct = round((allocated / max(1.0, grand_total_bid_usd)) * 100.0, 1)

        allocations.append({
            "scene_index": idx + 1,
            "scene_title": title,
            "runtime_seconds": dur,
            "allocated_budget_usd": allocated,
            "cost_per_second": alloc_cps,
            "percentage_of_budget": pct,
        })

    return allocations


def synthesize_default_aicp_bid(
    project_title: Union[str, Any] = "Commercial Production",
    shoot_days: int = 2,
    domain: Optional[str] = None,
    client_brand: str = "Global Brand",
    labor_tier: CrewLaborTier = CrewLaborTier.TIER_COMMERCIAL_TIER_1,
    total_runtime_seconds: float = 60.0,
    scenes: Optional[List[Any]] = None,
) -> MasterAicpBidSpec:
    """Synthesizes a complete AICP commercial bid package calibrated for high-end commercial production."""
    # Handle MasterProductionBible passed as first positional argument
    if hasattr(project_title, "project_title"):
        bible = project_title
        project_title = getattr(bible, "project_title", "Commercial Production")
        if domain is None:
            domain = str(getattr(bible, "commercial_domain", None) or getattr(bible, "genre_archetype", None) or "")
        if scenes is None and hasattr(bible, "scenes"):
            scenes = bible.scenes
            total_runtime_seconds = float(len(scenes) * 10.0)

    days = max(1, shoot_days)

    # Use union day rates where applicable
    dga_dir_rate = UNION_DAY_RATES["DGA_DIRECTOR"]
    dp_rate = UNION_DAY_RATES["IATSE_600_DP"]
    ad_rate = UNION_DAY_RATES["DGA_1ST_AD"]
    gaffer_rate = UNION_DAY_RATES["IATSE_728_GAFFER"]
    key_grip_rate = UNION_DAY_RATES["IATSE_80_KEY_GRIP"]
    sound_mixer_rate = UNION_DAY_RATES["IATSE_695_SOUND_MIXER"]
    dit_rate = UNION_DAY_RATES["IATSE_600_DIT"]
    drone_pilot_rate = UNION_DAY_RATES["FAA_PART_107_PILOT"]

    items: List[AicpLineItemSpec] = [
        # Section A: Pre-Production & Wrap
        AicpLineItemSpec(
            account_number="A-101",
            account_code="A-101",
            section=AicpSectionCode.SECTION_A,
            section_code="A",
            section_name=AICP_SECTION_NAMES["A"],
            description="Director (DGA Commercial)",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="prep_shoot_wrap",
            units_count=float(days + 4),
            days_or_qty=float(days + 4),
            unit_rate_usd=dga_dir_rate,
            rate=dga_dir_rate,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        AicpLineItemSpec(
            account_number="A-102",
            account_code="A-102",
            section=AicpSectionCode.SECTION_A,
            section_code="A",
            section_name=AICP_SECTION_NAMES["A"],
            description="Line Producer / Production Supervisor",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="prep_wrap",
            units_count=float(days + 4),
            days_or_qty=float(days + 4),
            unit_rate_usd=2200.0,
            rate=2200.0,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        AicpLineItemSpec(
            account_number="A-103",
            account_code="A-103",
            section=AicpSectionCode.SECTION_A,
            section_code="A",
            section_name=AICP_SECTION_NAMES["A"],
            description="First Assistant Director (DGA 1st AD)",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="prep_shoot",
            units_count=float(days + 2),
            days_or_qty=float(days + 2),
            unit_rate_usd=ad_rate,
            rate=ad_rate,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        # Section B: Shooting Crew Labor
        AicpLineItemSpec(
            account_number="B-101",
            account_code="B-101",
            section=AicpSectionCode.SECTION_B,
            section_code="B",
            section_name=AICP_SECTION_NAMES["B"],
            description="Director of Photography (IATSE Local 600 DP)",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=dp_rate,
            rate=dp_rate,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        AicpLineItemSpec(
            account_number="B-102",
            account_code="B-102",
            section=AicpSectionCode.SECTION_B,
            section_code="B",
            section_name=AICP_SECTION_NAMES["B"],
            description="Chief Lighting Technician / Gaffer (IATSE Local 728)",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=gaffer_rate,
            rate=gaffer_rate,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        AicpLineItemSpec(
            account_number="B-103",
            account_code="B-103",
            section=AicpSectionCode.SECTION_B,
            section_code="B",
            section_name=AICP_SECTION_NAMES["B"],
            description="Key Grip (IATSE Local 80)",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=key_grip_rate,
            rate=key_grip_rate,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        AicpLineItemSpec(
            account_number="B-104",
            account_code="B-104",
            section=AicpSectionCode.SECTION_B,
            section_code="B",
            section_name=AICP_SECTION_NAMES["B"],
            description="Production Sound Mixer (IATSE Local 695)",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=sound_mixer_rate,
            rate=sound_mixer_rate,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        AicpLineItemSpec(
            account_number="B-105",
            account_code="B-105",
            section=AicpSectionCode.SECTION_B,
            section_code="B",
            section_name=AICP_SECTION_NAMES["B"],
            description="Digital Imaging Technician / DIT (IATSE Local 600)",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=dit_rate,
            rate=dit_rate,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        AicpLineItemSpec(
            account_number="B-106",
            account_code="B-106",
            section=AicpSectionCode.SECTION_B,
            section_code="B",
            section_name=AICP_SECTION_NAMES["B"],
            description="FAA Part 107 Commercial Drone Pilot / RPIC",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=drone_pilot_rate,
            rate=drone_pilot_rate,
            fringes_pct=DEFAULT_FRINGE_RATE_PCT,
        ),
        # Section C: Location & Travel
        AicpLineItemSpec(
            account_number="C-101",
            account_code="C-101",
            section=AicpSectionCode.SECTION_C,
            section_code="C",
            section_name=AICP_SECTION_NAMES["C"],
            description="Location Scouting, Film Permits & City Police Escort",
            crew_tier=labor_tier,
            category="expense",
            rate_basis="flat",
            units_count=1.0,
            days_or_qty=1.0,
            unit_rate_usd=4800.0,
            rate=4800.0,
            fringes_pct=0.0,
        ),
        # Section D: Props, Wardrobe & Sets
        AicpLineItemSpec(
            account_number="D-101",
            account_code="D-101",
            section=AicpSectionCode.SECTION_D,
            section_code="D",
            section_name=AICP_SECTION_NAMES["D"],
            description="Hero Wardrobe Styling & Props Purchases",
            crew_tier=labor_tier,
            category="expense",
            rate_basis="flat",
            units_count=1.0,
            days_or_qty=1.0,
            unit_rate_usd=6500.0,
            rate=6500.0,
            fringes_pct=0.0,
        ),
        # Section E: Equipment Rental
        AicpLineItemSpec(
            account_number="E-101",
            account_code="E-101",
            section=AicpSectionCode.SECTION_E,
            section_code="E",
            section_name=AICP_SECTION_NAMES["E"],
            description="ARRI Alexa 35 Cinema Camera Package & Cooke S7/i Primes",
            crew_tier=labor_tier,
            category="equipment",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=3800.0,
            rate=3800.0,
            fringes_pct=0.0,
        ),
        AicpLineItemSpec(
            account_number="E-102",
            account_code="E-102",
            section=AicpSectionCode.SECTION_E,
            section_code="E",
            section_name=AICP_SECTION_NAMES["E"],
            description="5-Ton Grip & Electric Truck (ARRI Orbiter & SkyPanel X)",
            crew_tier=labor_tier,
            category="equipment",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=2900.0,
            rate=2900.0,
            fringes_pct=0.0,
        ),
        AicpLineItemSpec(
            account_number="E-103",
            account_code="E-103",
            section=AicpSectionCode.SECTION_E,
            section_code="E",
            section_name=AICP_SECTION_NAMES["E"],
            description="DJI Inspire 3 Aerial Cinema Drone System & High-Bright Monitors",
            crew_tier=labor_tier,
            category="equipment",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=2400.0,
            rate=2400.0,
            fringes_pct=0.0,
        ),
        # Section F: Studio Soundstage & Facilities
        AicpLineItemSpec(
            account_number="F-101",
            account_code="F-101",
            section=AicpSectionCode.SECTION_F,
            section_code="F",
            section_name=AICP_SECTION_NAMES["F"],
            description="Soundstage Rental, Power Distribution & HVAC Package",
            crew_tier=labor_tier,
            category="facility",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=4200.0,
            rate=4200.0,
            fringes_pct=0.0,
        ),
        # Section G: Production Expenses & Catering
        AicpLineItemSpec(
            account_number="G-101",
            account_code="G-101",
            section=AicpSectionCode.SECTION_G,
            section_code="G",
            section_name=AICP_SECTION_NAMES["G"],
            description="Production Catering, Craft Services & Expendables",
            crew_tier=labor_tier,
            category="expense",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=1650.0,
            rate=1650.0,
            fringes_pct=0.0,
        ),
        # Section H: Talent Labor (SAG-AFTRA)
        AicpLineItemSpec(
            account_number="H-101",
            account_code="H-101",
            section=AicpSectionCode.SECTION_H,
            section_code="H",
            section_name=AICP_SECTION_NAMES["H"],
            description="Principal On-Camera SAG-AFTRA Talent (Session Fee)",
            crew_tier=labor_tier,
            category="labor",
            rate_basis="day",
            units_count=float(days),
            days_or_qty=float(days),
            unit_rate_usd=2100.0,
            rate=2100.0,
            fringes_pct=21.0,
        ),
        # Section I: Talent Expenses
        AicpLineItemSpec(
            account_number="I-101",
            account_code="I-101",
            section=AicpSectionCode.SECTION_I,
            section_code="I",
            section_name=AICP_SECTION_NAMES["I"],
            description="Talent Wardrobe Fittings & Ground Transportation",
            crew_tier=labor_tier,
            category="expense",
            rate_basis="flat",
            units_count=1.0,
            days_or_qty=1.0,
            unit_rate_usd=1200.0,
            rate=1200.0,
            fringes_pct=0.0,
        ),
        # Section J: Post Editorial
        AicpLineItemSpec(
            account_number="J-101",
            account_code="J-101",
            section=AicpSectionCode.SECTION_J,
            section_code="J",
            section_name=AICP_SECTION_NAMES["J"],
            description="Offline Editorial & Director's Cut Assembly",
            crew_tier=labor_tier,
            category="post",
            rate_basis="flat",
            units_count=1.0,
            days_or_qty=1.0,
            unit_rate_usd=7500.0,
            rate=7500.0,
            fringes_pct=0.0,
        ),
        # Section K: Post Finishing & VFX
        AicpLineItemSpec(
            account_number="K-101",
            account_code="K-101",
            section=AicpSectionCode.SECTION_K,
            section_code="K",
            section_name=AICP_SECTION_NAMES["K"],
            description="DaVinci Resolve 3D LUT Color Grade & Flame Online Conform",
            crew_tier=labor_tier,
            category="post",
            rate_basis="flat",
            units_count=1.0,
            days_or_qty=1.0,
            unit_rate_usd=6200.0,
            rate=6200.0,
            fringes_pct=0.0,
        ),
        # Section L: Sound Design & Mix
        AicpLineItemSpec(
            account_number="L-101",
            account_code="L-101",
            section=AicpSectionCode.SECTION_L,
            section_code="L",
            section_name=AICP_SECTION_NAMES["L"],
            description="Dolby Atmos Sound Design, Diegetic Foley & Final Re-recording Mix",
            crew_tier=labor_tier,
            category="post",
            rate_basis="flat",
            units_count=1.0,
            days_or_qty=1.0,
            unit_rate_usd=4800.0,
            rate=4800.0,
            fringes_pct=0.0,
        ),
    ]

    top_sheet = calculate_aicp_top_sheet(
        items,
        production_fee_pct=DEFAULT_PRODUCTION_FEE_PCT,
        contingency_pct=DEFAULT_CONTINGENCY_PCT,
        insurance_rate_pct=DEFAULT_INSURANCE_RATE_PCT,
        fringe_rate_pct=DEFAULT_FRINGE_RATE_PCT,
        total_runtime_seconds=total_runtime_seconds,
    )

    scene_allocs = allocate_scene_budgets(
        grand_total_bid_usd=top_sheet.grand_total_bid_usd,
        scenes=scenes,
        total_runtime_seconds=total_runtime_seconds,
    )

    return MasterAicpBidSpec(
        project_title=project_title,
        client_brand=client_brand,
        client=client_brand,
        agency_name="Omni Creative Partners",
        production_company="Omni Studio Productions",
        shoot_days_count=days,
        shoot_days=days,
        prep_days=2,
        post_days=5,
        total_runtime_seconds=total_runtime_seconds,
        shoot_location="Los Angeles, CA",
        currency="USD",
        labor_tier=labor_tier,
        line_items=items,
        top_sheet=top_sheet,
        cost_per_second=top_sheet.cost_per_second,
        grand_total=top_sheet.grand_total_bid_usd,
        scene_allocations=scene_allocs,
    )


def generate_aicp_bid_sheet_csv(bid: MasterAicpBidSpec) -> str:
    """Generates standard Showbiz / Hot Budget compatible AICP bid sheet CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header metadata
    writer.writerow(["# AICP COMMERCIAL PRODUCTION BID SHEET"])
    writer.writerow(["# Project", bid.project_title])
    writer.writerow(["# Client/Brand", bid.client_brand])
    writer.writerow(["# Production Company", bid.production_company])
    writer.writerow(["# Shoot Days", bid.shoot_days_count])
    writer.writerow(["# Currency", bid.currency])
    writer.writerow([])

    # Table columns
    writer.writerow([
        "Account",
        "Section",
        "Section_Name",
        "Description",
        "Category",
        "Labor_Tier",
        "Basis",
        "Days_Qty",
        "Unit_Rate_USD",
        "Subtotal_USD",
        "Fringes_Pct",
        "Fringe_USD",
        "Total_USD",
    ])

    for item in bid.line_items:
        sec = item.section.value if hasattr(item.section, "value") else str(item.section)
        sec_name = item.section_name or AICP_SECTION_NAMES.get(sec, f"Section {sec}")
        tier = item.crew_tier.value if hasattr(item.crew_tier, "value") else str(item.crew_tier)
        qty = item.units_count if item.units_count > 0 else item.days_or_qty
        rate = item.unit_rate_usd if item.unit_rate_usd > 0 else item.rate
        sub = item.subtotal if item.subtotal > 0 else round(qty * rate, 2)
        f_pct = item.fringes_pct if item.fringes_pct > 0 else item.fringe_pct
        f_amt = item.fringe_amount if item.fringe_amount > 0 else round(sub * (f_pct / 100.0), 2)
        tot = item.total_cost_usd if item.total_cost_usd > 0 else item.total

        writer.writerow([
            item.account_number or item.account_code,
            sec,
            sec_name,
            item.description,
            item.category,
            tier,
            item.rate_basis,
            f"{qty:.1f}",
            f"{rate:.2f}",
            f"{sub:.2f}",
            f"{f_pct:.1f}",
            f"{f_amt:.2f}",
            f"{tot:.2f}",
        ])

    ts = bid.top_sheet
    writer.writerow([])
    writer.writerow(["# SUMMARY / MARKUP BREAKDOWN"])
    writer.writerow(["Section A-G", "Gross Production Costs", "", "", "", "", "", "", "", f"{ts.gross_production_costs_usd:.2f}"])
    writer.writerow(["Section H-I", "Talent Costs", "", "", "", "", "", "", "", f"{ts.talent_costs_usd:.2f}"])
    writer.writerow(["Section J-L", "Post-Production Costs", "", "", "", "", "", "", "", f"{ts.post_production_costs_usd:.2f}"])
    writer.writerow(["Insurance (3.2%)", "Production Insurance", "", "", "", "", "", "", "", f"{ts.total_insurance:.2f}"])
    writer.writerow(["Payroll Fringes (23.5%)", "Total Labor Fringes", "", "", "", "", "", "", "", f"{ts.total_fringes:.2f}"])
    writer.writerow(["Subtotal Direct Costs", "", "", "", "", "", "", "", "", f"{ts.subtotal_direct_costs_usd:.2f}"])
    writer.writerow([f"Production Fee ({ts.production_fee_pct:.1f}%)", "Company Markup", "", "", "", "", "", "", "", f"{ts.production_fee_usd:.2f}"])
    writer.writerow([f"Contingency ({ts.contingency_pct:.1f}%)", "Production Contingency Reserve", "", "", "", "", "", "", "", f"{ts.contingency_usd:.2f}"])
    writer.writerow(["GRAND TOTAL COMMERCIAL BID", "", "", "", "", "", "", "", "", f"{ts.grand_total_bid_usd:.2f}"])
    writer.writerow(["Cost-Per-Second (CPS)", f"${ts.cost_per_second:.2f}/sec", "", "", "", "", "", "", "", ""])

    return output.getvalue()


def generate_aicp_topsheet_md(bid: MasterAicpBidSpec) -> str:
    """Generates an executive C-suite AICP Top Sheet summary markdown report."""
    ts = bid.top_sheet
    totals = ts.section_totals

    lines = [
        f"# AICP Production Bid Top Sheet - {bid.project_title}",
        "",
        "## Commercial Production Identification",
        f"- **Project Title**: `{bid.project_title}`",
        f"- **Client / Brand**: `{bid.client_brand}`",
        f"- **Agency**: `{bid.agency_name}`",
        f"- **Production Company**: `{bid.production_company}`",
        f"- **Shoot Days**: `{bid.shoot_days_count} day(s)` | **Location**: `{bid.shoot_location}`",
        f"- **Total Runtime**: `{bid.total_runtime_seconds:.1f}s` | **Currency**: `{bid.currency}`",
        f"- **Labor Tier**: `{bid.labor_tier.value if hasattr(bid.labor_tier, 'value') else bid.labor_tier}`",
        f"- **Cost-Per-Second (CPS)**: **`${ts.cost_per_second:,.2f} / second`**",
        "",
        "## Above-The-Line (ATL) vs Below-The-Line (BTL) Analysis",
        f"- **Above-The-Line (ATL)**: `${ts.atl_subtotal:,.2f}` ({round(ts.atl_subtotal / max(1.0, ts.subtotal_direct_costs_usd) * 100.0, 1)}% of Direct Costs)",
        f"- **Below-The-Line (BTL)**: `${ts.btl_subtotal:,.2f}` ({round(ts.btl_subtotal / max(1.0, ts.subtotal_direct_costs_usd) * 100.0, 1)}% of Direct Costs)",
        "",
        "## AICP Summary Cost Sections (Chart of Accounts)",
        "| Section | Description | Subtotal (USD) |",
        "|---|---|---|",
    ]

    for code, name in AICP_SECTION_NAMES.items():
        val = totals.get(code, 0.0)
        lines.append(f"| Section {code} | {name} | ${val:,.2f} |")

    lines.extend([
        "",
        "## Executive Summary & Markup Breakdown",
        f"- **Gross Production Costs (Sections A-G)**: `${ts.gross_production_costs_usd:,.2f}`",
        f"- **Talent Costs (Sections H-I)**: `${ts.talent_costs_usd:,.2f}`",
        f"- **Post-Production Costs (Sections J-L)**: `${ts.post_production_costs_usd:,.2f}`",
        f"- **Payroll Fringes (23.5% on Labor)**: `${ts.total_fringes:,.2f}`",
        f"- **Production Insurance (3.2%)**: `${ts.total_insurance:,.2f}`",
        "---",
        f"- **Subtotal Direct Costs**: `${ts.subtotal_direct_costs_usd:,.2f}`",
        f"- **Production Fee Markup ({ts.production_fee_pct:.1f}%)**: `${ts.production_fee_usd:,.2f}`",
        f"- **Contingency Reserve ({ts.contingency_pct:.1f}%)**: `${ts.contingency_usd:,.2f}`",
        "---",
        f"### **GRAND TOTAL COMMERCIAL BID**: `${ts.grand_total_bid_usd:,.2f} {bid.currency}**",
        f"### **COST-PER-SECOND**: `${ts.cost_per_second:,.2f} / sec**",
        "",
    ])

    if bid.scene_allocations:
        lines.extend([
            "## Per-Scene Budget Allocation",
            "| Scene | Title | Duration (s) | Allocated Budget | Cost / Sec | % of Budget |",
            "|---|---|---|---|---|---|",
        ])
        for alloc in bid.scene_allocations:
            lines.append(
                f"| {alloc.get('scene_index', '-')} | {alloc.get('scene_title', '-')} | "
                f"{alloc.get('runtime_seconds', 0.0):.1f}s | "
                f"${alloc.get('allocated_budget_usd', 0.0):,.2f} | "
                f"${alloc.get('cost_per_second', 0.0):,.2f}/s | "
                f"{alloc.get('percentage_of_budget', 0.0):.1f}% |"
            )
        lines.append("")

    return "\n".join(lines)


def generate_aicp_bid_manifest_json(bid: MasterAicpBidSpec) -> str:
    """Serializes the complete AICP bid spec and top sheet summary into JSON."""
    return json.dumps(bid.model_dump(), indent=2)


def export_aicp_budget_bundle(
    bible_or_bid: Union[MasterProductionBible, MasterAicpBidSpec],
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports all AICP budget deliverables (CSV bid sheet, TopSheet MD, JSON manifest) into output_dir."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if isinstance(bible_or_bid, MasterProductionBible):
        bible = bible_or_bid
        bid = bible.master_aicp_bid or getattr(bible, "aicp_bid", None)
        if bid is None:
            domain = getattr(bible, "domain_archetype", None)
            total_sec = getattr(bible, "total_runtime_seconds", 60.0)
            scenes = getattr(bible, "scenes", [])
            bid = synthesize_default_aicp_bid(
                project_title=bible.project_title,
                shoot_days=max(1, len(scenes) // 2),
                domain=domain,
                total_runtime_seconds=total_sec,
                scenes=scenes,
            )
    else:
        bid = bible_or_bid

    csv_p = out_path / "aicp_bid_sheet.csv"
    json_p = out_path / "aicp_bid_manifest.json"
    md_p = out_path / "production_budget_topsheet.md"

    csv_p.write_text(generate_aicp_bid_sheet_csv(bid), encoding="utf-8")
    json_p.write_text(generate_aicp_bid_manifest_json(bid), encoding="utf-8")
    md_p.write_text(generate_aicp_topsheet_md(bid), encoding="utf-8")

    return {
        "aicp_csv": str(csv_p),
        "aicp_manifest": str(json_p),
        "aicp_topsheet": str(md_p),
    }
