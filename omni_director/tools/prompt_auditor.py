"""Prompt Auditor tool implementing the 7-Point Gemini Omni Prompting Verification Checklist and Self-Healing Loop."""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
from omni_director.schemas import (
    AuditResult,
    EditBridgeSpec,
    InterSceneCutCheckSpec,
    LikenessConsentStatus,
    LocaleSyncStatus,
    LocalizationManifestSpec,
    LocalizedLineSpec,
    MasterProductionBible,
    PromptAuditResult,
    QcVerdictStatus,
    RegimeType,
    ReviewApprovalStatus,
    RiskSeverityLevel,
    SafetySignoffStatus,
    ScenePromptSpec,
    SpottingManifestSpec,
    StorytellingMode,
)
from omni_director.tools.optical_lens import format_optical_prompt_token
from omni_director.tools.dof_simulator import format_dof_prompt_token
from omni_director.tools.dit_lut import format_lut_prompt_token
from omni_director.tools.spatial_audio import format_spatial_audio_prompt_token
from omni_director.tools.vfx_compositor import format_vfx_compositing_prompt_token
from omni_director.tools.hdr_signal import format_hdr_prompt_token
from omni_director.tools.stripboard_scheduler import format_script_breakdown_prompt_token
from omni_director.tools.film_emulation import (
    format_film_emulation_prompt_token,
    synthesize_default_film_stock,
)
from omni_director.tools.clapper_slate import (
    format_clapper_slate_prompt_token,
    synthesize_default_clapper_slate,
)
from omni_director.tools.drone_flight import (
    format_drone_flight_prompt_token,
    synthesize_default_drone_flight,
)
from omni_director.tools.delivery_reframe import (
    format_reframe_prompt_token,
    synthesize_default_scene_reframe,
)
from omni_director.tools.broadcast_qc import (
    format_broadcast_qc_prompt_token,
    synthesize_default_scene_qc,
)
from omni_director.tools.continuity_blocking import (
    evaluate_180_axis_and_30_rule,
    format_continuity_prompt_token,
    synthesize_scene_blocking,
)
from omni_director.tools.review_notes import format_review_prompt_token
from omni_director.tools.c2pa_provenance import (
    format_c2pa_prompt_token,
    synthesize_scene_c2pa_provenance,
    verify_model_lineage_2026,
)
from omni_director.tools.safety_risk import (
    assess_scene_hazards,
    format_safety_prompt_token,
)


def _format_localization_prompt_token(
    locale_tracks: Optional[List[Any]] = None,
    localization_manifest: Optional[LocalizationManifestSpec] = None,
) -> str:
    """Formats a compact machine telemetry token for PM-FEAT-027 localization & ADR timing."""
    tracks = list(locale_tracks or [])
    tags: List[str] = []
    max_ratio = 1.0
    worst_status = LocaleSyncStatus.LOCKED.value
    rank = {
        LocaleSyncStatus.LOCKED.value: 0,
        LocaleSyncStatus.STRETCH_CAUTION.value: 1,
        LocaleSyncStatus.RESCRIPT_REQUIRED.value: 2,
    }
    for tr in tracks:
        tag = getattr(tr, "bcp47_tag", None) or (tr.get("bcp47_tag") if isinstance(tr, dict) else None)
        loc = getattr(tr, "locale", None) or (tr.get("locale") if isinstance(tr, dict) else None)
        label = str(tag or loc or "").strip()
        if label and label not in tags:
            tags.append(label)
        ratio = getattr(tr, "lip_sync_ratio", None) if not isinstance(tr, dict) else tr.get("lip_sync_ratio")
        if isinstance(ratio, (int, float)) and float(ratio) > max_ratio:
            max_ratio = float(ratio)
        st = getattr(tr, "sync_status", None) if not isinstance(tr, dict) else tr.get("sync_status")
        st_str = (st.value if hasattr(st, "value") else str(st or LocaleSyncStatus.LOCKED.value)).lower()
        if rank.get(st_str, 0) > rank.get(worst_status, 0):
            worst_status = st_str

    if not tags and localization_manifest is not None:
        tags = list(getattr(localization_manifest, "target_locales", None) or [])
        if not tags and getattr(localization_manifest, "territories", None):
            tags = [
                str(getattr(t, "bcp47_tag", "") or getattr(t, "locale", ""))
                for t in localization_manifest.territories
                if getattr(t, "bcp47_tag", "") or getattr(t, "locale", "")
            ]
    if not tags and localization_manifest is not None:
        tags = [str(getattr(localization_manifest, "source_locale", "en-US") or "en-US")]

    imsc1 = getattr(localization_manifest, "imsc1_profile", "imsc1-text-1.1") if localization_manifest is not None else "imsc1-text-1.1"
    return f"[LOCALIZATION_ADR: locales={','.join(tags)} max_ratio={max_ratio:.2f} status={worst_status} profile={imsc1}]"


def _format_spotting_prompt_token(
    edit_bridge: Optional[EditBridgeSpec] = None,
    spotting_manifest: Optional[SpottingManifestSpec] = None,
) -> str:
    """Formats a compact machine telemetry token for PM-FEAT-028 editorial J/L-cut & BPM spotting sync."""
    bpm = float(getattr(spotting_manifest, "tempo_bpm", 120.0)) if spotting_manifest is not None else 120.0
    if edit_bridge is not None:
        btype = getattr(edit_bridge, "bridge_type", "j_cut")
        btype_str = btype.value if hasattr(btype, "value") else str(btype)
        j_pre = int(getattr(edit_bridge, "j_prelap_frames", 12))
        l_over = int(getattr(edit_bridge, "l_overhang_frames", 0))
        beat_idx = int(getattr(edit_bridge, "nearest_beat_index", 0))
        locked = bool(getattr(edit_bridge, "beat_locked", True))
        return (
            f"[SPOTTING_SYNC: bridge={btype_str} j_pre={j_pre}f l_over={l_over}f "
            f"beat={beat_idx} locked={str(locked).lower()} bpm={bpm:.0f}]"
        )
    fpb = float(getattr(spotting_manifest, "frames_per_beat", 12.0)) if spotting_manifest is not None else 12.0
    splits = int(getattr(spotting_manifest, "total_split_edits", 0)) if spotting_manifest is not None else 0
    score = float(getattr(spotting_manifest, "beat_alignment_score", 95.0)) if spotting_manifest is not None else 95.0
    return f"[SPOTTING_SYNC: bpm={bpm:.0f} fpb={fpb:.1f} split_edits={splits} score={score:.1f}]"


