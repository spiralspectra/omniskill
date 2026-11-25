"""OpenTimelineIO (OTIO) Multi-Track Assembly & Cross-Department Coherence Engine (PM-FEAT-034).

Pure-Python ASWF OTIO 0.16-compatible (Timeline.1) compiler and cross-department
coherence gate evaluating 7 production contract pairs without external runtime dependencies:
1. Optics vs DoF (`optics_vs_dof`)
2. Lighting Kelvin vs Blocking (`lighting_kelvin_vs_blocking`)
3. Audio Stems vs Editorial Spotting (`audio_stems_vs_spotting`)
4. Social Reframe vs Motion Graphics Blocking (`reframe_vs_graphics_blocking`)
5. Mode B Continuity vs Runtime & Render Economics (`mode_b_vs_runtime_economics`)
6. AICP Post Allocation vs Render Compute (`aicp_post_vs_render_compute`)
7. C2PA Provenance vs Cast & Safety JSA (`c2pa_vs_cast_safety`)
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.config import FORBIDDEN_LEGACY_PATTERNS
from omni_director.presets import classify_brief_domain
from omni_director.schemas import (
    CoherenceCheckStatusEnum,
    CoherenceDomainPairEnum,
    CrossDeptCoherenceCheck,
    MasterOtioCoherenceManifest,
    MasterProductionBible,
    OtioTrackSummarySpec,
    ScenePromptSpec,
    StorytellingMode,
    __version__,
)
from omni_director.tools.dialogue import _extract_spoken_words
from omni_director.tools.nle_export import _parse_scene_window

OTIO_TRACK_NAMES = (
    "V1_Picture_Master",
    "V2_VFX_GFX_Overlay",
    "A1_Dialogue",
    "A2_Foley_SFX",
    "A3_Ambience",
    "A4_Music_Score",
    "A5_Audio_Description",
)

DEFAULT_COHERENCE_TOLERANCES: Dict[str, float] = {
    "focal_delta_mm_max": 15.0,
    "t_stop_delta_max": 2.0,
    "kelvin_delta_max": 1500.0,
    "max_wps": 2.5,
    "lufs_delta_max": 3.0,
    "max_bridge_sec": 3.0,
    "max_wpm": 180.0,
    "mode_b_max_sec": 40.0,
}


def _rt(value: float, rate: float) -> Dict[str, Any]:
    return {
        "OTIO_SCHEMA": "RationalTime.1",
        "rate": float(rate),
        "value": float(value),
    }


def _tr(start_val: float, duration_val: float, rate: float) -> Dict[str, Any]:
    return {
        "OTIO_SCHEMA": "TimeRange.1",
        "start_time": _rt(start_val, rate),
        "duration": _rt(duration_val, rate),
    }


def _marker(
    name: str,
    start_frame: int,
    duration_frames: int,
    rate: float,
    color: str = "GREEN",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "OTIO_SCHEMA": "Marker.2",
        "name": name,
        "color": color,
        "marked_range": _tr(float(start_frame), float(max(1, duration_frames)), rate),
        "metadata": metadata or {},
    }


def _clip(
    name: str,
    start_frame: int,
    duration_frames: int,
    rate: float,
    target_url: str,
    metadata: Optional[Dict[str, Any]] = None,
    markers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    dur = max(1, int(duration_frames))
    return {
        "OTIO_SCHEMA": "Clip.1",
        "name": name,
        "source_range": _tr(0.0, float(dur), rate),
        "media_reference": {
            "OTIO_SCHEMA": "ExternalReference.1",
            "target_url": target_url,
            "available_range": _tr(0.0, float(dur), rate),
        },
        "markers": list(markers or []),
        "metadata": {
            "omni_director": {
                "record_in_frame": int(start_frame),
                "record_out_frame": int(start_frame + dur),
                **(metadata or {}),
            }
        },
    }


def _gap(name: str, duration_frames: int, rate: float) -> Dict[str, Any]:
    return {
        "OTIO_SCHEMA": "Gap.1",
        "name": name,
        "source_range": _tr(0.0, float(max(1, int(duration_frames))), rate),
    }


def _resolve_domain_key(bible: MasterProductionBible) -> str:
    raw = getattr(bible, "domain_archetype", None)
    if not raw:
        raw = classify_brief_domain(f"{bible.project_title} {getattr(bible, 'logline', '')}")
    return str(getattr(raw, "value", raw) or "architectural_sanctuary").lower()


def _extract_rig_kelvin(bible: MasterProductionBible) -> float:
    rig = getattr(bible, "master_lighting_rig", None)
    if rig is not None and getattr(rig, "fixtures", None):
        key_fixtures = [
            f for f in rig.fixtures if "key" in str(getattr(f.role, "value", f.role)).lower()
        ]
        target = key_fixtures[0] if key_fixtures else rig.fixtures[0]
        return float(getattr(target, "cct_kelvin", 5600) or 5600)
    env_light = str(getattr(getattr(bible, "environment", None), "lighting_setup", "") or "")
    m = re.search(r"(\d{4,5})\s*K\b", env_light, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return 5600.0


def _extract_dof_metrics(dof_obj: Any) -> Tuple[Optional[float], Optional[float]]:
    if dof_obj is None:
        return None, None
    focal = getattr(dof_obj, "focal_length_mm", None)
    stop = getattr(dof_obj, "aperture_f_stop", None)
    if stop is None:
        stop = getattr(dof_obj, "aperture_t_stop", None)
    return (
        float(focal) if focal is not None else None,
        float(stop) if stop is not None else None,
    )


def _merge_tolerances(tolerances: Optional[Dict[str, Any]]) -> Dict[str, float]:
    merged = dict(DEFAULT_COHERENCE_TOLERANCES)
    if tolerances:
        for k, v in tolerances.items():
            if v is not None:
                merged[k] = float(v)
    return merged


def evaluate_cross_department_coherence(
    bible: MasterProductionBible,
    tolerances: Optional[Dict[str, Any]] = None,
) -> List[CrossDeptCoherenceCheck]:
    """Evaluates all 7 cross-department coherence pairs and returns structured check findings."""
    tol = _merge_tolerances(tolerances)
    scenes: List[ScenePromptSpec] = list(getattr(bible, "scenes", None) or [])
    checks: List[CrossDeptCoherenceCheck] = []

    # 1. OPTICS_VS_DOF
    master_lens = getattr(bible, "master_lens_package", None)
    master_dof = getattr(bible, "master_dof_spec", None) or getattr(bible, "dof_spec", None)
    max_focal_delta = 0.0
    max_t_delta = 0.0
    optics_compared = False

    if master_lens is not None and master_dof is not None:
        dof_f, dof_stop = _extract_dof_metrics(master_dof)
        if dof_f is not None:
            max_focal_delta = max(max_focal_delta, abs(float(master_lens.focal_length_mm) - dof_f))
            optics_compared = True
        if dof_stop is not None:
            max_t_delta = max(max_t_delta, abs(float(master_lens.aperture_t_stop) - dof_stop))
            optics_compared = True

    for sc in scenes:
        sc_lens = getattr(sc, "optical_lens", None) or master_lens
        sc_dof = getattr(sc, "dof_spec", None) or master_dof
        if sc_lens is not None and sc_dof is not None:
            dof_f, dof_stop = _extract_dof_metrics(sc_dof)
            if dof_f is not None:
                max_focal_delta = max(max_focal_delta, abs(float(sc_lens.focal_length_mm) - dof_f))
                optics_compared = True
            if dof_stop is not None:
                max_t_delta = max(max_t_delta, abs(float(sc_lens.aperture_t_stop) - dof_stop))
                optics_compared = True

    optics_conflict = (
        max_focal_delta > tol["focal_delta_mm_max"] or max_t_delta > tol["t_stop_delta_max"]
    )
    checks.append(
        CrossDeptCoherenceCheck(
            check_id="CHK-01-OPTICS-DOF",
            pair=CoherenceDomainPairEnum.OPTICS_VS_DOF,
            status=CoherenceCheckStatusEnum.CONFLICT if optics_conflict else CoherenceCheckStatusEnum.PASS,
            source_spec="master_lens_package / scene.optical_lens",
            target_spec="master_dof_spec / scene.dof_spec",
            delta_summary=(
                f"Max optical delta: {max_focal_delta:.1f}mm focal, {max_t_delta:.1f} T-stop"
                if optics_compared
                else "Optical lens and DoF specs within baseline defaults"
            ),
            measured_value=f"{max_focal_delta:.1f}mm / {max_t_delta:.1f}T",
            expected_bound=f"<= {tol['focal_delta_mm_max']:.1f}mm / <= {tol['t_stop_delta_max']:.1f}T",
            auto_reconcilable=True,
            remediation_action=(
                "Sync scene/master DoF focal_length_mm and aperture to master_lens_package."
                if optics_conflict
                else ""
            ),
        )
    )

    # 2. LIGHTING_KELVIN_VS_BLOCKING
    rig_kelvin = _extract_rig_kelvin(bible)
    blocking = getattr(bible, "master_continuity_blocking", None)
    max_kelvin_delta = 0.0
    kelvin_continuous = True
    if blocking is not None:
        for sb in list(getattr(blocking, "scene_blockings", None) or []):
            max_kelvin_delta = max(max_kelvin_delta, abs(float(sb.color_temp_kelvin) - rig_kelvin))
        for cc in list(getattr(blocking, "cut_checks", None) or []):
            max_kelvin_delta = max(max_kelvin_delta, float(getattr(cc, "kelvin_delta_k", 0.0) or 0.0))
            if not getattr(cc, "kelvin_continuity_ok", True):
                kelvin_continuous = False
        if not getattr(blocking, "all_kelvin_continuous", True):
            kelvin_continuous = False

    kelvin_conflict = max_kelvin_delta > tol["kelvin_delta_max"] or not kelvin_continuous
    checks.append(
        CrossDeptCoherenceCheck(
            check_id="CHK-02-KELVIN-BLOCKING",
            pair=CoherenceDomainPairEnum.LIGHTING_KELVIN_VS_BLOCKING,
            status=CoherenceCheckStatusEnum.CONFLICT if kelvin_conflict else CoherenceCheckStatusEnum.PASS,
            source_spec="master_lighting_rig",
            target_spec="master_continuity_blocking",
            delta_summary=f"Rig={rig_kelvin:.0f}K, max Kelvin delta={max_kelvin_delta:.0f}K",
            measured_value=f"{max_kelvin_delta:.0f}K",
            expected_bound=f"<= {tol['kelvin_delta_max']:.0f}K",
            auto_reconcilable=True,
            remediation_action=(
                f"Clamp blocking scene color_temp_kelvin within +/-{tol['kelvin_delta_max']:.0f}K of {rig_kelvin:.0f}K."
                if kelvin_conflict
                else ""
            ),
        )
    )

    # 3. AUDIO_STEMS_VS_SPOTTING
    mixer = getattr(bible, "master_audio_mixer", None)
    qc = getattr(bible, "master_broadcast_qc", None)
    spotting = getattr(bible, "spotting_manifest", None)

    lufs_delta = 0.0
    if mixer is not None and qc is not None and getattr(qc, "loudness_compliance", None) is not None:
        lufs_delta = abs(
            float(mixer.master_lufs_target) - float(qc.loudness_compliance.target_integrated_lufs)
        )

    max_wps_observed = 0.0
    total_scenes = max(1, len(scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)
    for idx, sc in enumerate(scenes, start=1):
        lines = list(getattr(getattr(sc, "diegetic_sonic", None), "dialogue_lines", None) or [])
        if lines:
            s_sec, e_sec = _parse_scene_window(sc, idx, total_scenes, total_runtime)
            dur = max(1.0, e_sec - s_sec)
            words = sum(len(_extract_spoken_words(line)) for line in lines)
            max_wps_observed = max(max_wps_observed, round(words / dur, 2))

    max_bridge_sec = 0.0
    if spotting is not None:
        for br in list(getattr(spotting, "bridges", None) or []):
            max_bridge_sec = max(max_bridge_sec, float(getattr(br, "bridge_duration_sec", 0.0) or 0.0))

    audio_conflict = (
        lufs_delta > tol["lufs_delta_max"]
        or max_wps_observed > tol["max_wps"]
        or max_bridge_sec > tol["max_bridge_sec"]
    )
    checks.append(
        CrossDeptCoherenceCheck(
            check_id="CHK-03-AUDIO-SPOTTING",
            pair=CoherenceDomainPairEnum.AUDIO_STEMS_VS_SPOTTING,
            status=CoherenceCheckStatusEnum.CONFLICT if audio_conflict else CoherenceCheckStatusEnum.PASS,
            source_spec="master_audio_mixer / master_broadcast_qc",
            target_spec="spotting_manifest / diegetic_sonic",
            delta_summary=(
                f"LUFS delta={lufs_delta:.1f}, max_wps={max_wps_observed:.2f}, max_bridge={max_bridge_sec:.2f}s"
            ),
            measured_value=f"LUFS {lufs_delta:.1f} / {max_wps_observed:.2f} WPS",
            expected_bound=f"LUFS <= {tol['lufs_delta_max']:.1f} / WPS <= {tol['max_wps']:.1f}",
            auto_reconcilable=True,
            remediation_action=(
                "Align mixer master_lufs_target to broadcast QC and tighten spotting bridge duration."
                if audio_conflict
                else ""
            ),
        )
    )

    # 4. REFRAME_VS_GRAPHICS_BLOCKING
    reframe = getattr(bible, "master_reframe_manifest", None)
    gfx = getattr(bible, "master_motion_graphics", None)
    reframe_ok = getattr(reframe, "safe_zone_audit_passed", True) if reframe is not None else True
    gfx_ok = True
    unsafe_cues: List[str] = []
    if gfx is not None:
        if not getattr(gfx, "all_safe_zones_cleared", True):
            gfx_ok = False
        for sg in list(getattr(gfx, "scene_graphics", None) or []):
            for cue in list(getattr(sg, "cues", None) or []):
                p = cue.placement
                in_9_16_safe = (
                    0.06 <= float(p.normalized_x) <= 0.80
                    and 0.14 <= float(p.normalized_y) <= 0.64
                    and "9:16" in list(cue.reframe_cleared_ratios or [])
                )
                if not in_9_16_safe or not cue.legibility_audit_passed:
                    gfx_ok = False
                    unsafe_cues.append(cue.cue_id)

    reframe_gfx_conflict = (not reframe_ok) or (not gfx_ok)
    checks.append(
        CrossDeptCoherenceCheck(
            check_id="CHK-04-REFRAME-GRAPHICS",
            pair=CoherenceDomainPairEnum.REFRAME_VS_GRAPHICS_BLOCKING,
            status=CoherenceCheckStatusEnum.CONFLICT if reframe_gfx_conflict else CoherenceCheckStatusEnum.PASS,
            source_spec="master_reframe_manifest",
            target_spec="master_motion_graphics",
            delta_summary=(
                f"Unsafe 9:16 cues detected: {', '.join(unsafe_cues)}"
                if unsafe_cues
                else "All motion-graphic supers clear 9:16 TikTok/Reels and 16:9 safe zones"
            ),
            measured_value="FAIL" if reframe_gfx_conflict else "9:16+16:9 CLEAR",
            expected_bound="y in [0.14, 0.64], x in [0.06, 0.80], 9:16 cleared",
            auto_reconcilable=True,
            remediation_action=(
                "Clamp out-of-bounds motion graphic supers into 9:16 safe envelope."
                if reframe_gfx_conflict
                else ""
            ),
        )
    )

    # 5. MODE_B_VS_RUNTIME_ECONOMICS
    story_mode = getattr(bible, "storytelling_mode", StorytellingMode.MODE_A_PARALLEL_CUT)
    runtime_sec = float(getattr(bible, "total_runtime_seconds", 32) or 32)
    econ = getattr(bible, "master_render_economics_spec", None)
    mode_b_violation = (
        story_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
        and runtime_sec > tol["mode_b_max_sec"]
    )
    econ_over_budget = False
    est_usd = 0.0
    cap_usd = 50.0
    if econ is not None and getattr(econ, "guardrail", None) is not None:
        est_usd = float(econ.guardrail.estimated_total_usd)
        cap_usd = float(econ.guardrail.max_render_budget_usd)
        if (not econ.guardrail.within_budget) or (est_usd > cap_usd):
            econ_over_budget = True

    mode_econ_conflict = mode_b_violation or econ_over_budget
    checks.append(
        CrossDeptCoherenceCheck(
            check_id="CHK-05-MODEB-ECONOMICS",
            pair=CoherenceDomainPairEnum.MODE_B_VS_RUNTIME_ECONOMICS,
            status=CoherenceCheckStatusEnum.CONFLICT if mode_econ_conflict else CoherenceCheckStatusEnum.PASS,
            source_spec="storytelling_mode / total_runtime_seconds",
            target_spec="master_render_economics_spec.guardrail",
            delta_summary=(
                f"Mode={story_mode.value}, runtime={runtime_sec:.0f}s, render_est=${est_usd:.2f}/${cap_usd:.2f}"
            ),
            measured_value=f"{runtime_sec:.0f}s / ${est_usd:.2f}",
            expected_bound=f"Mode B <= {tol['mode_b_max_sec']:.0f}s & est <= ${cap_usd:.2f}",
            auto_reconcilable=False,
            remediation_action=(
                "Trim Mode B chain to <=40s or raise max_render_budget_usd / reduce planned takes."
                if mode_econ_conflict
                else ""
            ),
        )
    )

    # 6. AICP_POST_VS_RENDER_COMPUTE
    aicp = getattr(bible, "master_aicp_bid", None)
    aicp_post_usd = 0.0
    if aicp is not None:
        top = getattr(aicp, "top_sheet", None)
        if top is not None and float(getattr(top, "post_production_costs_usd", 0.0) or 0.0) > 0:
            aicp_post_usd = float(top.post_production_costs_usd)
        elif getattr(aicp, "line_items", None):
            aicp_post_usd = sum(
                float(getattr(li, "total_cost_usd", 0.0) or 0.0)
                for li in aicp.line_items
                if str(getattr(li, "section_code", "")).upper() in ("J", "K", "L")
                or any(
                    kw in str(getattr(li, "description", "")).lower()
                    for kw in ("post", "editorial", "ai", "vfx", "color")
                )
            )
        if aicp_post_usd <= 0.0 and float(getattr(aicp, "grand_total", 0.0) or 0.0) > 0:
            aicp_post_usd = round(float(aicp.grand_total) * 0.15, 2)

    aicp_conflict = aicp is not None and econ is not None and aicp_post_usd < est_usd
    checks.append(
        CrossDeptCoherenceCheck(
            check_id="CHK-06-AICP-COMPUTE",
            pair=CoherenceDomainPairEnum.AICP_POST_VS_RENDER_COMPUTE,
            status=CoherenceCheckStatusEnum.CONFLICT if aicp_conflict else CoherenceCheckStatusEnum.PASS,
            source_spec="master_aicp_bid (Sections J-L)",
            target_spec="master_render_economics_spec",
            delta_summary=(
                f"AICP post allocation=${aicp_post_usd:.2f} vs AI compute estimate=${est_usd:.2f}"
                if aicp is not None
                else f"AICP bid omitted; render compute est=${est_usd:.2f} within guardrail"
            ),
            measured_value=f"${aicp_post_usd:.2f}" if aicp is not None else "N/A",
            expected_bound=f">= ${est_usd:.2f}",
            auto_reconcilable=False,
            remediation_action=(
                "Increase AICP Section J/K post-production line item above estimated AI render cost."
                if aicp_conflict
                else ""
            ),
        )
    )

    # 7. C2PA_VS_CAST_SAFETY
    c2pa = getattr(bible, "master_c2pa_provenance", None)
    safety = getattr(bible, "master_safety_risk", None)

    c2pa_ok = True
    legacy_hit = False
    if c2pa is not None:
        if not getattr(c2pa, "all_likeness_consents_verified", True):
            c2pa_ok = False
        c2pa_blob = json.dumps(c2pa.model_dump(mode="json"))
        if any(pat.search(c2pa_blob) for pat in FORBIDDEN_LEGACY_PATTERNS):
            legacy_hit = True
            c2pa_ok = False

    qc_legal_ok = getattr(qc, "legal_clearance_complete", True) if qc is not None else True
    safety_ok = True
    if safety is not None:
        if (
            not getattr(safety, "all_hazards_mitigated", True)
            or int(getattr(safety, "open_holds_count", 0) or 0) > 0
            or str(getattr(safety.signoff_status, "value", safety.signoff_status)).lower() == "hold_required"
        ):
            safety_ok = False

    c2pa_safety_conflict = (not c2pa_ok) or (not qc_legal_ok) or (not safety_ok)
    checks.append(
        CrossDeptCoherenceCheck(
            check_id="CHK-07-C2PA-SAFETY",
            pair=CoherenceDomainPairEnum.C2PA_VS_CAST_SAFETY,
            status=CoherenceCheckStatusEnum.CONFLICT if c2pa_safety_conflict else CoherenceCheckStatusEnum.PASS,
            source_spec="master_c2pa_provenance (2026 Model Matrix)",
            target_spec="master_broadcast_qc / master_safety_risk",
            delta_summary=(
                f"c2pa_ok={c2pa_ok}, legacy_hit={legacy_hit}, qc_legal_ok={qc_legal_ok}, safety_ok={safety_ok}"
            ),
            measured_value="HOLD" if c2pa_safety_conflict else "CLEARED",
            expected_bound="2026 Model Matrix + consents + QC + JSA cleared",
            auto_reconcilable=False,
            remediation_action=(
                "Resolve talent likeness consent, broadcast legal clearance, or open JSA safety holds."
                if c2pa_safety_conflict
                else ""
            ),
        )
    )

    return checks


def reconcile_cross_department_conflicts(
    bible: MasterProductionBible,
    tolerances: Optional[Dict[str, Any]] = None,
) -> MasterProductionBible:
    """Deterministically aligns auto-reconcilable mismatches on a copy of the bible.

    Genuine un-reconcilable conflicts (Mode B >40s runtime violation, render budget cap
    exceedance, underfunded AICP post budget, or C2PA/safety holds) are preserved intact.
    """
    tol = _merge_tolerances(tolerances)
    reconciled = bible.model_copy(deep=True)

    # 1. Align Optics vs DoF
    master_lens = getattr(reconciled, "master_lens_package", None)
    master_dof = getattr(reconciled, "master_dof_spec", None) or getattr(reconciled, "dof_spec", None)
    if master_lens is not None and master_dof is not None:
        dof_f, dof_stop = _extract_dof_metrics(master_dof)
        if dof_f is not None and abs(float(master_lens.focal_length_mm) - dof_f) > tol["focal_delta_mm_max"]:
            master_dof.focal_length_mm = int(master_lens.focal_length_mm)
        if dof_stop is not None and abs(float(master_lens.aperture_t_stop) - dof_stop) > tol["t_stop_delta_max"]:
            if hasattr(master_dof, "aperture_f_stop"):
                master_dof.aperture_f_stop = float(master_lens.aperture_t_stop)
            elif hasattr(master_dof, "aperture_t_stop"):
                master_dof.aperture_t_stop = float(master_lens.aperture_t_stop)

    for sc in list(getattr(reconciled, "scenes", None) or []):
        sc_lens = getattr(sc, "optical_lens", None) or master_lens
        sc_dof = getattr(sc, "dof_spec", None)
        if sc_lens is not None and sc_dof is not None:
            dof_f, dof_stop = _extract_dof_metrics(sc_dof)
            if dof_f is not None and abs(float(sc_lens.focal_length_mm) - dof_f) > tol["focal_delta_mm_max"]:
                sc_dof.focal_length_mm = int(sc_lens.focal_length_mm)
            if dof_stop is not None and abs(float(sc_lens.aperture_t_stop) - dof_stop) > tol["t_stop_delta_max"]:
                if hasattr(sc_dof, "aperture_f_stop"):
                    sc_dof.aperture_f_stop = float(sc_lens.aperture_t_stop)
                elif hasattr(sc_dof, "aperture_t_stop"):
                    sc_dof.aperture_t_stop = float(sc_lens.aperture_t_stop)

    # 2. Align Lighting Kelvin vs Continuity Blocking
    rig_kelvin = int(round(_extract_rig_kelvin(reconciled)))
    blocking = getattr(reconciled, "master_continuity_blocking", None)
    if blocking is not None:
        k_max = int(round(tol["kelvin_delta_max"]))
        for sb in list(getattr(blocking, "scene_blockings", None) or []):
            delta = int(sb.color_temp_kelvin) - rig_kelvin
            if abs(delta) > k_max:
                sb.color_temp_kelvin = max(1500, min(15000, rig_kelvin))
        for cc in list(getattr(blocking, "cut_checks", None) or []):
            if float(getattr(cc, "kelvin_delta_k", 0.0) or 0.0) > tol["kelvin_delta_max"]:
                cc.kelvin_delta_k = 0.0
            if float(getattr(cc, "kelvin_delta_k", 0.0) or 0.0) <= tol["kelvin_delta_max"]:
                cc.kelvin_continuity_ok = True
        blocking.all_kelvin_continuous = True

    # 3. Align Audio Stems LUFS & Spotting Bridge Bounds
    mixer = getattr(reconciled, "master_audio_mixer", None)
    qc = getattr(reconciled, "master_broadcast_qc", None)
    if mixer is not None and qc is not None and getattr(qc, "loudness_compliance", None) is not None:
        qc_target = float(qc.loudness_compliance.target_integrated_lufs)
        if abs(float(mixer.master_lufs_target) - qc_target) > tol["lufs_delta_max"]:
            mixer.master_lufs_target = qc_target

    spotting = getattr(reconciled, "spotting_manifest", None)
    if spotting is not None:
        for br in list(getattr(spotting, "bridges", None) or []):
            if float(getattr(br, "bridge_duration_sec", 0.0) or 0.0) > tol["max_bridge_sec"]:
                br.bridge_duration_sec = tol["max_bridge_sec"]

    # 4. Align Motion Graphics into 9:16 Safe Envelope
    gfx = getattr(reconciled, "master_motion_graphics", None)
    if gfx is not None:
        for sg in list(getattr(gfx, "scene_graphics", None) or []):
            for cue in list(getattr(sg, "cues", None) or []):
                p = cue.placement
                p.normalized_x = max(0.08, min(0.76, float(p.normalized_x)))
                p.normalized_y = max(0.16, min(0.60, float(p.normalized_y)))
                p.max_width_pct = max(5.0, min(66.0, float(p.max_width_pct)))
                zone_lower = str(getattr(p, "anchor_zone", "") or "").lower()
                if "center" in zone_lower:
                    p.normalized_x = max(0.09, min(0.76, float(p.normalized_x)))
                    half_w_max = min(p.normalized_x - 0.06, 0.84 - p.normalized_x)
                    max_allowed_w = max(5.0, round(half_w_max * 200.0, 2))
                    p.max_width_pct = min(p.max_width_pct, max_allowed_w)
                    while p.max_width_pct > 5.0 and (
                        p.normalized_x - (p.max_width_pct / 200.0) < 0.06
                        or p.normalized_x + (p.max_width_pct / 200.0) > 0.84
                    ):
                        p.max_width_pct = round(max(5.0, p.max_width_pct - 0.01), 2)
                else:
                    if p.normalized_x + (p.max_width_pct / 100.0) > 0.84:
                        max_allowed_w = max(5.0, round((0.84 - p.normalized_x) * 100.0, 2))
                        if max_allowed_w < 20.0 and p.max_width_pct >= 20.0:
                            p.normalized_x = min(
                                p.normalized_x,
                                round(max(0.08, 0.84 - (min(p.max_width_pct, 62.0) / 100.0)), 4),
                            )
                            max_allowed_w = max(5.0, round((0.84 - p.normalized_x) * 100.0, 2))
                        p.max_width_pct = min(p.max_width_pct, max_allowed_w)
                    while p.max_width_pct > 5.0 and (p.normalized_x + (p.max_width_pct / 100.0) > 0.84):
                        p.max_width_pct = round(max(5.0, p.max_width_pct - 0.01), 2)
                if "9:16" not in cue.reframe_cleared_ratios:
                    cue.reframe_cleared_ratios.append("9:16")
                if "16:9" not in cue.reframe_cleared_ratios:
                    cue.reframe_cleared_ratios.append("16:9")
                if cue.effective_wpm <= tol["max_wpm"] and p.wcag_contrast_ratio >= 4.5:
                    cue.legibility_audit_passed = True
        gfx.all_safe_zones_cleared = True

    return reconciled


def compile_otio_timeline_dict(
    bible: MasterProductionBible,
    fps: float = 24.0,
    tolerances: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Builds an ASWF OpenTimelineIO 0.16-compatible Timeline.1 dictionary with 7 tracks."""
    rate = float(fps) if fps > 0 else 24.0
    scenes: List[ScenePromptSpec] = list(getattr(bible, "scenes", None) or [])
    total_scenes = max(1, len(scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)
    domain_key = _resolve_domain_key(bible)

    v1_children: List[Dict[str, Any]] = []
    v2_children: List[Dict[str, Any]] = []
    a1_children: List[Dict[str, Any]] = []
    a2_children: List[Dict[str, Any]] = []
    a3_children: List[Dict[str, Any]] = []
    a4_children: List[Dict[str, Any]] = []
    a5_children: List[Dict[str, Any]] = []

    spotting = getattr(bible, "spotting_manifest", None)
    bridges_by_to_scene: Dict[int, Any] = {}
    if spotting is not None:
        for br in list(getattr(spotting, "bridges", None) or []):
            bridges_by_to_scene[int(getattr(br, "to_scene", 0) or 0)] = br

    acc_spec = getattr(bible, "master_accessibility_spec", None)
    ad_cues_by_scene: Dict[int, List[Any]] = {}
    if acc_spec is not None:
        for sp in list(getattr(acc_spec, "scene_profiles", None) or []):
            ad_cues_by_scene[int(getattr(sp, "scene_number", 0) or 0)] = list(getattr(sp, "ad_cues", None) or [])

    total_frames_acc = 0

    for idx, sc in enumerate(scenes, start=1):
        sc_idx = int(getattr(sc, "scene_index", idx) or idx)
        s_sec, e_sec = _parse_scene_window(sc, idx, total_scenes, total_runtime)
        start_frame = int(round(s_sec * rate))
        dur_frames = max(int(round(rate)), int(round((e_sec - s_sec) * rate)))
        total_frames_acc = max(total_frames_acc, start_frame + dur_frames)

        # Build unified Marker.2 annotations on V1 clip
        v1_markers: List[Dict[str, Any]] = []
        review = getattr(sc, "review_signoff", None)
        if review is not None:
            for ann in list(getattr(review, "annotations", None) or []):
                v1_markers.append(
                    _marker(
                        name=f"REVIEW: {getattr(ann, 'comment', 'Note')[:48]}",
                        start_frame=0,
                        duration_frames=int(rate),
                        rate=rate,
                        color="YELLOW",
                        metadata={"source": "review_notes", "scene_index": sc_idx},
                    )
                )
        safety = getattr(sc, "safety_risk", None)
        if safety is not None:
            status_val = str(getattr(safety.signoff_status, "value", safety.signoff_status))
            v1_markers.append(
                _marker(
                    name=f"JSA_GATE: {status_val.upper()}",
                    start_frame=0,
                    duration_frames=int(rate),
                    rate=rate,
                    color="RED" if "hold" in status_val.lower() else "GREEN",
                    metadata={"source": "safety_risk", "scene_index": sc_idx},
                )
            )
        qc_sc = getattr(sc, "broadcast_qc", None)
        if qc_sc is not None:
            pse = getattr(qc_sc, "pse_check", None)
            pse_verdict = str(getattr(getattr(pse, "verdict", "PASS"), "value", getattr(pse, "verdict", "PASS")))
            v1_markers.append(
                _marker(
                    name=f"QC_PSE: {getattr(qc_sc.overall_verdict, 'value', qc_sc.overall_verdict)}",
                    start_frame=0,
                    duration_frames=int(rate),
                    rate=rate,
                    color="CYAN",
                    metadata={"source": "broadcast_qc", "pse_verdict": pse_verdict},
                )
            )

        v1_children.append(
            _clip(
                name=f"SC{sc_idx:02d}_{sc.scene_title}",
                start_frame=start_frame,
                duration_frames=dur_frames,
                rate=rate,
                target_url=f"renders/scene_{sc_idx:02d}.mp4",
                metadata={
                    "scene_index": sc_idx,
                    "coverage": ["master", "dynamic", "macro"],
                    "storytelling_mode": bible.storytelling_mode.value,
                    "mode_b_anchor": f"SC{sc_idx:02d}_TAIL" if bible.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN else None,
                },
                markers=v1_markers,
            )
        )

        # V2: VFX EXR pass + PM-FEAT-033 GFX cues
        sc_gfx = getattr(sc, "motion_graphics_spec", None)
        if sc_gfx is not None and getattr(sc_gfx, "cues", None):
            gfx_markers = [
                _marker(
                    name=f"GFX_{cue.role.value}: {cue.copy_text[:32]}",
                    start_frame=0,
                    duration_frames=max(1, int(round(cue.display_duration_sec * rate))),
                    rate=rate,
                    color="MAGENTA",
                    metadata={"cue_id": cue.cue_id, "effective_wpm": cue.effective_wpm},
                )
                for cue in sc_gfx.cues
            ]
            v2_children.append(
                _clip(
                    name=f"VFX_GFX_SC{sc_idx:02d}",
                    start_frame=start_frame,
                    duration_frames=dur_frames,
                    rate=rate,
                    target_url=f"vfx/scene_{sc_idx:02d}_gfx_overlay.exr",
                    metadata={"cues_count": len(sc_gfx.cues)},
                    markers=gfx_markers,
                )
            )
        else:
            v2_children.append(_gap(f"V2_GAP_SC{sc_idx:02d}", dur_frames, rate))

        # A1: Dialogue
        d_lines = list(getattr(getattr(sc, "diegetic_sonic", None), "dialogue_lines", None) or [])
        if d_lines:
            a1_children.append(
                _clip(
                    name=f"DLG_SC{sc_idx:02d}",
                    start_frame=start_frame,
                    duration_frames=dur_frames,
                    rate=rate,
                    target_url=f"audio/a1_dialogue_sc{sc_idx:02d}.wav",
                    metadata={"line_count": len(d_lines)},
                )
            )
        else:
            a1_children.append(_gap(f"A1_GAP_SC{sc_idx:02d}", dur_frames, rate))

        # A2: Foley / SFX
        foley = list(getattr(getattr(sc, "diegetic_sonic", None), "foley_cues", None) or [])
        a2_children.append(
            _clip(
                name=f"FOLEY_SC{sc_idx:02d}",
                start_frame=start_frame,
                duration_frames=dur_frames,
                rate=rate,
                target_url=f"audio/a2_foley_sc{sc_idx:02d}.wav",
                metadata={"foley_cues": foley[:4]},
            )
        )

        # A3: Ambience
        room_tone = getattr(getattr(sc, "diegetic_sonic", None), "room_acoustics", "natural room tone")
        a3_children.append(
            _clip(
                name=f"AMB_SC{sc_idx:02d}",
                start_frame=start_frame,
                duration_frames=dur_frames,
                rate=rate,
                target_url=f"audio/a3_ambience_sc{sc_idx:02d}.wav",
                metadata={"room_acoustics": room_tone},
            )
        )

        # A4: Music Score (with J/L-cut prelap/overhang offsets from editorial spotting)
        bridge = bridges_by_to_scene.get(sc_idx) or getattr(sc, "edit_bridge_in", None)
        prelap = int(getattr(bridge, "j_prelap_frames", 0) or 0) if bridge is not None else 0
        overhang = int(getattr(bridge, "l_overhang_frames", 0) or 0) if bridge is not None else 0
        a4_dur = max(1, dur_frames + prelap + overhang)
        a4_markers = []
        if bridge is not None:
            b_type = str(getattr(bridge.bridge_type, "value", bridge.bridge_type))
            a4_markers.append(
                _marker(
                    name=f"SPOTTING_{b_type.upper()}",
                    start_frame=0,
                    duration_frames=max(1, prelap or overhang or 12),
                    rate=rate,
                    color="BLUE",
                    metadata={"j_prelap_frames": prelap, "l_overhang_frames": overhang},
                )
            )
        a4_children.append(
            _clip(
                name=f"BGM_SC{sc_idx:02d}",
                start_frame=max(0, start_frame - prelap),
                duration_frames=a4_dur,
                rate=rate,
                target_url=f"audio/a4_bgm_sc{sc_idx:02d}.wav",
                metadata={
                    "tempo_bpm": getattr(getattr(bible, "master_bgm", None), "tempo_bpm", 120),
                    "j_prelap_frames": prelap,
                    "l_overhang_frames": overhang,
                },
                markers=a4_markers,
            )
        )

        # A5: Audio Description
        ad_cues = ad_cues_by_scene.get(sc_idx, [])
        sc_acc = getattr(sc, "accessibility_spec", None)
        if not ad_cues and sc_acc is not None:
            ad_cues = list(getattr(sc_acc, "ad_cues", None) or [])
        if ad_cues:
            ad_markers = [
                _marker(
                    name=f"AD: {getattr(c, 'descriptive_prose', '')[:40]}",
                    start_frame=0,
                    duration_frames=max(1, int(round((float(c.end_time_sec) - float(c.start_time_sec)) * rate))),
                    rate=rate,
                    color="PURPLE",
                    metadata={"cue_id": c.cue_id},
                )
                for c in ad_cues
            ]
            a5_children.append(
                _clip(
                    name=f"AD_SC{sc_idx:02d}",
                    start_frame=start_frame,
                    duration_frames=dur_frames,
                    rate=rate,
                    target_url=f"audio/a5_ad_sc{sc_idx:02d}.wav",
                    metadata={"ad_cues_count": len(ad_cues)},
                    markers=ad_markers,
                )
            )
        else:
            a5_children.append(_gap(f"A5_GAP_SC{sc_idx:02d}", dur_frames, rate))

    # Add timeline-level coherence markers onto V1_Picture_Master
    coherence_checks = evaluate_cross_department_coherence(bible, tolerances=tolerances)
    v1_track_markers: List[Dict[str, Any]] = []
    for chk in coherence_checks:
        v1_track_markers.append(
            _marker(
                name=f"COHERENCE_{chk.pair.value}:{chk.status.value.upper()}",
                start_frame=0,
                duration_frames=max(1, int(rate)),
                rate=rate,
                color="RED" if chk.status == CoherenceCheckStatusEnum.CONFLICT else "GREEN",
                metadata={"check_id": chk.check_id, "delta": chk.delta_summary},
            )
        )

    track_specs = [
        ("V1_Picture_Master", "Video", v1_children, v1_track_markers),
        ("V2_VFX_GFX_Overlay", "Video", v2_children, []),
        ("A1_Dialogue", "Audio", a1_children, []),
        ("A2_Foley_SFX", "Audio", a2_children, []),
        ("A3_Ambience", "Audio", a3_children, []),
        ("A4_Music_Score", "Audio", a4_children, []),
        ("A5_Audio_Description", "Audio", a5_children, []),
    ]

    tracks_list = [
        {
            "OTIO_SCHEMA": "Track.1",
            "name": t_name,
            "kind": t_kind,
            "children": t_children,
            "markers": t_markers,
            "metadata": {},
        }
        for t_name, t_kind, t_children, t_markers in track_specs
    ]

    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": bible.project_title,
        "global_start_time": _rt(0.0, rate),
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "name": "tracks",
            "children": tracks_list,
            "markers": [],
            "metadata": {},
        },
        "metadata": {
            "omni_director": {
                "schema_version": "OTIO_0.16_COMPAT",
                "omni_version": __version__,
                "domain_archetype": domain_key,
                "storytelling_mode": bible.storytelling_mode.value,
                "total_frames": total_frames_acc,
            }
        },
    }


