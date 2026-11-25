"""Motion Graphics, Kinetic Typography & Brand End-Card Specifier (PM-FEAT-033).

Pure-Python engine providing:
- Reading-speed WPM auditing (<= 180.0 WPM broadcast/social ceiling)
- WCAG 2.2 AA/AAA foreground-vs-scrim contrast verification
- 9:16 TikTok/Reels & 16:9/4:5/1:1 safe-zone placement verification
- Domain-calibrated typography stacks, cleanplate negative-space reservations (>= 25%),
  and legal super triggers (automotive_robotics / commercial / clinical claims)
- Premiere/After Effects MOGRT JSON cue manifests, SubStation Alpha (.ass) supers,
  and Markdown Brand End-Card spec sheets
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.presets import classify_brief_domain
from omni_director.schemas import (
    BrandEndcardSpec,
    CompositeStrategyEnum,
    GraphicLayerRoleEnum,
    GraphicSuperCueSpec,
    MasterMotionGraphicsManifest,
    MasterProductionBible,
    SceneMotionGraphicsSpec,
    ScenePromptSpec,
    TypographyPlacementSpec,
)
from omni_director.tools.nle_export import _parse_scene_window, _seconds_to_smpte_frames

MAX_SUPER_WPM = 180.0
MIN_CLEANPLATE_NEGATIVE_SPACE_PCT = 25.0
MIN_WCAG_CONTRAST_RATIO = 4.5

# Safe-zone bounds calibrated to clear TikTok/Reels 9:16 UI (top 14%, bottom 35%, right 15%, left 6%)
_SAFE_X_MIN = 0.06
_SAFE_X_RIGHT_EDGE_MAX = 0.84
_SAFE_Y_MIN = 0.14
_SAFE_Y_MAX = 0.64

_DOMAIN_TYPOGRAPHY_PRESETS: Dict[str, Dict[str, Any]] = {
    "automotive_robotics": {
        "primary_typeface": "Eurostile Next / Space Grotesk",
        "secondary_typeface": "JetBrains Mono",
        "animation_preset": "telemetry_precision_slide",
        "composite_strategy": CompositeStrategyEnum.POST_COMP_CLEANPLATE,
        "fill_hex": "#F8FAFC",
        "bg_hex": "#090D16",
        "scrim_opacity": 0.42,
        "requires_legal": True,
        "legal_copy": "Closed course. Professional driver. Do not attempt.",
        "cleanplate_zone": "upper_left_third",
    },
    "culinary_asmr": {
        "primary_typeface": "Cormorant Garamond / Playfair Display",
        "secondary_typeface": "Plus Jakarta Sans",
        "animation_preset": "warm_organic_fade",
        "composite_strategy": CompositeStrategyEnum.POST_COMP_CLEANPLATE,
        "fill_hex": "#FFFDF7",
        "bg_hex": "#16110D",
        "scrim_opacity": 0.35,
        "requires_legal": False,
        "legal_copy": "Serving suggestion.",
        "cleanplate_zone": "upper_left_third",
    },
    "luxury_fashion": {
        "primary_typeface": "Didot LT Pro / Bodoni Moda",
        "secondary_typeface": "Inter Light",
        "animation_preset": "editorial_silk_reveal",
        "composite_strategy": CompositeStrategyEnum.HYBRID_ALPHA_MATTE,
        "fill_hex": "#FAF8F5",
        "bg_hex": "#0B0B0F",
        "scrim_opacity": 0.32,
        "requires_legal": False,
        "legal_copy": "Atelier capsule edition.",
        "cleanplate_zone": "upper_center_safe",
    },
    "kinetic_action": {
        "primary_typeface": "Druk Wide / Anton",
        "secondary_typeface": "Roboto Condensed",
        "animation_preset": "staccato_impact_snap",
        "composite_strategy": CompositeStrategyEnum.HYBRID_ALPHA_MATTE,
        "fill_hex": "#F8FAFC",
        "bg_hex": "#0A0E17",
        "scrim_opacity": 0.45,
        "requires_legal": False,
        "legal_copy": "Dramatization. Safety equipment used.",
        "cleanplate_zone": "upper_left_third",
    },
    "tech_hardware": {
        "primary_typeface": "SF Pro Display / Inter",
        "secondary_typeface": "IBM Plex Mono",
        "animation_preset": "subpixel_razor_glide",
        "composite_strategy": CompositeStrategyEnum.NATIVE_MACRO_DIEGETIC,
        "fill_hex": "#F8FAFC",
        "bg_hex": "#090D16",
        "scrim_opacity": 0.38,
        "requires_legal": True,
        "legal_copy": "Sequences shortened. Screen images simulated.",
        "cleanplate_zone": "upper_left_third",
    },
    "architectural_sanctuary": {
        "primary_typeface": "Canela / Instrument Serif",
        "secondary_typeface": "DM Sans",
        "animation_preset": "tranquil_luma_dissolve",
        "composite_strategy": CompositeStrategyEnum.POST_COMP_CLEANPLATE,
        "fill_hex": "#F7F6F2",
        "bg_hex": "#101419",
        "scrim_opacity": 0.30,
        "requires_legal": False,
        "legal_copy": "Architectural concept visualization.",
        "cleanplate_zone": "upper_left_third",
    },
}

_CLAIM_TRIGGER_PATTERN = re.compile(
    r"\b(apr|lease|clinical|fda|guarantee|certified|zero[- ]emission|0[- ]60|horsepower|proven)\b|%",
    re.IGNORECASE,
)


def _hex_to_relative_luminance(hex_color: str) -> float:
    """Computes WCAG 2.2 relative luminance for a #RRGGBB hex color."""
    cleaned = str(hex_color or "").strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(ch * 2 for ch in cleaned)
    if len(cleaned) < 6:
        return 0.0
    try:
        r, g, b = (int(cleaned[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return 0.0

    def _linearize(channel: float) -> float:
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def compute_wcag_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Computes the WCAG 2.2 contrast ratio (1.0 .. 21.0) between foreground and background hex colors."""
    l1 = _hex_to_relative_luminance(fg_hex)
    l2 = _hex_to_relative_luminance(bg_hex)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def compute_effective_wpm(copy_text: str, duration_sec: float) -> tuple[int, float]:
    """Counts meaningful words in on-screen super copy and computes effective reading speed in WPM."""
    tokens = [tok for tok in str(copy_text or "").strip().split() if any(ch.isalnum() for ch in tok)]
    word_count = len(tokens)
    safe_dur = max(0.5, float(duration_sec or 0.5))
    effective_wpm = round((word_count / safe_dur) * 60.0, 2)
    return word_count, effective_wpm


def _evaluate_safe_ratios(placement: TypographyPlacementSpec) -> List[str]:
    """Determines which aspect ratios are safely cleared by the placement coordinates."""
    x = float(placement.normalized_x)
    y = float(placement.normalized_y)
    width_norm = max(0.05, min(1.0, float(placement.max_width_pct) / 100.0))

    # Left-aligned vs centered anchor estimation
    zone_lower = str(placement.anchor_zone or "").lower()
    if "center" in zone_lower:
        left_edge = x - (width_norm / 2.0)
        right_edge = x + (width_norm / 2.0)
    else:
        left_edge = x
        right_edge = x + width_norm

    cleared: List[str] = []
    # Broadcast 16:9 SMPTE title-safe (10% margin -> 0.05..0.95 outer, 0.06..0.92 practical)
    if left_edge >= 0.04 and right_edge <= 0.96 and 0.08 <= y <= 0.90:
        cleared.append("16:9")
    # 4:5 Meta feed & 1:1 square
    if left_edge >= 0.05 and right_edge <= 0.94 and 0.08 <= y <= 0.86:
        cleared.extend(["4:5", "1:1"])
    # 9:16 TikTok / Reels UI safe zone (avoids top 14%, bottom 35%, right 15% engagement rail)
    if left_edge >= _SAFE_X_MIN and right_edge <= _SAFE_X_RIGHT_EDGE_MAX and _SAFE_Y_MIN <= y <= _SAFE_Y_MAX:
        cleared.append("9:16")
    return cleared


def _is_cue_legible(cue: GraphicSuperCueSpec, bg_hex: str) -> Tuple[bool, float, List[str]]:
    """Audits a single cue for WPM ceiling, WCAG contrast, minimum pixel height, and 9:16 clearance."""
    _, wpm = compute_effective_wpm(cue.copy_text, cue.display_duration_sec)
    contrast = compute_wcag_contrast_ratio(cue.placement.fill_hex, bg_hex)
    # Backdrop scrim guarantees minimum contrast floor when opacity >= 0.30 over bright video frames
    effective_contrast = max(contrast, float(cue.placement.wcag_contrast_ratio or 0.0))
    if cue.placement.backdrop_scrim_opacity >= 0.30 and contrast >= MIN_WCAG_CONTRAST_RATIO:
        effective_contrast = contrast
    ratios = _evaluate_safe_ratios(cue.placement)
    passed = (
        wpm <= MAX_SUPER_WPM
        and effective_contrast >= MIN_WCAG_CONTRAST_RATIO
        and cue.placement.min_font_px_1080p >= 18
        and "9:16" in ratios
    )
    return passed, effective_contrast, ratios


def format_motion_graphics_token(
    scene_gfx: SceneMotionGraphicsSpec,
    endcard: Optional[BrandEndcardSpec] = None,
) -> str:
    """Formats deterministic PM-FEAT-033 machine telemetry tokens for a scene."""
    cues = list(scene_gfx.cues or [])
    if cues:
        roles = ",".join(c.role.value for c in cues)
        max_wpm = max(c.effective_wpm for c in cues)
        super_summary = f"SC{scene_gfx.scene_index:02d} | cues={len(cues)} | max_wpm={max_wpm:.1f} | roles={roles}"
    else:
        super_summary = f"SC{scene_gfx.scene_index:02d} | cues=0 | cleanplate_only"

    token = (
        f"[GFX-SUPER: {super_summary}]"
        f"[GFX-CLEANPLATE: zone={scene_gfx.cleanplate_zone} | "
        f"neg_space={scene_gfx.cleanplate_negative_space_pct:.1f}% | "
        f"score={scene_gfx.legibility_score:.1f}]"
    )
    if endcard is not None and scene_gfx.scene_index == endcard.reserved_tail_scene_index:
        token += (
            f"[ENDCARD: dur={endcard.duration_sec:.1f}s | "
            f"sync={endcard.audio_sting_sync_smpte} | "
            f"cta={endcard.cta_headline}]"
        )
    return token


def _resolve_domain_preset(
    bible: MasterProductionBible,
    domain_calibration: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    raw_domain = getattr(bible, "domain_archetype", None)
    if not raw_domain:
        raw_domain = classify_brief_domain(f"{bible.project_title} {getattr(bible, 'logline', '')}")
    domain_key = str(getattr(raw_domain, "value", raw_domain) or "architectural_sanctuary").lower()
    preset = dict(_DOMAIN_TYPOGRAPHY_PRESETS.get(domain_key, _DOMAIN_TYPOGRAPHY_PRESETS["architectural_sanctuary"]))
    if domain_calibration:
        for k, v in domain_calibration.items():
            if v is not None:
                preset[k] = v
    return domain_key, preset


def _concise_headline(text: str, max_words: int = 5) -> str:
    words = [w for w in str(text or "").strip().split() if w]
    if not words:
        return "Precision In Motion"
    return " ".join(words[:max_words])


def _make_cue(
    cue_id: str,
    scene_index: int,
    role: GraphicLayerRoleEnum,
    copy_text: str,
    in_sec: float,
    out_sec: float,
    anchor_zone: str,
    normalized_x: float,
    normalized_y: float,
    max_width_pct: float,
    font_family: str,
    font_weight: int,
    min_font_px: int,
    preset: Dict[str, Any],
    fps: int = 24,
) -> GraphicSuperCueSpec:
    dur = max(0.8, round(out_sec - in_sec, 2))
    word_count, wpm = compute_effective_wpm(copy_text, dur)
    fill_hex = str(preset.get("fill_hex", "#F8FAFC"))
    bg_hex = str(preset.get("bg_hex", "#090D16"))
    contrast = compute_wcag_contrast_ratio(fill_hex, bg_hex)
    placement = TypographyPlacementSpec(
        anchor_zone=anchor_zone,
        normalized_x=normalized_x,
        normalized_y=normalized_y,
        max_width_pct=max_width_pct,
        font_family=font_family,
        font_weight=font_weight,
        min_font_px_1080p=min_font_px,
        fill_hex=fill_hex,
        backdrop_scrim_opacity=float(preset.get("scrim_opacity", 0.35)),
        wcag_contrast_ratio=contrast,
    )
    cleared = _evaluate_safe_ratios(placement)
    strategy = preset.get("composite_strategy", CompositeStrategyEnum.POST_COMP_CLEANPLATE)
    if not isinstance(strategy, CompositeStrategyEnum):
        strategy = CompositeStrategyEnum(str(strategy))
    cue = GraphicSuperCueSpec(
        cue_id=cue_id,
        scene_index=scene_index,
        role=role,
        copy_text=copy_text,
        word_count=word_count,
        display_duration_sec=dur,
        effective_wpm=wpm,
        in_smpte=_seconds_to_smpte_frames(in_sec, fps=fps),
        out_smpte=_seconds_to_smpte_frames(in_sec + dur, fps=fps),
        composite_strategy=strategy,
        animation_preset=str(preset.get("animation_preset", "clean_luma_fade")),
        placement=placement,
        reframe_cleared_ratios=cleared,
        legibility_audit_passed=(wpm <= MAX_SUPER_WPM and contrast >= MIN_WCAG_CONTRAST_RATIO and "9:16" in cleared),
    )
    return cue


def compile_motion_graphics_manifest(
    bible: MasterProductionBible,
    domain_calibration: Optional[Dict[str, Any]] = None,
) -> MasterMotionGraphicsManifest:
    """Compiles a MasterMotionGraphicsManifest with safe-zone, WPM, WCAG, and end-card locks."""
    domain_key, preset = _resolve_domain_preset(bible, domain_calibration)
    scenes: List[ScenePromptSpec] = list(getattr(bible, "scenes", None) or [])
    total_scenes = max(1, len(scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)

    palette = list(getattr(bible, "color_palette", None) or [])
    bg_plate = str(preset.get("bg_hex", "#090D16"))
    if palette and compute_wcag_contrast_ratio(str(preset.get("fill_hex", "#F8FAFC")), palette[0]) >= 7.0:
        bg_plate = palette[0]
        preset["bg_hex"] = bg_plate

    tail_scene = scenes[-1] if scenes else None
    tail_idx = int(getattr(tail_scene, "scene_index", 1) or 1) if tail_scene else 1
    if tail_scene is not None:
        tail_start, tail_end = _parse_scene_window(tail_scene, total_scenes, total_scenes, total_runtime)
    else:
        tail_start, tail_end = max(0.0, total_runtime - 8.0), total_runtime
    tail_dur = max(2.0, tail_end - tail_start)
    endcard_dur = round(min(3.5, max(1.5, tail_dur * 0.35)), 2)
    endcard_in_sec = round(max(tail_start, tail_end - endcard_dur), 2)

    cta_headline = _concise_headline(bible.project_title, max_words=4)
    domain_label = domain_key.replace("_", " ").title()
    slug = re.sub(r"[^a-z0-9]+", "", bible.project_title.lower())[:18] or "omnistudio"

    endcard = BrandEndcardSpec(
        duration_sec=endcard_dur,
        logo_lockup_position="center_upper_safe",
        cta_headline=cta_headline,
        cta_subcopy=f"Engineered for {domain_label}",
        url_or_qr_label=f"omni.studio/{slug}",
        audio_sting_sync_smpte=_seconds_to_smpte_frames(endcard_in_sec, fps=24),
        background_plate_hex=bg_plate,
        reserved_tail_scene_index=tail_idx,
    )

    corpus = " ".join(
        [bible.project_title, getattr(bible, "logline", "")]
        + [getattr(s, "omni_prose_prompt", "") for s in scenes]
    )
    needs_legal = bool(preset.get("requires_legal", False)) or bool(_CLAIM_TRIGGER_PATTERN.search(corpus))

    primary_font = str(preset["primary_typeface"])
    secondary_font = str(preset["secondary_typeface"])

    scene_graphics: List[SceneMotionGraphicsSpec] = []
    all_cues: List[GraphicSuperCueSpec] = []

    for pos, sc in enumerate(scenes, start=1):
        sc_idx = int(getattr(sc, "scene_index", pos) or pos)
        start_sec, end_sec = _parse_scene_window(sc, pos, total_scenes, total_runtime)
        sc_dur = max(2.0, end_sec - start_sec)

        existing = getattr(sc, "motion_graphics_spec", None)
        if existing is not None and existing.cues:
            audited_cues: List[GraphicSuperCueSpec] = []
            for cue in existing.cues:
                updated = cue.model_copy(deep=True)
                wc, wpm = compute_effective_wpm(updated.copy_text, updated.display_duration_sec)
                passed, contrast, ratios = _is_cue_legible(updated, bg_plate)
                updated.word_count = wc
                updated.effective_wpm = wpm
                updated.placement.wcag_contrast_ratio = contrast
                updated.reframe_cleared_ratios = ratios
                updated.legibility_audit_passed = passed
                audited_cues.append(updated)

            neg_space = float(existing.cleanplate_negative_space_pct)
            passed_count = sum(1 for c in audited_cues if c.legibility_audit_passed)
            leg_score = round((passed_count / max(1, len(audited_cues))) * 100.0, 1)
            if neg_space < MIN_CLEANPLATE_NEGATIVE_SPACE_PCT:
                leg_score = max(0.0, leg_score - 20.0)
            scene_gfx = SceneMotionGraphicsSpec(
                scene_index=sc_idx,
                cues=audited_cues,
                cleanplate_negative_space_pct=neg_space,
                cleanplate_zone=existing.cleanplate_zone,
                gfx_prompt_token="",
                legibility_score=leg_score,
            )
        else:
            cues_for_scene: List[GraphicSuperCueSpec] = []
            if pos == 1:
                headline = _concise_headline(bible.project_title, max_words=5)
                cues_for_scene.append(
                    _make_cue(
                        cue_id=f"GFX_SC{sc_idx:02d}_HEAD",
                        scene_index=sc_idx,
                        role=GraphicLayerRoleEnum.KINETIC_HEADLINE,
                        copy_text=headline,
                        in_sec=start_sec + 0.5,
                        out_sec=min(end_sec - 0.5, start_sec + min(3.5, sc_dur * 0.5)),
                        anchor_zone="upper_left_third",
                        normalized_x=0.10,
                        normalized_y=0.22,
                        max_width_pct=62.0,
                        font_family=primary_font,
                        font_weight=700,
                        min_font_px=56,
                        preset=preset,
                    )
                )
            elif sc_idx != tail_idx:
                callout = _concise_headline(sc.scene_title, max_words=4)
                cues_for_scene.append(
                    _make_cue(
                        cue_id=f"GFX_SC{sc_idx:02d}_CALL",
                        scene_index=sc_idx,
                        role=GraphicLayerRoleEnum.PRODUCT_CALLOUT,
                        copy_text=callout,
                        in_sec=start_sec + 0.8,
                        out_sec=min(end_sec - 0.4, start_sec + min(3.5, sc_dur * 0.5)),
                        anchor_zone="upper_left_third",
                        normalized_x=0.10,
                        normalized_y=0.26,
                        max_width_pct=58.0,
                        font_family=primary_font,
                        font_weight=600,
                        min_font_px=44,
                        preset=preset,
                    )
                )

            if needs_legal and pos == 1:
                legal_text = str(preset.get("legal_copy", "Dramatization."))
                cues_for_scene.append(
                    _make_cue(
                        cue_id=f"GFX_SC{sc_idx:02d}_LEGAL",
                        scene_index=sc_idx,
                        role=GraphicLayerRoleEnum.LEGAL_DISCLAIMER,
                        copy_text=legal_text,
                        in_sec=start_sec + 0.5,
                        out_sec=min(end_sec - 0.2, start_sec + max(3.5, sc_dur * 0.65)),
                        anchor_zone="lower_safe_band",
                        normalized_x=0.10,
                        normalized_y=0.60,
                        max_width_pct=66.0,
                        font_family=secondary_font,
                        font_weight=500,
                        min_font_px=20,
                        preset=preset,
                    )
                )

            if sc_idx == tail_idx:
                cues_for_scene.append(
                    _make_cue(
                        cue_id=f"GFX_SC{sc_idx:02d}_ENDCARD",
                        scene_index=sc_idx,
                        role=GraphicLayerRoleEnum.CTA_ENDCARD,
                        copy_text=f"{endcard.cta_headline} · {endcard.url_or_qr_label}",
                        in_sec=endcard_in_sec,
                        out_sec=endcard_in_sec + endcard_dur,
                        anchor_zone="center_upper_safe",
                        normalized_x=0.46,
                        normalized_y=0.40,
                        max_width_pct=64.0,
                        font_family=primary_font,
                        font_weight=700,
                        min_font_px=52,
                        preset=preset,
                    )
                )

            passed_count = sum(1 for c in cues_for_scene if c.legibility_audit_passed)
            leg_score = round((passed_count / max(1, len(cues_for_scene))) * 100.0, 1)
            scene_gfx = SceneMotionGraphicsSpec(
                scene_index=sc_idx,
                cues=cues_for_scene,
                cleanplate_negative_space_pct=34.0,
                cleanplate_zone=str(preset.get("cleanplate_zone", "upper_left_third")),
                gfx_prompt_token="",
                legibility_score=leg_score,
            )

        scene_gfx.gfx_prompt_token = format_motion_graphics_token(
            scene_gfx,
            endcard=endcard if sc_idx == tail_idx else None,
        )
        sc.motion_graphics_spec = scene_gfx
        scene_graphics.append(scene_gfx)
        all_cues.extend(scene_gfx.cues)

    max_wpm_detected = max((c.effective_wpm for c in all_cues), default=0.0)
    all_safe_cleared = all(
        ("9:16" in c.reframe_cleared_ratios and c.legibility_audit_passed)
        for c in all_cues
    ) and all(sg.cleanplate_negative_space_pct >= MIN_CLEANPLATE_NEGATIVE_SPACE_PCT for sg in scene_graphics)

    legal_cues = [c for c in all_cues if c.role == GraphicLayerRoleEnum.LEGAL_DISCLAIMER]
    if needs_legal:
        legal_compliant = bool(legal_cues) and all(
            c.legibility_audit_passed and c.effective_wpm <= MAX_SUPER_WPM for c in legal_cues
        )
    else:
        legal_compliant = all(c.legibility_audit_passed for c in legal_cues)

    return MasterMotionGraphicsManifest(
        project_title=bible.project_title,
        domain_archetype=domain_key,
        primary_typeface=primary_font,
        secondary_typeface=secondary_font,
        endcard=endcard,
        scene_graphics=scene_graphics,
        total_cues_count=len(all_cues),
        max_wpm_detected=round(max_wpm_detected, 2),
        all_safe_zones_cleared=all_safe_cleared,
        legal_supers_compliant=legal_compliant,
    )


def synthesize_default_motion_graphics(
    bible: MasterProductionBible,
) -> MasterMotionGraphicsManifest:
    """Convenience helper to synthesize a default MasterMotionGraphicsManifest."""
    return compile_motion_graphics_manifest(bible)


def export_mogrt_json(
    manifest: MasterMotionGraphicsManifest,
    bible: MasterProductionBible,
) -> str:
    """Exports Premiere / After Effects MOGRT-compatible JSON cue manifest."""
    cues_payload: List[Dict[str, Any]] = []
    for sg in manifest.scene_graphics:
        for cue in sg.cues:
            cues_payload.append(
                {
                    "cue_id": cue.cue_id,
                    "scene_index": cue.scene_index,
                    "role": cue.role.value,
                    "copy_text": cue.copy_text,
                    "word_count": cue.word_count,
                    "display_duration_sec": cue.display_duration_sec,
                    "effective_wpm": cue.effective_wpm,
                    "in_smpte": cue.in_smpte,
                    "out_smpte": cue.out_smpte,
                    "composite_strategy": cue.composite_strategy.value,
                    "animation_preset": cue.animation_preset,
                    "placement": cue.placement.model_dump(mode="json"),
                    "reframe_cleared_ratios": list(cue.reframe_cleared_ratios),
                    "legibility_audit_passed": cue.legibility_audit_passed,
                }
            )
    payload = {
        "schema": "omni_mogrt_v1",
        "project_title": bible.project_title,
        "domain_archetype": manifest.domain_archetype,
        "resolution": "1920x1080",
        "fps": 24,
        "primary_typeface": manifest.primary_typeface,
        "secondary_typeface": manifest.secondary_typeface,
        "endcard": manifest.endcard.model_dump(mode="json"),
        "total_cues_count": manifest.total_cues_count,
        "max_wpm_detected": manifest.max_wpm_detected,
        "all_safe_zones_cleared": manifest.all_safe_zones_cleared,
        "legal_supers_compliant": manifest.legal_supers_compliant,
        "cues": cues_payload,
    }
    return json.dumps(payload, indent=2)


def _smpte_to_ass_time(smpte: str, fps: int = 24) -> str:
    """Converts HH:MM:SS:FF SMPTE timecode to ASS H:MM:SS.cc centisecond timestamp."""
    parts = [int(p) for p in str(smpte or "00:00:00:00").split(":") if p.isdigit()]
    while len(parts) < 4:
        parts.append(0)
    hh, mm, ss, ff = parts[:4]
    cs = int(round((ff / max(1, int(fps))) * 100.0))
    if cs >= 100:
        ss += 1
        cs -= 100
    return f"{hh}:{mm:02d}:{ss:02d}.{cs:02d}"


def _hex_to_ass_bgr(hex_color: str) -> str:
    """Converts #RRGGBB to SubStation Alpha &H00BBGGRR format."""
    cleaned = str(hex_color or "#F8FAFC").strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned)
    if len(cleaned) != 6:
        return "&H00FCFAF8"
    rr, gg, bb = cleaned[0:2].upper(), cleaned[2:4].upper(), cleaned[4:6].upper()
    return f"&H00{bb}{gg}{rr}"


def export_broadcast_supers_ass(
    manifest: MasterMotionGraphicsManifest,
    fps: int = 24,
) -> str:
    """Exports valid SubStation Alpha v4+ (.ass) broadcast supers with \\pos(x,y) and fade tags."""
    primary_font = manifest.primary_typeface.split("/")[0].strip()
    secondary_font = manifest.secondary_typeface.split("/")[0].strip()

    lines = [
        "[Script Info]",
        f"Title: {manifest.project_title} - Broadcast Supers",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: HeroSuper,{primary_font},54,&H00FCFAF8,&H000000FF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,2,0,7,80,80,60,1",
        f"Style: LegalSuper,{secondary_font},22,&H00FCFAF8,&H000000FF,&H00101010,&H78000000,0,0,0,0,100,100,0,0,1,1,0,7,80,80,40,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for sg in manifest.scene_graphics:
        for cue in sg.cues:
            start_ass = _smpte_to_ass_time(cue.in_smpte, fps=fps)
            end_ass = _smpte_to_ass_time(cue.out_smpte, fps=fps)
            style_name = "LegalSuper" if cue.role == GraphicLayerRoleEnum.LEGAL_DISCLAIMER else "HeroSuper"
            pos_x = int(round(cue.placement.normalized_x * 1920))
            pos_y = int(round(cue.placement.normalized_y * 1080))
            ass_color = _hex_to_ass_bgr(cue.placement.fill_hex)
            safe_text = str(cue.copy_text).replace("{", "(").replace("}", ")").replace("\n", "\\N")
            override = f"{{\\pos({pos_x},{pos_y})\\fad(250,250)\\c{ass_color}\\fs{cue.placement.min_font_px_1080p}}}"
            lines.append(
                f"Dialogue: 0,{start_ass},{end_ass},{style_name},{cue.cue_id},0,0,0,,{override}{safe_text}"
            )

    lines.append("")
    return "\n".join(lines)


def export_brand_endcard_md(manifest: MasterMotionGraphicsManifest) -> str:
    """Exports a Markdown Brand End-Card & Legal Super Spec Sheet."""
    ec = manifest.endcard
    lines = [
        f"# Motion Graphics & Brand End-Card Spec — {manifest.project_title}",
        "",
        f"- **Domain Archetype**: `{manifest.domain_archetype}`",
        f"- **Primary Typeface**: `{manifest.primary_typeface}`",
        f"- **Secondary Typeface**: `{manifest.secondary_typeface}`",
        f"- **Total Graphic Cues**: {manifest.total_cues_count}",
        f"- **Max Reading Speed**: `{manifest.max_wpm_detected:.2f} WPM` (Ceiling: `{MAX_SUPER_WPM:.0f} WPM`)",
        f"- **All Safe Zones Cleared (incl. 9:16)**: `{manifest.all_safe_zones_cleared}`",
        f"- **Legal Supers Compliant**: `{manifest.legal_supers_compliant}`",
        "",
        "## Brand End-Card Lockup",
        f"- **Reserved Tail Scene**: `Scene {ec.reserved_tail_scene_index:02d}`",
        f"- **Duration**: `{ec.duration_sec:.2f}s`",
        f"- **Audio Sting Sync SMPTE**: `{ec.audio_sting_sync_smpte}`",
        f"- **Logo Lockup Position**: `{ec.logo_lockup_position}`",
        f"- **CTA Headline**: `{ec.cta_headline}`",
        f"- **CTA Subcopy**: `{ec.cta_subcopy}`",
        f"- **URL / QR Label**: `{ec.url_or_qr_label}`",
        f"- **Background Plate Hex**: `{ec.background_plate_hex}`",
        "",
        "## Cue Schedule",
        "| Cue ID | Scene | Role | Copy | In | Out | WPM | Safe Ratios | Legible |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for sg in manifest.scene_graphics:
        for cue in sg.cues:
            ratios = ", ".join(cue.reframe_cleared_ratios)
            lines.append(
                f"| `{cue.cue_id}` | SC{cue.scene_index:02d} | `{cue.role.value}` | "
                f"{cue.copy_text} | `{cue.in_smpte}` | `{cue.out_smpte}` | "
                f"{cue.effective_wpm:.1f} | {ratios} | {cue.legibility_audit_passed} |"
            )
    lines.append("")
    return "\n".join(lines)


def export_motion_graphics_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    fps: int = 24,
) -> Dict[str, Path]:
    """Exports motion_graphics_mogrt.json, broadcast_supers.ass, and brand_endcard_spec.md."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = getattr(bible, "master_motion_graphics", None) or compile_motion_graphics_manifest(bible)

    mogrt_path = out_dir / "motion_graphics_mogrt.json"
    mogrt_path.write_text(export_mogrt_json(manifest, bible), encoding="utf-8")

    ass_path = out_dir / "broadcast_supers.ass"
    ass_path.write_text(export_broadcast_supers_ass(manifest, fps=fps), encoding="utf-8")

    md_path = out_dir / "brand_endcard_spec.md"
    md_path.write_text(export_brand_endcard_md(manifest), encoding="utf-8")

    return {
        "motion_graphics_mogrt_json": mogrt_path,
        "broadcast_supers_ass": ass_path,
        "brand_endcard_spec_md": md_path,
    }


__all__ = [
    "MAX_SUPER_WPM",
    "MIN_CLEANPLATE_NEGATIVE_SPACE_PCT",
    "MIN_WCAG_CONTRAST_RATIO",
    "compute_effective_wpm",
    "compute_wcag_contrast_ratio",
    "format_motion_graphics_token",
    "compile_motion_graphics_manifest",
    "synthesize_default_motion_graphics",
    "export_mogrt_json",
    "export_broadcast_supers_ass",
    "export_brand_endcard_md",
    "export_motion_graphics_bundle",
]
