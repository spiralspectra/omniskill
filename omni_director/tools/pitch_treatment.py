"""Executive Director's Treatment, Print-Ready Pitch Lookbook & Bible Revision Diff (PM-FEAT-036).

Pure-Python engine providing:
- Domain-calibrated executive pitch treatment compilation across 9 canonical slide roles
  (cover_logline, creative_vision_regime, color_script_palette, cast_wardrobe_polarity,
  environment_plates, per-scene scene_beat_spread, sonic_bgm_arc, budget_roi_summary,
  deliverables_signoff)
- Deterministic SHA-256 Bible Revision Diff engine comparing ProductionBibles,
  ProductionBundles, JSON paths, or dicts across direction, prompts, optics, lighting,
  AICP bids, AI compute economics, and council scores
- Self-contained printable HTML5 Lookbook with @media print page breaks, dark-room
  cinema + print CSS, html.escape() safety, embedded Nano Banana SVG plates,
  color-script swatch strip, BGM/sonic arc, and AI-vs-AICP ROI summary
- Markdown, JSON, and bundle directory exporters
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    BibleRevisionDeltaItem,
    BibleRevisionDiffReport,
    MasterPitchTreatmentSpec,
    MasterProductionBible,
    ProductionBundle,
    ScenePromptSpec,
    TreatmentBoardSlideSpec,
    TreatmentSlideTypeEnum,
    load_bible_from_json,
)

# Fallback domain calibrations in case presets is still initializing
_FALLBACK_DOMAIN_TREATMENT_CALIBRATIONS: Dict[str, Dict[str, Any]] = {
    "automotive_robotics": {
        "executive_tone": "Precision Telemetry & Autonomous Engineering",
        "director_statement_template": (
            "{project_title} pairs robotic motion-control discipline with tactile high-speed telemetry. "
            "Built under {regime} in {mode}, every {runtime}s frame preserves rigid CAD geometry and "
            "kinetic inertia while highlighting {kpi}."
        ),
        "audience_hook": "Zero-latency machine craftsmanship meets visceral asphalt velocity.",
        "hero_kpi_focus": "Telemetry Precision & Hero Vehicle Silhouette Recall",
        "color_palette": ["#0B111E", "#1E293B", "#38BDF8", "#F59E0B", "#F8FAFC"],
    },
    "culinary_asmr": {
        "executive_tone": "Hyper-Tactile Macro Gastronomy & Sensory Intimacy",
        "director_statement_template": (
            "{project_title} celebrates micro-texture, natural daylight warmth, and unhurried ASMR foley. "
            "Designed in {regime} ({mode}) across {runtime}s, the lens isolates authentic material acoustics "
            "to drive {kpi}."
        ),
        "audience_hook": "Visceral close-range texture and acoustic crispness you can almost taste.",
        "hero_kpi_focus": "Appetite Appeal & Tactile ASMR Sensory Retention",
        "color_palette": ["#1C1410", "#78350F", "#F59E0B", "#FDE68A", "#FFFBEB"],
    },
    "luxury_fashion": {
        "executive_tone": "Editorial Couture Restraint & Kinetic Silk Fluidity",
        "director_statement_template": (
            "{project_title} frames bespoke tailoring and sculptural movement in an unbroken {runtime}s study. "
            "Guided by {regime} and {mode}, lighting ratios and fabric physics elevate {kpi}."
        ),
        "audience_hook": "Architectural poise and fluid textile drama in continuous editorial motion.",
        "hero_kpi_focus": "Maison Prestige & Silhouette Memorability",
        "color_palette": ["#0B0B0F", "#27272A", "#D4AF37", "#E5E7EB", "#FAF8F5"],
    },
    "kinetic_action": {
        "executive_tone": "High-Velocity Newtonian Impact & Staccato Rhythm",
        "director_statement_template": (
            "{project_title} translates pure physical momentum into disciplined {runtime}s storytelling. "
            "Operating under {regime} in {mode}, every impact chain preserves mass, inertia, and "
            "aerodynamic truth to maximize {kpi}."
        ),
        "audience_hook": "Unflinching kinetic force anchored by crisp 180-degree shutter clarity.",
        "hero_kpi_focus": "Adrenaline Completion Rate & Brand Hero Impact",
        "color_palette": ["#090D16", "#DC2626", "#06B6D4", "#94A3B8", "#F8FAFC"],
    },
    "tech_hardware": {
        "executive_tone": "Cleanroom Optical Minimalism & Sub-Millimeter Craft",
        "director_statement_template": (
            "{project_title} reveals precision industrial design through locked-off MoCo macro optics. "
            "Structured in {regime} ({mode}) over {runtime}s, specular highlights and chamfered aluminum "
            "reflections reinforce {kpi}."
        ),
        "audience_hook": "Sub-millimeter industrial elegance engineered for instant flagship authority.",
        "hero_kpi_focus": "Product Detail Comprehension & Hardware Desire",
        "color_palette": ["#090D16", "#1E293B", "#6366F1", "#38BDF8", "#F8FAFC"],
    },
    "architectural_sanctuary": {
        "executive_tone": "Serene Spatial Minimalism & Quiet Light Choreography",
        "director_statement_template": (
            "{project_title} honors stillness, daylight geometry, and honest natural materials across {runtime}s. "
            "Composed in {regime} using {mode}, measured spatial breathing room deepens {kpi}."
        ),
        "audience_hook": "Calm Nordic light and honest materiality transforming empty space into sanctuary.",
        "hero_kpi_focus": "Atmospheric Affinity & Brand Sanctuary Recall",
        "color_palette": ["#1E293B", "#64748B", "#D97706", "#E2E8F0", "#F8FAFC"],
    },
}

_LOOK_PRESET_PALETTES: Dict[str, List[str]] = {
    "rec709_neutral": ["#111827", "#374151", "#60A5FA", "#E5E7EB", "#F9FAFB"],
    "kodak_5219_vision3": ["#1A1412", "#7C2D12", "#D97706", "#FDE68A", "#FFFDF7"],
    "fuji_eterna_500t": ["#0F172A", "#1E3A5F", "#10B981", "#CBD5E1", "#F8FAFC"],
    "bleach_bypass_silver": ["#09090B", "#27272A", "#71717A", "#D4D4D8", "#FAFAFA"],
    "teal_and_orange_blockbuster": ["#082F49", "#0E7490", "#EA580C", "#FB923C", "#F8FAFC"],
    "monochrome_panatomic_x": ["#0A0A0A", "#262626", "#737373", "#D4D4D4", "#FAFAFA"],
}

_DEFAULT_SCHEMA_PALETTE = ["#2C3E50", "#E74C3C", "#ECF0F1", "#F39C12"]


def _enum_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _normalize_hex(raw: str) -> Optional[str]:
    s = str(raw or "").strip()
    if not s:
        return None
    if not s.startswith("#"):
        s = f"#{s}"
    cleaned = s[1:]
    if len(cleaned) == 3 and all(ch in "0123456789abcdefABCDEF" for ch in cleaned):
        cleaned = "".join(ch * 2 for ch in cleaned)
    if len(cleaned) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in cleaned):
        return f"#{cleaned.upper()}"
    return None


def _resolve_domain_key(bible: MasterProductionBible) -> str:
    raw = getattr(bible, "domain_archetype", None)
    if raw:
        key = _enum_str(raw).strip().lower().replace("-", "_").replace(" ", "_")
        if key in _FALLBACK_DOMAIN_TREATMENT_CALIBRATIONS:
            return key
    try:
        from omni_director.presets import classify_brief_domain

        classified = classify_brief_domain(
            f"{getattr(bible, 'project_title', '')} {getattr(bible, 'logline', '')}"
        )
        key = _enum_str(classified).strip().lower()
        if key in _FALLBACK_DOMAIN_TREATMENT_CALIBRATIONS:
            return key
    except Exception:
        pass
    return "architectural_sanctuary"


def _resolve_domain_calibration(
    domain_key: str,
    domain_calibration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base = dict(
        _FALLBACK_DOMAIN_TREATMENT_CALIBRATIONS.get(
            domain_key,
            _FALLBACK_DOMAIN_TREATMENT_CALIBRATIONS["architectural_sanctuary"],
        )
    )
    try:
        from omni_director.presets import get_domain_pitch_treatment_spec

        preset_cal = get_domain_pitch_treatment_spec(domain_key)
        if isinstance(preset_cal, dict):
            for k, v in preset_cal.items():
                if v is not None:
                    base[k] = v
    except Exception:
        pass
    if isinstance(domain_calibration, dict):
        for k, v in domain_calibration.items():
            if v is not None:
                base[k] = v
    return base


def _derive_color_script_swatches(
    bible: MasterProductionBible,
    calibration: Dict[str, Any],
) -> List[str]:
    """Derives hex color swatches from bible.color_look / master_color_look, bible.color_palette, or domain defaults."""
    swatches: List[str] = []

    raw_palette = list(getattr(bible, "color_palette", None) or [])
    normalized_bible_palette = [hx for hx in (_normalize_hex(c) for c in raw_palette) if hx]
    default_upper = [c.upper() for c in _DEFAULT_SCHEMA_PALETTE]
    has_custom_bible_palette = bool(normalized_bible_palette) and normalized_bible_palette != default_upper

    color_look = getattr(bible, "color_look", None) or getattr(bible, "master_color_look", None)
    look_preset_swatches: List[str] = []
    if color_look is not None:
        preset_key = _enum_str(getattr(color_look, "look_preset", None), "").lower()
        if preset_key in _LOOK_PRESET_PALETTES:
            look_preset_swatches = list(_LOOK_PRESET_PALETTES[preset_key])
        cdl = getattr(color_look, "cdl", None)
        if cdl is not None and not look_preset_swatches:
            slope = getattr(cdl, "slope", (1.0, 1.0, 1.0))
            r = max(0, min(255, int(round(128 * float(slope[0])))))
            g = max(0, min(255, int(round(128 * float(slope[1])))))
            b = max(0, min(255, int(round(128 * float(slope[2])))))
            look_preset_swatches.append(f"#{r:02X}{g:02X}{b:02X}")

    domain_palette = [
        hx for hx in (_normalize_hex(c) for c in (calibration.get("color_palette") or [])) if hx
    ]

    if has_custom_bible_palette:
        candidates = normalized_bible_palette + look_preset_swatches[:2]
    elif look_preset_swatches and domain_palette:
        candidates = domain_palette[:3] + look_preset_swatches[:2]
    elif look_preset_swatches:
        candidates = look_preset_swatches
    elif domain_palette:
        candidates = domain_palette
    else:
        candidates = normalized_bible_palette or list(_DEFAULT_SCHEMA_PALETTE)

    for hx in candidates:
        norm = _normalize_hex(hx)
        if norm and norm not in swatches:
            swatches.append(norm)
    return swatches[:6]


def _extract_kelvin_from_bible(bible: MasterProductionBible) -> int:
    lighting_rig = getattr(bible, "master_lighting_rig", None)
    if lighting_rig is not None:
        fixtures = list(getattr(lighting_rig, "fixtures", None) or [])
        if fixtures:
            key_fix = next(
                (f for f in fixtures if "key" in _enum_str(getattr(f, "role", ""), "").lower()),
                fixtures[0],
            )
            cct = getattr(key_fix, "cct_kelvin", None)
            if cct is not None:
                return int(cct)
    env = getattr(bible, "environment", None)
    if env is not None:
        setup = str(getattr(env, "lighting_setup", "") or "")
        match = re.search(r"(\d{4,5})\s*K\b", setup, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 5600


def _extract_scene_kelvin(scene: ScenePromptSpec, fallback_kelvin: int) -> int:
    rig = getattr(scene, "lighting_rig", None)
    if rig is not None:
        fixtures = list(getattr(rig, "fixtures", None) or [])
        if fixtures:
            key_fix = next(
                (f for f in fixtures if "key" in _enum_str(getattr(f, "role", ""), "").lower()),
                fixtures[0],
            )
            cct = getattr(key_fix, "cct_kelvin", None)
            if cct is not None:
                return int(cct)
    return fallback_kelvin


def _extract_scene_focal_mm(scene: ScenePromptSpec, bible: Optional[MasterProductionBible] = None) -> int:
    cam = getattr(scene, "craft_camera", None)
    if cam is not None:
        val = getattr(cam, "focal_length_mm", None) or getattr(cam, "lens_mm", None)
        if val is not None:
            return int(val)
    opt = getattr(scene, "optical_lens", None)
    if opt is not None:
        val = getattr(opt, "focal_length_mm", None)
        if val is not None:
            return int(val)
    if bible is not None:
        master_cam = getattr(bible, "camera_rig", None)
        if master_cam is not None:
            val = getattr(master_cam, "focal_length_mm", None) or getattr(master_cam, "lens_mm", None)
            if val is not None:
                return int(val)
    return 35


def _extract_aicp_total_usd(bible: MasterProductionBible) -> float:
    bid = (
        getattr(bible, "master_aicp_bid", None)
        or getattr(bible, "aicp_bid", None)
        or getattr(bible, "master_aicp_budget", None)
        or getattr(bible, "aicp_budget", None)
    )
    if bid is None:
        return 0.0
    if isinstance(bid, dict):
        top = bid.get("top_sheet") or {}
        val = (
            bid.get("grand_total_usd")
            or bid.get("grand_total")
            or bid.get("total_bid_usd")
            or (top.get("grand_total_bid_usd") if isinstance(top, dict) else 0.0)
            or (top.get("grand_total_bid") if isinstance(top, dict) else 0.0)
            or (top.get("grand_total") if isinstance(top, dict) else 0.0)
        )
        return round(float(val or 0.0), 2)
    top_sheet = getattr(bid, "top_sheet", None)
    val = (
        getattr(bid, "grand_total_usd", 0.0)
        or getattr(bid, "grand_total", 0.0)
        or getattr(top_sheet, "grand_total_bid_usd", 0.0)
        or getattr(top_sheet, "grand_total_bid", 0.0)
        or getattr(top_sheet, "grand_total", 0.0)
    )
    return round(float(val or 0.0), 2)


def _extract_render_economics_totals(bible: MasterProductionBible) -> Tuple[float, float, float]:
    """Returns (estimated_total_compute_usd, dry_run_billable_usd, savings_vs_aicp_pct)."""
    econ = getattr(bible, "master_render_economics_spec", None)
    if econ is None:
        scenes_count = len(getattr(bible, "scenes", None) or [])
        est = round(max(1.0, scenes_count * 3.2), 2)
        return est, 0.0, 0.0
    if isinstance(econ, dict):
        guard = econ.get("guardrail") or {}
        est = float(guard.get("estimated_total_usd") or econ.get("estimated_total_compute_usd") or 0.0)
        dry = float(econ.get("dry_run_billable_usd") or 0.0)
        pct = float(guard.get("simulation_savings_vs_aicp_pct") or 0.0)
        return round(est, 4), round(dry, 4), round(pct, 2)
    guard = getattr(econ, "guardrail", None)
    est = float(getattr(guard, "estimated_total_usd", 0.0) or 0.0)
    if est <= 0.0:
        scene_ests = list(getattr(econ, "scene_estimates", None) or [])
        est = sum(float(getattr(s, "estimated_scene_usd", 0.0) or 0.0) for s in scene_ests)
    dry = float(getattr(econ, "dry_run_billable_usd", 0.0) or 0.0)
    pct = float(getattr(guard, "simulation_savings_vs_aicp_pct", 0.0) or 0.0)
    return round(est, 4), round(dry, 4), round(pct, 2)


def _resolve_client_brand(bible: MasterProductionBible) -> str:
    bid = getattr(bible, "master_aicp_bid", None) or getattr(bible, "aicp_bid", None)
    if bid is not None:
        brand = getattr(bid, "client_brand", None) or getattr(bid, "client", None)
        if brand and str(brand).strip() not in ("Commercial Brand", "Commercial Client"):
            return str(brand).strip()
    title = str(getattr(bible, "project_title", "") or "")
    if ":" in title:
        prefix = title.split(":", 1)[0].strip()
        if prefix and len(prefix) <= 32:
            return prefix
    return "Brand Partner"


def _resolve_bible_and_council_score(payload: Any) -> Tuple[MasterProductionBible, Optional[float]]:
    """Resolves MasterProductionBible and optional council_report.overall_score from Bible/Bundle/Path/dict."""
    council_score: Optional[float] = None
    if isinstance(payload, ProductionBundle):
        if payload.council_report is not None:
            council_score = float(payload.council_report.overall_score)
        return payload.bible, council_score
    if isinstance(payload, MasterProductionBible):
        return payload, None

    raw_dict: Optional[Dict[str, Any]] = None
    if isinstance(payload, dict):
        raw_dict = payload
    elif isinstance(payload, (str, Path)):
        p = Path(payload)
        if p.is_file():
            raw_dict = json.loads(p.read_text(encoding="utf-8"))
        else:
            raw_str = str(payload).strip()
            if raw_str.startswith("{"):
                raw_dict = json.loads(raw_str)

    if isinstance(raw_dict, dict):
        cr = raw_dict.get("council_report")
        if isinstance(cr, dict) and cr.get("overall_score") is not None:
            council_score = float(cr["overall_score"])
        elif cr is not None and hasattr(cr, "overall_score"):
            council_score = float(cr.overall_score)

    return load_bible_from_json(payload), council_score


def _canonical_bible_sha256(bible: MasterProductionBible) -> str:
    dumped = bible.model_dump(mode="json")
    canonical = json.dumps(dumped, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def diff_production_bibles(baseline: Any, target: Any) -> BibleRevisionDiffReport:
    """Computes a structured SHA-256 and field-level revision diff between two ProductionBibles or Bundles."""
    base_bible, base_council = _resolve_bible_and_council_score(baseline)
    targ_bible, targ_council = _resolve_bible_and_council_score(target)

    base_sha = _canonical_bible_sha256(base_bible)
    targ_sha = _canonical_bible_sha256(targ_bible)

    deltas: List[BibleRevisionDeltaItem] = []

    def _add_delta(
        section: str,
        field_path: str,
        prev_val: Any,
        curr_val: Any,
        severity: str = "low",
        owner: str = "Direction",
        change_type: str = "modified",
    ) -> None:
        deltas.append(
            BibleRevisionDeltaItem(
                section=section,
                field_path=field_path,
                change_type=change_type,  # type: ignore[arg-type]
                previous_value=str(prev_val),
                current_value=str(curr_val),
                impact_severity=severity,  # type: ignore[arg-type]
                department_owner=owner,
            )
        )

    # 1. Core metadata & direction invariants
    if base_bible.project_title != targ_bible.project_title:
        _add_delta(
            "Metadata",
            "project_title",
            base_bible.project_title,
            targ_bible.project_title,
            severity="medium",
            owner="Direction",
        )

    base_regime = _enum_str(base_bible.creative_regime)
    targ_regime = _enum_str(targ_bible.creative_regime)
    if base_regime != targ_regime:
        _add_delta(
            "Direction",
            "creative_regime",
            base_regime,
            targ_regime,
            severity="high",
            owner="Direction",
        )

    base_mode = _enum_str(base_bible.storytelling_mode)
    targ_mode = _enum_str(targ_bible.storytelling_mode)
    if base_mode != targ_mode:
        _add_delta(
            "Direction",
            "storytelling_mode",
            base_mode,
            targ_mode,
            severity="high",
            owner="Editorial",
        )

    base_ar = _enum_str(base_bible.aspect_ratio)
    targ_ar = _enum_str(targ_bible.aspect_ratio)
    if base_ar != targ_ar:
        _add_delta(
            "Delivery",
            "aspect_ratio",
            base_ar,
            targ_ar,
            severity="high",
            owner="Camera",
        )

    # 2. Master lighting Kelvin
    base_kelvin = _extract_kelvin_from_bible(base_bible)
    targ_kelvin = _extract_kelvin_from_bible(targ_bible)
    if base_kelvin != targ_kelvin:
        _add_delta(
            "Lighting",
            "master_lighting_rig.key_cct_kelvin",
            f"{base_kelvin}K",
            f"{targ_kelvin}K",
            severity="medium",
            owner="Gaffer / Lighting",
        )

    # 3. Master camera focal length
    base_master_mm = (
        getattr(base_bible.camera_rig, "focal_length_mm", None)
        if base_bible.camera_rig is not None
        else None
    )
    targ_master_mm = (
        getattr(targ_bible.camera_rig, "focal_length_mm", None)
        if targ_bible.camera_rig is not None
        else None
    )
    if base_master_mm != targ_master_mm:
        _add_delta(
            "Camera",
            "camera_rig.focal_length_mm",
            f"{base_master_mm}mm" if base_master_mm is not None else "unset",
            f"{targ_master_mm}mm" if targ_master_mm is not None else "unset",
            severity="medium",
            owner="Cinematography",
        )

    # 4. Per-scene prompt, focal length, and lighting Kelvin
    base_scenes = {int(sc.scene_index): sc for sc in (base_bible.scenes or [])}
    targ_scenes = {int(sc.scene_index): sc for sc in (targ_bible.scenes or [])}
    all_scene_indices = sorted(set(base_scenes.keys()) | set(targ_scenes.keys()))

    scene_prompt_deltas_count = 0
    for idx_pos, sc_idx in enumerate(all_scene_indices):
        b_sc = base_scenes.get(sc_idx)
        t_sc = targ_scenes.get(sc_idx)
        sec_label = f"Scene {sc_idx:02d}"
        if b_sc is None and t_sc is not None:
            scene_prompt_deltas_count += 1
            _add_delta(
                sec_label,
                f"scenes[{idx_pos}].omni_prose_prompt",
                "(absent)",
                (t_sc.omni_prose_prompt or t_sc.scene_title)[:140],
                severity="high",
                owner="Prompt Engineering",
                change_type="added",
            )
            continue
        if t_sc is None and b_sc is not None:
            scene_prompt_deltas_count += 1
            _add_delta(
                sec_label,
                f"scenes[{idx_pos}].omni_prose_prompt",
                (b_sc.omni_prose_prompt or b_sc.scene_title)[:140],
                "(removed)",
                severity="high",
                owner="Prompt Engineering",
                change_type="removed",
            )
            continue
        assert b_sc is not None and t_sc is not None

        if (b_sc.omni_prose_prompt or "").strip() != (t_sc.omni_prose_prompt or "").strip():
            scene_prompt_deltas_count += 1
            _add_delta(
                sec_label,
                f"scenes[{idx_pos}].omni_prose_prompt",
                (b_sc.omni_prose_prompt or "")[:140],
                (t_sc.omni_prose_prompt or "")[:140],
                severity="high",
                owner="Prompt Engineering",
            )

        b_mm = _extract_scene_focal_mm(b_sc, base_bible)
        t_mm = _extract_scene_focal_mm(t_sc, targ_bible)
        if b_mm != t_mm:
            _add_delta(
                sec_label,
                f"scenes[{idx_pos}].craft_camera.lens_mm",
                f"{b_mm}mm",
                f"{t_mm}mm",
                severity="medium",
                owner="Cinematography",
            )

        b_sc_k = _extract_scene_kelvin(b_sc, base_kelvin)
        t_sc_k = _extract_scene_kelvin(t_sc, targ_kelvin)
        if b_sc_k != t_sc_k:
            _add_delta(
                sec_label,
                f"scenes[{idx_pos}].lighting_rig.cct_kelvin",
                f"{b_sc_k}K",
                f"{t_sc_k}K",
                severity="medium",
                owner="Gaffer / Lighting",
            )

    # 5. AICP Bid grand_total_usd
    base_aicp = _extract_aicp_total_usd(base_bible)
    targ_aicp = _extract_aicp_total_usd(targ_bible)
    aicp_delta = round(targ_aicp - base_aicp, 2)
    if abs(aicp_delta) > 0.009:
        _add_delta(
            "Production Economics",
            "master_aicp_bid.grand_total_usd",
            f"${base_aicp:,.2f}",
            f"${targ_aicp:,.2f}",
            severity="medium",
            owner="Line Producer",
        )

    # 6. Render Economics estimated_total_compute_usd
    base_compute, _, _ = _extract_render_economics_totals(base_bible)
    targ_compute, _, _ = _extract_render_economics_totals(targ_bible)
    compute_delta = round(targ_compute - base_compute, 4)
    if abs(compute_delta) > 0.0001:
        _add_delta(
            "Render Economics",
            "render_economics.estimated_total_compute_usd",
            f"${base_compute:,.4f}",
            f"${targ_compute:,.4f}",
            severity="low",
            owner="AI Compute",
        )

    # 7. Council Score delta (if ProductionBundles compared)
    council_score_delta: Optional[float] = None
    if base_council is not None and targ_council is not None:
        council_score_delta = round(targ_council - base_council, 2)
        if abs(council_score_delta) > 0.009:
            _add_delta(
                "Governance",
                "council_report.overall_score",
                f"{base_council:.2f}/100",
                f"{targ_council:.2f}/100",
                severity="medium",
                owner="Product Council",
            )

    return BibleRevisionDiffReport(
        baseline_title=base_bible.project_title,
        target_title=targ_bible.project_title,
        baseline_sha256=base_sha,
        target_sha256=targ_sha,
        total_changes=len(deltas),
        scene_prompt_deltas_count=scene_prompt_deltas_count,
        aicp_budget_delta_usd=aicp_delta,
        render_compute_delta_usd=compute_delta,
        council_score_delta=council_score_delta,
        deltas=deltas,
    )


def format_pitch_treatment_token(
    slide_spec: TreatmentBoardSlideSpec,
    treatment: MasterPitchTreatmentSpec,
) -> str:
    """Formats deterministic PM-FEAT-036 machine telemetry token for a treatment slide."""
    idx = slide_spec.scene_index if slide_spec.scene_index is not None else slide_spec.slide_index
    slide_type = _enum_str(slide_spec.slide_type, "scene_beat_spread")

    executive_tone = ""
    for sl in getattr(treatment, "slides", None) or []:
        tone_cand = (getattr(sl, "key_metrics", None) or {}).get("executive_tone")
        if tone_cand:
            executive_tone = str(tone_cand)
            break
    if not executive_tone:
        domain_key = str(getattr(treatment, "domain_archetype", "architectural_sanctuary") or "architectural_sanctuary")
        cal = _resolve_domain_calibration(domain_key)
        executive_tone = str(cal.get("executive_tone") or "Executive Cinema")
    clean_tone = executive_tone.replace("|", "/").replace("\n", " ").strip()

    raw_hook = str(getattr(treatment, "target_audience_hook", "") or slide_spec.subhead or slide_spec.headline or "")
    clean_hook = raw_hook.replace("|", "/").replace("\n", " ").strip()
    if len(clean_hook) > 64:
        clean_hook = clean_hook[:61].rstrip() + "..."

    return f"[TREATMENT-BEAT: SC{int(idx):02d} | slide={slide_type} | tone={clean_tone} | hook={clean_hook}]"


def compile_pitch_treatment(
    bible: MasterProductionBible,
    domain_calibration: Optional[Dict[str, Any]] = None,
    baseline_bible: Optional[Any] = None,
) -> MasterPitchTreatmentSpec:
    """Compiles a complete Executive Director's Treatment & Pitch Lookbook manifest (PM-FEAT-036)."""
    domain_key = _resolve_domain_key(bible)
    cal = _resolve_domain_calibration(domain_key, domain_calibration=domain_calibration)

    executive_tone = str(cal.get("executive_tone") or "Executive Commercial Direction")
    audience_hook = str(cal.get("audience_hook") or bible.logline)
    hero_kpi_focus = str(cal.get("hero_kpi_focus") or "Brand Recall & Visual Continuity")

    regime_val = _enum_str(getattr(bible, "creative_regime", None), "Regime 1: Photorealism")
    mode_val = _enum_str(getattr(bible, "storytelling_mode", None), "Mode A: Parallel Cuts")
    aspect_val = _enum_str(getattr(bible, "aspect_ratio", None), "16:9")
    runtime_sec = int(getattr(bible, "total_runtime_seconds", 32) or 32)
    client_brand = _resolve_client_brand(bible)

    template = str(
        cal.get("director_statement_template")
        or "{project_title} unites {regime} craft with {mode} rhythm across {runtime}s to deliver {kpi}."
    )
    try:
        director_statement = template.format(
            project_title=bible.project_title,
            logline=bible.logline,
            domain=domain_key,
            regime=regime_val,
            mode=mode_val,
            runtime=runtime_sec,
            tone=executive_tone,
            kpi=hero_kpi_focus,
        )
    except Exception:
        director_statement = (
            f"{bible.project_title} delivers {executive_tone} under {regime_val} ({mode_val}) "
            f"across {runtime_sec}s, focused on {hero_kpi_focus}."
        )

    swatches = _derive_color_script_swatches(bible, cal)
    kelvin = _extract_kelvin_from_bible(bible)
    color_look = getattr(bible, "color_look", None) or getattr(bible, "master_color_look", None)
    look_label = _enum_str(getattr(color_look, "look_preset", None), "rec709_neutral") if color_look else "rec709_neutral"
    working_space = str(getattr(color_look, "working_color_space", "ACEScg") if color_look else "ACEScg")

    assets = list(getattr(bible, "nano_banana_assets", None) or [])
    cover_plate_ref = assets[0].local_path or assets[0].asset_id if assets else "<image_1>"

    slides: List[TreatmentBoardSlideSpec] = []
    slide_cursor = 1

    # Slide 1: Cover & Logline
    slides.append(
        TreatmentBoardSlideSpec(
            slide_index=slide_cursor,
            slide_type=TreatmentSlideTypeEnum.COVER_LOGLINE,
            headline=bible.project_title,
            subhead=f"{client_brand} · {domain_key} · {executive_tone}",
            narrative_copy=bible.logline,
            visual_plate_ref=str(cover_plate_ref),
            color_swatches=swatches,
            key_metrics={
                "client_brand": client_brand,
                "runtime": f"{runtime_sec}s",
                "aspect_ratio": aspect_val,
                "storytelling_mode": mode_val,
                "executive_tone": executive_tone,
            },
        )
    )
    slide_cursor += 1

    # Slide 2: Creative Vision & Regime
    slides.append(
        TreatmentBoardSlideSpec(
            slide_index=slide_cursor,
            slide_type=TreatmentSlideTypeEnum.CREATIVE_VISION_REGIME,
            headline="Creative Vision & Storytelling Regime",
            subhead=f"{regime_val} · {mode_val}",
            narrative_copy=director_statement,
            visual_plate_ref=str(assets[0].asset_id if assets else "<image_1>"),
            color_swatches=swatches[:4],
            key_metrics={
                "creative_regime": regime_val,
                "storytelling_mode": mode_val,
                "executive_tone": executive_tone,
                "hero_kpi_focus": hero_kpi_focus,
                "audience_hook": audience_hook,
            },
        )
    )
    slide_cursor += 1

    # Slide 3: Color Script & Look Science
    slides.append(
        TreatmentBoardSlideSpec(
            slide_index=slide_cursor,
            slide_type=TreatmentSlideTypeEnum.COLOR_SCRIPT_PALETTE,
            headline="Color Script & Optical Look Science",
            subhead=f"Look: {look_label} · {working_space} · {kelvin}K Key",
            narrative_copy=(
                f"Master palette {', '.join(swatches)} calibrated in {working_space} with "
                f"{look_label} tonal curve and {kelvin}K primary illumination."
            ),
            visual_plate_ref="COLOR_SCRIPT_STRIP",
            color_swatches=swatches,
            key_metrics={
                "look_preset": look_label,
                "working_color_space": working_space,
                "key_kelvin": f"{kelvin}K",
                "swatch_count": str(len(swatches)),
            },
        )
    )
    slide_cursor += 1

    # Slide 4: Cast & Wardrobe Polarity
    characters = list(getattr(bible, "characters", None) or [])
    if characters:
        cast_summary = " | ".join(
            f"{c.name}: {c.silhouette} (Wardrobe Polarity: {c.wardrobe_polarity}; Motion: {c.movement_signature})"
            for c in characters
        )
        cast_plate = characters[0].image_path or characters[0].name
    else:
        hero_ref_desc = assets[0].job_description if assets else "Hero subject product design & surface finish"
        cast_summary = f"Product-led hero subject: {hero_ref_desc}. Strict material polarity lock enforced across all cuts."
        cast_plate = str(assets[0].local_path or assets[0].asset_id) if assets else "<image_1>"

    slides.append(
        TreatmentBoardSlideSpec(
            slide_index=slide_cursor,
            slide_type=TreatmentSlideTypeEnum.CAST_WARDROBE_POLARITY,
            headline="Cast, Hero Subject & Wardrobe Polarity",
            subhead=f"{len(characters)} Character Anchor(s) · {len(assets)}/3 Nano Banana References",
            narrative_copy=cast_summary,
            visual_plate_ref=str(cast_plate),
            color_swatches=swatches[:3],
            key_metrics={
                "characters_count": str(len(characters)),
                "nano_banana_refs": f"{len(assets)}/3",
                "polarity_lock": "ENFORCED",
            },
        )
    )
    slide_cursor += 1

    # Slide 5: Environment Plates
    env = bible.environment
    invariants_txt = "; ".join(env.positive_invariants[:3]) if env.positive_invariants else "Rigid architectural geometry"
    env_plate = env.image_path or (assets[1].local_path or assets[1].asset_id if len(assets) > 1 else "ENV_MASTER_PLATE")
    slides.append(
        TreatmentBoardSlideSpec(
            slide_index=slide_cursor,
            slide_type=TreatmentSlideTypeEnum.ENVIRONMENT_PLATES,
            headline=f"Master Environment — {env.location_name}",
            subhead=f"Key Light {kelvin}K · {len(env.positive_invariants)} Geometric Invariants",
            narrative_copy=(
                f"{env.spatial_architecture} Lighting: {env.lighting_setup} "
                f"Atmosphere: {env.atmospheric_particles} Invariants: {invariants_txt}"
            ),
            visual_plate_ref=str(env_plate),
            color_swatches=swatches[:4],
            key_metrics={
                "location": env.location_name,
                "kelvin": f"{kelvin}K",
                "invariants": str(len(env.positive_invariants)),
            },
        )
    )
    slide_cursor += 1

    # Slides 6..N: One scene_beat_spread slide per scene in bible.scenes
    scenes = list(getattr(bible, "scenes", None) or [])
    for sc in scenes:
        sc_idx = int(getattr(sc, "scene_index", 1) or 1)
        sc_regime = _enum_str(getattr(sc, "regime", None), regime_val)
        sc_lens = _extract_scene_focal_mm(sc, bible=bible)
        sc_kelvin = _extract_scene_kelvin(sc, kelvin)
        beats = list(getattr(sc, "action_beats", None) or [])
        beat_text = " -> ".join(beats) if beats else (sc.omni_prose_prompt[:220] if sc.omni_prose_prompt else sc.scene_title)
        chain_text = f" Kinetic Chain: {sc.kinetic_contact_chain}" if sc.kinetic_contact_chain else ""
        kf = getattr(sc, "keyframe_spec", None) or getattr(sc, "scene_keyframe", None)
        kf_ref = getattr(kf, "image_path", None) if kf is not None else None
        plate_ref = str(kf_ref or f"SC{sc_idx:02d}_KEYFRAME")

        slides.append(
            TreatmentBoardSlideSpec(
                slide_index=slide_cursor,
                slide_type=TreatmentSlideTypeEnum.SCENE_BEAT_SPREAD,
                scene_index=sc_idx,
                headline=f"SC{sc_idx:02d}: {sc.scene_title}",
                subhead=f"{sc.timestamp_range} · {sc_regime} · {sc_lens}mm · {sc_kelvin}K",
                narrative_copy=f"{beat_text}{chain_text}",
                visual_plate_ref=plate_ref,
                color_swatches=swatches[:4],
                key_metrics={
                    "scene_index": str(sc_idx),
                    "timestamp_range": sc.timestamp_range,
                    "lens_mm": f"{sc_lens}mm",
                    "kelvin": f"{sc_kelvin}K",
                    "beats_count": str(len(beats)),
                    "regime": sc_regime,
                },
            )
        )
        slide_cursor += 1

    # Sonic & BGM Arc slide
    bgm = bible.master_bgm
    sonic = bible.sonic_blueprint
    foley_preview = "; ".join(sonic.foley_cues[:4]) if sonic.foley_cues else "Diegetic tactile contact foley"
    stems_summary = ", ".join(f"{k}: {v}" for k, v in list((bgm.stems or {}).items())[:4])
    slides.append(
        TreatmentBoardSlideSpec(
            slide_index=slide_cursor,
            slide_type=TreatmentSlideTypeEnum.SONIC_BGM_ARC,
            headline=f"Sonic Architecture & BGM Arc — {bgm.track_title}",
            subhead=f"{bgm.genre_style} · {bgm.tempo_bpm} BPM · {bgm.key_signature}",
            narrative_copy=(
                f"Dynamic Arc: {bgm.dynamic_arc} | Diegetic Foley: {foley_preview} | "
                f"Room Acoustics: {sonic.room_acoustics} | Stems: {stems_summary}"
            ),
            visual_plate_ref="SONIC_BGM_ARC",
            color_swatches=swatches[:3],
            key_metrics={
                "track_title": bgm.track_title,
                "tempo_bpm": str(bgm.tempo_bpm),
                "key_signature": bgm.key_signature,
                "foley_cues": str(len(sonic.foley_cues)),
                "stems_count": str(len(bgm.stems or {})),
            },
        )
    )
    slide_cursor += 1

    # Budget & AI-vs-AICP ROI Summary slide
    aicp_total = _extract_aicp_total_usd(bible)
    if aicp_total <= 0.0:
        aicp_total = round(max(24000.0, len(scenes) * 11500.0), 2)
    ai_compute_usd, dry_run_usd, econ_savings_pct = _extract_render_economics_totals(bible)
    if ai_compute_usd <= 0.0:
        ai_compute_usd = round(max(1.2, len(scenes) * 3.15), 2)
    net_savings_usd = round(max(0.0, aicp_total - ai_compute_usd), 2)
    savings_pct = econ_savings_pct if econ_savings_pct > 0.0 else round(
        max(0.0, (1.0 - (ai_compute_usd / max(1.0, aicp_total))) * 100.0),
        2,
    )

    slides.append(
        TreatmentBoardSlideSpec(
            slide_index=slide_cursor,
            slide_type=TreatmentSlideTypeEnum.BUDGET_ROI_SUMMARY,
            headline="Production Economics: AI-First vs. Traditional AICP Bid",
            subhead=f"AICP Baseline ${aicp_total:,.2f} vs. AI Live Compute ${ai_compute_usd:,.2f} ({savings_pct:.2f}% Savings)",
            narrative_copy=(
                f"Traditional AICP commercial shoot baseline is estimated at ${aicp_total:,.2f}. "
                f"Omni 2026 Matrix simulation mode executes at ${dry_run_usd:.2f} billable cost, while "
                f"planned multi-take live rendering totals ${ai_compute_usd:,.2f} — capturing "
                f"${net_savings_usd:,.2f} ({savings_pct:.2f}%) in production capital efficiency."
            ),
            visual_plate_ref="BUDGET_ROI_SUMMARY",
            color_swatches=swatches[:3],
            key_metrics={
                "aicp_grand_total_usd": f"${aicp_total:,.2f}",
                "ai_compute_est_usd": f"${ai_compute_usd:,.2f}",
                "dry_run_billable_usd": f"${dry_run_usd:,.2f}",
                "net_savings_usd": f"${net_savings_usd:,.2f}",
                "savings_pct": f"{savings_pct:.2f}%",
            },
        )
    )
    slide_cursor += 1

    # Deliverables & Sign-Off slide
    slides.append(
        TreatmentBoardSlideSpec(
            slide_index=slide_cursor,
            slide_type=TreatmentSlideTypeEnum.DELIVERABLES_SIGNOFF,
            headline="Deliverables Matrix & Executive Greenlight",
            subhead=f"2026 Gemini Model Matrix · {aspect_val} · {runtime_sec}s @ 24fps",
            narrative_copy=(
                "Approved deliverables package includes: immutable MasterProductionBible SSOT JSON, "
                "interactive dark-room Cinema Animatic HTML5, SMPTE EDL/FCPXML/SRT/VTT timelines, "
                "OpenTimelineIO (.otio) cross-department coherence manifest, C2PA provenance manifest, "
                "and print-ready Executive Director's Lookbook."
            ),
            visual_plate_ref="DELIVERABLES_SIGNOFF",
            color_swatches=swatches,
            key_metrics={
                "hero_kpi_focus": hero_kpi_focus,
                "scenes_count": str(len(scenes)),
                "model_matrix": "2026-Compliant",
                "signoff_status": "READY_FOR_GREENLIGHT",
            },
        )
    )

    revision_diff: Optional[BibleRevisionDiffReport] = None
    if baseline_bible is not None:
        revision_diff = diff_production_bibles(baseline_bible, bible)

    id_seed = f"{bible.project_title}:{domain_key}:{len(scenes)}:{runtime_sec}"
    treatment_id = f"pt-{hashlib.sha256(id_seed.encode('utf-8')).hexdigest()[:10]}"
    treatment_token = (
        f"[PITCH-TREATMENT: id={treatment_id} | domain={domain_key} | "
        f"slides={len(slides)} | tone={executive_tone} | roi_savings={savings_pct:.1f}%]"
    )

    return MasterPitchTreatmentSpec(
        treatment_id=treatment_id,
        project_title=bible.project_title,
        client_brand_label=client_brand,
        domain_archetype=domain_key,
        executive_director_statement=director_statement,
        target_audience_hook=audience_hook,
        slides=slides,
        color_script_strip=swatches,
        revision_diff=revision_diff,
        treatment_token=treatment_token,
    )