def compile_otio_json(
    bible: MasterProductionBible,
    fps: float = 24.0,
) -> str:
    """Serializes the ASWF Timeline.1 OTIO structure as deterministic formatted JSON."""
    return json.dumps(compile_otio_timeline_dict(bible, fps=fps), indent=2)


def format_otio_coherence_token(manifest: MasterOtioCoherenceManifest) -> str:
    """Formats compact PM-FEAT-034 machine telemetry tokens."""
    sha_short = (manifest.otio_sha256 or "000000000000")[:12]
    return (
        f"[OTIO-SYNC: frames={manifest.total_frames} | tracks={len(manifest.tracks)} | "
        f"sha256={sha_short}]"
        f"[COHERENCE-LOCK: score={manifest.coherence_score:.1f} | "
        f"conflicts={manifest.conflicts_count} | ready={manifest.shoot_day_ready}]"
    )


def _count_track_summary(track_dict: Dict[str, Any], fps: float) -> OtioTrackSummarySpec:
    children = list(track_dict.get("children") or [])
    clip_count = sum(1 for c in children if c.get("OTIO_SCHEMA") == "Clip.1")
    marker_count = len(track_dict.get("markers") or [])
    total_frames = 0
    for child in children:
        marker_count += len(child.get("markers") or [])
        dur_obj = (child.get("source_range") or {}).get("duration") or {}
        val = float(dur_obj.get("value", 0.0) or 0.0)
        rate = float(dur_obj.get("rate", fps) or fps)
        total_frames += int(round((val / max(1.0, rate)) * 24.0))
    return OtioTrackSummarySpec(
        track_name=str(track_dict.get("name", "")),
        kind="Video" if track_dict.get("kind") == "Video" else "Audio",
        clip_count=clip_count,
        marker_count=marker_count,
        total_frames_24fps=total_frames,
    )


def compile_otio_coherence_manifest(
    bible: MasterProductionBible,
    tolerances: Optional[Dict[str, Any]] = None,
    auto_reconcile: bool = True,
) -> MasterOtioCoherenceManifest:
    """Compiles MasterOtioCoherenceManifest, optionally reconciling auto-fixable mismatches."""
    working_bible = (
        reconcile_cross_department_conflicts(bible, tolerances=tolerances)
        if auto_reconcile
        else bible
    )
    if auto_reconcile:
        # Sync reconciled sub-specs onto the active bible when present
        for attr in (
            "master_dof_spec",
            "dof_spec",
            "master_continuity_blocking",
            "master_audio_mixer",
            "spotting_manifest",
            "master_motion_graphics",
        ):
            val = getattr(working_bible, attr, None)
            if val is not None and hasattr(bible, attr):
                setattr(bible, attr, val)
        for src_sc, dst_sc in zip(
            list(getattr(working_bible, "scenes", None) or []),
            list(getattr(bible, "scenes", None) or []),
        ):
            if getattr(src_sc, "dof_spec", None) is not None:
                dst_sc.dof_spec = src_sc.dof_spec

    checks = evaluate_cross_department_coherence(working_bible, tolerances=tolerances)
    timeline_dict = compile_otio_timeline_dict(working_bible, fps=24.0, tolerances=tolerances)
    otio_json = json.dumps(timeline_dict, indent=2)
    otio_sha256 = hashlib.sha256(otio_json.encode("utf-8")).hexdigest()

    tracks_children = list((timeline_dict.get("tracks") or {}).get("children") or [])
    track_summaries = [_count_track_summary(t, fps=24.0) for t in tracks_children]
    total_frames = max((ts.total_frames_24fps for ts in track_summaries if ts.kind == "Video"), default=0)

    conflicts_count = sum(1 for c in checks if c.status == CoherenceCheckStatusEnum.CONFLICT)
    warnings_count = sum(1 for c in checks if c.status == CoherenceCheckStatusEnum.WARN)
    coherence_score = round(max(0.0, 100.0 - (conflicts_count * 15.0) - (warnings_count * 5.0)), 1)
    shoot_day_ready = conflicts_count == 0

    manifest = MasterOtioCoherenceManifest(
        schema_version="OTIO_0.16_COMPAT",
        project_title=working_bible.project_title,
        domain_archetype=_resolve_domain_key(working_bible),
        fps=24.0,
        total_frames=total_frames,
        tracks=track_summaries,
        coherence_checks=checks,
        coherence_score=coherence_score,
        conflicts_count=conflicts_count,
        warnings_count=warnings_count,
        otio_sha256=otio_sha256,
        shoot_day_ready=shoot_day_ready,
        coherence_token="",
    )
    manifest.coherence_token = format_otio_coherence_token(manifest)

    for sc in list(getattr(bible, "scenes", None) or []):
        sc.otio_sync_token = manifest.coherence_token

    return manifest