def audit_omni_scene_prompt(
    scene: Union[ScenePromptSpec, str],
    regime: Optional[Union[RegimeType, int]] = None,
    scene_index: int = 1,
    duration_seconds: int = 15,
    storytelling_mode: Optional[StorytellingMode] = None,
    **kwargs: Any,
) -> AuditResult:
    """Audits a single ScenePromptSpec or prompt string against the 7-Point Gemini Omni prompt standards.

    Rules:
    1. No internal markdown headers (###, ##, #) or HTML headings (<h1>-<h6>) inside the generation prompt.
    2. Max 3 serialized action beats per 10s window (prevents temporal rushing and object morphing).
    3. Regime 2 mandates 1.0x real-time speed, gravity/friction locks, and a 5-part kinetic contact chain.
    4. CRAFT camera completeness (Composition, Route, Action Anchor, Focus/Axis Invariant, Tone/Rig).
    5. Max 3 Nano Banana image references (<image_1>, <image_2>, <image_3>) with single-duty contracts.
    6. Synchronized diegetic audio specification included natively.
    7. Mode B extension continuity check (unbroken continuous flow if extension scene or scene_index > 1 in Mode B).
    """
    errors: List[str] = []
    warnings: List[str] = []
    details: dict = {}

    # Handle positional signature variations (e.g. audit_omni_scene_prompt(scene, 1))
    if isinstance(regime, int):
        scene_index = regime
        regime = None

    if isinstance(scene, ScenePromptSpec):
        prompt = scene.omni_prose_prompt
        effective_scene_index = scene.scene_index
        action_beats = scene.action_beats
        craft_camera = scene.craft_camera
        diegetic_sonic = scene.diegetic_sonic
        timestamp_range = scene.timestamp_range
        kinetic_contact_chain = scene.kinetic_contact_chain
        effective_regime = regime or scene.regime
    else:
        prompt = str(scene)
        effective_scene_index = scene_index
        action_beats = kwargs.get("action_beats", [])
        craft_camera = kwargs.get("craft_camera", None)
        diegetic_sonic = kwargs.get("diegetic_sonic", None)
        timestamp_range = kwargs.get("timestamp_range", f"00:00 - 00:{duration_seconds:02d}")
        kinetic_contact_chain = kwargs.get("kinetic_contact_chain", "")
        effective_regime = regime or RegimeType.REGIME_1_ATMOSPHERIC

    # Rule 1: Clean natural prose formatting (NO markdown or HTML headers inside prompt)
    heading_match = re.search(r"(?:^|\n)\s*#{1,6}\s+", prompt)
    html_heading_match = re.search(r"</?h[1-6][^>]*>", prompt, re.IGNORECASE)
    if heading_match or html_heading_match:
        errors.append(
            "Rule 1 Violation: Markdown heading ('#', '##', '###') or HTML heading ('<h1>'-'<h6>') detected inside omni_prose_prompt. "
            "Gemini Omni's internal visual text engine can misinterpret headings as graphic text overlay instructions. "
            "Format prompt as unbroken natural-language prose."
        )

    # Rule 2: Max 3 serialized action beats per 10s window
    details["action_beats_count"] = len(action_beats)
    if len(action_beats) > 3:
        errors.append(
            f"Rule 2 Violation: {len(action_beats)} action beats detected. "
            "Gemini Omni enforces a strict ceiling of max 3 serialized cause-and-effect beats per 10s window."
        )

    # Detect speed ramp configuration
    speed_ramp_spec = getattr(scene, "speed_ramp", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("speed_ramp")
    has_speed_ramp = False
    if speed_ramp_spec is not None:
        mode_val = getattr(speed_ramp_spec, "mode", None)
        mode_str = mode_val.value if hasattr(mode_val, "value") else str(mode_val)
        if mode_str != "constant_realtime":
            has_speed_ramp = True
    elif re.search(r"\b(?:speed\s*ramp|time-?warp|time\s*dilation|deceleration\s*impact|acceleration\s*burst|snap\s*freeze)\b", prompt, re.IGNORECASE):
        has_speed_ramp = True

    # Optical lens recognition & reward (PM-FEAT-007)
    optical_lens_spec = getattr(scene, "optical_lens", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("optical_lens")
    if optical_lens_spec is None and craft_camera is not None:
        optical_lens_spec = getattr(craft_camera, "optical_lens", None)
    lens_patterns = r"(?:\bT\s*\d+(?:\.\d+)?\b|focal\s*length|\b\d+mm\b|anamorphic|spherical|Super35|Full\s*Frame|ARRI\s*LF|IMAX|VistaVision|bokeh|Cooke|Zeiss|apochromatic|hyperfocal)"
    lens_match = re.search(lens_patterns, prompt, re.IGNORECASE)
    if optical_lens_spec is not None or lens_match:
        details["optical_lens_compliant"] = True
        details["optical_lens_reward"] = 2.0
        if optical_lens_spec is not None:
            sensor_str = optical_lens_spec.sensor_format.value if hasattr(optical_lens_spec.sensor_format, "value") else str(optical_lens_spec.sensor_format)
            details["optical_lens_descriptor"] = f"{optical_lens_spec.focal_length_mm}mm T{optical_lens_spec.aperture_t_stop} ({sensor_str})"

    # Virtual Production stage recognition & reward (PM-FEAT-008)
    vp_stage_spec = getattr(scene, "virtual_production", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("virtual_production")
    vp_patterns = r"(?:LED\s*(?:wall|volume)|nDisplay|virtual\s*production|frustum|in-camera\s*VFX|ICVFX|DMX|parallax\s*depth)"
    vp_match = re.search(vp_patterns, prompt, re.IGNORECASE)
    if vp_stage_spec is not None or vp_match:
        details["virtual_production_compliant"] = True
        details["virtual_production_reward"] = 2.0
        if vp_stage_spec is not None:
            proto_str = vp_stage_spec.frustum_tracking_protocol.value if hasattr(vp_stage_spec.frustum_tracking_protocol, "value") else str(vp_stage_spec.frustum_tracking_protocol)
            details["virtual_production_descriptor"] = f"{vp_stage_spec.stage_name} ({proto_str})"

    # Motion Control (MoCo) rig recognition & reward (PM-FEAT-009)
    moco_rig_spec = getattr(scene, "moco_rig", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("moco_rig")
    if moco_rig_spec is None and craft_camera is not None:
        moco_rig_spec = getattr(craft_camera, "moco_rig", None)
    moco_patterns = r"(?:motion\s*control|moco|bolt\s*cinebot|technocrane|cablecam|motorized\s*dolly|russian\s*arm|drone\s*fpv|6-?DOF|trajectory\s*waypoint|robotic\s*(?:camera|rig)|cinebot)"
    moco_match = re.search(moco_patterns, prompt, re.IGNORECASE)
    if moco_rig_spec is not None or moco_match:
        details["moco_rig_compliant"] = True
        details["moco_rig_reward"] = 2.0
        if moco_rig_spec is not None:
            rig_str = moco_rig_spec.rig_type.value if hasattr(moco_rig_spec.rig_type, "value") else str(moco_rig_spec.rig_type)
            details["moco_rig_descriptor"] = f"{rig_str} ({moco_rig_spec.track_length_meters}m track, max {moco_rig_spec.max_velocity_mps}m/s)"
        elif moco_match:
            details["moco_rig_descriptor"] = moco_match.group(0)

    # Studio Lighting rig recognition & reward (PM-FEAT-010)
    lighting_rig_spec = getattr(scene, "lighting_rig", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("lighting_rig")
    lighting_patterns = r"(?:key\s*light|fill\s*light|rim\s*(?:light|backlight)|kicker|practicals|lighting\s*ratio|chiaroscuro|lux|cct|kelvin|\b\d{4}K\b|diffusion|skypanel|fresnel|softbox|atmospheric\s*haze|particulate\s*haze|volumetric\s*(?:light|shaft|haze)|mineral\s*haze|cryogenic\s*smoke|oil\s*fog)"
    lighting_match = re.search(lighting_patterns, prompt, re.IGNORECASE)
    if lighting_rig_spec is not None or lighting_match:
        details["lighting_rig_compliant"] = True
        details["lighting_rig_reward"] = 2.0
        if lighting_rig_spec is not None:
            details["lighting_rig_descriptor"] = f"{len(lighting_rig_spec.fixtures)} fixtures (Key:Fill {lighting_rig_spec.key_to_fill_ratio}:1, {lighting_rig_spec.total_lux} lux)"
        elif lighting_match:
            details["lighting_rig_descriptor"] = lighting_match.group(0)

    # Depth of Field (DoF) & Optical Focus recognition & reward (PM-FEAT-011)
    dof_spec_obj = getattr(scene, "dof_spec", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("dof_spec")
    if dof_spec_obj is None and craft_camera is not None:
        dof_spec_obj = getattr(craft_camera, "dof_spec", None)
    dof_patterns = r"(?:depth\s*of\s*field|\bdof\b|rack\s*focus|shallow\s*(?:focus|dof)|deep\s*focus|f\/\d+(?:\.\d+)?|T\d+(?:\.\d+)?|focal\s*plane|bokeh|circle\s*of\s*confusion|hyperfocal|focus\s*pull)"
    dof_match = re.search(dof_patterns, prompt, re.IGNORECASE)
    if dof_spec_obj is not None or dof_match:
        details["dof_spec_compliant"] = True
        details["dof_spec_reward"] = 1.0
        if dof_spec_obj is not None:
            details["dof_spec_descriptor"] = format_dof_prompt_token(dof_spec_obj)
        elif dof_match:
            details["dof_spec_descriptor"] = dof_match.group(0)

    # 3D LUT Cube Color Science recognition & reward (PM-FEAT-012)
    lut_spec_obj = getattr(scene, "lut_spec", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("lut_spec")
    if lut_spec_obj is None and isinstance(scene, ScenePromptSpec) and getattr(scene, "scene_color_look", None):
        lut_spec_obj = getattr(scene.scene_color_look, "lut_spec", None)
    lut_patterns = r"(?:3d\s*lut|\blut\b|\.cube|color\s*grade|asc\s*cdl|\bcdl\b|acescg|rec\.?709|gamut\s*transform|tetrahedral|film\s*stock|kodak|fuji|eterna|bleach\s*bypass)"
    lut_match = re.search(lut_patterns, prompt, re.IGNORECASE)
    if lut_spec_obj is not None or lut_match:
        details["lut_spec_compliant"] = True
        details["lut_spec_reward"] = 1.0
        if lut_spec_obj is not None:
            details["lut_spec_descriptor"] = format_lut_prompt_token(lut_spec_obj)
        elif lut_match:
            details["lut_spec_descriptor"] = lut_match.group(0)

    # Spatial Audio & Binaural Soundfield recognition & reward (PM-FEAT-013)
    spatial_audio_spec = getattr(scene, "spatial_audio", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("spatial_audio")
    if spatial_audio_spec is None and diegetic_sonic is not None:
        spatial_audio_spec = getattr(diegetic_sonic, "spatial_audio", None)
    spatial_patterns = r"(?:spatial\s*audio|dolby\s*atmos|7\.1\.4|binaural|ambisonic(?:s)?|soundfield|rt60|reverberation|impulse\s*response|acoustic\s*space|vbap)"
    spatial_match = re.search(spatial_patterns, prompt, re.IGNORECASE)
    if spatial_audio_spec is not None or spatial_match:
        details["spatial_audio_compliant"] = True
        details["spatial_audio_reward"] = 1.0
        if spatial_audio_spec is not None:
            details["spatial_audio_descriptor"] = format_spatial_audio_prompt_token(spatial_audio_spec)
        elif spatial_match:
            details["spatial_audio_descriptor"] = spatial_match.group(0)

    # Advanced Multi-Pass VFX Compositing recognition & reward (PM-FEAT-014)
    vfx_manifest_spec = getattr(scene, "vfx_compositing", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("vfx_compositing")
    vfx_patterns = r"(?:cryptomatte|render\s*pass(?:es)?|openexr|\.exr|nuke\s*comp|deep\s*compositing|beauty\s*pass|diffuse\s*pass|specular\s*pass|zdepth|depth\s*pass|motion\s*vector\s*pass|compositing\s*manifest)"
    vfx_match = re.search(vfx_patterns, prompt, re.IGNORECASE)
    if vfx_manifest_spec is not None or vfx_match:
        details["vfx_compositing_compliant"] = True
        details["vfx_compositing_reward"] = 1.0
        if vfx_manifest_spec is not None:
            details["vfx_compositing_descriptor"] = format_vfx_compositing_prompt_token(vfx_manifest_spec)
        elif vfx_match:
            details["vfx_compositing_descriptor"] = vfx_match.group(0)

    # HDR Signal & Color Volume recognition & reward (PM-FEAT-015)
    hdr_spec_obj = getattr(scene, "hdr_spec", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("hdr_spec")
    hdr_patterns = r"(?:\[HDR\s*Signal:?|hdr10|smpte\s*st\s*2084|st\s*2084|arib\s*std-b67|\bhlg\b|bt\.?2100|maxcll|maxfall|peak\s*luminance|\bnits\b)"
    hdr_match = re.search(hdr_patterns, prompt, re.IGNORECASE)
    if hdr_spec_obj is not None or hdr_match:
        details["hdr_signal_compliant"] = True
        details["hdr_signal_reward"] = 1.0
        if hdr_spec_obj is not None:
            details["hdr_signal_descriptor"] = format_hdr_prompt_token(hdr_spec_obj)
        elif hdr_match:
            details["hdr_signal_descriptor"] = hdr_match.group(0)

    # 1st AD Script Breakdown & Stripboard recognition & reward (PM-FEAT-016)
    breakdown_obj = getattr(scene, "breakdown_sheet", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("breakdown_sheet")
    breakdown_patterns = r"(?:\[1st\s*AD\s*Breakdown:?|stripboard|dood|day-out-of-days|script\s*breakdown|page\s*eighths|\b\d+\/8\s*pgs?\b|yellow\s*strip|blue\s*strip|white\s*strip|green\s*strip)"
    breakdown_match = re.search(breakdown_patterns, prompt, re.IGNORECASE)
    if breakdown_obj is not None or breakdown_match:
        details["script_breakdown_compliant"] = True
        details["script_breakdown_reward"] = 1.0
        if breakdown_obj is not None:
            details["script_breakdown_descriptor"] = format_script_breakdown_prompt_token(breakdown_obj)
        elif breakdown_match:
            details["script_breakdown_descriptor"] = breakdown_match.group(0)

    # Physical Film Stock Emulation recognition & reward (PM-FEAT-017)
    film_emulation_spec = getattr(scene, "film_emulation", None) if isinstance(scene, ScenePromptSpec) else (kwargs.get("film_emulation") or kwargs.get("film_stock"))
    film_patterns = r"(?:\[FILM[ _]EMULATION:?|\[FILM_STOCK:?|film\s*emulation|film\s*stock|silver\s*halide|dye\s*cloud|rem-jet|gate\s*weave|grain\s*density|5219|5207|5203|7219|eterna|fuji\s*eterna|kodak\s*vision3)"
    film_match = re.search(film_patterns, prompt, re.IGNORECASE)
    if film_match:
        details["film_emulation_compliant"] = True
        details["film_emulation_reward"] = 1.0
        if film_emulation_spec is not None:
            details["film_emulation_descriptor"] = format_film_emulation_prompt_token(film_emulation_spec)
        else:
            details["film_emulation_descriptor"] = film_match.group(0)
    elif film_emulation_spec is not None:
        details["film_emulation_configured"] = True

    # Clapper Slate & SMPTE 12M Timecode Sync recognition & reward (PM-FEAT-018)
    clapper_slate_spec = getattr(scene, "clapper_slate", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("clapper_slate")
    slate_patterns = r"(?:\[PRODUCTION[ _]SLATE:?|\[CLAPPER_SLATE:?|clapper\s*slate|production\s*slate|take\s*\d+|camera\s*roll|sound\s*roll|smpte\s*12m)"
    slate_match = re.search(slate_patterns, prompt, re.IGNORECASE)
    if slate_match:
        details["clapper_slate_compliant"] = True
        details["clapper_slate_reward"] = 1.0
        if clapper_slate_spec is not None:
            details["clapper_slate_descriptor"] = format_clapper_slate_prompt_token(clapper_slate_spec)
        else:
            details["clapper_slate_descriptor"] = slate_match.group(0)
    elif clapper_slate_spec is not None:
        details["clapper_slate_configured"] = True

    # Drone Flight Path & Aerial GPS Telemetry recognition & reward (PM-FEAT-019)
    drone_flight_spec = getattr(scene, "drone_flight", None) if isinstance(scene, ScenePromptSpec) else kwargs.get("drone_flight")
    drone_patterns = r"(?:\[DRONE[ _]FLIGHT:?|drone\s*flight|flight\s*path|aerial\s*orbit|gimbal\s*pitch|flight\s*waypoint|flyover\s*reveal)"
    drone_match = re.search(drone_patterns, prompt, re.IGNORECASE)
    has_aerial_keywords = bool(re.search(r"\b(?:aerial|drone|flyover|orbit|overhead|altitude|bird's-eye|birds eye|uav)\b", prompt, re.IGNORECASE))
    if drone_match or (drone_flight_spec is not None and has_aerial_keywords):
        details["drone_flight_compliant"] = True
        details["drone_flight_reward"] = 1.0
        if drone_flight_spec is not None:
            details["drone_flight_descriptor"] = format_drone_flight_prompt_token(drone_flight_spec)
        elif drone_match:
            details["drone_flight_descriptor"] = drone_match.group(0)
    elif drone_flight_spec is not None:
        details["drone_flight_configured"] = True

    # Multi-Aspect Social Reframe & Safe-Zone recognition & reward (PM-FEAT-021)
    reframe_spec_obj = (
        getattr(scene, "reframe_spec", None)
        if isinstance(scene, ScenePromptSpec)
        else (
            kwargs.get("reframe_spec")
            or kwargs.get("reframe")
            or kwargs.get("aspect_reframe")
            or kwargs.get("delivery_reframe")
        )
    )
    reframe_patterns = r"(?:\[REFRAME:?|reframe|safe-?zone|ui_safe|center\s+of\s+interest|coi\(|cutdown|pan-and-scan)"
    reframe_match = re.search(reframe_patterns, prompt, re.IGNORECASE)
    reframe_compliant_val = True
    if reframe_spec_obj is not None:
        if getattr(reframe_spec_obj, "all_platforms_cleared", True) is False:
            reframe_compliant_val = False
            details["reframe_compliant"] = False
            warnings.append(
                "Reframe Safe-Zone Warning: Subject COI intrudes into target social platform UI overlay zone."
            )
        else:
            details["reframe_compliant"] = True
            details["reframe_reward"] = 1.0
            details["reframe_descriptor"] = format_reframe_prompt_token(reframe_spec_obj)
    elif reframe_match:
        details["reframe_compliant"] = True
        details["reframe_reward"] = 1.0
        details["reframe_descriptor"] = reframe_match.group(0)

    # Broadcast QC, PSE Flash-Safety & Loudness recognition & reward (PM-FEAT-022)
    broadcast_qc_obj = (
        getattr(scene, "broadcast_qc", None)
        if isinstance(scene, ScenePromptSpec)
        else (
            kwargs.get("broadcast_qc")
            or kwargs.get("qc_spec")
            or kwargs.get("pse_qc")
            or kwargs.get("trafficking_qc")
        )
    )
    qc_patterns = r"(?:\[BROADCAST[ _]QC:?|atsc\s*a/?85|ebu\s*r128|pse_bt1702|itu-?r\s*bt\.?1702|lufs|lkfs|dbtp|rec709_legal|broadcast\s*qc)"
    qc_match = re.search(qc_patterns, prompt, re.IGNORECASE)
    broadcast_qc_compliant_val = True
    if broadcast_qc_obj is not None:
        ov = getattr(broadcast_qc_obj, "overall_verdict", QcVerdictStatus.PASS)
        ov_str = ov.value if hasattr(ov, "value") else str(ov)
        if ov_str == "FAIL":
            broadcast_qc_compliant_val = False
            details["broadcast_qc_compliant"] = False
            errors.append(
                "Broadcast QC Violation: Scene failed ITU-R BT.1702 PSE flash-safety (>3.0 Hz) or loudness/chroma ceiling."
            )
        else:
            details["broadcast_qc_compliant"] = True
            details["broadcast_qc_reward"] = 1.0
            details["broadcast_qc_descriptor"] = format_broadcast_qc_prompt_token(broadcast_qc_obj)
    elif qc_match:
        details["broadcast_qc_compliant"] = True
        details["broadcast_qc_reward"] = 1.0
        details["broadcast_qc_descriptor"] = qc_match.group(0)

    # 180-Degree Continuity Axis & Blocking recognition & reward (PM-FEAT-023)
    blocking_spec_obj = (
        getattr(scene, "blocking_spec", None)
        if isinstance(scene, ScenePromptSpec)
        else (
            kwargs.get("blocking_spec")
            or kwargs.get("continuity_blocking")
            or kwargs.get("blocking")
        )
    )
    continuity_patterns = r"(?:\[CONTINUITY[ _]AXIS:?|180_deg_lock|180-degree\s+axis|line\s+of\s+action|eyeline\s+match|screen\s+direction)"
    continuity_match = re.search(continuity_patterns, prompt, re.IGNORECASE)
    continuity_blocking_compliant_val = True
    if blocking_spec_obj is not None:
        if getattr(blocking_spec_obj, "one_eighty_lock_ok", True) is False:
            continuity_blocking_compliant_val = False
            details["continuity_blocking_compliant"] = False
            warnings.append(
                "Continuity Blocking Warning: Scene failed 180-degree axis lock on stage blocking."
            )
        else:
            details["continuity_blocking_compliant"] = True
            details["continuity_blocking_reward"] = 1.0
            details["continuity_blocking_descriptor"] = format_continuity_prompt_token(blocking_spec_obj)
    elif continuity_match:
        details["continuity_blocking_compliant"] = True
        details["continuity_blocking_reward"] = 1.0
        details["continuity_blocking_descriptor"] = continuity_match.group(0)

    # Client Review Signoff Gate recognition & reward (PM-FEAT-024)
    review_signoff_obj = (
        getattr(scene, "review_signoff", None)
        if isinstance(scene, ScenePromptSpec)
        else (
            kwargs.get("review_signoff")
            or kwargs.get("review_spec")
            or kwargs.get("client_review")
        )
    )
    review_patterns = r"(?:\[REVIEW[ _]GATE:?|review_gate|open_notes=)"
    review_match = re.search(review_patterns, prompt, re.IGNORECASE)
    review_gate_compliant_val = True
    if review_signoff_obj is not None:
        rev_status = getattr(review_signoff_obj, "approval_status", ReviewApprovalStatus.APPROVED)
        rev_status_str = rev_status.value if hasattr(rev_status, "value") else str(rev_status)
        if rev_status_str == ReviewApprovalStatus.CHANGES_REQUESTED.value:
            review_gate_compliant_val = False
            details["review_gate_compliant"] = False
            warnings.append(
                "Client Review Warning: Scene has CHANGES_REQUESTED pending stakeholder resolution."
            )
        else:
            details["review_gate_compliant"] = True
            details["review_gate_reward"] = 1.0
            details["review_gate_descriptor"] = format_review_prompt_token(review_signoff_obj)
    elif review_match:
        details["review_gate_compliant"] = True
        details["review_gate_reward"] = 1.0
        details["review_gate_descriptor"] = review_match.group(0)

    # C2PA Content Credentials v2.1 & Talent Likeness Provenance (PM-FEAT-025)
    c2pa_obj = (
        getattr(scene, "c2pa_provenance", None)
        if isinstance(scene, ScenePromptSpec)
        else (
            kwargs.get("c2pa_provenance")
            or kwargs.get("provenance_spec")
            or kwargs.get("content_credentials")
        )
    )
    c2pa_patterns = r"(?:\[C2PA[ _]PROVENANCE:?|\bc2pa\b|content\s+credentials|\bsynthid\b)"
    c2pa_match = re.search(c2pa_patterns, prompt, re.IGNORECASE)
    c2pa_provenance_compliant_val = True
    if c2pa_obj is not None:
        c2pa_models = [
            getattr(act, "model_used", "")
            for act in (getattr(c2pa_obj, "actions", None) or [])
            if getattr(act, "model_used", None)
        ] + [
            getattr(ing, "generative_model", "")
            for ing in (getattr(c2pa_obj, "ingredients", None) or [])
            if getattr(ing, "generative_model", None)
        ]
        if c2pa_models:
            lineage_ok, offending_models = verify_model_lineage_2026(c2pa_models)
            if not lineage_ok:
                c2pa_provenance_compliant_val = False
                details["c2pa_provenance_compliant"] = False
                errors.append(
                    f"C2PA Provenance Violation: Unapproved or legacy model reference(s) {offending_models} "
                    "detected in C2PA lineage actions/ingredients. Only 2026 Gemini Model Matrix identifiers are permitted."
                )

        if not bool(getattr(c2pa_obj, "eu_ai_act_art50_compliant", True)):
            c2pa_provenance_compliant_val = False
            details["c2pa_provenance_compliant"] = False
            errors.append(
                "C2PA Provenance Violation: Scene failed EU AI Act Article 50 synthetic disclosure compliance."
            )

        likeness_records = getattr(c2pa_obj, "talent_likeness_records", None) or []
        has_revoked = False
        has_pending = False
        for rec in likeness_records:
            cst = getattr(rec, "consent_status", None)
            cst_str = (cst.value if hasattr(cst, "value") else str(cst)).lower()
            if cst_str == LikenessConsentStatus.REVOKED.value:
                has_revoked = True
            elif cst_str == LikenessConsentStatus.PENDING_CONSENT.value:
                has_pending = True

        consent_ok = bool(getattr(c2pa_obj, "consent_gate_passed", True))
        if has_revoked:
            c2pa_provenance_compliant_val = False
            details["c2pa_provenance_compliant"] = False
            errors.append(
                "C2PA Likeness Consent Violation: Talent likeness consent is REVOKED; scene cannot proceed."
            )
        elif has_pending or not consent_ok:
            c2pa_provenance_compliant_val = False
            details["c2pa_provenance_compliant"] = False
            warnings.append(
                "C2PA Likeness Consent Warning: Talent likeness consent gate is pending or incomplete."
            )

        if c2pa_provenance_compliant_val:
            details["c2pa_provenance_compliant"] = True
            details["c2pa_provenance_reward"] = 1.0
            details["c2pa_provenance_descriptor"] = format_c2pa_prompt_token(c2pa_obj)
    elif c2pa_match:
        details["c2pa_provenance_compliant"] = True
        details["c2pa_provenance_reward"] = 1.0
        details["c2pa_provenance_descriptor"] = c2pa_match.group(0)

    # On-Set Stunt, Pyro/SFX, Rigging & Environmental Safety JSA (PM-FEAT-026)
    safety_risk_obj = (
        getattr(scene, "safety_risk", None)
        if isinstance(scene, ScenePromptSpec)
        else (
            kwargs.get("safety_risk")
            or kwargs.get("safety_spec")
            or kwargs.get("jsa_spec")
        )
    )
    safety_patterns = r"(?:\[SAFETY[ _]JSA:?|exclusion\s+zone|safety\s+bulletin|stunt\s+coordinator)"
    safety_match = re.search(safety_patterns, prompt, re.IGNORECASE)
    safety_risk_compliant_val = True
    if safety_risk_obj is not None:
        s_status = getattr(safety_risk_obj, "signoff_status", SafetySignoffStatus.CLEARED)
        s_status_str = (s_status.value if hasattr(s_status, "value") else str(s_status)).lower()
        hazards = getattr(safety_risk_obj, "hazards", None) or []
        has_critical_residual = any(
            (
                getattr(getattr(h, "residual_risk_level", None), "value", getattr(h, "residual_risk_level", ""))
                or ""
            ).lower() == RiskSeverityLevel.CRITICAL.value
            for h in hazards
        )
        if has_critical_residual:
            safety_risk_compliant_val = False
            details["safety_risk_compliant"] = False
            errors.append(
                "On-Set Safety Violation: Scene contains an unmitigated CRITICAL residual safety hazard."
            )
        if s_status_str == SafetySignoffStatus.HOLD_REQUIRED.value:
            safety_risk_compliant_val = False
            details["safety_risk_compliant"] = False
            warnings.append(
                "On-Set Safety Warning: Scene JSA signoff_status is HOLD_REQUIRED pending mitigation verification."
            )
        if safety_risk_compliant_val:
            details["safety_risk_compliant"] = True
            details["safety_risk_reward"] = 1.0
            details["safety_risk_descriptor"] = format_safety_prompt_token(safety_risk_obj)
    elif safety_match:
        details["safety_risk_compliant"] = True
        details["safety_risk_reward"] = 1.0
        details["safety_risk_descriptor"] = safety_match.group(0)

    # Multi-Territory Localization, ADR Dubbing & Lip-Sync Timing (PM-FEAT-027)
    bible_ctx = kwargs.get("bible")
    locale_tracks_obj = (
        getattr(scene, "locale_tracks", None)
        if isinstance(scene, ScenePromptSpec)
        else kwargs.get("locale_tracks")
    )
    loc_manifest_obj = (
        kwargs.get("localization_manifest")
        or kwargs.get("localization")
        or (getattr(bible_ctx, "localization_manifest", None) if bible_ctx is not None else None)
    )
    loc_patterns = r"(?:\[LOCALIZATION[ _]ADR:?|localization_adr|lip_sync_ratio|bcp47|imsc1)"
    loc_match = re.search(loc_patterns, prompt, re.IGNORECASE)
    localization_adr_compliant_val = True
    has_locale_tracks = bool(locale_tracks_obj)
    if has_locale_tracks or loc_manifest_obj is not None:
        max_drift = float(getattr(loc_manifest_obj, "max_allowed_drift_ratio", 1.15)) if loc_manifest_obj is not None else 1.15
        has_rescript = False
        for tr in (locale_tracks_obj or []):
            st = getattr(tr, "sync_status", None) if not isinstance(tr, dict) else tr.get("sync_status")
            st_str = (st.value if hasattr(st, "value") else str(st or "")).lower()
            ratio = getattr(tr, "lip_sync_ratio", 1.0) if not isinstance(tr, dict) else tr.get("lip_sync_ratio", 1.0)
            if st_str == LocaleSyncStatus.RESCRIPT_REQUIRED.value or float(ratio) > max_drift:
                has_rescript = True
                break
        if has_rescript or (loc_manifest_obj is not None and getattr(loc_manifest_obj, "broadcast_ready", True) is False):
            localization_adr_compliant_val = False
            details["localization_adr_compliant"] = False
            warnings.append(
                "Localization ADR Warning: Localized dialogue track exceeds lip-sync drift ceiling and requires rescript/viseme retiming."
            )
        else:
            details["localization_adr_compliant"] = True
            details["localization_adr_reward"] = 1.0
            details["localization_adr_descriptor"] = _format_localization_prompt_token(locale_tracks_obj, loc_manifest_obj)
    elif loc_match:
        details["localization_adr_compliant"] = True
        details["localization_adr_reward"] = 1.0
        details["localization_adr_descriptor"] = loc_match.group(0)

    # Editorial J-Cut / L-Cut Audio Bridge & BPM Beat-Grid Spotting Sync (PM-FEAT-028)
    edit_bridge_obj = (
        getattr(scene, "edit_bridge_in", None)
        if isinstance(scene, ScenePromptSpec)
        else (kwargs.get("edit_bridge_in") or kwargs.get("audio_bridge_in") or kwargs.get("j_l_bridge"))
    )
    spotting_manifest_obj = (
        kwargs.get("spotting_manifest")
        or kwargs.get("editorial_spotting")
        or (getattr(bible_ctx, "spotting_manifest", None) if bible_ctx is not None else None)
    )
    spotting_patterns = r"(?:\[SPOTTING[ _]SYNC:?|spotting_sync|j_cut|l_cut|jl_overlap|beat_locked)"
    spotting_match = re.search(spotting_patterns, prompt, re.IGNORECASE)
    spotting_sync_compliant_val = True
    if edit_bridge_obj is not None or spotting_manifest_obj is not None:
        bridge_locked = bool(getattr(edit_bridge_obj, "beat_locked", True)) if edit_bridge_obj is not None else True
        offset_frames = abs(int(getattr(edit_bridge_obj, "beat_offset_frames", 0))) if edit_bridge_obj is not None else 0
        if edit_bridge_obj is not None and not bridge_locked and offset_frames > 6:
            spotting_sync_compliant_val = False
            details["spotting_sync_compliant"] = False
            warnings.append(
                "Editorial Spotting Warning: Incoming J-Cut/L-Cut audio bridge is unlocked from the BPM beat grid."
            )
        else:
            details["spotting_sync_compliant"] = True
            details["spotting_sync_reward"] = 1.0
            details["spotting_sync_descriptor"] = _format_spotting_prompt_token(edit_bridge_obj, spotting_manifest_obj)
    elif spotting_match:
        details["spotting_sync_compliant"] = True
        details["spotting_sync_reward"] = 1.0
        details["spotting_sync_descriptor"] = spotting_match.group(0)

    # Shutter angle recognition & reward
    shutter_patterns = r"(?:180[°\s\-]*degree\s+shutter|180°\s*(?:cinematic\s+)?shutter|90[°\s\-]*degree\s+shutter|90°\s*(?:staccato\s+)?shutter|(?:45|90|180|270|360)[°\s\-]*(?:degree\s+)?shutter|shutter\s*angle|1\/(?:24|48|96|120|240)s?\s*(?:optical\s+)?(?:shutter|exposure)|staccato\s+shutter)"
    shutter_match = re.search(shutter_patterns, prompt, re.IGNORECASE)
    has_shutter_spec = bool(
        craft_camera and (
            getattr(craft_camera, "shutter_timing_token", None) or
            getattr(craft_camera, "shutter_angle_deg", None) is not None
        )
    )
    if shutter_match or has_shutter_spec:
        details["shutter_angle_compliant"] = True
        desc = shutter_match.group(0) if shutter_match else (craft_camera.shutter_timing_token or f"{craft_camera.shutter_angle_deg}° shutter")
        details["shutter_angle_descriptor"] = desc
        details["shutter_angle_reward"] = 5.0

    # Rule 3: Regime 2 High-Kinetic & Precision Commercial constraints
    if effective_regime == RegimeType.REGIME_2_KINETIC:
        # Check 1.0x real-time playback lock or speed-ramp timing
        has_speed_lock = bool(re.search(r"\b1\.0x\b|real-time|natural speed", prompt, re.IGNORECASE))
        if has_speed_ramp:
            has_momentum_conservation = bool(re.search(r"momentum|inertia|kinetic\s+(?:energy|transfer|conservation|continuity)|velocity\s+(?:vector|continuity)|force\s+dissipation", prompt, re.IGNORECASE))
            if not has_momentum_conservation:
                errors.append(
                    "Rule 3 Violation (Speed Ramp): Speed-ramped scenes must explicitly preserve kinetic momentum conservation "
                    "(momentum, inertia, or continuous velocity vector across velocity shifts) to prevent temporal detachment or smearing."
                )
            if not has_speed_lock and not bool(re.search(r"24fps|base\s+fps|real-time|1\.0x|speed\s*ramp|\b\d+fps\b", prompt, re.IGNORECASE)):
                errors.append(
                    "Rule 3 Violation: Regime 2 requires explicit '1.0x' or 'real-time' playback speed lock "
                    "to eliminate floatiness and prevent the model from defaulting to dreamy slow motion."
                )
        elif not has_speed_lock:
            errors.append(
                "Rule 3 Violation: Regime 2 requires explicit '1.0x' or 'real-time' playback speed lock "
                "to eliminate floatiness and prevent the model from defaulting to dreamy slow motion."
            )

        # Check kinetic contact chain (required when auditing ScenePromptSpec)
        if isinstance(scene, ScenePromptSpec) and (not kinetic_contact_chain or len(kinetic_contact_chain.strip()) < 10):
            errors.append(
                "Rule 3 Violation: Regime 2 requires an explicit 5-part Kinetic Contact Chain "
                "(Initiation -> Contact Point -> Force Transfer -> Environmental Evidence -> Recovery Stance)."
            )

        # Check positive physics / friction / gravity invariants
        has_physics_terms = bool(re.search(r"gravity|friction|rigid|momentum|solid|weight|inertia|aerodynamic", prompt, re.IGNORECASE))
        if not has_physics_terms:
            warnings.append(
                "Rule 3 Warning: Regime 2 prompt should explicitly invoke physical invariants "
                "(gravity, friction, rigid materials, or momentum) to prevent elastic cushioning."
            )
    elif has_speed_ramp:
        has_momentum_conservation = bool(re.search(r"momentum|inertia|kinetic\s+(?:energy|transfer|conservation|continuity)|velocity\s+(?:vector|continuity)|force\s+dissipation", prompt, re.IGNORECASE))
        if not has_momentum_conservation:
            errors.append(
                "Rule 3 Violation (Speed Ramp): Speed-ramped scenes must explicitly preserve kinetic momentum conservation "
                "(momentum, inertia, or continuous velocity vector across velocity shifts) to prevent temporal detachment or smearing."
            )

    # Rule 4: CRAFT camera completeness
    camera_terms = [
        "camera", "shot", "lens", "framing", "dolly", "steadicam", "tripod",
        "pan", "tracking", "close-up", "wide", "prime", "tilt",
        "[hdr signal:", "[1st ad breakdown:", "[film emulation:", "[film_stock:",
        "[production slate:", "[clapper_slate:", "[drone_flight:", "[drone flight:",
        "[reframe:", "[broadcast_qc:", "[broadcast qc:",
        "[continuity_axis:", "[continuity axis:",
        "[review_gate:", "[review gate:",
        "[c2pa_provenance:", "[c2pa provenance:",
        "[safety_jsa:", "[safety jsa:",
        "[localization_adr:", "[localization adr:",
        "[spotting_sync:", "[spotting sync:",
    ]
    has_camera = any(term in prompt.lower() for term in camera_terms)
    if craft_camera is not None:
        details["craft_camera_configured"] = True
    elif has_camera:
        details["craft_camera_inferred"] = True
    else:
        errors.append(
            "Rule 4 Violation: CRAFT Camera specification missing. Prompt must specify camera composition, "
            "route, focal length or framing rig."
        )

    # Rule 5: Max 3 Nano Banana image references ceiling
    image_refs = re.findall(r"<image_?(\d+)>", prompt)
    if image_refs:
        int_refs = [int(idx) for idx in image_refs]
        details["image_refs_detected"] = [f"<image_{idx}>" for idx in set(image_refs)]
        invalid_refs = [idx for idx in int_refs if idx < 1 or idx > 3]
        if invalid_refs:
            errors.append(
                f"Rule 5 Violation: Invalid image reference index {invalid_refs} detected. "
                "Gemini Omni enforces an architectural ceiling of at most 3 image references (<image_1>, <image_2>, <image_3>)."
            )

    # Rule 6: Synchronized diegetic audio inclusion
    audio_keywords = ["audio", "sound", "foley", "acoustic", "pop", "thud", "snap", "click", "rustle", "tone", "music", "hum", "whisper", "reverb", "bass", "echo"]
    has_audio_mention = any(k in prompt.lower() for k in audio_keywords)
    has_sonic_cues = bool(diegetic_sonic and diegetic_sonic.foley_cues)
    if not has_audio_mention and not has_sonic_cues:
        errors.append(
            "Rule 6 Violation: Synchronized diegetic audio cues are missing from prompt. "
            "Gemini Omni requires explicit foley, surface acoustics, or sound effects embedded in the video prompt."
        )

    # Rule 7: Mode B extension continuity check
    is_extension = bool(re.search(r"\+10s|extension", timestamp_range, re.IGNORECASE))
    continuity_keywords = ["continue", "continuous", "unbroken", "without jump cut", "maintains", "extending", "anchor"]
    has_continuity = any(k in prompt.lower() for k in continuity_keywords)

    if effective_scene_index > 1 and storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN:
        if not has_continuity:
            errors.append(
                "Rule 7 Violation: Mode B continuous chain requires explicit continuity assertion for scene_index > 1 "
                "('One continuous shot, no jump cuts')."
            )
    elif is_extension:
        if not has_continuity:
            warnings.append(
                "Rule 7 Warning: Mode B extension scene should explicitly assert unbroken camera and physical continuity "
                "('One continuous shot, no jump cuts')."
            )

    passed = len(errors) == 0
    if errors:
        score = max(0.0, 100.0 - (len(errors) * 15.0) - (len(warnings) * 2.0))
    else:
        score = max(80.0, 100.0 - (len(warnings) * 2.0))
        if details.get("shutter_angle_compliant"):
            score = min(100.0, score + 2.0)
        if details.get("optical_lens_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("virtual_production_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("moco_rig_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("lighting_rig_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("dof_spec_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("lut_spec_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("spatial_audio_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("vfx_compositing_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("hdr_signal_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("script_breakdown_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("film_emulation_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("clapper_slate_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("drone_flight_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("reframe_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("broadcast_qc_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("continuity_blocking_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("review_gate_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("c2pa_provenance_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("safety_risk_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("localization_adr_compliant"):
            score = min(100.0, score + 1.0)
        if details.get("spotting_sync_compliant"):
            score = min(100.0, score + 1.0)

    drone_ok = (
        bool(details.get("drone_flight_compliant", False))
        if (drone_flight_spec is not None or has_aerial_keywords)
        else True
    )

    return AuditResult(
        scene_index=effective_scene_index,
        passed=passed,
        score=score,
        errors=errors,
        warnings=warnings,
        details=details,
        drone_flight_compliant=drone_ok,
        reframe_compliant=reframe_compliant_val,
        broadcast_qc_compliant=broadcast_qc_compliant_val,
        continuity_blocking_compliant=continuity_blocking_compliant_val,
        review_gate_compliant=review_gate_compliant_val,
        c2pa_provenance_compliant=c2pa_provenance_compliant_val,
        safety_risk_compliant=safety_risk_compliant_val,
        localization_adr_compliant=localization_adr_compliant_val,
        spotting_sync_compliant=spotting_sync_compliant_val,
    )


class HealedPromptResult(tuple):
    """Result tuple of heal_omni_scene_prompt supporting both tuple unpacking and property access."""

    def __new__(cls, healed_target: Union[ScenePromptSpec, str], audit: AuditResult):
        return super().__new__(cls, (healed_target, audit))

    @property
    def healed(self) -> Union[ScenePromptSpec, str]:
        return self[0]

    @property
    def healed_prompt(self) -> str:
        if isinstance(self[0], ScenePromptSpec):
            return self[0].omni_prose_prompt
        return str(self[0])

    @property
    def audit(self) -> AuditResult:
        return self[1]

    @property
    def passed(self) -> bool:
        return self[1].passed

    @property
    def score(self) -> float:
        return self[1].score

    @property
    def errors(self) -> List[str]:
        return self[1].errors

    @property
    def warnings(self) -> List[str]:
        return self[1].warnings

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, str):
            if item in self.healed_prompt:
                return True
        return super().__contains__(item)

    def __getattr__(self, name: str) -> Any:
        if hasattr(self[0], name):
            return getattr(self[0], name)
        if hasattr(self[1], name):
            return getattr(self[1], name)
        raise AttributeError(f"'HealedPromptResult' object has no attribute '{name}'")


def heal_omni_scene_prompt(
    scene: Union[ScenePromptSpec, str],
    audit_result: Optional[Union[AuditResult, ScenePromptSpec]] = None,
    regime: Optional[Union[RegimeType, int]] = None,
    storytelling_mode: Optional[StorytellingMode] = None,
    scene_index: int = 1,
    duration_seconds: int = 15,
    max_attempts: int = 3,
    **kwargs: Any,
) -> HealedPromptResult:
    """Iteratively repairs prompts violating 7-Point Omni standards.

    Repairs:
    - Markdown headings (#, ##, ###) and HTML tags (<h1>-<h6>)
    - Replaces deprecated 3.1 model names if mentioned
    - Injects '1.0x real-time speed' and physical invariants in Regime 2
    - Injects synchronized diegetic foley and acoustics
    - Enforces Mode B continuity markers for scene_index > 1
    - Caps image references to <image_3>

    Returns (healed_target, final_audit_result) where healed_target has the same type
    as the input `scene` (ScenePromptSpec or str).
    """
    spec_context: Optional[ScenePromptSpec] = None
    real_audit_result: Optional[AuditResult] = None
    if isinstance(audit_result, ScenePromptSpec):
        spec_context = audit_result
    elif isinstance(audit_result, AuditResult):
        real_audit_result = audit_result

    is_spec = isinstance(scene, ScenePromptSpec)
    current_prompt = scene.omni_prose_prompt if is_spec else str(scene)
    eff_scene_index = scene.scene_index if is_spec else (spec_context.scene_index if spec_context else (regime if isinstance(regime, int) else scene_index))
    eff_regime = regime if isinstance(regime, RegimeType) else (scene.regime if is_spec else (spec_context.regime if spec_context else RegimeType.REGIME_2_KINETIC))

    current_audit = real_audit_result or audit_omni_scene_prompt(
        scene=scene if is_spec else (spec_context or scene),
        regime=eff_regime,
        scene_index=eff_scene_index,
        duration_seconds=duration_seconds,
        storytelling_mode=storytelling_mode,
        **kwargs,
    )

    initial_score = current_audit.score
    applied_patches: List[str] = []
    attempts_executed = 0

    needs_film_injection = bool(
        ((getattr(scene, "film_emulation", None) if is_spec else None) or (getattr(spec_context, "film_emulation", None) if spec_context else None) or kwargs.get("film_emulation") or kwargs.get("film_stock"))
        and not (current_audit.details and current_audit.details.get("film_emulation_compliant"))
    )
    needs_slate_injection = bool(
        ((getattr(scene, "clapper_slate", None) if is_spec else None) or (getattr(spec_context, "clapper_slate", None) if spec_context else None) or kwargs.get("clapper_slate"))
        and not (current_audit.details and current_audit.details.get("clapper_slate_compliant"))
    )
    needs_drone_injection = bool(
        (
            (getattr(scene, "drone_flight", None) if is_spec else None)
            or (getattr(spec_context, "drone_flight", None) if spec_context else None)
            or kwargs.get("drone_flight")
            or re.search(r"\b(?:aerial|drone|flyover|orbit|overhead|altitude|bird's-eye|birds eye|uav)\b", current_prompt, re.IGNORECASE)
        )
        and not (current_audit.details and current_audit.details.get("drone_flight_compliant"))
    )
    needs_reframe_injection = bool(
        (
            (getattr(scene, "reframe_spec", None) if is_spec else None)
            or (getattr(spec_context, "reframe_spec", None) if spec_context else None)
            or kwargs.get("reframe_spec")
            or kwargs.get("reframe")
            or kwargs.get("aspect_reframe")
            or kwargs.get("delivery_reframe")
        )
        and not re.search(r"\[REFRAME:?", current_prompt, re.IGNORECASE)
    )
    needs_qc_injection = bool(
        (
            (getattr(scene, "broadcast_qc", None) if is_spec else None)
            or (getattr(spec_context, "broadcast_qc", None) if spec_context else None)
            or kwargs.get("broadcast_qc")
            or kwargs.get("qc_spec")
            or kwargs.get("pse_qc")
            or kwargs.get("trafficking_qc")
        )
        and not re.search(r"\[BROADCAST[ _]QC:?", current_prompt, re.IGNORECASE)
    )
    needs_continuity_injection = bool(
        (
            (getattr(scene, "blocking_spec", None) if is_spec else None)
            or (getattr(spec_context, "blocking_spec", None) if spec_context else None)
            or kwargs.get("blocking_spec")
            or kwargs.get("continuity_blocking")
            or kwargs.get("blocking")
        )
        and not re.search(r"\[CONTINUITY[ _]AXIS:?", current_prompt, re.IGNORECASE)
    )
    needs_review_injection = bool(
        (
            (getattr(scene, "review_signoff", None) if is_spec else None)
            or (getattr(spec_context, "review_signoff", None) if spec_context else None)
            or kwargs.get("review_signoff")
            or kwargs.get("review_spec")
            or kwargs.get("client_review")
        )
        and not re.search(r"\[REVIEW[ _]GATE:?", current_prompt, re.IGNORECASE)
    )
    needs_c2pa_injection = bool(
        (
            (getattr(scene, "c2pa_provenance", None) if is_spec else None)
            or (getattr(spec_context, "c2pa_provenance", None) if spec_context else None)
            or kwargs.get("c2pa_provenance")
            or kwargs.get("provenance_spec")
            or kwargs.get("content_credentials")
        )
        and not re.search(r"\[C2PA[ _]PROVENANCE:?", current_prompt, re.IGNORECASE)
    )
    needs_safety_injection = bool(
        (
            (getattr(scene, "safety_risk", None) if is_spec else None)
            or (getattr(spec_context, "safety_risk", None) if spec_context else None)
            or kwargs.get("safety_risk")
            or kwargs.get("safety_spec")
            or kwargs.get("jsa_spec")
        )
        and not re.search(r"\[SAFETY[ _]JSA:?", current_prompt, re.IGNORECASE)
    )
    bible_ctx_heal = kwargs.get("bible")
    loc_tracks_heal = (
        (getattr(scene, "locale_tracks", None) if is_spec else None)
        or (getattr(spec_context, "locale_tracks", None) if spec_context else None)
        or kwargs.get("locale_tracks")
    )
    loc_manifest_heal = (
        kwargs.get("localization_manifest")
        or kwargs.get("localization")
        or (getattr(bible_ctx_heal, "localization_manifest", None) if bible_ctx_heal is not None else None)
    )
    needs_localization_injection = bool(
        (loc_tracks_heal or loc_manifest_heal is not None)
        and not re.search(r"\[LOCALIZATION[ _]ADR:?", current_prompt, re.IGNORECASE)
    )
    edit_bridge_heal = (
        (getattr(scene, "edit_bridge_in", None) if is_spec else None)
        or (getattr(spec_context, "edit_bridge_in", None) if spec_context else None)
        or kwargs.get("edit_bridge_in")
        or kwargs.get("audio_bridge_in")
        or kwargs.get("j_l_bridge")
    )
    spotting_manifest_heal = (
        kwargs.get("spotting_manifest")
        or kwargs.get("editorial_spotting")
        or (getattr(bible_ctx_heal, "spotting_manifest", None) if bible_ctx_heal is not None else None)
    )
    needs_spotting_injection = bool(
        (edit_bridge_heal is not None or spotting_manifest_heal is not None)
        and not re.search(r"\[SPOTTING[ _]SYNC:?", current_prompt, re.IGNORECASE)
    )

    if (
        current_audit.passed
        and current_audit.score >= 100.0
        and not current_audit.warnings
        and not needs_film_injection
        and not needs_slate_injection
        and not needs_drone_injection
        and not needs_reframe_injection
        and not needs_qc_injection
        and not needs_continuity_injection
        and not needs_review_injection
        and not needs_c2pa_injection
        and not needs_safety_injection
        and not needs_localization_injection
        and not needs_spotting_injection
    ):
        if current_audit.details is None:
            current_audit.details = {}
        current_audit.details["healing_history"] = {
            "applied_patches": applied_patches,
            "applied_fixes": list(applied_patches),
            "attempts_executed": attempts_executed,
            "initial_score": initial_score,
            "final_score": current_audit.score,
            "healed": False,
        }
        return HealedPromptResult(scene, current_audit)

    working_prompt = current_prompt

    for attempt in range(max_attempts):
        attempts_executed += 1

        # 1. Clean markdown headings
        prev = working_prompt
        working_prompt = re.sub(r"(^|\n)\s*#{1,6}\s*", r"\1", working_prompt)
        working_prompt = re.sub(r"</?h[1-6][^>]*>", " ", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bgemini[-_ ]?(?:1\.5|2\.0|2\.5|3\.0|3\.1)[-_a-z0-9]*\b", "gemini-4-argon", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bveo[-_ ]?(?:2\.0|3\.0|3\.1)[-_a-z0-9]*\b", "gemini-omni-1.1-flash-preview", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bimagen[-_ ]?3[-_a-z0-9]*\b", "gemini-3-pro-image", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bmodel[-_ ]?(?:1\.5|2\.0|2\.5|3\.0|3\.1)\b", "model 4.0", working_prompt, flags=re.IGNORECASE)
        if working_prompt != prev and "sanitized_headings" not in applied_patches:
            applied_patches.append("sanitized_headings")

        # 1b. Sanitize negative constraints into affirmative physical descriptions
        prev = working_prompt
        working_prompt = re.sub(r"\bno\s+blur\b", "sharp edge focus", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bwithout\s+blur\b", "sharp edge focus", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bnot\s+blurry\b", "sharp and clear", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\b(?:no|without)\s+(?:camera\s+)?(?:shake|shaking)\b", "steady fluid framing", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\b(?:no|without)\s+jitter\b", "steady and stable motion", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\b(?:no|without)\s+artifacts?\b", "pristine organic texture", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bno\s+cuts\b", "one continuous unbroken shot", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bwithout\s+(?:any\s+)?jump\s+cuts\b", "one continuous unbroken shot", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\b(?:do\s+not|don't)\s+(?:pan|rotate|move)\s+(?:the\s+)?camera\b", "maintain locked static framing", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\b(?:do\s+not|don't)\s+(?:cut|switch\s+angles?)\b", "maintain one continuous unbroken shot", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\b(?:do\s+not|don't)\s+obscure\b", "keep fully visible and unobstructed", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bavoid\s+(?:any\s+)?(?:cuts?|editing)\b", "maintain one continuous unbroken shot", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bavoid\s+(?:camera\s+)?(?:shake|shaking|jitter)\b", "maintain steady fluid framing", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\b(?:do\s+not|don't|avoid)\s+", "refrain from ", working_prompt, flags=re.IGNORECASE)
        if working_prompt != prev and "sanitized_negative_constraints" not in applied_patches:
            applied_patches.append("sanitized_negative_constraints")

        # 2. Check speed lock and physics invariants for Regime 2 and speed ramp momentum
        prev = working_prompt
        speed_ramp_obj = getattr(scene, "speed_ramp", None) if is_spec else kwargs.get("speed_ramp")
        ramp_active = bool(speed_ramp_obj and getattr(speed_ramp_obj, "mode", None) != "constant_realtime") or bool(re.search(r"\b(?:speed\s*ramp|time-?warp|time\s*dilation|deceleration\s*impact|acceleration\s*burst|snap\s*freeze)\b", working_prompt, re.IGNORECASE))
        if ramp_active and not re.search(r"momentum|inertia|kinetic\s+(?:energy|transfer|conservation|continuity)|velocity\s+(?:vector|continuity)|force\s+dissipation", working_prompt, re.IGNORECASE):
            working_prompt = working_prompt.rstrip() + " Preserving continuous kinetic momentum and physical inertia across speed transitions."
            if "injected_speed_ramp_momentum" not in applied_patches:
                applied_patches.append("injected_speed_ramp_momentum")

        if eff_regime == RegimeType.REGIME_2_KINETIC:
            if not re.search(r"\b1\.0x\b|real-time|natural speed", working_prompt, re.IGNORECASE):
                working_prompt = working_prompt.rstrip() + " Rendered at natural 1.0x real-time speed with solid gravity and friction invariants."
            elif not re.search(r"gravity|friction|rigid|momentum|solid|weight|inertia|aerodynamic", working_prompt, re.IGNORECASE):
                working_prompt = working_prompt.rstrip() + " Grounded with rigid material physics, natural gravity, and surface friction invariants."
        if working_prompt != prev and "injected_speed_and_physics_locks" not in applied_patches:
            applied_patches.append("injected_speed_and_physics_locks")

        # 3. Check camera terms
        prev = working_prompt
        camera_terms = ["camera", "shot", "lens", "framing", "dolly", "steadicam", "tripod", "pan", "tracking", "close-up", "wide", "prime"]
        if not any(k in working_prompt.lower() for k in camera_terms):
            working_prompt = working_prompt.rstrip() + " Shot on 35mm Prime lens with dynamic forward tracking movement, 180° shutter at 1/48s."
        if working_prompt != prev and "expanded_narrative_prose" not in applied_patches:
            applied_patches.append("expanded_narrative_prose")

        # 3b. Inject Optical Lens Spec tokens if configured
        prev = working_prompt
        opt_lens = getattr(scene, "optical_lens", None) if is_spec else kwargs.get("optical_lens")
        if opt_lens is None and is_spec and getattr(scene, "craft_camera", None):
            opt_lens = getattr(scene.craft_camera, "optical_lens", None)
        if opt_lens is not None and not re.search(r"\bT\s*\d+(?:\.\d+)?\b|focal\s*length|\b\d+mm\b", working_prompt, re.IGNORECASE):
            token = format_optical_prompt_token(opt_lens)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_optical_lens_spec" not in applied_patches:
                applied_patches.append("injected_optical_lens_spec")

        # 3c. Inject Virtual Production frustum tracking anchor if configured
        prev = working_prompt
        vp_stage = getattr(scene, "virtual_production", None) if is_spec else kwargs.get("virtual_production")
        if vp_stage is not None and not re.search(r"LED\s*volume|nDisplay|virtual\s*production|frustum", working_prompt, re.IGNORECASE):
            working_prompt = working_prompt.rstrip() + " Staged within an in-camera VFX LED volume with dynamic perspective frustum tracking and parallax depth planes."
            if "injected_vp_stage_frustum" not in applied_patches:
                applied_patches.append("injected_vp_stage_frustum")

        # 3d. Inject MoCo rig tokens if configured (PM-FEAT-009)
        prev = working_prompt
        moco_obj = (getattr(scene, "moco_rig", None) if is_spec else None) or (getattr(spec_context, "moco_rig", None) if spec_context else None) or kwargs.get("moco_rig")
        if moco_obj is None:
            if is_spec and getattr(scene, "craft_camera", None):
                moco_obj = getattr(scene.craft_camera, "moco_rig", None)
            elif spec_context and getattr(spec_context, "craft_camera", None):
                moco_obj = getattr(spec_context.craft_camera, "moco_rig", None)
        if moco_obj is not None and not re.search(r"motion\s*control|moco|bolt\s*cinebot|technocrane|cablecam|motorized\s*dolly|russian\s*arm|drone\s*fpv|6-?DOF|robotic\s*(?:camera|rig)", working_prompt, re.IGNORECASE):
            rig_name = moco_obj.rig_type.value if hasattr(moco_obj.rig_type, "value") else str(moco_obj.rig_type)
            working_prompt = working_prompt.rstrip() + f" Executed on precision robotic motion control (MoCo) {rig_name} rig following calibrated 6-DOF trajectory waypoints."
            if "injected_moco_rig_spec" not in applied_patches:
                applied_patches.append("injected_moco_rig_spec")

        # 3e. Inject Lighting rig tokens if configured (PM-FEAT-010)
        prev = working_prompt
        light_obj = (getattr(scene, "lighting_rig", None) if is_spec else None) or (getattr(spec_context, "lighting_rig", None) if spec_context else None) or kwargs.get("lighting_rig")
        if light_obj is not None and not re.search(r"key\s*light|fill\s*light|rim\s*(?:light|backlight)|kicker|lighting\s*ratio|skypanel|atmospheric\s*haze|particulate", working_prompt, re.IGNORECASE):
            haze_str = (light_obj.atmospheric_haze.haze_type.value if hasattr(light_obj.atmospheric_haze.haze_type, "value") else str(light_obj.atmospheric_haze.haze_type)) if light_obj.atmospheric_haze else "clean air"
            working_prompt = working_prompt.rstrip() + f" Calibrated studio lighting rig with Key:Fill {light_obj.key_to_fill_ratio:.1f}:1 contrast ratio and {haze_str.replace('_', ' ')} atmospheric scattering."
            if "injected_lighting_rig_spec" not in applied_patches:
                applied_patches.append("injected_lighting_rig_spec")

        # 3f. Inject Depth of Field (DoF) spec tokens if configured (PM-FEAT-011)
        prev = working_prompt
        dof_obj = (getattr(scene, "dof_spec", None) if is_spec else None) or (getattr(spec_context, "dof_spec", None) if spec_context else None) or kwargs.get("dof_spec")
        if dof_obj is None:
            if is_spec and getattr(scene, "craft_camera", None):
                dof_obj = getattr(scene.craft_camera, "dof_spec", None)
            elif spec_context and getattr(spec_context, "craft_camera", None):
                dof_obj = getattr(spec_context.craft_camera, "dof_spec", None)
        if dof_obj is not None and not re.search(r"depth\s*of\s*field|\bdof\b|rack\s*focus|shallow\s*(?:focus|dof)|deep\s*focus|focal\s*plane|bokeh|circle\s*of\s*confusion|hyperfocal|focus\s*pull", working_prompt, re.IGNORECASE):
            token = format_dof_prompt_token(dof_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_dof_spec" not in applied_patches:
                applied_patches.append("injected_dof_spec")

        # 3g. Inject 3D LUT spec tokens if configured (PM-FEAT-012)
        prev = working_prompt
        lut_obj = (getattr(scene, "lut_spec", None) if is_spec else None) or (getattr(spec_context, "lut_spec", None) if spec_context else None) or kwargs.get("lut_spec")
        if lut_obj is None:
            if is_spec and getattr(scene, "scene_color_look", None):
                lut_obj = getattr(scene.scene_color_look, "lut_spec", None)
            elif spec_context and getattr(spec_context, "scene_color_look", None):
                lut_obj = getattr(spec_context.scene_color_look, "lut_spec", None)
        if lut_obj is not None and not re.search(r"3d\s*lut|\blut\b|\.cube|color\s*grade|asc\s*cdl|\bcdl\b|acescg|rec\.?709|gamut\s*transform|tetrahedral", working_prompt, re.IGNORECASE):
            token = format_lut_prompt_token(lut_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_lut_spec" not in applied_patches:
                applied_patches.append("injected_lut_spec")

        # 3h. Inject Spatial Audio spec tokens if configured (PM-FEAT-013)
        prev = working_prompt
        spatial_obj = (getattr(scene, "spatial_audio", None) if is_spec else None) or (getattr(spec_context, "spatial_audio", None) if spec_context else None) or kwargs.get("spatial_audio")
        if spatial_obj is None and is_spec and getattr(scene, "diegetic_sonic", None):
            spatial_obj = getattr(scene.diegetic_sonic, "spatial_audio", None)
        if spatial_obj is not None and not re.search(r"spatial\s*audio|dolby\s*atmos|7\.1\.4|binaural|ambisonic", working_prompt, re.IGNORECASE):
            token = format_spatial_audio_prompt_token(spatial_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_spatial_audio_spec" not in applied_patches:
                applied_patches.append("injected_spatial_audio_spec")

        # 3i. Inject Multi-Pass VFX Compositing tokens if configured (PM-FEAT-014)
        prev = working_prompt
        vfx_obj = (getattr(scene, "vfx_compositing", None) if is_spec else None) or (getattr(spec_context, "vfx_compositing", None) if spec_context else None) or kwargs.get("vfx_compositing")
        if vfx_obj is not None and not re.search(r"cryptomatte|render\s*pass|openexr|\.exr|deep\s*compositing", working_prompt, re.IGNORECASE):
            token = format_vfx_compositing_prompt_token(vfx_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_vfx_compositing_spec" not in applied_patches:
                applied_patches.append("injected_vfx_compositing_spec")

        # 3j. Inject HDR Signal tokens if configured (PM-FEAT-015)
        prev = working_prompt
        hdr_obj = (getattr(scene, "hdr_spec", None) if is_spec else None) or (getattr(spec_context, "hdr_spec", None) if spec_context else None) or kwargs.get("hdr_spec")
        if hdr_obj is not None and not re.search(r"\[HDR\s*Signal:?|hdr10|smpte\s*st\s*2084|arib\s*std-b67|\bhlg\b|bt\.?2100|maxcll|maxfall", working_prompt, re.IGNORECASE):
            token = format_hdr_prompt_token(hdr_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_hdr_spec" not in applied_patches:
                applied_patches.append("injected_hdr_spec")

        # 3k. Inject 1st AD Script Breakdown tokens if configured (PM-FEAT-016)
        prev = working_prompt
        breakdown_sheet_obj = (getattr(scene, "breakdown_sheet", None) if is_spec else None) or (getattr(spec_context, "breakdown_sheet", None) if spec_context else None) or kwargs.get("breakdown_sheet")
        if breakdown_sheet_obj is not None and not re.search(r"\[1st\s*AD\s*Breakdown:?|stripboard|script\s*breakdown|page\s*eighths|\b\d+\/8\s*pgs?\b", working_prompt, re.IGNORECASE):
            token = format_script_breakdown_prompt_token(breakdown_sheet_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_script_breakdown_spec" not in applied_patches:
                applied_patches.append("injected_script_breakdown_spec")

        # 3l. Inject Film Emulation tokens if configured (PM-FEAT-017)
        prev = working_prompt
        film_obj = (getattr(scene, "film_emulation", None) if is_spec else None) or (getattr(spec_context, "film_emulation", None) if spec_context else None) or kwargs.get("film_emulation") or kwargs.get("film_stock")
        if film_obj is None and is_spec and getattr(scene, "film_stock", None):
            film_obj = getattr(scene, "film_stock", None)
        if film_obj is None:
            domain_arch = getattr(spec_context, "domain_archetype", None) or kwargs.get("domain_archetype")
            if domain_arch:
                arch_str = str(domain_arch).lower()
                if "culinary" in arch_str or "fashion" in arch_str or "sanctuary" in arch_str or "fuji" in arch_str:
                    film_obj = synthesize_default_film_stock("fuji")
                else:
                    film_obj = synthesize_default_film_stock("kodak")
        if film_obj is not None and not re.search(r"\[FILM[ _]EMULATION:?|\[FILM_STOCK:?|film\s*emulation|film\s*stock|silver\s*halide|5219|5207|eterna", working_prompt, re.IGNORECASE):
            token = format_film_emulation_prompt_token(film_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_film_emulation_spec" not in applied_patches:
                applied_patches.append("injected_film_emulation_spec")

        # 3m. Inject Production Clapper Slate tokens if configured (PM-FEAT-018)
        prev = working_prompt
        slate_obj = (getattr(scene, "clapper_slate", None) if is_spec else None) or (getattr(spec_context, "clapper_slate", None) if spec_context else None) or kwargs.get("clapper_slate")
        if slate_obj is None:
            slate_obj = synthesize_default_clapper_slate(eff_scene_index)
        if slate_obj is not None and not re.search(r"\[PRODUCTION[ _]SLATE:?|\[CLAPPER_SLATE:?|clapper\s*slate|production\s*slate", working_prompt, re.IGNORECASE):
            token = format_clapper_slate_prompt_token(slate_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_clapper_slate_spec" not in applied_patches:
                applied_patches.append("injected_clapper_slate_spec")

        # 3n. Inject Drone Flight Path tokens if configured or aerial keywords detected (PM-FEAT-019)
        prev = working_prompt
        drone_obj = (getattr(scene, "drone_flight", None) if is_spec else None) or (getattr(spec_context, "drone_flight", None) if spec_context else None) or kwargs.get("drone_flight")
        has_aerial_intent = bool(re.search(r"\b(?:aerial|drone|flyover|orbit|overhead|altitude|bird's-eye|birds eye|uav)\b", working_prompt, re.IGNORECASE))
        if drone_obj is None and has_aerial_intent:
            profile = "orbit" if "orbit" in working_prompt.lower() else "flyover_reveal"
            drone_obj = synthesize_default_drone_flight(profile=profile, alt_m=25.0)
            if is_spec and getattr(scene, "drone_flight", None) is None:
                try:
                    scene.drone_flight = drone_obj
                except Exception:
                    pass
        if drone_obj is not None and not re.search(r"\[DRONE[ _]FLIGHT:?|drone\s*flight|flight\s*path", working_prompt, re.IGNORECASE):
            token = format_drone_flight_prompt_token(drone_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "injected_drone_flight_spec" not in applied_patches:
                applied_patches.append("injected_drone_flight_spec")

        # 3o. Inject Multi-Aspect Reframe & Safe-Zone tokens (PM-FEAT-021)
        reframe_obj = (
            (getattr(scene, "reframe_spec", None) if is_spec else None)
            or (getattr(spec_context, "reframe_spec", None) if spec_context else None)
            or kwargs.get("reframe_spec")
            or kwargs.get("reframe")
            or kwargs.get("aspect_reframe")
            or kwargs.get("delivery_reframe")
        )
        domain_arch_hint = str(getattr(spec_context, "domain_archetype", None) or kwargs.get("domain_archetype") or "architectural_sanctuary")
        if reframe_obj is None:
            reframe_obj = synthesize_default_scene_reframe(
                scene=scene if is_spec else None,
                scene_index=eff_scene_index,
                domain=domain_arch_hint,
            )
        elif getattr(reframe_obj, "all_platforms_cleared", True) is False:
            reframe_obj = synthesize_default_scene_reframe(
                scene=None,
                scene_index=eff_scene_index,
                scene_title=getattr(reframe_obj, "scene_title", ""),
                domain=domain_arch_hint,
            )
        if reframe_obj is not None and not re.search(r"\[REFRAME:?", working_prompt, re.IGNORECASE):
            token = format_reframe_prompt_token(reframe_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "reframe_spec" not in applied_patches:
                applied_patches.append("reframe_spec")

        # 3p. Inject Broadcast QC & PSE Flash-Safety tokens (PM-FEAT-022)
        qc_obj = (
            (getattr(scene, "broadcast_qc", None) if is_spec else None)
            or (getattr(spec_context, "broadcast_qc", None) if spec_context else None)
            or kwargs.get("broadcast_qc")
            or kwargs.get("qc_spec")
            or kwargs.get("pse_qc")
            or kwargs.get("trafficking_qc")
        )
        if qc_obj is None:
            qc_obj = synthesize_default_scene_qc(
                scene=scene if is_spec else None,
                scene_index=eff_scene_index,
            )
        if qc_obj is not None and getattr(qc_obj, "overall_verdict", QcVerdictStatus.PASS) == QcVerdictStatus.FAIL:
            working_prompt = re.sub(
                r"\b(?:stroboscopic|strobe|strobing|rapid\s+flash(?:ing)?|rapid\s+flicker|red\s+strobe)\b",
                "smooth continuous illumination",
                working_prompt,
                flags=re.IGNORECASE,
            )
            qc_obj = synthesize_default_scene_qc(scene=None, scene_index=eff_scene_index)
            if "broadcast_qc" not in applied_patches:
                applied_patches.append("broadcast_qc")
        if qc_obj is not None and not re.search(r"\[BROADCAST[ _]QC:?", working_prompt, re.IGNORECASE):
            token = format_broadcast_qc_prompt_token(qc_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "broadcast_qc" not in applied_patches:
                applied_patches.append("broadcast_qc")

        # 3q. Inject 180-Degree Continuity Axis & Blocking tokens (PM-FEAT-023)
        blocking_obj = (
            (getattr(scene, "blocking_spec", None) if is_spec else None)
            or (getattr(spec_context, "blocking_spec", None) if spec_context else None)
            or kwargs.get("blocking_spec")
            or kwargs.get("continuity_blocking")
            or kwargs.get("blocking")
        )
        if blocking_obj is None:
            blocking_obj = synthesize_scene_blocking(
                scene=scene if is_spec else None,
                scene_index=eff_scene_index,
                domain=domain_arch_hint,
            )
        elif getattr(blocking_obj, "one_eighty_lock_ok", True) is False:
            blocking_obj = synthesize_scene_blocking(
                scene=None,
                scene_index=eff_scene_index,
                domain=domain_arch_hint,
            )
            if "blocking_spec" not in applied_patches:
                applied_patches.append("blocking_spec")
        if blocking_obj is not None and not re.search(r"\[CONTINUITY[ _]AXIS:?", working_prompt, re.IGNORECASE):
            token = format_continuity_prompt_token(blocking_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "blocking_spec" not in applied_patches:
                applied_patches.append("blocking_spec")

        # 3r. Inject Client Review Signoff Gate tokens (PM-FEAT-024)
        # Only inject [REVIEW_GATE: when review_obj is explicitly present; never auto-approve unreviewed scenes.
        review_obj = (
            (getattr(scene, "review_signoff", None) if is_spec else None)
            or (getattr(spec_context, "review_signoff", None) if spec_context else None)
            or kwargs.get("review_signoff")
            or kwargs.get("review_spec")
            or kwargs.get("client_review")
        )
        if review_obj is not None and not re.search(r"\[REVIEW[ _]GATE:?", working_prompt, re.IGNORECASE):
            token = format_review_prompt_token(review_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "review_signoff" not in applied_patches:
                applied_patches.append("review_signoff")

        # 3s. Inject / repair C2PA Content Credentials & Likeness Provenance tokens (PM-FEAT-025)
        c2pa_obj = (
            (getattr(scene, "c2pa_provenance", None) if is_spec else None)
            or (getattr(spec_context, "c2pa_provenance", None) if spec_context else None)
            or kwargs.get("c2pa_provenance")
            or kwargs.get("provenance_spec")
            or kwargs.get("content_credentials")
        )
        has_revoked_consent = False
        if c2pa_obj is not None:
            for rec in (getattr(c2pa_obj, "talent_likeness_records", None) or []):
                cst = getattr(rec, "consent_status", None)
                cst_str = (cst.value if hasattr(cst, "value") else str(cst)).lower()
                if cst_str == LikenessConsentStatus.REVOKED.value:
                    has_revoked_consent = True
                    break

        c2pa_repaired = False
        if not has_revoked_consent:
            c2pa_needs_repair = False
            if c2pa_obj is not None:
                c2pa_models = [
                    getattr(act, "model_used", "")
                    for act in (getattr(c2pa_obj, "actions", None) or [])
                    if getattr(act, "model_used", None)
                ] + [
                    getattr(ing, "generative_model", "")
                    for ing in (getattr(c2pa_obj, "ingredients", None) or [])
                    if getattr(ing, "generative_model", None)
                ]
                lineage_ok = verify_model_lineage_2026(c2pa_models)[0] if c2pa_models else True
                eu_ok = bool(getattr(c2pa_obj, "eu_ai_act_art50_compliant", True))
                consent_ok = bool(getattr(c2pa_obj, "consent_gate_passed", True))
                if not lineage_ok or not eu_ok or not consent_ok:
                    c2pa_needs_repair = True

            if c2pa_obj is None or c2pa_needs_repair:
                kw_c2pa = kwargs.get("c2pa_provenance") or kwargs.get("provenance_spec") or kwargs.get("content_credentials")
                kw_valid = False
                if kw_c2pa is not None and kw_c2pa is not c2pa_obj:
                    kw_models = [
                        getattr(act, "model_used", "")
                        for act in (getattr(kw_c2pa, "actions", None) or [])
                        if getattr(act, "model_used", None)
                    ] + [
                        getattr(ing, "generative_model", "")
                        for ing in (getattr(kw_c2pa, "ingredients", None) or [])
                        if getattr(ing, "generative_model", None)
                    ]
                    kw_lineage_ok = verify_model_lineage_2026(kw_models)[0] if kw_models else True
                    kw_valid = (
                        kw_lineage_ok
                        and bool(getattr(kw_c2pa, "eu_ai_act_art50_compliant", True))
                        and bool(getattr(kw_c2pa, "consent_gate_passed", True))
                    )
                if kw_valid:
                    c2pa_obj = kw_c2pa
                else:
                    target_scene_c2pa = (
                        scene
                        if is_spec
                        else ScenePromptSpec(
                            scene_index=eff_scene_index,
                            timestamp_range=f"00:00 - 00:{duration_seconds:02d}",
                            scene_title=f"Scene {eff_scene_index}",
                            omni_prose_prompt=working_prompt,
                        )
                    )
                    c2pa_obj = synthesize_scene_c2pa_provenance(
                        scene=target_scene_c2pa,
                        scene_index=eff_scene_index,
                        domain=domain_arch_hint,
                    )
                c2pa_repaired = True
                if "c2pa_provenance" not in applied_patches:
                    applied_patches.append("c2pa_provenance")
                if not is_spec and "c2pa_provenance" in kwargs:
                    kwargs["c2pa_provenance"] = c2pa_obj

        if c2pa_obj is not None and not re.search(r"\[C2PA[ _]PROVENANCE:?", working_prompt, re.IGNORECASE):
            token = format_c2pa_prompt_token(c2pa_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "c2pa_provenance" not in applied_patches:
                applied_patches.append("c2pa_provenance")

        # 3t. Inject / repair On-Set Safety JSA tokens (PM-FEAT-026)
        safety_obj = (
            (getattr(scene, "safety_risk", None) if is_spec else None)
            or (getattr(spec_context, "safety_risk", None) if spec_context else None)
            or kwargs.get("safety_risk")
            or kwargs.get("safety_spec")
            or kwargs.get("jsa_spec")
        )
        safety_needs_repair = False
        if safety_obj is not None:
            s_st = getattr(safety_obj, "signoff_status", SafetySignoffStatus.CLEARED)
            s_st_str = (s_st.value if hasattr(s_st, "value") else str(s_st)).lower()
            has_crit_res = any(
                (
                    getattr(getattr(h, "residual_risk_level", None), "value", getattr(h, "residual_risk_level", ""))
                    or ""
                ).lower() == RiskSeverityLevel.CRITICAL.value
                for h in (getattr(safety_obj, "hazards", None) or [])
            )
            if s_st_str == SafetySignoffStatus.HOLD_REQUIRED.value or has_crit_res:
                safety_needs_repair = True

        safety_repaired = False
        if safety_obj is None or safety_needs_repair:
            kw_safety = kwargs.get("safety_risk") or kwargs.get("safety_spec") or kwargs.get("jsa_spec")
            kw_s_valid = False
            if kw_safety is not None and kw_safety is not safety_obj:
                kw_st = getattr(kw_safety, "signoff_status", SafetySignoffStatus.CLEARED)
                kw_st_str = (kw_st.value if hasattr(kw_st, "value") else str(kw_st)).lower()
                kw_crit = any(
                    (
                        getattr(getattr(h, "residual_risk_level", None), "value", getattr(h, "residual_risk_level", ""))
                        or ""
                    ).lower() == RiskSeverityLevel.CRITICAL.value
                    for h in (getattr(kw_safety, "hazards", None) or [])
                )
                kw_s_valid = kw_st_str != SafetySignoffStatus.HOLD_REQUIRED.value and not kw_crit
            if kw_s_valid:
                safety_obj = kw_safety
            else:
                target_scene_safety = (
                    scene
                    if is_spec
                    else ScenePromptSpec(
                        scene_index=eff_scene_index,
                        timestamp_range=f"00:00 - 00:{duration_seconds:02d}",
                        scene_title=f"Scene {eff_scene_index}",
                        omni_prose_prompt=working_prompt,
                    )
                )
                safety_obj = assess_scene_hazards(
                    target_scene_safety,
                    scene_index=eff_scene_index,
                    domain=domain_arch_hint,
                )
            safety_repaired = True
            if "safety_risk" not in applied_patches:
                applied_patches.append("safety_risk")
            if not is_spec and "safety_risk" in kwargs:
                kwargs["safety_risk"] = safety_obj

        if safety_obj is not None and not re.search(r"\[SAFETY[ _]JSA:?", working_prompt, re.IGNORECASE):
            token = format_safety_prompt_token(safety_obj)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "safety_risk" not in applied_patches:
                applied_patches.append("safety_risk")

        # 3u. Inject Localization & ADR Lip-Sync tokens if configured (PM-FEAT-027)
        if (loc_tracks_heal or loc_manifest_heal is not None) and not re.search(r"\[LOCALIZATION[ _]ADR:?", working_prompt, re.IGNORECASE):
            token = _format_localization_prompt_token(loc_tracks_heal, loc_manifest_heal)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "localization_adr" not in applied_patches:
                applied_patches.append("localization_adr")

        # 3v. Inject Editorial J-Cut/L-Cut & BPM Spotting Sync tokens if configured (PM-FEAT-028)
        if (edit_bridge_heal is not None or spotting_manifest_heal is not None) and not re.search(r"\[SPOTTING[ _]SYNC:?", working_prompt, re.IGNORECASE):
            token = _format_spotting_prompt_token(edit_bridge_heal, spotting_manifest_heal)
            working_prompt = working_prompt.rstrip() + f" {token}."
            if "spotting_sync" not in applied_patches:
                applied_patches.append("spotting_sync")

        # 4. Check image references ceiling (>3 or <1)
        prev = working_prompt
        working_prompt = re.sub(r"<image_?0>", "<image_1>", working_prompt)
        working_prompt = re.sub(r"<image_?([4-9]|\d{2,})>", "<image_3>", working_prompt)
        if working_prompt != prev and "capped_image_references" not in applied_patches:
            applied_patches.append("capped_image_references")

        # 5. Check synchronized audio
        prev = working_prompt
        audio_keywords = ["audio", "sound", "foley", "acoustic", "pop", "thud", "snap", "click", "rustle", "tone", "music", "hum", "whisper", "reverb"]
        if not any(k in working_prompt.lower() for k in audio_keywords):
            working_prompt = working_prompt.rstrip() + " Synchronized diegetic audio captures crisp physical foley, tactile surface contact rustle, and resonant low-frequency room ambience."
        if working_prompt != prev and "injected_diegetic_audio" not in applied_patches:
            applied_patches.append("injected_diegetic_audio")

        # 6. Check Mode B continuity
        prev = working_prompt
        is_mode_b = storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN or (is_spec and bool(re.search(r"\+10s|extension", scene.timestamp_range, re.IGNORECASE)))
        if eff_scene_index > 1 and is_mode_b:
            continuity_keywords = ["continue", "continuous", "unbroken", "without jump cut", "maintains", "extending", "anchor"]
            if not any(k in working_prompt.lower() for k in continuity_keywords):
                working_prompt = working_prompt.rstrip() + f" [MODE B CONTINUITY: ANCHOR End_Frame_0{eff_scene_index-1}.png] One continuous shot, no jump cuts, seamlessly continuing camera and subject momentum."
        if working_prompt != prev and "anchored_mode_b_continuous_shot" not in applied_patches:
            applied_patches.append("anchored_mode_b_continuous_shot")

        # Format whitespace
        working_prompt = re.sub(r"\s+", " ", working_prompt).strip()

        # Update spec if applicable
        if is_spec:
            scene.omni_prose_prompt = working_prompt
            if not scene.timestamp_range or "00:" not in scene.timestamp_range:
                scene.timestamp_range = f"00:00 - 00:{duration_seconds:02d}"
            if len(scene.action_beats or []) > 3:
                scene.action_beats = scene.action_beats[:3]
                if "trimmed_action_beats" not in applied_patches:
                    applied_patches.append("trimmed_action_beats")
            if not scene.action_beats:
                scene.action_beats = [
                    f"Beat 1: Establishing initial movement (00:00 - 00:{max(1, duration_seconds//2):02d})",
                    f"Beat 2: Kinetic culmination (00:{max(1, duration_seconds//2):02d} - 00:{duration_seconds:02d})",
                ]
                if "populated_action_beats" not in applied_patches:
                    applied_patches.append("populated_action_beats")
            if not scene.kinetic_contact_chain or len(scene.kinetic_contact_chain.strip()) < 10:
                scene.kinetic_contact_chain = "Initiation -> Contact Point -> Force Transfer -> Environmental Evidence -> Recovery Stance"
                if "repaired_kinetic_contact_chain" not in applied_patches:
                    applied_patches.append("repaired_kinetic_contact_chain")
            if not scene.craft_camera:
                from omni_director.schemas import CraftCameraSpec
                scene.craft_camera = CraftCameraSpec(
                    rig_type="35mm Prime",
                    focal_length_mm=35,
                    composition="Balanced wide composition with centered focus",
                    route="Forward dolly tracking",
                    action_anchor="Hero subject movement",
                    focus_axis="180-degree axis",
                    tone_rig="Cinematic Prime",
                )
                if "populated_craft_camera" not in applied_patches:
                    applied_patches.append("populated_craft_camera")
            if not scene.diegetic_sonic:
                from omni_director.schemas import DiegeticSonicSpec
                scene.diegetic_sonic = DiegeticSonicSpec(
                    foley_cues=["Tactile surface contact rustle", "Resonant low-frequency impact"],
                    dialogue_lines=[],
                    room_acoustics="Controlled cinematic soundstage",
                )
                if "populated_diegetic_sonic" not in applied_patches:
                    applied_patches.append("populated_diegetic_sonic")
            elif not scene.diegetic_sonic.foley_cues:
                scene.diegetic_sonic.foley_cues = ["Tactile surface contact rustle", "Resonant low-frequency impact"]
                if "populated_diegetic_sonic" not in applied_patches:
                    applied_patches.append("populated_diegetic_sonic")
            if film_obj is not None and getattr(scene, "film_emulation", None) is None:
                scene.film_emulation = film_obj
            if slate_obj is not None and getattr(scene, "clapper_slate", None) is None:
                scene.clapper_slate = slate_obj
            if reframe_obj is not None and (getattr(scene, "reframe_spec", None) is None or not getattr(scene.reframe_spec, "all_platforms_cleared", True)):
                scene.reframe_spec = reframe_obj
                if "reframe_spec" not in applied_patches:
                    applied_patches.append("reframe_spec")
            if qc_obj is not None and (getattr(scene, "broadcast_qc", None) is None or getattr(scene.broadcast_qc, "overall_verdict", QcVerdictStatus.PASS) == QcVerdictStatus.FAIL):
                scene.broadcast_qc = qc_obj
                if "broadcast_qc" not in applied_patches:
                    applied_patches.append("broadcast_qc")
            if blocking_obj is not None and (getattr(scene, "blocking_spec", None) is None or not getattr(scene.blocking_spec, "one_eighty_lock_ok", True)):
                scene.blocking_spec = blocking_obj
                if "blocking_spec" not in applied_patches:
                    applied_patches.append("blocking_spec")
            if review_obj is not None and getattr(scene, "review_signoff", None) is None:
                scene.review_signoff = review_obj
                if "review_signoff" not in applied_patches:
                    applied_patches.append("review_signoff")
            if c2pa_obj is not None and not has_revoked_consent and (
                getattr(scene, "c2pa_provenance", None) is None or c2pa_repaired
            ):
                scene.c2pa_provenance = c2pa_obj
                if "c2pa_provenance" not in applied_patches:
                    applied_patches.append("c2pa_provenance")
            if safety_obj is not None and (
                getattr(scene, "safety_risk", None) is None or safety_repaired
            ):
                scene.safety_risk = safety_obj
                if "safety_risk" not in applied_patches:
                    applied_patches.append("safety_risk")
            target_to_audit = scene
        else:
            if "action_beats" in kwargs and isinstance(kwargs["action_beats"], list) and len(kwargs["action_beats"]) > 3:
                kwargs["action_beats"] = kwargs["action_beats"][:3]
                if "trimmed_action_beats" not in applied_patches:
                    applied_patches.append("trimmed_action_beats")
            target_to_audit = working_prompt

        current_audit = audit_omni_scene_prompt(
            scene=target_to_audit,
            regime=eff_regime,
            scene_index=eff_scene_index,
            duration_seconds=duration_seconds,
            storytelling_mode=storytelling_mode,
            **kwargs,
        )

        needs_film_still = bool(film_obj is not None and not (current_audit.details and current_audit.details.get("film_emulation_compliant")))
        needs_slate_still = bool(slate_obj is not None and not (current_audit.details and current_audit.details.get("clapper_slate_compliant")))
        needs_drone_still = bool(drone_obj is not None and not (current_audit.details and current_audit.details.get("drone_flight_compliant")))
        needs_reframe_still = bool(reframe_obj is not None and not (current_audit.details and current_audit.details.get("reframe_compliant")))
        needs_qc_still = bool(qc_obj is not None and not (current_audit.details and current_audit.details.get("broadcast_qc_compliant")))
        needs_continuity_still = bool(blocking_obj is not None and not (current_audit.details and current_audit.details.get("continuity_blocking_compliant")))
        needs_review_still = bool(review_obj is not None and not (current_audit.details and current_audit.details.get("review_gate_compliant")))
        needs_c2pa_still = bool(not has_revoked_consent and c2pa_obj is not None and not (current_audit.details and current_audit.details.get("c2pa_provenance_compliant")))
        needs_safety_still = bool(safety_obj is not None and not (current_audit.details and current_audit.details.get("safety_risk_compliant")))
        needs_localization_still = bool((loc_tracks_heal or loc_manifest_heal is not None) and not re.search(r"\[LOCALIZATION[ _]ADR:?", working_prompt, re.IGNORECASE))
        needs_spotting_still = bool((edit_bridge_heal is not None or spotting_manifest_heal is not None) and not re.search(r"\[SPOTTING[ _]SYNC:?", working_prompt, re.IGNORECASE))
        if (
            current_audit.passed
            and current_audit.score >= 90.0
            and not needs_film_still
            and not needs_slate_still
            and not needs_drone_still
            and not needs_reframe_still
            and not needs_qc_still
            and not needs_continuity_still
            and not needs_review_still
            and not needs_c2pa_still
            and not needs_safety_still
            and not needs_localization_still
            and not needs_spotting_still
        ):
            break

    if current_audit.details is None:
        current_audit.details = {}
    current_audit.details["healing_history"] = {
        "applied_patches": applied_patches,
        "applied_fixes": list(applied_patches),
        "attempts_executed": attempts_executed,
        "initial_score": initial_score,
        "final_score": current_audit.score,
        "healed": len(applied_patches) > 0,
    }

    return HealedPromptResult(scene if is_spec else working_prompt, current_audit)


def audit_bible_inter_scene_continuity(
    bible: MasterProductionBible,
) -> List[InterSceneCutCheckSpec]:
    """Audits inter-scene 180-degree axis, 30-degree rule, and Kelvin continuity across a MasterProductionBible."""
    scenes = list(getattr(bible, "scenes", []) or [])
    if len(scenes) < 2:
        return []

    domain = getattr(bible, "domain_archetype", None) or "architectural_sanctuary"
    blockings = []
    prev_blk = None
    for sc in scenes:
        blk = getattr(sc, "blocking_spec", None)
        if blk is None:
            blk = synthesize_scene_blocking(sc, scene_index=sc.scene_index, domain=domain, prev_blocking=prev_blk)
        blockings.append(blk)
        prev_blk = blk

    checks: List[InterSceneCutCheckSpec] = []
    for i in range(len(blockings) - 1):
        prev_b = blockings[i]
        next_b = blockings[i + 1]
        checks.append(
            evaluate_180_axis_and_30_rule(
                prev_b,
                next_b,
                prev_kelvin=getattr(prev_b, "color_temp_kelvin", 5600),
                next_kelvin=getattr(next_b, "color_temp_kelvin", 5600),
            )
        )
    return checks


_MACHINE_TELEMETRY_TOKEN_RE = re.compile(
    r"\s*\[(?:DOF|3D_LUT|3D\s+LUT|HDR\s+Signal|HDR_SIGNAL|1st\s+AD\s+Breakdown|"
    r"FILM_STOCK|FILM\s+EMULATION|CLAPPER_SLATE|PRODUCTION\s+SLATE|"
    r"DRONE_FLIGHT|DRONE\s+FLIGHT|REFRAME|BROADCAST_QC|BROADCAST\s+QC|"
    r"CONTINUITY_AXIS|CONTINUITY\s+AXIS|REVIEW_GATE|REVIEW\s+GATE|"
    r"C2PA_PROVENANCE|C2PA\s+PROVENANCE|SAFETY_JSA|SAFETY\s+JSA|"
    r"LOCALIZATION_ADR|LOCALIZATION\s+ADR|SPOTTING_SYNC|SPOTTING\s+SYNC|"
    r"LIGHTING_RIG|MOCO_RIG|OPTICAL_LENS|SPATIAL_AUDIO|SPATIAL\s+AUDIO|"
    r"VFX_COMPOSITING|VFX\s+COMPOSITING)\s*:[^\]]*\]\.?",
    re.IGNORECASE,
)


def compile_clean_omni_prompt(prose: str) -> str:
    """Strips machine-only bracketed telemetry tokens while preserving natural cinematography prose and audio cues."""
    if not prose:
        return ""
    cleaned = _MACHINE_TELEMETRY_TOKEN_RE.sub("", prose)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned
