"""Prompt Auditor tool implementing the 7-Point Gemini Omni Prompting Verification Checklist and Self-Healing Loop."""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
from omni_director.schemas import (
    AuditResult,
    PromptAuditResult,
    RegimeType,
    ScenePromptSpec,
    StorytellingMode,
)
from omni_director.tools.optical_lens import format_optical_prompt_token


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
    camera_terms = ["camera", "shot", "lens", "framing", "dolly", "steadicam", "tripod", "pan", "tracking", "close-up", "wide", "prime", "tilt"]
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

    return AuditResult(
        scene_index=effective_scene_index,
        passed=passed,
        score=score,
        errors=errors,
        warnings=warnings,
        details=details,
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

    if current_audit.passed and current_audit.score >= 100.0 and not current_audit.warnings:
        if current_audit.details is None:
            current_audit.details = {}
        current_audit.details["healing_history"] = {
            "applied_patches": applied_patches,
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
        working_prompt = re.sub(r"\bgemini[-_ ]?3\.1\b", "gemini-4-argon", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bveo[-_ ]?3\.1\b", "gemini-omni-1.1-flash-preview", working_prompt, flags=re.IGNORECASE)
        working_prompt = re.sub(r"\bmodel[-_ ]?3\.1\b", "model 4.0", working_prompt, flags=re.IGNORECASE)
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

        if current_audit.passed and current_audit.score >= 90.0:
            break

    if current_audit.details is None:
        current_audit.details = {}
    current_audit.details["healing_history"] = {
        "applied_patches": applied_patches,
        "attempts_executed": attempts_executed,
        "initial_score": initial_score,
        "final_score": current_audit.score,
        "healed": len(applied_patches) > 0,
    }

    return HealedPromptResult(scene if is_spec else working_prompt, current_audit)