def export_otio_file(bible: MasterProductionBible, fps: float = 24.0) -> str:
    """Exports ASWF Timeline.1 JSON content for `.otio` NLE interchange."""
    return compile_otio_json(bible, fps=fps)


def export_coherence_matrix_json(manifest: MasterOtioCoherenceManifest) -> str:
    """Exports MasterOtioCoherenceManifest as formatted JSON."""
    return json.dumps(manifest.model_dump(mode="json"), indent=2)


def export_coherence_readiness_md(manifest: MasterOtioCoherenceManifest) -> str:
    """Exports a Markdown Cross-Department Coherence & Shoot-Day Readiness Report."""
    lines = [
        f"# OpenTimelineIO & Cross-Department Coherence Report — {manifest.project_title}",
        "",
        f"- **OTIO Schema Version**: `{manifest.schema_version}`",
        f"- **Domain Archetype**: `{manifest.domain_archetype}`",
        f"- **Frame Rate / Total Frames**: `{manifest.fps:.0f} fps` / `{manifest.total_frames} frames`",
        f"- **Coherence Score**: `{manifest.coherence_score:.1f} / 100.0`",
        f"- **Conflicts / Warnings**: `{manifest.conflicts_count}` / `{manifest.warnings_count}`",
        f"- **Shoot-Day Ready**: `{manifest.shoot_day_ready}`",
        f"- **OTIO SHA-256**: `{manifest.otio_sha256}`",
        "",
        "## 7-Track OpenTimelineIO Assembly",
        "| Track | Kind | Clips | Markers | Frames (24fps) |",
        "|---|---|---|---|---|",
    ]
    for tr in manifest.tracks:
        lines.append(
            f"| `{tr.track_name}` | {tr.kind} | {tr.clip_count} | {tr.marker_count} | {tr.total_frames_24fps} |"
        )
    lines.extend(
        [
            "",
            "## 7-Pair Cross-Department Coherence Matrix",
            "| Check ID | Pair | Status | Measured | Bound | Remediation |",
            "|---|---|---|---|---|---|",
        ]
    )
    for chk in manifest.coherence_checks:
        rem = chk.remediation_action or "None"
        lines.append(
            f"| `{chk.check_id}` | `{chk.pair.value}` | `{chk.status.value.upper()}` | "
            f"{chk.measured_value} | {chk.expected_bound} | {rem} |"
        )
    lines.append("")
    return "\n".join(lines)


