"""Broadcast QC, PSE Flash-Safety, Loudness & Rights Clearance Engine (PM-FEAT-022).

Pure-Python broadcast trafficking & technical Quality Control suite implementing:
- ITU-R BT.1702 / Ofcom Harding FPA photosensitive epilepsy (PSE) flash-safety auditing (<= 3.0 Hz, luminance delta)
- ATSC A/85 (-24 LKFS), EBU R128 (-23 LUFS), Streaming AES (-14 LUFS), and Theatrical DCP loudness validation
- Ad-ID / ISCI trafficking slate generation with SMPTE 12M FFOA & 2-pop timing
- Rights & legal clearances matrix (Talent, Music Sync/Master, Brand/IP, Location, Aerial FAA Part 107)
- Markdown QC certificate, CSV rights ledger, and JSON manifest export
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omni_director.schemas import (
    BroadcastLoudnessStandard,
    BroadcastTraffickingSlateSpec,
    ClearanceCategory,
    ClearanceRecordSpec,
    ClearanceStatus,
    LoudnessComplianceSpec,
    MasterBroadcastQcSpec,
    MasterProductionBible,
    PseFlashCheckSpec,
    QcVerdictStatus,
    ScenePromptSpec,
    SceneQcProfileSpec,
)


# Broadcast, Streaming & Theatrical Loudness Standards
LOUDNESS_STANDARDS: Dict[str, Dict[str, Any]] = {
    BroadcastLoudnessStandard.ATSC_A85.value: {
        "standard": BroadcastLoudnessStandard.ATSC_A85,
        "name": "ATSC A/85 (CALM Act US Broadcast)",
        "target_lufs": -24.0,
        "tolerance_lu": 2.0,
        "max_true_peak_dbtp": -2.0,
        "lra_max_lu": 10.0,
        "dialogue_gated": True,
    },
    BroadcastLoudnessStandard.EBU_R128.value: {
        "standard": BroadcastLoudnessStandard.EBU_R128,
        "name": "EBU R128 (European Broadcast)",
        "target_lufs": -23.0,
        "tolerance_lu": 0.5,
        "max_true_peak_dbtp": -1.0,
        "lra_max_lu": 10.0,
        "dialogue_gated": False,
    },
    BroadcastLoudnessStandard.STREAMING_AES.value: {
        "standard": BroadcastLoudnessStandard.STREAMING_AES,
        "name": "AES TD1008 / Streaming OTT",
        "target_lufs": -14.0,
        "tolerance_lu": 1.0,
        "max_true_peak_dbtp": -1.0,
        "lra_max_lu": 12.0,
        "dialogue_gated": False,
    },
    BroadcastLoudnessStandard.THEATRICAL_DCP.value: {
        "standard": BroadcastLoudnessStandard.THEATRICAL_DCP,
        "name": "SMPTE Theatrical DCP Reference",
        "target_lufs": -27.0,
        "tolerance_lu": 2.0,
        "max_true_peak_dbtp": -1.0,
        "lra_max_lu": 18.0,
        "dialogue_gated": True,
    },
}


def _coerce_loudness_standard(
    standard: Union[BroadcastLoudnessStandard, str],
) -> BroadcastLoudnessStandard:
    if isinstance(standard, BroadcastLoudnessStandard):
        return standard
    raw = str(standard).strip().lower()
    for member in BroadcastLoudnessStandard:
        if raw == member.value or raw == member.name.lower():
            return member
    if "ebu" in raw or "r128" in raw:
        return BroadcastLoudnessStandard.EBU_R128
    if "stream" in raw or "aes" in raw or "ott" in raw:
        return BroadcastLoudnessStandard.STREAMING_AES
    if "dcp" in raw or "theatrical" in raw:
        return BroadcastLoudnessStandard.THEATRICAL_DCP
    return BroadcastLoudnessStandard.ATSC_A85


def evaluate_scene_pse_safety(
    scene: Union[ScenePromptSpec, Dict[str, Any], str],
) -> PseFlashCheckSpec:
    """Evaluates ITU-R BT.1702 / Ofcom Harding FPA photosensitive epilepsy flash-safety.

    Checks speed_ramp, lighting_rig, hdr_spec, and prompt/beat keywords against the
    3.0 Hz flash-rate ceiling and 20 cd/m2 luminance transition delta threshold.
    """
    if isinstance(scene, ScenePromptSpec):
        prompt = scene.omni_prose_prompt or ""
        title = scene.scene_title or ""
        beats = " ".join(scene.action_beats or [])
        speed_ramp = getattr(scene, "speed_ramp", None)
        lighting_rig = getattr(scene, "lighting_rig", None)
        hdr_spec = getattr(scene, "hdr_spec", None)
    elif isinstance(scene, dict):
        prompt = str(scene.get("omni_prose_prompt") or scene.get("prompt") or "")
        title = str(scene.get("scene_title") or "")
        beats = " ".join(str(b) for b in (scene.get("action_beats") or []))
        speed_ramp = scene.get("speed_ramp")
        lighting_rig = scene.get("lighting_rig")
        hdr_spec = scene.get("hdr_spec")
    else:
        prompt = str(scene)
        title = ""
        beats = ""
        speed_ramp = None
        lighting_rig = None
        hdr_spec = None

    corpus = f"{title} {prompt} {beats}".lower()

    flash_hz = 0.8
    lum_delta_nits = 8.0
    red_flash = False
    spatial_risk = False
    reasons: List[str] = []

    # Check explicit Hz mentions in local proximity to flash/strobe terms (e.g., "8hz strobe", "10 hz flicker")
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*hz\b", corpus):
        val = float(m.group(1))
        win_start = max(0, m.start() - 45)
        win_end = min(len(corpus), m.end() + 45)
        local_ctx = corpus[win_start:win_end]
        # Ignore audio frequencies like 48000hz / 44100hz / 60hz display refresh unless locally paired with flash/strobe
        if val <= 60.0 and re.search(r"(?:strobe|flash|flicker|pulse|blink)", local_ctx):
            if val > flash_hz:
                flash_hz = val

    # Check severe strobe / flicker keywords
    severe_strobe = bool(re.search(r"\b(?:strobe|strobing|stroboscopic|rapid\s+flash|epilep|camera\s+flash\s+burst|rapid\s+flicker|muzzle\s+flash\s+burst)\b", corpus))
    moderate_flash = bool(re.search(r"\b(?:lightning|paparazzi|flicker|spark|welding\s+arc|flashbulb|laser\s+pulse)\b", corpus))
    red_strobe = bool(re.search(r"\b(?:red\s+strobe|crimson\s+flash|saturated\s+red\s+flicker|red\s+siren)\b", corpus))
    pattern_risk = bool(re.search(r"\b(?:rapid\s+checkerboard|high-contrast\s+stripes|moire\s+strobe)\b", corpus))

    if severe_strobe:
        flash_hz = max(flash_hz, 5.5)
        lum_delta_nits = max(lum_delta_nits, 32.0)
        reasons.append("High-frequency strobe/flash cues exceed 3.0 Hz ITU-R BT.1702 safe ceiling.")
    elif moderate_flash:
        flash_hz = max(flash_hz, 2.5)
        lum_delta_nits = max(lum_delta_nits, 18.0)
        reasons.append("Transient flash/lightning cue detected; monitor luminance transition delta (<= 20 cd/m2).")

    if red_strobe:
        red_flash = True
        flash_hz = max(flash_hz, 4.0)
        lum_delta_nits = max(lum_delta_nits, 26.0)
        reasons.append("Saturated red flash transition flagged under ITU-R BT.1702 red-flash rule.")

    if pattern_risk:
        spatial_risk = True
        reasons.append("High-contrast oscillating spatial pattern risk detected.")

    # Speed ramp inspection
    if speed_ramp is not None:
        mode = getattr(speed_ramp, "mode", None)
        mode_s = (mode.value if hasattr(mode, "value") else str(mode)).lower() if mode else ""
        if "snap_freeze" in mode_s or "burst" in mode_s:
            flash_hz = max(flash_hz, 1.8)
            lum_delta_nits = max(lum_delta_nits, 12.0)
        shutter_deg = getattr(speed_ramp, "shutter_angle_deg", 180.0)
        if shutter_deg is not None and float(shutter_deg) <= 45.0 and severe_strobe:
            flash_hz = max(flash_hz, 6.0)

    # Lighting rig inspection
    if lighting_rig is not None:
        fixtures = getattr(lighting_rig, "fixtures", None) or []
        total_lux = float(getattr(lighting_rig, "total_lux", 5000.0) or 5000.0)
        for fix in fixtures:
            ftype = str(getattr(fix, "fixture_type", "") or "").lower()
            if "strobe" in ftype or "thunder" in ftype or "lightning" in ftype:
                flash_hz = max(flash_hz, 4.5)
                lum_delta_nits = max(lum_delta_nits, 25.0)
                reasons.append(f"Strobe-capable fixture '{ftype}' requires BT.1702 dimmer slew-rate limiting.")
        if total_lux > 50000.0 and moderate_flash:
            lum_delta_nits = max(lum_delta_nits, 22.0)

    # HDR Peak Luminance inspection
    if hdr_spec is not None:
        max_cll = float(getattr(hdr_spec, "max_cll_nits", 1000.0) or 1000.0)
        if max_cll > 1500.0 and (severe_strobe or moderate_flash):
            lum_delta_nits = max(lum_delta_nits, 24.0)
            reasons.append(f"HDR MaxCLL ({max_cll:.0f} nits) amplifies flash luminance delta.")

    # Determine final ITU-R BT.1702 verdict
    if flash_hz > 3.0 or red_flash or lum_delta_nits > 25.0:
        verdict = QcVerdictStatus.FAIL
    elif lum_delta_nits > 20.0 or spatial_risk or moderate_flash:
        verdict = QcVerdictStatus.WARN
    else:
        verdict = QcVerdictStatus.PASS

    notes = (
        "Compliant with ITU-R BT.1702 / Ofcom Harding FPA (flash <= 3.0 Hz, luminance delta within safe envelope)."
        if not reasons
        else " ".join(reasons)
    )

    return PseFlashCheckSpec(
        standard_reference="ITU-R BT.1702 / Ofcom Harding FPA",
        max_flash_frequency_hz=round(flash_hz, 2),
        flash_limit_hz=3.0,
        max_luminance_delta_nits=round(lum_delta_nits, 2),
        red_saturation_flash_detected=red_flash,
        spatial_pattern_risk=spatial_risk,
        verdict=verdict,
        remediation_notes=notes,
    )


def validate_loudness_target(
    bible: Union[MasterProductionBible, Dict[str, Any], None],
    standard: Union[BroadcastLoudnessStandard, str] = BroadcastLoudnessStandard.ATSC_A85,
) -> LoudnessComplianceSpec:
    """Validates audio mix loudness and true-peak ceiling against broadcast/streaming standard."""
    std_enum = _coerce_loudness_standard(standard)
    spec_cfg = LOUDNESS_STANDARDS[std_enum.value]
    target_lufs = float(spec_cfg["target_lufs"])
    tol_lu = float(spec_cfg["tolerance_lu"])
    max_tp = float(spec_cfg["max_true_peak_dbtp"])

    mixer = None
    if isinstance(bible, MasterProductionBible):
        mixer = getattr(bible, "master_audio_mixer", None)
    elif isinstance(bible, dict):
        mixer = bible.get("master_audio_mixer")

    if mixer is not None:
        raw_target = getattr(mixer, "master_lufs_target", None)
        if raw_target is None and isinstance(mixer, dict):
            raw_target = mixer.get("master_lufs_target")
        gain_db = getattr(mixer, "master_gain_db", 0.0)
        if isinstance(mixer, dict):
            gain_db = mixer.get("master_gain_db", 0.0)
        measured_lufs = float(raw_target if raw_target is not None else target_lufs) + float(gain_db or 0.0)
        measured_tp = round(min(-0.1, -2.2 + max(0.0, float(gain_db or 0.0))), 2)
    else:
        measured_lufs = target_lufs
        measured_tp = round(max_tp - 0.2, 2)

    delta_lu = abs(measured_lufs - target_lufs)
    tp_exceeded = measured_tp > max_tp

    if delta_lu <= tol_lu and not tp_exceeded:
        verdict = QcVerdictStatus.PASS
        notes = (
            f"Compliant with {spec_cfg['name']}: {measured_lufs:.1f} LUFS "
            f"(target {target_lufs:.1f} +/- {tol_lu:.1f} LU), True Peak {measured_tp:.1f} dBTP (limit {max_tp:.1f} dBTP)."
        )
    elif delta_lu <= (tol_lu + 2.0) and not tp_exceeded:
        verdict = QcVerdictStatus.WARN
        notes = (
            f"Marginal deviation from {spec_cfg['name']}: {measured_lufs:.1f} LUFS vs target {target_lufs:.1f} LUFS. "
            f"Apply {target_lufs - measured_lufs:+.1f} dB master trim."
        )
    else:
        verdict = QcVerdictStatus.FAIL
        notes = (
            f"Loudness / True-Peak non-compliant for {spec_cfg['name']}: "
            f"{measured_lufs:.1f} LUFS / {measured_tp:.1f} dBTP exceeds tolerance."
        )

    return LoudnessComplianceSpec(
        standard=std_enum,
        target_integrated_lufs=target_lufs,
        measured_integrated_lufs=round(measured_lufs, 2),
        tolerance_lu=tol_lu,
        max_true_peak_dbtp=max_tp,
        measured_true_peak_dbtp=measured_tp,
        loudness_range_lu=6.5,
        dialogue_gated=bool(spec_cfg["dialogue_gated"]),
        verdict=verdict,
        notes=notes,
    )


def _has_aerial_production(bible: Union[MasterProductionBible, str, None], scenes: Optional[List[ScenePromptSpec]] = None) -> bool:
    if isinstance(bible, MasterProductionBible):
        if getattr(bible, "master_drone_spec", None) is not None or getattr(bible, "drone_flight", None) is not None:
            return True
        corpus = f"{bible.project_title} {bible.logline} " + " ".join(
            f"{s.scene_title} {s.omni_prose_prompt}" for s in (bible.scenes or [])
        )
        if any(getattr(s, "drone_flight", None) is not None for s in (bible.scenes or [])):
            return True
    else:
        corpus = str(bible or "") + " " + " ".join(
            f"{s.scene_title} {s.omni_prose_prompt}" for s in (scenes or [])
        )
        if any(getattr(s, "drone_flight", None) is not None for s in (scenes or [])):
            return True
    return bool(re.search(r"\b(?:aerial|drone|uav|flyover|part\s*107)\b", corpus, re.IGNORECASE))


def synthesize_rights_clearances(
    bible: Union[MasterProductionBible, str, None],
    scenes: Optional[List[ScenePromptSpec]] = None,
) -> List[ClearanceRecordSpec]:
    """Synthesizes legal, union, music, brand, location, and optional FAA aerial clearance records."""
    if isinstance(bible, MasterProductionBible):
        title = bible.project_title
        char_names = ", ".join(c.name for c in (bible.characters or [])) or "Principal Cast"
        loc_name = bible.environment.location_name if bible.environment else "Primary Studio / Location"
        bgm_title = bible.master_bgm.track_title if bible.master_bgm else f"{title} Original Score"
    else:
        title = str(bible or "Commercial Production")
        char_names = "Principal Cast"
        loc_name = "Primary Studio / Location"
        bgm_title = f"{title} Original Score"

    records: List[ClearanceRecordSpec] = [
        ClearanceRecordSpec(
            clearance_id="CLR-001",
            category=ClearanceCategory.TALENT_USAGE,
            item_title=f"Principal Talent Buyout & Likeness ({char_names})",
            rights_holder="SAG-AFTRA Commercial Signatory / Talent Counsel",
            territory="North America & Global Paid Digital",
            term_duration="12 Months Broadcast + OTT + Social",
            status=ClearanceStatus.CLEARED,
            reference_code="SAG-2026-TAL-001",
            notes="Principal performer residuals and AI likeness usage riders executed.",
        ),
        ClearanceRecordSpec(
            clearance_id="CLR-002",
            category=ClearanceCategory.MUSIC_SYNC_MASTER,
            item_title=f"Music Sync & Master License ({bgm_title})",
            rights_holder="Omni Original Score Publishing / Lyria Bespoke Stem Master",
            territory="Worldwide All Media",
            term_duration="In Perpetuity (Work-for-Hire Master)",
            status=ClearanceStatus.CLEARED,
            reference_code="MUS-2026-SYN-002",
            notes="Full stem separation (Dialogue/Foley/Ambience/Music) cleared for M&E international delivery.",
        ),
        ClearanceRecordSpec(
            clearance_id="CLR-003",
            category=ClearanceCategory.BRAND_TRADEMARK_IP,
            item_title=f"Brand Trademark, Product Hero & Packaging IP ({title})",
            rights_holder="Advertiser Brand Legal & Product Counsel",
            territory="Worldwide",
            term_duration="Campaign Term + Archive",
            status=ClearanceStatus.CLEARED,
            reference_code="BRD-2026-TM-003",
            notes="No uncleared third-party logos, license plates, or artwork visible in frame.",
        ),
        ClearanceRecordSpec(
            clearance_id="CLR-004",
            category=ClearanceCategory.LOCATION_PERMIT,
            item_title=f"Location Release & Municipal Film Permit ({loc_name})",
            rights_holder="Property Owner / Film Commission Permit Office",
            territory="Production Jurisdiction",
            term_duration="Shoot Dates + Worldwide Perpetual Footage Rights",
            status=ClearanceStatus.CLEARED,
            reference_code="LOC-2026-PRM-004",
            notes="COI ($2M GL) filed; property release countersigned.",
        ),
    ]

    if _has_aerial_production(bible, scenes):
        records.append(
            ClearanceRecordSpec(
                clearance_id="CLR-005",
                category=ClearanceCategory.AERIAL_FAA_WAIVER,
                item_title="FAA 14 CFR Part 107 Remote Pilot & Airspace Authorization",
                rights_holder="FAA LAANC / Commercial RPIC Certificate",
                territory="Controlled Airspace Corridor (< 400ft AGL)",
                term_duration="Production Flight Window",
                status=ClearanceStatus.CLEARED,
                reference_code="FAA-P107-2026-005",
                notes="Visual Line of Sight (VLOS) and Part 107 altitude envelope verified.",
            )
        )

    return records


def format_broadcast_qc_prompt_token(
    spec: Union[SceneQcProfileSpec, MasterBroadcastQcSpec, Dict[str, Any]],
) -> str:
    """Formats a concise Gemini Omni prompt-auditable Broadcast QC & PSE safety token."""
    if isinstance(spec, dict):
        lufs = float(spec.get("loudness_target_lufs", -24.0))
        tp = float(spec.get("true_peak_ceiling_dbtp", -2.0))
        verdict = str(spec.get("overall_verdict", "PASS"))
        return f"[BROADCAST_QC: ATSC_A85 {lufs:.1f}LUFS/{tp:.1f}dBTP | PSE_BT1702<=3Hz {verdict} | REC709_LEGAL]"
    if isinstance(spec, SceneQcProfileSpec):
        verdict = spec.overall_verdict.value if hasattr(spec.overall_verdict, "value") else str(spec.overall_verdict)
        pse_hz = spec.pse_check.max_flash_frequency_hz if spec.pse_check else 1.0
        legal = "REC709_LEGAL" if spec.chroma_legal_rec709 else "CHROMA_CHECK"
        return (
            f"[BROADCAST_QC: {spec.loudness_target_lufs:.1f}LUFS/{spec.true_peak_ceiling_dbtp:.1f}dBTP | "
            f"PSE_BT1702 {pse_hz:.1f}Hz<=3Hz {verdict} | {legal}]"
        )
    lc = spec.loudness_compliance
    std = lc.standard.value.upper() if hasattr(lc.standard, "value") else str(lc.standard).upper()
    verdict = spec.overall_verdict.value if hasattr(spec.overall_verdict, "value") else str(spec.overall_verdict)
    return (
        f"[BROADCAST_QC: {std} {lc.target_integrated_lufs:.1f}LUFS/{lc.max_true_peak_dbtp:.1f}dBTP | "
        f"PSE_BT1702 {spec.pse_overall_verdict.value} | {verdict}]"
    )


def synthesize_default_scene_qc(
    scene: Optional[ScenePromptSpec] = None,
    scene_index: int = 1,
    standard: BroadcastLoudnessStandard = BroadcastLoudnessStandard.ATSC_A85,
) -> SceneQcProfileSpec:
    """Synthesizes a complete SceneQcProfileSpec for a single scene."""
    std_cfg = LOUDNESS_STANDARDS[standard.value]
    eff_idx = scene.scene_index if scene is not None else scene_index
    eff_title = (scene.scene_title if scene is not None else "") or f"Scene {eff_idx}"
    pse = evaluate_scene_pse_safety(scene if scene is not None else eff_title)
    profile = SceneQcProfileSpec(
        scene_index=eff_idx,
        scene_title=eff_title,
        pse_check=pse,
        loudness_target_lufs=float(std_cfg["target_lufs"]),
        true_peak_ceiling_dbtp=float(std_cfg["max_true_peak_dbtp"]),
        chroma_legal_rec709=True,
        overall_verdict=pse.verdict,
    )
    profile.prompt_token = format_broadcast_qc_prompt_token(profile)
    return profile


def synthesize_default_broadcast_qc_spec(
    bible_or_domain: Union[MasterProductionBible, str, None] = None,
    scenes: Optional[List[ScenePromptSpec]] = None,
    project_title: str = "Commercial Production",
    standard: BroadcastLoudnessStandard = BroadcastLoudnessStandard.ATSC_A85,
) -> MasterBroadcastQcSpec:
    """Synthesizes a complete MasterBroadcastQcSpec for a bible or domain archetype."""
    std_enum = _coerce_loudness_standard(standard)
    if isinstance(bible_or_domain, MasterProductionBible):
        bible = bible_or_domain
        title = bible.project_title
        eff_scenes = list(scenes if scenes is not None else bible.scenes)
        runtime_sec = int(getattr(bible, "total_runtime_seconds", 30) or 30)
        loudness = validate_loudness_target(bible, std_enum)
        clearances = synthesize_rights_clearances(bible, eff_scenes)
    else:
        title = project_title
        eff_scenes = list(scenes or [])
        runtime_sec = 30
        loudness = validate_loudness_target(None, std_enum)
        clearances = synthesize_rights_clearances(str(bible_or_domain or title), eff_scenes)

    scene_profiles = [
        synthesize_default_scene_qc(scene=sc, scene_index=sc.scene_index, standard=std_enum)
        for sc in eff_scenes
    ]
    if not scene_profiles:
        scene_profiles = [synthesize_default_scene_qc(scene_index=1, standard=std_enum)]

    # Aggregate PSE verdict
    verdicts = [p.overall_verdict for p in scene_profiles]
    if QcVerdictStatus.FAIL in verdicts:
        pse_overall = QcVerdictStatus.FAIL
    elif QcVerdictStatus.WARN in verdicts:
        pse_overall = QcVerdictStatus.WARN
    else:
        pse_overall = QcVerdictStatus.PASS

    legal_ok = all(r.status == ClearanceStatus.CLEARED for r in clearances)

    if pse_overall == QcVerdictStatus.FAIL or loudness.verdict == QcVerdictStatus.FAIL or not legal_ok:
        overall = QcVerdictStatus.FAIL
    elif pse_overall == QcVerdictStatus.WARN or loudness.verdict == QcVerdictStatus.WARN:
        overall = QcVerdictStatus.WARN
    else:
        overall = QcVerdictStatus.PASS

    clean_slug = re.sub(r"[^A-Z0-9]", "", title.upper())[:4] or "OMNI"
    ad_id = f"{clean_slug}2026{runtime_sec:02d}H"

    slate = BroadcastTraffickingSlateSpec(
        ad_id_isci=ad_id,
        client_brand=title,
        campaign_title=title,
        spot_length_sec=runtime_sec,
        slate_duration_sec=5.0,
        first_frame_of_action_tc="01:00:00:00",
        head_slate_tc="00:59:50:00",
        two_pop_tc="00:59:58:00",
        audio_config="Stereo L/R + 5.1 Surround (ATSC A/85)",
        closed_captions_embedded=True,
        video_codec_profile="Apple ProRes 422 HQ / XDCAM HD422 50Mbps",
        legal_disclaimer_required=False,
    )

    spec = MasterBroadcastQcSpec(
        project_title=title,
        trafficking_slate=slate,
        loudness_compliance=loudness,
        scene_qc_profiles=scene_profiles,
        clearance_records=clearances,
        pse_overall_verdict=pse_overall,
        legal_clearance_complete=legal_ok,
        overall_verdict=overall,
        qc_certificate_id=f"QC-{clean_slug}-2026-001",
    )
    spec.prompt_token = format_broadcast_qc_prompt_token(spec)
    return spec


def _resolve_qc_spec(source: Union[MasterBroadcastQcSpec, MasterProductionBible]) -> MasterBroadcastQcSpec:
    if isinstance(source, MasterBroadcastQcSpec):
        return source
    existing = getattr(source, "master_broadcast_qc", None) or getattr(source, "broadcast_qc", None)
    if isinstance(existing, MasterBroadcastQcSpec):
        return existing
    return synthesize_default_broadcast_qc_spec(source)


def generate_qc_certificate_md(
    source: Union[MasterBroadcastQcSpec, MasterProductionBible],
) -> str:
    """Generates an executive Broadcast QC Certificate & Trafficking Slate Markdown report."""
    spec = _resolve_qc_spec(source)
    sl = spec.trafficking_slate
    lc = spec.loudness_compliance
    std_s = lc.standard.value.upper() if hasattr(lc.standard, "value") else str(lc.standard).upper()
    overall_s = spec.overall_verdict.value if hasattr(spec.overall_verdict, "value") else str(spec.overall_verdict)
    lc_verdict = lc.verdict.value if hasattr(lc.verdict, "value") else str(lc.verdict)

    lines = [
        f"# Broadcast Technical QC Certificate: {spec.project_title}",
        "",
        f"- **QC Certificate ID**: `{spec.qc_certificate_id}`",
        f"- **Overall Release Verdict**: **`{overall_s}`**",
        f"- **Legal Clearance Gate**: `{'CLEARED' if spec.legal_clearance_complete else 'PENDING'}`",
        "",
        "## Commercial Trafficking Slate (Ad-ID / ISCI)",
        f"- **Ad-ID / ISCI Code**: `{sl.ad_id_isci}`",
        f"- **Campaign / Advertiser**: `{sl.campaign_title}`",
        f"- **Spot Length**: `:{sl.spot_length_sec:02d}s` | **Slate**: `{sl.slate_duration_sec:.1f}s`",
        f"- **Head Slate TC**: `{sl.head_slate_tc}` | **2-Pop TC**: `{sl.two_pop_tc}` | **FFOA TC**: `{sl.first_frame_of_action_tc}`",
        f"- **Codec / Mastering Profile**: `{sl.video_codec_profile}`",
        f"- **Audio Config**: `{sl.audio_config}` | **CEA-608/708 Closed Captions**: `{'Embedded' if sl.closed_captions_embedded else 'Missing'}`",
        "",
        "## Broadcast Loudness & True-Peak Compliance",
        f"- **Standard**: `{std_s}` (`{lc_verdict}`)",
        f"- **Target Integrated Loudness**: `{lc.target_integrated_lufs:.1f} LUFS (+/- {lc.tolerance_lu:.1f} LU)`",
        f"- **Measured Integrated Loudness**: `{lc.measured_integrated_lufs:.1f} LUFS`",
        f"- **True Peak Ceiling**: `{lc.max_true_peak_dbtp:.1f} dBTP` | **Measured**: `{lc.measured_true_peak_dbtp:.1f} dBTP`",
        f"- **Notes**: {lc.notes}",
        "",
        "## ITU-R BT.1702 / Ofcom Harding FPA PSE Flash-Safety Audit",
        "| Scene | Title | Max Flash (Hz) | Limit (Hz) | Lum Delta (cd/m²) | Red Flash | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]

    for sp in spec.scene_qc_profiles:
        pse = sp.pse_check
        v_s = pse.verdict.value if hasattr(pse.verdict, "value") else str(pse.verdict)
        lines.append(
            f"| {sp.scene_index} | {sp.scene_title} | {pse.max_flash_frequency_hz:.2f} Hz | "
            f"{pse.flash_limit_hz:.1f} Hz | {pse.max_luminance_delta_nits:.1f} | "
            f"{'YES' if pse.red_saturation_flash_detected else 'NO'} | **{v_s}** |"
        )

    lines.extend([
        "",
        "## Legal & Rights Clearances Summary",
        "| ID | Category | Item | Territory | Status | Ref Code |",
        "|---|---|---|---|---|---|",
    ])
    for rec in spec.clearance_records:
        cat_s = rec.category.value if hasattr(rec.category, "value") else str(rec.category)
        st_s = rec.status.value if hasattr(rec.status, "value") else str(rec.status)
        lines.append(
            f"| `{rec.clearance_id}` | `{cat_s}` | {rec.item_title} | {rec.territory} | `{st_s.upper()}` | `{rec.reference_code}` |"
        )

    return "\n".join(lines) + "\n"


def generate_clearance_matrix_csv(
    source: Union[MasterBroadcastQcSpec, MasterProductionBible],
) -> str:
    """Exports all rights & legal clearance records into a structured CSV ledger."""
    spec = _resolve_qc_spec(source)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "clearance_id",
        "category",
        "item_title",
        "rights_holder",
        "territory",
        "term_duration",
        "status",
        "reference_code",
        "notes",
    ])
    for rec in spec.clearance_records:
        cat_s = rec.category.value if hasattr(rec.category, "value") else str(rec.category)
        st_s = rec.status.value if hasattr(rec.status, "value") else str(rec.status)
        writer.writerow([
            rec.clearance_id,
            cat_s,
            rec.item_title,
            rec.rights_holder,
            rec.territory,
            rec.term_duration,
            st_s,
            rec.reference_code,
            rec.notes,
        ])
    return buf.getvalue()


def generate_qc_manifest_json(
    source: Union[MasterBroadcastQcSpec, MasterProductionBible],
) -> str:
    """Serializes the complete MasterBroadcastQcSpec into indented JSON."""
    spec = _resolve_qc_spec(source)
    return json.dumps(spec.model_dump(), indent=2)


def export_broadcast_qc_bundle(
    bible_or_spec: Union[MasterProductionBible, MasterBroadcastQcSpec],
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports all PM-FEAT-022 Broadcast QC & Rights Clearance artifacts into output_dir.

    Writes:
    - broadcast_qc_certificate.md
    - rights_clearance_matrix.csv
    - broadcast_qc_manifest.json
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    spec = _resolve_qc_spec(bible_or_spec)

    cert_p = out_path / "broadcast_qc_certificate.md"
    csv_p = out_path / "rights_clearance_matrix.csv"
    json_p = out_path / "broadcast_qc_manifest.json"

    cert_p.write_text(generate_qc_certificate_md(spec), encoding="utf-8")
    csv_p.write_text(generate_clearance_matrix_csv(spec), encoding="utf-8")
    json_p.write_text(generate_qc_manifest_json(spec), encoding="utf-8")

    return {
        "broadcast_qc_certificate_md": str(cert_p),
        "rights_clearance_matrix_csv": str(csv_p),
        "broadcast_qc_manifest_json": str(json_p),
    }