def _sanitize_svg_markup(raw_svg: str) -> str:
    """Strips script tags and inline event handlers from embedded SVG markup."""
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", raw_svg, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\son\w+\s*=\s*(['\"]).*?\1", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    return cleaned


def _fallback_plate_svg(label: str, swatches: List[str]) -> str:
    bg = swatches[0] if len(swatches) > 0 else "#0F172A"
    accent = swatches[2] if len(swatches) > 2 else "#38BDF8"
    warm = swatches[1] if len(swatches) > 1 else "#F59E0B"
    safe_label = html.escape(label[:48])
    return (
        f'<svg viewBox="0 0 640 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{safe_label}">'
        f'<defs><linearGradient id="ptGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{html.escape(bg)}"/><stop offset="100%" stop-color="#1E293B"/></linearGradient></defs>'
        f'<rect width="640" height="360" fill="url(#ptGrad)" rx="8"/>'
        f'<rect x="24" y="24" width="592" height="312" fill="none" stroke="{html.escape(accent)}" stroke-opacity="0.45" stroke-width="1.5" stroke-dasharray="6 4"/>'
        f'<line x1="213" y1="24" x2="213" y2="336" stroke="#FFFFFF" stroke-opacity="0.12"/>'
        f'<line x1="426" y1="24" x2="426" y2="336" stroke="#FFFFFF" stroke-opacity="0.12"/>'
        f'<line x1="24" y1="128" x2="616" y2="128" stroke="#FFFFFF" stroke-opacity="0.12"/>'
        f'<line x1="24" y1="232" x2="616" y2="232" stroke="#FFFFFF" stroke-opacity="0.12"/>'
        f'<circle cx="320" cy="180" r="46" fill="none" stroke="{html.escape(warm)}" stroke-width="2" stroke-opacity="0.75"/>'
        f'<text x="320" y="185" text-anchor="middle" fill="#F8FAFC" font-family="ui-monospace, monospace" font-size="15">{safe_label}</text>'
        f'<text x="40" y="320" fill="{html.escape(accent)}" font-family="ui-monospace, monospace" font-size="11">OMNI 2026 NANO BANANA PLATE</text>'
        f'</svg>'
    )


