"""Prompt Auditor tool implementing the 7-Point Gemini Omni Prompting Verification Checklist."""

import re
from typing import List, Optional
from omni_director.schemas import AuditResult, RegimeType, ScenePromptSpec


def audit_omni_scene_prompt(scene: ScenePromptSpec, regime: Optional[RegimeType] = None) -> AuditResult:
    """Audits a single ScenePromptSpec against the 7-Point Gemini Omni prompt standards.

    Rules:
    1. No internal markdown headers (###, ##, #) inside the generation prompt (prevents on-screen text hallucinations).
    2. Max 3 serialized action beats per 10s window (prevents temporal rushing and object morphing).
    3. Regime 2 mandates 1.0x real-time speed, gravity/friction locks, and a 5-part kinetic contact chain.
    4. CRAFT camera completeness (Composition, Route, Action Anchor, Focus/Axis Invariant, Tone/Rig).
    5. Max 3 Nano Banana image references (<image_1>, <image_2>, <image_3>) with single-duty contracts.
    6. Synchronized diegetic audio specification included natively.
    7. Mode B extension continuity check (unbroken continuous flow if extension scene).
    """
    errors: List[str] = []
    warnings: List[str] = []
    details: dict = {}
    prompt = scene.omni_prose_prompt

    # Rule 1: Clean natural prose formatting (NO markdown headers inside prompt)
    heading_match = re.search(r"(^|\n)\s*#{1,6}\s+", prompt)
    if heading_match:
        errors.append(
            "Rule 1 Violation: Markdown heading ('#', '##', '###') detected inside omni_prose_prompt. "
            "Gemini Omni's internal visual text engine can misinterpret headings as graphic text overlay instructions. "
            "Format prompt as unbroken natural-language prose."
        )

    # Rule 2: Max 3 serialized action beats per 10s window
    details["action_beats_count"] = len(scene.action_beats)
    if len(scene.action_beats) > 3:
        errors.append(
            f"Rule 2 Violation: {len(scene.action_beats)} action beats detected. "
            "Gemini Omni enforces a strict ceiling of max 3 serialized cause-and-effect beats per 10s window."
        )

    # Rule 3: Regime 2 High-Kinetic & Precision Commercial constraints
    effective_regime = regime or scene.regime
    if effective_regime == RegimeType.REGIME_2_KINETIC:
        # Check 1.0x real-time playback lock
        has_speed_lock = bool(re.search(r"\b1\.0x\b|real-time|natural speed", prompt, re.IGNORECASE))
        if not has_speed_lock:
            errors.append(
                "Rule 3 Violation: Regime 2 requires explicit '1.0x' or 'real-time' playback speed lock "
                "to eliminate floatiness and prevent the model from defaulting to dreamy slow motion."
            )

        # Check kinetic contact chain
        if not scene.kinetic_contact_chain or len(scene.kinetic_contact_chain.strip()) < 10:
            errors.append(
                "Rule 3 Violation: Regime 2 requires an explicit 5-part Kinetic Contact Chain "
                "(Initiation -> Contact Point -> Force Transfer -> Environmental Evidence -> Recovery Stance)."
            )

        # Check positive physics / friction / gravity invariants
        has_physics_terms = bool(re.search(r"gravity|friction|rigid|momentum|solid|weight", prompt, re.IGNORECASE))
        if not has_physics_terms:
            warnings.append(
                "Rule 3 Warning: Regime 2 prompt should explicitly invoke physical invariants "
                "(gravity, friction, rigid materials, or momentum) to prevent elastic cushioning."
            )

    # Rule 4: CRAFT camera completeness
    camera_terms = ["camera", "shot", "lens", "framing", "dolly", "steadicam", "tripod", "pan", "tracking", "close-up", "wide"]
    has_camera = any(term in prompt.lower() for term in camera_terms)
    if scene.craft_camera is not None:
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
        max_ref = max(int(idx) for idx in image_refs)
        details["image_refs_detected"] = [f"<image_{idx}>" for idx in set(image_refs)]
        if max_ref > 3:
            errors.append(
                f"Rule 5 Violation: Reference <image_{max_ref}> detected. "
                "Gemini Omni enforces an architectural ceiling of at most 3 image references (<image_1>, <image_2>, <image_3>)."
            )

    # Rule 6: Synchronized diegetic audio inclusion
    audio_keywords = ["audio", "sound", "foley", "acoustic", "pop", "thud", "snap", "click", "rustle", "tone", "music", "hum", "whisper", "reverb"]
    has_audio_mention = any(k in prompt.lower() for k in audio_keywords)
    if not has_audio_mention and (scene.diegetic_sonic is None or not scene.diegetic_sonic.foley_cues):
        errors.append(
            "Rule 6 Violation: Synchronized diegetic audio cues are missing from prompt. "
            "Gemini Omni requires explicit foley, surface acoustics, or sound effects embedded in the video prompt."
        )

    # Rule 7: Mode B extension continuity check
    is_extension = bool(re.search(r"\+10s|extension", scene.timestamp_range, re.IGNORECASE))
    if is_extension:
        continuity_keywords = ["continue", "continuous", "unbroken", "without jump cut", "maintains", "extending"]
        has_continuity = any(k in prompt.lower() for k in continuity_keywords)
        if not has_continuity:
            warnings.append(
                "Rule 7 Warning: Mode B extension scene should explicitly assert unbroken camera and physical continuity "
                "('One continuous shot, no jump cuts')."
            )

    passed = len(errors) == 0
    return AuditResult(
        scene_index=scene.scene_index,
        passed=passed,
        errors=errors,
        warnings=warnings,
        details=details
    )