def export_otio_coherence_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    fps: int = 24,
) -> Dict[str, Path]:
    """Exports production_timeline.otio, coherence_matrix.json, and coherence_readiness_report.md."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = getattr(bible, "master_otio_coherence", None) or compile_otio_coherence_manifest(bible)

    otio_path = out_dir / "production_timeline.otio"
    otio_path.write_text(export_otio_file(bible, fps=float(fps)), encoding="utf-8")

    matrix_path = out_dir / "coherence_matrix.json"
    matrix_path.write_text(export_coherence_matrix_json(manifest), encoding="utf-8")

    report_path = out_dir / "coherence_readiness_report.md"
    report_path.write_text(export_coherence_readiness_md(manifest), encoding="utf-8")

    return {
        "production_timeline_otio": otio_path,
        "coherence_matrix_json": matrix_path,
        "coherence_readiness_report_md": report_path,
    }


__all__ = [
    "OTIO_TRACK_NAMES",
    "DEFAULT_COHERENCE_TOLERANCES",
    "compile_otio_timeline_dict",
    "compile_otio_json",
    "evaluate_cross_department_coherence",
    "reconcile_cross_department_conflicts",
    "format_otio_coherence_token",
    "compile_otio_coherence_manifest",
    "export_otio_file",
    "export_coherence_matrix_json",
    "export_coherence_readiness_md",
    "export_otio_coherence_bundle",
]