def _render_lookbook_plate(plate_candidate: Optional[str], label: str, swatches: List[str]) -> str:
    val = str(plate_candidate or "").strip()
    if "<svg" in val.lower():
        start = val.lower().find("<svg")
        return _sanitize_svg_markup(val[start:])
    if val:
        try:
            p = Path(val)
            if p.is_file():
                suf = p.suffix.lower()
                if suf == ".svg":
                    txt = p.read_text(encoding="utf-8")
                    if "<svg" in txt.lower():
                        return _sanitize_svg_markup(txt[txt.lower().find("<svg"):])
                elif suf in (".png", ".jpg", ".jpeg", ".webp"):
                    mime = "image/png" if suf == ".png" else ("image/webp" if suf == ".webp" else "image/jpeg")
                    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
                    return f'<img src="data:{mime};base64,{b64}" alt="{html.escape(label)}" class="plate-img" />'
        except Exception:
            pass
    return _fallback_plate_svg(label, swatches)


def _resolve_slide_plate_html(
    slide: TreatmentBoardSlideSpec,
    bible: MasterProductionBible,
    swatches: List[str],
) -> str:
    stype = slide.slide_type
    assets = list(getattr(bible, "nano_banana_assets", None) or [])
    chars = list(getattr(bible, "characters", None) or [])
    scenes = list(getattr(bible, "scenes", None) or [])
    env = getattr(bible, "environment", None)

    if stype == TreatmentSlideTypeEnum.CAST_WARDROBE_POLARITY:
        if chars:
            cand = chars[0].svg_markup or chars[0].image_path
            return _render_lookbook_plate(cand, f"Character: {chars[0].name}", swatches)
        if assets:
            cand = assets[0].svg_markup or assets[0].local_path
            return _render_lookbook_plate(cand, assets[0].asset_id, swatches)

    if stype == TreatmentSlideTypeEnum.ENVIRONMENT_PLATES:
        if env is not None:
            cand = env.svg_markup or env.image_path
            if cand:
                return _render_lookbook_plate(cand, env.location_name, swatches)
        if len(assets) > 1:
            cand = assets[1].svg_markup or assets[1].local_path
            return _render_lookbook_plate(cand, assets[1].asset_id, swatches)

    if stype == TreatmentSlideTypeEnum.SCENE_BEAT_SPREAD and slide.scene_index is not None:
        matched_sc = next((s for s in scenes if s.scene_index == slide.scene_index), None)
        if matched_sc is not None:
            kf = getattr(matched_sc, "keyframe_spec", None) or getattr(matched_sc, "scene_keyframe", None)
            if kf is not None:
                cand = getattr(kf, "svg_markup", None) or getattr(kf, "image_path", None)
                if cand:
                    return _render_lookbook_plate(cand, f"SC{slide.scene_index:02d} Keyframe", swatches)
        if assets:
            asset = assets[(slide.scene_index - 1) % len(assets)]
            cand = asset.svg_markup or asset.local_path
            return _render_lookbook_plate(cand, f"SC{slide.scene_index:02d} · {asset.asset_id}", swatches)

    if stype in (TreatmentSlideTypeEnum.COVER_LOGLINE, TreatmentSlideTypeEnum.CREATIVE_VISION_REGIME) and assets:
        cand = assets[0].svg_markup or assets[0].local_path
        return _render_lookbook_plate(cand, slide.headline, swatches)

    return _render_lookbook_plate(slide.visual_plate_ref, slide.headline, swatches)


def export_treatment_lookbook_html(
    manifest: MasterPitchTreatmentSpec,
    bible: MasterProductionBible,
) -> str:
    """Exports a self-contained, printable HTML5 Executive Director's Treatment Lookbook (PM-FEAT-036)."""
    esc = html.escape
    swatches = list(manifest.color_script_strip or _DEFAULT_SCHEMA_PALETTE)
    primary_accent = _normalize_hex(swatches[2] if len(swatches) > 2 else swatches[0]) or "#38BDF8"
    warm_accent = _normalize_hex(swatches[1] if len(swatches) > 1 else swatches[0]) or "#F59E0B"

    swatch_strip_html = "".join(
        f'<div class="swatch-chip"><span class="swatch-color" style="background:{esc(hx)};"></span>'
        f'<span class="swatch-code">{esc(hx)}</span></div>'
        for hx in swatches
    )

    # Nano Banana Gallery summary cards
    nb_cards: List[str] = []
    for asset in list(getattr(bible, "nano_banana_assets", None) or []):
        plate_html = _render_lookbook_plate(
            asset.svg_markup or asset.local_path,
            asset.asset_id,
            swatches,
        )
        nb_cards.append(
            f'<div class="nb-card">'
            f'<div class="nb-plate">{plate_html}</div>'
            f'<div class="nb-meta"><strong>{esc(asset.asset_id)}</strong>'
            f'<p>{esc(asset.job_description)}</p></div>'
            f'</div>'
        )
    nb_gallery_html = "".join(nb_cards)

    # Render each presentation slide with page-break-after: always
    slide_sections: List[str] = []
    for slide in manifest.slides:
        stype_val = _enum_str(slide.slide_type)
        plate_html = _resolve_slide_plate_html(slide, bible, swatches)
        slide_swatches_html = "".join(
            f'<span class="mini-swatch" style="background:{esc(c)};" title="{esc(c)}"></span>'
            for c in (slide.color_swatches or swatches)
        )
        metrics_html = "".join(
            f'<div class="metric-pill"><span class="metric-k">{esc(str(k))}</span>'
            f'<span class="metric-v">{esc(str(v))}</span></div>'
            for k, v in (slide.key_metrics or {}).items()
        )
        token_str = format_pitch_treatment_token(slide, manifest)

        extra_block = ""
        if slide.slide_type == TreatmentSlideTypeEnum.COVER_LOGLINE and nb_gallery_html:
            extra_block = f'<div class="nb-strip">{nb_gallery_html}</div>'
        elif slide.slide_type == TreatmentSlideTypeEnum.SONIC_BGM_ARC:
            bgm = bible.master_bgm
            stems_li = "".join(
                f"<li><strong>{esc(str(k))}:</strong> {esc(str(v))}</li>"
                for k, v in (bgm.stems or {}).items()
            )
            extra_block = (
                f'<div class="sonic-box">'
                f'<div><strong>Lyria Prompt:</strong> {esc(bgm.lyria_prompt)}</div>'
                f'<ul class="stem-list">{stems_li}</ul>'
                f'</div>'
            )

        slide_sections.append(
            f'<section class="lookbook-slide" data-slide-type="{esc(stype_val)}">'
            f'  <header class="slide-header">'
            f'    <div class="slide-kicker">BOARD {slide.slide_index:02d} · {esc(stype_val.upper())}</div>'
            f'    <div class="slide-swatches">{slide_swatches_html}</div>'
            f'  </header>'
            f'  <div class="slide-body">'
            f'    <div class="slide-copy">'
            f'      <h2>{esc(slide.headline)}</h2>'
            f'      <p class="slide-subhead">{esc(slide.subhead)}</p>'
            f'      <p class="slide-narrative">{esc(slide.narrative_copy)}</p>'
            f'      <div class="metrics-grid">{metrics_html}</div>'
            f'      {extra_block}'
            f'    </div>'
            f'    <div class="slide-plate-wrap">{plate_html}</div>'
            f'  </div>'
            f'  <footer class="slide-footer">'
            f'    <span>{esc(manifest.project_title)} — {esc(manifest.client_brand_label)}</span>'
            f'    <code>{esc(token_str)}</code>'
            f'  </footer>'
            f'</section>'
        )

    diff_html = ""
    if manifest.revision_diff is not None:
        rd = manifest.revision_diff
        rows_html = "".join(
            f"<tr><td>{esc(d.section)}</td><td><code>{esc(d.field_path)}</code></td>"
            f"<td>{esc(d.change_type)}</td><td>{esc(d.previous_value)}</td>"
            f"<td>{esc(d.current_value)}</td><td>{esc(d.impact_severity)}</td></tr>"
            for d in rd.deltas
        )
        if not rows_html:
            rows_html = '<tr><td colspan="6">No structural deltas detected between baseline and target revisions.</td></tr>'
        diff_html = (
            f'<section class="lookbook-slide revision-diff-slide">'
            f'  <header class="slide-header"><div class="slide-kicker">BIBLE REVISION DIFF</div>'
            f'  <div class="slide-kicker">{rd.total_changes} TOTAL CHANGES</div></header>'
            f'  <h2>Revision Comparison: {esc(rd.baseline_title)} → {esc(rd.target_title)}</h2>'
            f'  <p class="slide-subhead">Baseline SHA-256: <code>{esc(rd.baseline_sha256[:16])}</code> · '
            f'Target SHA-256: <code>{esc(rd.target_sha256[:16])}</code> · '
            f'AICP Delta: ${rd.aicp_budget_delta_usd:+,.2f} · Compute Delta: ${rd.render_compute_delta_usd:+,.4f}</p>'
            f'  <table class="diff-table"><thead><tr><th>Section</th><th>Field</th><th>Type</th>'
            f'<th>Baseline</th><th>Target</th><th>Severity</th></tr></thead>'
            f'  <tbody>{rows_html}</tbody></table>'
            f'</section>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(manifest.project_title)} — Executive Director's Lookbook</title>
  <style>
    :root {{
      --bg-cinema: #090C12;
      --bg-panel: #111622;
      --border-subtle: rgba(148, 163, 184, 0.22);
      --ink-primary: #F8FAFC;
      --ink-secondary: #94A3B8;
      --accent-primary: {esc(primary_accent)};
      --accent-warm: {esc(warm_accent)};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--bg-cinema);
      color: var(--ink-primary);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      line-height: 1.5;
    }}
    .lookbook-masthead {{
      max-width: 1200px;
      margin: 0 auto 24px auto;
      padding: 20px 24px;
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .masthead-title h1 {{ margin: 0 0 4px 0; font-size: 1.4rem; }}
    .masthead-title p {{ margin: 0; color: var(--ink-secondary); font-size: 0.9rem; }}
    .swatch-strip {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .swatch-chip {{ display: flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border-subtle); font-size: 0.78rem; }}
    .swatch-color {{ width: 14px; height: 14px; border-radius: 3px; display: inline-block; }}
    .lookbook-deck {{ max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; }}
    .lookbook-slide {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 24px;
      page-break-after: always;
      break-after: page;
    }}
    .lookbook-slide:last-of-type {{
      page-break-after: auto;
      break-after: auto;
    }}
    .slide-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 10px;
      margin-bottom: 18px;
    }}
    .slide-kicker {{
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      color: var(--accent-primary);
    }}
    .slide-swatches {{ display: flex; gap: 6px; }}
    .mini-swatch {{ width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.25); }}
    .slide-body {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 24px;
      align-items: start;
    }}
    @media (max-width: 860px) {{
      .slide-body {{ grid-template-columns: 1fr; }}
    }}
    .slide-copy h2 {{ margin: 0 0 8px 0; font-size: 1.45rem; }}
    .slide-subhead {{ margin: 0 0 12px 0; color: var(--accent-warm); font-weight: 600; font-size: 0.95rem; }}
    .slide-narrative {{ margin: 0 0 16px 0; color: #E2E8F0; font-size: 0.96rem; }}
    .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 14px; }}
    .metric-pill {{
      background: rgba(15, 23, 42, 0.75);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 8px 10px;
    }}
    .metric-k {{ display: block; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-secondary); }}
    .metric-v {{ display: block; font-size: 0.9rem; font-weight: 600; color: var(--ink-primary); }}
    .slide-plate-wrap {{
      background: #05070B;
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 10px;
    }}
    .slide-plate-wrap svg, .plate-img {{ width: 100%; height: auto; display: block; border-radius: 6px; }}
    .nb-strip {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 12px; }}
    .nb-card {{ border: 1px solid var(--border-subtle); border-radius: 8px; padding: 8px; background: rgba(15, 23, 42, 0.55); }}
    .nb-plate svg {{ width: 100%; height: auto; display: block; border-radius: 4px; }}
    .nb-meta {{ font-size: 0.75rem; margin-top: 6px; color: var(--ink-secondary); }}
    .sonic-box {{ border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px; background: rgba(15, 23, 42, 0.55); font-size: 0.85rem; }}
    .stem-list {{ margin: 8px 0 0 18px; padding: 0; }}
    .slide-footer {{
      margin-top: 18px;
      padding-top: 10px;
      border-top: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      font-size: 0.75rem;
      color: var(--ink-secondary);
    }}
    .diff-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 12px; }}
    .diff-table th, .diff-table td {{ border: 1px solid var(--border-subtle); padding: 8px; text-align: left; vertical-align: top; }}
    .diff-table th {{ background: rgba(15, 23, 42, 0.85); color: var(--accent-primary); }}
    @media print {{
      @page {{ size: landscape; margin: 12mm; }}
      body {{ background: #FFFFFF; color: #0F172A; padding: 0; }}
      .lookbook-masthead, .lookbook-slide, .metric-pill, .sonic-box, .nb-card {{
        background: #FFFFFF !important;
        color: #0F172A !important;
        border-color: #CBD5E1 !important;
      }}
      .slide-narrative, .nb-meta, .slide-footer, .masthead-title p {{ color: #334155 !important; }}
      .slide-kicker {{ color: #0369A1 !important; }}
      .slide-subhead {{ color: #B45309 !important; }}
      .lookbook-slide {{ page-break-after: always; break-after: page; margin-bottom: 0; box-shadow: none; }}
      .lookbook-slide:last-of-type {{ page-break-after: auto; break-after: auto; }}
    }}
  </style>
</head>
<body>
  <header class="lookbook-masthead">
    <div class="masthead-title">
      <h1>{esc(manifest.project_title)} — Director's Pitch Lookbook</h1>
      <p>{esc(manifest.client_brand_label)} · {esc(manifest.domain_archetype)} · Hook: {esc(manifest.target_audience_hook)}</p>
    </div>
    <div class="swatch-strip">{swatch_strip_html}</div>
  </header>
  <main class="lookbook-deck">
    {''.join(slide_sections)}
    {diff_html}
  </main>
</body>
</html>
"""


def export_treatment_brief_md(manifest: MasterPitchTreatmentSpec) -> str:
    """Exports the Executive Director's Pitch Treatment as a structured Markdown brief."""
    lines = [
        f"# Executive Director's Treatment — {manifest.project_title}",
        "",
        f"- **Treatment ID**: `{manifest.treatment_id}`",
        f"- **Client / Brand**: {manifest.client_brand_label}",
        f"- **Domain Archetype**: `{manifest.domain_archetype}`",
        f"- **Target Audience Hook**: {manifest.target_audience_hook}",
        f"- **Color Script Strip**: `{', '.join(manifest.color_script_strip)}`",
        f"- **Treatment Token**: `{manifest.treatment_token}`",
        "",
        "## Director's Statement",
        manifest.executive_director_statement,
        "",
        "## Presentation Boards",
    ]
    for slide in manifest.slides:
        stype = _enum_str(slide.slide_type)
        lines.extend([
            f"### Board {slide.slide_index:02d} — {slide.headline} (`{stype}`)",
            f"*{slide.subhead}*",
            "",
            slide.narrative_copy,
            "",
        ])
        if slide.key_metrics:
            metrics_str = " | ".join(f"**{k}**: {v}" for k, v in slide.key_metrics.items())
            lines.append(f"- **Metrics**: {metrics_str}")
        lines.append(f"- **Token**: `{format_pitch_treatment_token(slide, manifest)}`")
        lines.append("")

    if manifest.revision_diff is not None:
        lines.append(export_bible_revision_diff_md(manifest.revision_diff))

    return "\n".join(lines)


def export_treatment_manifest_json(manifest: MasterPitchTreatmentSpec) -> str:
    """Serializes MasterPitchTreatmentSpec to formatted JSON."""
    return manifest.model_dump_json(indent=2)


def export_bible_revision_diff_md(diff_report: BibleRevisionDiffReport) -> str:
    """Exports a BibleRevisionDiffReport as a Markdown audit report."""
    lines = [
        f"## Bible Revision Diff — {diff_report.baseline_title} -> {diff_report.target_title}",
        "",
        f"- **Baseline SHA-256**: `{diff_report.baseline_sha256}`",
        f"- **Target SHA-256**: `{diff_report.target_sha256}`",
        f"- **Total Changes**: {diff_report.total_changes}",
        f"- **Scene Prompt Deltas**: {diff_report.scene_prompt_deltas_count}",
        f"- **AICP Budget Delta (USD)**: `${diff_report.aicp_budget_delta_usd:+,.2f}`",
        f"- **Render Compute Delta (USD)**: `${diff_report.render_compute_delta_usd:+,.4f}`",
        f"- **Council Score Delta**: `{diff_report.council_score_delta if diff_report.council_score_delta is not None else 'N/A'}`",
        "",
        "| Section | Field | Change | Previous | Current | Severity | Owner |",
        "|---|---|---|---|---|---|---|",
    ]
    if diff_report.deltas:
        for d in diff_report.deltas:
            lines.append(
                f"| {d.section} | `{d.field_path}` | {d.change_type} | "
                f"{d.previous_value.replace('|', '/')} | {d.current_value.replace('|', '/')} | "
                f"{d.impact_severity} | {d.department_owner} |"
            )
    else:
        lines.append("| All | `*` | none | identical | identical | low | Direction |")
    lines.append("")
    return "\n".join(lines)


def export_bible_revision_diff_json(diff_report: BibleRevisionDiffReport) -> str:
    """Serializes BibleRevisionDiffReport to formatted JSON."""
    return diff_report.model_dump_json(indent=2)


def export_pitch_treatment_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    baseline_bible: Optional[Any] = None,
) -> Dict[str, Path]:
    """Writes director_treatment_lookbook.html, director_treatment_brief.md, and pitch_treatment_manifest.json."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    existing = getattr(bible, "master_pitch_treatment", None)
    if existing is not None and baseline_bible is None:
        manifest = existing
    else:
        manifest = compile_pitch_treatment(bible, baseline_bible=baseline_bible)

    html_path = out_dir / "director_treatment_lookbook.html"
    html_path.write_text(export_treatment_lookbook_html(manifest, bible), encoding="utf-8")

    md_path = out_dir / "director_treatment_brief.md"
    md_path.write_text(export_treatment_brief_md(manifest), encoding="utf-8")

    json_path = out_dir / "pitch_treatment_manifest.json"
    json_path.write_text(export_treatment_manifest_json(manifest), encoding="utf-8")

    return {
        "director_treatment_lookbook_html": html_path,
        "director_treatment_brief_md": md_path,
        "pitch_treatment_manifest_json": json_path,
    }


__all__ = [
    "compile_pitch_treatment",
    "diff_production_bibles",
    "format_pitch_treatment_token",
    "export_treatment_lookbook_html",
    "export_treatment_brief_md",
    "export_treatment_manifest_json",
    "export_bible_revision_diff_md",
    "export_bible_revision_diff_json",
    "export_pitch_treatment_bundle",
]
