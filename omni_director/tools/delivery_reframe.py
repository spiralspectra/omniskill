"""Multi-Aspect Social Reframe, Safe-Zone Cropping & Cutdown Delivery Engine (PM-FEAT-021).

Pure-Python engine providing:
- Mathematical pan-and-scan crop window calculation across 16:9, 9:16, 4:5, 1:1, and 2.39:1
- Platform UI safe-zone clearance auditing (Broadcast TV, TikTok, Instagram Reels, YouTube Shorts, Meta 4:5, Cinema 2.39:1)
- Automated broadcast/social editorial cutdown synthesis (:30s when runtime >= 30s, :15s, :06s bumper)
- CMX 3600 cutdown EDLs, FCPXML v1.10 vertical reframe timelines, CSV crop matrices, and JSON manifests
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from xml.sax.saxutils import escape as xml_escape

from omni_director.schemas import (
    AspectCropWindowSpec,
    CutdownFormatType,
    CutdownSegmentSpec,
    CutdownVersionSpec,
    DeliverableAspectRatio,
    DeliveryReframeManifestSpec,
    MasterProductionBible,
    ReframePanMode,
    ScenePromptSpec,
    SceneReframeSpec,
    SocialDeliveryPlatform,
)


# Platform UI Safe-Zone Geometry & Mastering Output Resolutions
PLATFORM_SAFE_ZONES: Dict[str, Dict[str, Any]] = {
    SocialDeliveryPlatform.BROADCAST_TV.value: {
        "platform": SocialDeliveryPlatform.BROADCAST_TV,
        "aspect_ratio": DeliverableAspectRatio.RATIO_16_9,
        "output_width_px": 1920,
        "output_height_px": 1080,
        "top_pct": 10.0,
        "bottom_pct": 10.0,
        "left_pct": 10.0,
        "right_pct": 10.0,
        "notes": "SMPTE ST 2046 action-safe 5% / title-safe 10% broadcast envelope",
    },
    SocialDeliveryPlatform.TIKTOK_9X16.value: {
        "platform": SocialDeliveryPlatform.TIKTOK_9X16,
        "aspect_ratio": DeliverableAspectRatio.RATIO_9_16,
        "output_width_px": 1080,
        "output_height_px": 1920,
        "top_pct": 14.0,
        "bottom_pct": 35.0,
        "left_pct": 6.0,
        "right_pct": 15.0,
        "notes": "TikTok 9:16 UI overlay clearance (top search/tabs, bottom caption/audio bar, right engagement rail)",
    },
    SocialDeliveryPlatform.REELS_9X16.value: {
        "platform": SocialDeliveryPlatform.REELS_9X16,
        "aspect_ratio": DeliverableAspectRatio.RATIO_9_16,
        "output_width_px": 1080,
        "output_height_px": 1920,
        "top_pct": 14.0,
        "bottom_pct": 32.0,
        "left_pct": 6.0,
        "right_pct": 14.0,
        "notes": "Instagram Reels 9:16 UI overlay clearance (bottom handle/caption, right action stack)",
    },
    SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16.value: {
        "platform": SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
        "aspect_ratio": DeliverableAspectRatio.RATIO_9_16,
        "output_width_px": 1080,
        "output_height_px": 1920,
        "top_pct": 12.0,
        "bottom_pct": 30.0,
        "left_pct": 6.0,
        "right_pct": 14.0,
        "notes": "YouTube Shorts 9:16 UI overlay clearance (bottom title/subscribe CTA, right icons)",
    },
    SocialDeliveryPlatform.META_FEED_4X5.value: {
        "platform": SocialDeliveryPlatform.META_FEED_4X5,
        "aspect_ratio": DeliverableAspectRatio.RATIO_4_5,
        "output_width_px": 1080,
        "output_height_px": 1350,
        "top_pct": 8.0,
        "bottom_pct": 12.0,
        "left_pct": 6.0,
        "right_pct": 6.0,
        "notes": "Meta / Instagram Feed 4:5 vertical-mobile card safe area",
    },
    SocialDeliveryPlatform.CINEMA_239.value: {
        "platform": SocialDeliveryPlatform.CINEMA_239,
        "aspect_ratio": DeliverableAspectRatio.RATIO_2_39_1,
        "output_width_px": 2048,
        "output_height_px": 858,
        "top_pct": 5.0,
        "bottom_pct": 5.0,
        "left_pct": 5.0,
        "right_pct": 5.0,
        "notes": "DCI 2K Scope 2.39:1 theatrical projection matte",
    },
}


_ASPECT_NUMERIC: Dict[str, float] = {
    DeliverableAspectRatio.RATIO_16_9.value: 16.0 / 9.0,
    DeliverableAspectRatio.RATIO_9_16.value: 9.0 / 16.0,
    DeliverableAspectRatio.RATIO_4_5.value: 4.0 / 5.0,
    DeliverableAspectRatio.RATIO_1_1.value: 1.0,
    DeliverableAspectRatio.RATIO_2_39_1.value: 2.39,
}

_DEFAULT_OUTPUT_DIMS: Dict[str, Tuple[int, int]] = {
    DeliverableAspectRatio.RATIO_16_9.value: (1920, 1080),
    DeliverableAspectRatio.RATIO_9_16.value: (1080, 1920),
    DeliverableAspectRatio.RATIO_4_5.value: (1080, 1350),
    DeliverableAspectRatio.RATIO_1_1.value: (1080, 1080),
    DeliverableAspectRatio.RATIO_2_39_1.value: (2048, 858),
}


def _coerce_aspect_ratio(value: Union[DeliverableAspectRatio, str]) -> DeliverableAspectRatio:
    if isinstance(value, DeliverableAspectRatio):
        return value
    raw = str(value).strip()
    for member in DeliverableAspectRatio:
        if raw == member.value or raw.lower() == member.name.lower():
            return member
    if "9:16" in raw or "9x16" in raw:
        return DeliverableAspectRatio.RATIO_9_16
    if "4:5" in raw or "4x5" in raw:
        return DeliverableAspectRatio.RATIO_4_5
    if "1:1" in raw or "1x1" in raw:
        return DeliverableAspectRatio.RATIO_1_1
    if "2.39" in raw:
        return DeliverableAspectRatio.RATIO_2_39_1
    return DeliverableAspectRatio.RATIO_16_9


def _coerce_platform(
    platform: Union[SocialDeliveryPlatform, str, None],
    aspect_ratio: DeliverableAspectRatio,
) -> SocialDeliveryPlatform:
    if isinstance(platform, SocialDeliveryPlatform):
        return platform
    if platform is not None:
        raw = str(platform).strip().lower()
        for member in SocialDeliveryPlatform:
            if raw == member.value or raw == member.name.lower():
                return member
    if aspect_ratio == DeliverableAspectRatio.RATIO_9_16:
        return SocialDeliveryPlatform.TIKTOK_9X16
    if aspect_ratio == DeliverableAspectRatio.RATIO_4_5:
        return SocialDeliveryPlatform.META_FEED_4X5
    if aspect_ratio == DeliverableAspectRatio.RATIO_2_39_1:
        return SocialDeliveryPlatform.CINEMA_239
    return SocialDeliveryPlatform.BROADCAST_TV


def _coerce_pan_mode(pan_mode: Union[ReframePanMode, str]) -> ReframePanMode:
    if isinstance(pan_mode, ReframePanMode):
        return pan_mode
    raw = str(pan_mode).strip().lower()
    for member in ReframePanMode:
        if raw == member.value or raw == member.name.lower():
            return member
    return ReframePanMode.EASE_IN_OUT_COI


def _seconds_to_smpte(seconds: float, fps: int = 24) -> str:
    total_frames = max(0, int(round(seconds * fps)))
    ff = total_frames % fps
    total_sec = total_frames // fps
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _parse_scene_window(
    scene: ScenePromptSpec,
    idx: int,
    total_scenes: int,
    total_runtime: float,
) -> Tuple[float, float]:
    ts = getattr(scene, "timestamp_range", "") or ""
    match = re.search(r"(\d+):(\d+)\s*[-–—]\s*(\d+):(\d+)", ts)
    if match:
        m1, s1, m2, s2 = map(int, match.groups())
        start_s = float(m1 * 60 + s1)
        end_s = float(m2 * 60 + s2)
        if end_s > start_s:
            return start_s, end_s
    per_scene = max(1.0, float(total_runtime) / max(1, total_scenes))
    return (idx - 1) * per_scene, idx * per_scene


def check_platform_ui_clearance(
    crop_or_coi_x: Union[AspectCropWindowSpec, float] = 0.5,
    coi_y: float = 0.48,
    platform: Union[SocialDeliveryPlatform, str] = SocialDeliveryPlatform.TIKTOK_9X16,
) -> Dict[str, Any]:
    """Evaluates whether the subject Center of Interest (COI) clears platform UI overlays.

    Accepts either an ``AspectCropWindowSpec`` or normalized ``(coi_x, coi_y, platform)`` coordinates.
    Returns a structured clearance report dict with ``cleared`` / ``ui_clearance_ok`` booleans.
    """
    if isinstance(crop_or_coi_x, AspectCropWindowSpec):
        crop = crop_or_coi_x
        plat_enum = crop.platform
        rel_x = ((crop.center_of_interest_x * crop.source_width_px) - crop.crop_x_px) / max(1.0, float(crop.crop_width_px))
        rel_y = ((crop.center_of_interest_y * crop.source_height_px) - crop.crop_y_px) / max(1.0, float(crop.crop_height_px))
    else:
        rel_x = float(crop_or_coi_x)
        rel_y = float(coi_y)
        plat_enum = _coerce_platform(platform, DeliverableAspectRatio.RATIO_9_16)

    rel_x = max(0.0, min(1.0, rel_x))
    rel_y = max(0.0, min(1.0, rel_y))

    zone = PLATFORM_SAFE_ZONES.get(
        plat_enum.value,
        PLATFORM_SAFE_ZONES[SocialDeliveryPlatform.TIKTOK_9X16.value],
    )
    min_x = zone["left_pct"] / 100.0
    max_x = 1.0 - (zone["right_pct"] / 100.0)
    min_y = zone["top_pct"] / 100.0
    max_y = 1.0 - (zone["bottom_pct"] / 100.0)

    violations: List[str] = []
    if rel_x < min_x:
        violations.append(f"COI X={rel_x:.2f} intrudes into left margin ({zone['left_pct']:.0f}%).")
    if rel_x > max_x:
        violations.append(f"COI X={rel_x:.2f} intrudes into right UI engagement rail ({zone['right_pct']:.0f}%).")
    if rel_y < min_y:
        violations.append(f"COI Y={rel_y:.2f} intrudes into top UI header ({zone['top_pct']:.0f}%).")
    if rel_y > max_y:
        violations.append(f"COI Y={rel_y:.2f} intrudes into bottom caption/CTA overlay ({zone['bottom_pct']:.0f}%).")

    cleared = len(violations) == 0
    notes = (
        f"Subject COI ({rel_x:.2f}, {rel_y:.2f}) clears {plat_enum.value} UI safe-zone."
        if cleared
        else " | ".join(violations)
    )

    return {
        "cleared": cleared,
        "ui_clearance_ok": cleared,
        "platform": plat_enum.value,
        "relative_coi_x": round(rel_x, 4),
        "relative_coi_y": round(rel_y, 4),
        "safe_bounds": {
            "min_x": round(min_x, 3),
            "max_x": round(max_x, 3),
            "min_y": round(min_y, 3),
            "max_y": round(max_y, 3),
        },
        "violations": violations,
        "notes": notes,
    }


def calculate_aspect_crop_window(
    source_width: int = 3840,
    source_height: int = 2160,
    target_aspect_ratio: Union[DeliverableAspectRatio, str] = DeliverableAspectRatio.RATIO_9_16,
    center_of_interest_x: float = 0.5,
    center_of_interest_y: float = 0.48,
    platform: Union[SocialDeliveryPlatform, str, None] = None,
    pan_mode: Union[ReframePanMode, str] = ReframePanMode.EASE_IN_OUT_COI,
) -> AspectCropWindowSpec:
    """Calculates an exact pan-and-scan crop rectangle and safe-zone clearance for a target ratio."""
    ratio_enum = _coerce_aspect_ratio(target_aspect_ratio)
    plat_enum = _coerce_platform(platform, ratio_enum)
    pan_enum = _coerce_pan_mode(pan_mode)

    coi_x = max(0.0, min(1.0, float(center_of_interest_x)))
    coi_y = max(0.0, min(1.0, float(center_of_interest_y)))
    target_r = _ASPECT_NUMERIC[ratio_enum.value]
    source_r = float(source_width) / max(1.0, float(source_height))

    if target_r < source_r:
        # Target is narrower (e.g., 16:9 -> 9:16, 4:5, 1:1): full height, crop width
        crop_h = int(source_height)
        crop_w = int(round(crop_h * target_r))
        # Align to even pixel boundary for H.264/ProRes chroma subsampling
        crop_w = max(2, min(source_width, crop_w - (crop_w % 2)))
    else:
        # Target is wider or equal (e.g., 16:9 -> 2.39:1): full width, crop height
        crop_w = int(source_width)
        crop_h = int(round(crop_w / target_r))
        crop_h = max(2, min(source_height, crop_h - (crop_h % 2)))

    target_cx = coi_x * source_width
    target_cy = coi_y * source_height

    raw_x = int(round(target_cx - (crop_w / 2.0)))
    raw_y = int(round(target_cy - (crop_h / 2.0)))

    crop_x = max(0, min(source_width - crop_w, raw_x))
    crop_y = max(0, min(source_height - crop_h, raw_y))

    zone = PLATFORM_SAFE_ZONES.get(plat_enum.value, PLATFORM_SAFE_ZONES[SocialDeliveryPlatform.BROADCAST_TV.value])
    out_w, out_h = _DEFAULT_OUTPUT_DIMS.get(ratio_enum.value, (zone["output_width_px"], zone["output_height_px"]))

    temp_spec = AspectCropWindowSpec(
        target_aspect_ratio=ratio_enum,
        platform=plat_enum,
        source_width_px=source_width,
        source_height_px=source_height,
        crop_x_px=crop_x,
        crop_y_px=crop_y,
        crop_width_px=crop_w,
        crop_height_px=crop_h,
        output_width_px=out_w,
        output_height_px=out_h,
        center_of_interest_x=round(coi_x, 4),
        center_of_interest_y=round(coi_y, 4),
        pan_mode=pan_enum,
        safe_zone_top_pct=zone["top_pct"],
        safe_zone_bottom_pct=zone["bottom_pct"],
        safe_zone_right_pct=zone["right_pct"],
        safe_zone_left_pct=zone["left_pct"],
    )

    clearance = check_platform_ui_clearance(temp_spec)
    temp_spec.ui_clearance_ok = bool(clearance["ui_clearance_ok"])
    temp_spec.clearance_notes = str(clearance["notes"])
    return temp_spec


def _build_cutdown_for_duration(
    bible: MasterProductionBible,
    cutdown_type: CutdownFormatType,
    target_sec: float,
    label: str,
    target_aspect: DeliverableAspectRatio,
    target_platform: SocialDeliveryPlatform,
    fps: int = 24,
) -> CutdownVersionSpec:
    scenes = list(bible.scenes or [])
    total_runtime = float(getattr(bible, "total_runtime_seconds", 30) or 30)
    total_scenes = max(1, len(scenes))

    if not scenes:
        seg = CutdownSegmentSpec(
            scene_index=1,
            scene_title="Master Hero",
            source_in_sec=0.0,
            source_out_sec=target_sec,
            record_in_sec=0.0,
            record_out_sec=target_sec,
            duration_sec=target_sec,
            src_in_smpte=_seconds_to_smpte(0.0, fps),
            src_out_smpte=_seconds_to_smpte(target_sec, fps),
            rec_in_smpte=_seconds_to_smpte(0.0, fps),
            rec_out_smpte=_seconds_to_smpte(target_sec, fps),
            narrative_role="hero_action",
        )
        return CutdownVersionSpec(
            cutdown_type=cutdown_type,
            label=label,
            target_duration_sec=target_sec,
            actual_duration_sec=target_sec,
            target_aspect_ratio=target_aspect,
            target_platform=target_platform,
            segments=[seg],
            cta_endcard_sec=min(2.0, target_sec * 0.25),
        )

    # Select scenes: for 6s bumper pick opening hook + climax payoff (max 2-3 scenes)
    if cutdown_type == CutdownFormatType.BUMPER_06S and len(scenes) >= 2:
        chosen = [(1, scenes[0], "hook"), (len(scenes), scenes[-1], "cta_endcard")]
    else:
        chosen = []
        for idx, sc in enumerate(scenes, start=1):
            if idx == 1:
                role = "hook"
            elif idx == len(scenes):
                role = "cta_endcard"
            else:
                role = "hero_action"
            chosen.append((idx, sc, role))

    per_seg_dur = round(target_sec / len(chosen), 3)
    segments: List[CutdownSegmentSpec] = []
    rec_cursor = 0.0

    for i, (orig_idx, sc, role) in enumerate(chosen):
        win_start, win_end = _parse_scene_window(sc, orig_idx, total_scenes, total_runtime)
        avail = max(1.0, win_end - win_start)
        seg_dur = target_sec - rec_cursor if i == len(chosen) - 1 else per_seg_dur
        seg_dur = max(0.5, round(seg_dur, 3))
        take_dur = min(avail, seg_dur)
        src_in = win_start
        src_out = round(src_in + take_dur, 3)
        rec_in = round(rec_cursor, 3)
        rec_out = round(rec_cursor + seg_dur, 3)

        segments.append(
            CutdownSegmentSpec(
                scene_index=sc.scene_index,
                scene_title=sc.scene_title,
                source_in_sec=round(src_in, 3),
                source_out_sec=round(src_out, 3),
                record_in_sec=rec_in,
                record_out_sec=rec_out,
                duration_sec=seg_dur,
                src_in_smpte=_seconds_to_smpte(src_in, fps),
                src_out_smpte=_seconds_to_smpte(src_out, fps),
                rec_in_smpte=_seconds_to_smpte(rec_in, fps),
                rec_out_smpte=_seconds_to_smpte(rec_out, fps),
                narrative_role=role,
            )
        )
        rec_cursor = rec_out

    return CutdownVersionSpec(
        cutdown_type=cutdown_type,
        label=label,
        target_duration_sec=target_sec,
        actual_duration_sec=round(rec_cursor, 3),
        target_aspect_ratio=target_aspect,
        target_platform=target_platform,
        segments=segments,
        cta_endcard_sec=min(2.0, round(target_sec * 0.25, 2)),
        pacing_notes=f"{label} assembled from {len(segments)} key beats; brand CTA anchored in final frame.",
    )


def synthesize_cutdown_versions(
    bible: MasterProductionBible,
    fps: int = 24,
) -> List[CutdownVersionSpec]:
    """Synthesizes standardized commercial cutdown assemblies (:30s if runtime >= 30s, :15s, :06s)."""
    runtime = float(getattr(bible, "total_runtime_seconds", 30) or 30)
    cutdowns: List[CutdownVersionSpec] = []

    if runtime >= 30.0:
        cutdowns.append(
            _build_cutdown_for_duration(
                bible=bible,
                cutdown_type=CutdownFormatType.CUTDOWN_30S,
                target_sec=30.0,
                label=":30s Broadcast & CTV Cutdown",
                target_aspect=DeliverableAspectRatio.RATIO_16_9,
                target_platform=SocialDeliveryPlatform.BROADCAST_TV,
                fps=fps,
            )
        )

    cutdowns.append(
        _build_cutdown_for_duration(
            bible=bible,
            cutdown_type=CutdownFormatType.CUTDOWN_15S,
            target_sec=15.0,
            label=":15s Paid Social Cutdown",
            target_aspect=DeliverableAspectRatio.RATIO_9_16,
            target_platform=SocialDeliveryPlatform.TIKTOK_9X16,
            fps=fps,
        )
    )

    cutdowns.append(
        _build_cutdown_for_duration(
            bible=bible,
            cutdown_type=CutdownFormatType.BUMPER_06S,
            target_sec=6.0,
            label=":06s Bumper Ad",
            target_aspect=DeliverableAspectRatio.RATIO_9_16,
            target_platform=SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
            fps=fps,
        )
    )

    return cutdowns


def _infer_scene_coi(scene: Optional[ScenePromptSpec], domain: str = "architectural_sanctuary") -> Tuple[float, float, ReframePanMode]:
    """Infers sensible Center-of-Interest coordinates and pan mode from scene composition."""
    coi_x = 0.5
    coi_y = 0.48
    pan_mode = ReframePanMode.EASE_IN_OUT_COI
    if scene is not None:
        prompt = (getattr(scene, "omni_prose_prompt", "") or "").lower()
        if "left" in prompt and "right" not in prompt:
            coi_x = 0.42
        elif "right" in prompt and "left" not in prompt:
            coi_x = 0.58
        if "static" in prompt or "locked" in prompt:
            pan_mode = ReframePanMode.STATIC_LOCK
        elif "dolly" in prompt or "tracking" in prompt or "orbit" in prompt:
            pan_mode = ReframePanMode.EASE_IN_OUT_COI
    if "kinetic" in str(domain).lower() or "automotive" in str(domain).lower():
        pan_mode = ReframePanMode.EASE_IN_OUT_COI
    return coi_x, coi_y, pan_mode


def synthesize_default_scene_reframe(
    scene: Optional[ScenePromptSpec] = None,
    scene_index: int = 1,
    scene_title: str = "",
    domain: str = "architectural_sanctuary",
    source_width: int = 3840,
    source_height: int = 2160,
) -> SceneReframeSpec:
    """Synthesizes a complete multi-aspect SceneReframeSpec for a single scene."""
    eff_idx = scene.scene_index if scene is not None else scene_index
    eff_title = (scene.scene_title if scene is not None else scene_title) or f"Scene {eff_idx}"
    coi_x, coi_y, pan_mode = _infer_scene_coi(scene, domain)

    targets: List[Tuple[DeliverableAspectRatio, SocialDeliveryPlatform]] = [
        (DeliverableAspectRatio.RATIO_16_9, SocialDeliveryPlatform.BROADCAST_TV),
        (DeliverableAspectRatio.RATIO_9_16, SocialDeliveryPlatform.TIKTOK_9X16),
        (DeliverableAspectRatio.RATIO_9_16, SocialDeliveryPlatform.REELS_9X16),
        (DeliverableAspectRatio.RATIO_4_5, SocialDeliveryPlatform.META_FEED_4X5),
        (DeliverableAspectRatio.RATIO_1_1, SocialDeliveryPlatform.META_FEED_4X5),
        (DeliverableAspectRatio.RATIO_2_39_1, SocialDeliveryPlatform.CINEMA_239),
    ]

    windows = [
        calculate_aspect_crop_window(
            source_width=source_width,
            source_height=source_height,
            target_aspect_ratio=ratio,
            center_of_interest_x=coi_x,
            center_of_interest_y=coi_y,
            platform=plat,
            pan_mode=pan_mode,
        )
        for ratio, plat in targets
    ]

    all_cleared = all(w.ui_clearance_ok for w in windows)
    spec = SceneReframeSpec(
        scene_index=eff_idx,
        scene_title=eff_title,
        source_aspect_ratio=DeliverableAspectRatio.RATIO_16_9,
        center_of_interest_x=coi_x,
        center_of_interest_y=coi_y,
        pan_mode=pan_mode,
        pan_start_coi_x=max(0.0, round(coi_x - 0.04, 3)),
        pan_end_coi_x=min(1.0, round(coi_x + 0.04, 3)),
        crop_windows=windows,
        all_platforms_cleared=all_cleared,
    )
    spec.prompt_token = format_reframe_prompt_token(spec)
    return spec


def format_reframe_prompt_token(spec: Union[SceneReframeSpec, DeliveryReframeManifestSpec, Dict[str, Any]]) -> str:
    """Formats a concise Gemini Omni prompt-auditable reframe & safe-zone token."""
    if isinstance(spec, dict):
        coi_x = float(spec.get("center_of_interest_x", 0.5))
        coi_y = float(spec.get("center_of_interest_y", 0.48))
        pan = str(spec.get("pan_mode", "ease_in_out_coi"))
        cleared = bool(spec.get("all_platforms_cleared", spec.get("safe_zone_audit_passed", True)))
        return f"[REFRAME: 16:9->9:16/4:5/1:1 | COI({coi_x:.2f},{coi_y:.2f}) | {pan} | {'UI_SAFE_CLEARED' if cleared else 'UI_SAFE_WARN'}]"
    if isinstance(spec, SceneReframeSpec):
        pan = spec.pan_mode.value if hasattr(spec.pan_mode, "value") else str(spec.pan_mode)
        status = "UI_SAFE_CLEARED" if spec.all_platforms_cleared else "UI_SAFE_WARN"
        return f"[REFRAME: 16:9->9:16/4:5/1:1 | COI({spec.center_of_interest_x:.2f},{spec.center_of_interest_y:.2f}) | {pan} | {status}]"
    status = "UI_SAFE_CLEARED" if spec.safe_zone_audit_passed else "UI_SAFE_WARN"
    return f"[REFRAME: 16:9->9:16/4:5/1:1 | {len(spec.cutdown_versions)} cutdowns | {spec.deliverable_matrix_count} crops | {status}]"


def synthesize_default_reframe_manifest(
    bible_or_domain: Union[MasterProductionBible, str, None] = None,
    scenes: Optional[List[ScenePromptSpec]] = None,
    project_title: str = "Commercial Production",
) -> DeliveryReframeManifestSpec:
    """Synthesizes a complete DeliveryReframeManifestSpec from a MasterProductionBible or domain archetype."""
    if isinstance(bible_or_domain, MasterProductionBible):
        bible = bible_or_domain
        domain = str(getattr(bible, "domain_archetype", None) or "architectural_sanctuary")
        eff_scenes = list(scenes if scenes is not None else bible.scenes)
        title = bible.project_title
        src_ratio = _coerce_aspect_ratio(bible.aspect_ratio.value if hasattr(bible.aspect_ratio, "value") else str(bible.aspect_ratio))
    else:
        domain = str(bible_or_domain or "architectural_sanctuary")
        eff_scenes = list(scenes or [])
        title = project_title
        src_ratio = DeliverableAspectRatio.RATIO_16_9

    scene_reframes = [
        synthesize_default_scene_reframe(scene=sc, scene_index=sc.scene_index, scene_title=sc.scene_title, domain=domain)
        for sc in eff_scenes
    ]
    if not scene_reframes:
        scene_reframes = [synthesize_default_scene_reframe(scene_index=1, scene_title=f"{title} Hero", domain=domain)]

    if isinstance(bible_or_domain, MasterProductionBible):
        cutdowns = synthesize_cutdown_versions(bible_or_domain)
    else:
        # Build lightweight cutdowns when called with domain string only
        cutdowns = [
            CutdownVersionSpec(
                cutdown_type=CutdownFormatType.CUTDOWN_15S,
                label=":15s Paid Social Cutdown",
                target_duration_sec=15.0,
                actual_duration_sec=15.0,
                target_aspect_ratio=DeliverableAspectRatio.RATIO_9_16,
                target_platform=SocialDeliveryPlatform.TIKTOK_9X16,
                segments=[
                    CutdownSegmentSpec(
                        scene_index=sr.scene_index,
                        scene_title=sr.scene_title,
                        source_in_sec=0.0,
                        source_out_sec=round(15.0 / len(scene_reframes), 2),
                        record_in_sec=round(i * (15.0 / len(scene_reframes)), 2),
                        record_out_sec=round((i + 1) * (15.0 / len(scene_reframes)), 2),
                        duration_sec=round(15.0 / len(scene_reframes), 2),
                        src_in_smpte=_seconds_to_smpte(0.0),
                        src_out_smpte=_seconds_to_smpte(15.0 / len(scene_reframes)),
                        rec_in_smpte=_seconds_to_smpte(i * (15.0 / len(scene_reframes))),
                        rec_out_smpte=_seconds_to_smpte((i + 1) * (15.0 / len(scene_reframes))),
                        narrative_role="hook" if i == 0 else "cta_endcard",
                    )
                    for i, sr in enumerate(scene_reframes)
                ],
            ),
            CutdownVersionSpec(
                cutdown_type=CutdownFormatType.BUMPER_06S,
                label=":06s Bumper Ad",
                target_duration_sec=6.0,
                actual_duration_sec=6.0,
                target_aspect_ratio=DeliverableAspectRatio.RATIO_9_16,
                target_platform=SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
                segments=[
                    CutdownSegmentSpec(
                        scene_index=scene_reframes[0].scene_index,
                        scene_title=scene_reframes[0].scene_title,
                        source_in_sec=0.0,
                        source_out_sec=6.0,
                        record_in_sec=0.0,
                        record_out_sec=6.0,
                        duration_sec=6.0,
                        src_in_smpte="00:00:00:00",
                        src_out_smpte="00:00:06:00",
                        rec_in_smpte="00:00:00:00",
                        rec_out_smpte="00:00:06:00",
                        narrative_role="hook",
                    )
                ],
            ),
        ]

    matrix_count = sum(len(sr.crop_windows) for sr in scene_reframes)
    safe_ok = all(sr.all_platforms_cleared for sr in scene_reframes)

    manifest = DeliveryReframeManifestSpec(
        project_title=title,
        source_aspect_ratio=src_ratio,
        source_resolution="3840x2160",
        fps=24,
        target_platforms=[
            SocialDeliveryPlatform.BROADCAST_TV,
            SocialDeliveryPlatform.TIKTOK_9X16,
            SocialDeliveryPlatform.REELS_9X16,
            SocialDeliveryPlatform.YOUTUBE_SHORTS_9X16,
            SocialDeliveryPlatform.META_FEED_4X5,
            SocialDeliveryPlatform.CINEMA_239,
        ],
        scene_reframes=scene_reframes,
        cutdown_versions=cutdowns,
        safe_zone_audit_passed=safe_ok,
        deliverable_matrix_count=matrix_count,
    )
    manifest.prompt_token = format_reframe_prompt_token(manifest)
    return manifest


def _resolve_manifest(source: Union[DeliveryReframeManifestSpec, MasterProductionBible]) -> DeliveryReframeManifestSpec:
    if isinstance(source, DeliveryReframeManifestSpec):
        return source
    existing = getattr(source, "master_reframe_manifest", None) or getattr(source, "reframe_manifest", None)
    if isinstance(existing, DeliveryReframeManifestSpec):
        return existing
    return synthesize_default_reframe_manifest(source)


def generate_cutdown_edl(
    source: Union[CutdownVersionSpec, DeliveryReframeManifestSpec, MasterProductionBible],
    cutdown_type: Union[CutdownFormatType, str] = CutdownFormatType.CUTDOWN_15S,
    fps: int = 24,
) -> str:
    """Generates a CMX 3600 EDL for a specified commercial cutdown (:30s, :15s, or :06s)."""
    if isinstance(source, CutdownVersionSpec):
        cutdown = source
        title = cutdown.label
    else:
        manifest = _resolve_manifest(source)
        title = manifest.project_title
        target_ct = cutdown_type.value if hasattr(cutdown_type, "value") else str(cutdown_type)
        matches = [c for c in manifest.cutdown_versions if (c.cutdown_type.value if hasattr(c.cutdown_type, "value") else str(c.cutdown_type)) == target_ct]
        cutdown = matches[0] if matches else (manifest.cutdown_versions[0] if manifest.cutdown_versions else CutdownVersionSpec())

    ratio_str = cutdown.target_aspect_ratio.value if hasattr(cutdown.target_aspect_ratio, "value") else str(cutdown.target_aspect_ratio)
    plat_str = cutdown.target_platform.value if hasattr(cutdown.target_platform, "value") else str(cutdown.target_platform)

    lines = [
        f"TITLE: {title.upper()[:45]} ({cutdown.label.upper()})",
        "FCM: NON-DROP FRAME",
        "",
    ]

    for idx, seg in enumerate(cutdown.segments, start=1):
        edit_num = f"{idx:03d}"
        src_in = seg.src_in_smpte or _seconds_to_smpte(seg.source_in_sec, fps)
        src_out = seg.src_out_smpte or _seconds_to_smpte(seg.source_out_sec, fps)
        rec_in = seg.rec_in_smpte or _seconds_to_smpte(seg.record_in_sec, fps)
        rec_out = seg.rec_out_smpte or _seconds_to_smpte(seg.record_out_sec, fps)
        lines.append(f"{edit_num}  AX       V     C        {src_in} {src_out} {rec_in} {rec_out}")
        lines.append(f"* FROM CLIP NAME: SCENE_{seg.scene_index:02d}_PLATE.MP4")
        lines.append(f"* COMMENT: CUTDOWN {cutdown.label} | ASPECT {ratio_str} | PLATFORM {plat_str} | ROLE {seg.narrative_role.upper()}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate_reframe_fcpxml(
    source: Union[DeliveryReframeManifestSpec, MasterProductionBible],
    target_aspect: Union[DeliverableAspectRatio, str] = DeliverableAspectRatio.RATIO_9_16,
    fps: int = 24,
) -> str:
    """Generates a valid FCPXML v1.10 timeline with vertical/social pan-and-scan crop transforms."""
    manifest = _resolve_manifest(source)
    ratio_enum = _coerce_aspect_ratio(target_aspect)
    out_w, out_h = _DEFAULT_OUTPUT_DIMS.get(ratio_enum.value, (1080, 1920))
    title_esc = xml_escape(f"{manifest.project_title} ({ratio_enum.value} Reframe)")

    resources_xml = [
        f'        <format id="r1" name="FFVideoFormat{out_w}x{out_h}p{fps}" '
        f'frameDuration="1/{fps}s" width="{out_w}" height="{out_h}" colorSpace="1-1-1 (Rec. 709)"/>'
    ]
    spine_xml: List[str] = []
    offset_frames = 0
    default_clip_frames = fps * 5

    for idx, sr in enumerate(manifest.scene_reframes):
        res_id = f"r{idx + 2}"
        resources_xml.append(
            f'        <asset id="{res_id}" name="SCENE_{sr.scene_index:02d}" '
            f'start="0s" duration="{default_clip_frames}/{fps}s" hasVideo="1" hasAudio="1" format="r1"/>'
        )
        matching_win = [w for w in sr.crop_windows if w.target_aspect_ratio == ratio_enum]
        win = matching_win[0] if matching_win else calculate_aspect_crop_window(target_aspect_ratio=ratio_enum, center_of_interest_x=sr.center_of_interest_x, center_of_interest_y=sr.center_of_interest_y)

        # Compute FCPXML horizontal pan offset percentage relative to frame center and exact aspect fill scale
        pan_offset_x = round((0.5 - win.center_of_interest_x) * 100.0, 2)
        pan_offset_y = round((0.5 - win.center_of_interest_y) * 50.0, 2)
        src_ar = win.source_width_px / max(1, win.source_height_px)
        tgt_ar = out_w / max(1, out_h)
        fill_scale = round(max(src_ar / tgt_ar, tgt_ar / src_ar), 4)
        clip_name = xml_escape(f"Scene_{sr.scene_index:02d}_{sr.scene_title[:35]}")
        note = xml_escape(f"COI({win.center_of_interest_x:.2f},{win.center_of_interest_y:.2f}) Crop {win.crop_width_px}x{win.crop_height_px}@{win.crop_x_px},{win.crop_y_px} | {win.pan_mode.value}")

        spine_xml.append(
            f'                        <asset-clip name="{clip_name}" ref="{res_id}" '
            f'offset="{offset_frames}/{fps}s" duration="{default_clip_frames}/{fps}s" start="0s" format="r1">\n'
            f'                            <adjust-transform position="{pan_offset_x} {pan_offset_y}" scale="{fill_scale:.4f} {fill_scale:.4f}"/>\n'
            f'                            <note>{note}</note>\n'
            f'                        </asset-clip>'
        )
        offset_frames += default_clip_frames

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<fcpxml version="1.10">\n'
        '    <resources>\n'
        + "\n".join(resources_xml) + "\n"
        '    </resources>\n'
        '    <library>\n'
        f'        <event name="{title_esc}">\n'
        f'            <project name="{title_esc}">\n'
        f'                <sequence format="r1" duration="{offset_frames}/{fps}s" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">\n'
        '                    <spine>\n'
        + "\n".join(spine_xml) + "\n"
        '                    </spine>\n'
        '                </sequence>\n'
        '            </project>\n'
        '        </event>\n'
        '    </library>\n'
        '</fcpxml>\n'
    )


def generate_reframe_matrix_csv(
    source: Union[DeliveryReframeManifestSpec, MasterProductionBible],
) -> str:
    """Exports the complete multi-aspect crop coordinate and platform safe-zone matrix as CSV."""
    manifest = _resolve_manifest(source)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "scene_index",
        "scene_title",
        "target_aspect_ratio",
        "platform",
        "source_resolution",
        "output_resolution",
        "crop_x_px",
        "crop_y_px",
        "crop_width_px",
        "crop_height_px",
        "coi_x",
        "coi_y",
        "pan_mode",
        "safe_zone_top_pct",
        "safe_zone_bottom_pct",
        "safe_zone_right_pct",
        "ui_clearance_ok",
        "clearance_notes",
    ])

    for sr in manifest.scene_reframes:
        for w in sr.crop_windows:
            ratio_s = w.target_aspect_ratio.value if hasattr(w.target_aspect_ratio, "value") else str(w.target_aspect_ratio)
            plat_s = w.platform.value if hasattr(w.platform, "value") else str(w.platform)
            pan_s = w.pan_mode.value if hasattr(w.pan_mode, "value") else str(w.pan_mode)
            writer.writerow([
                sr.scene_index,
                sr.scene_title,
                ratio_s,
                plat_s,
                f"{w.source_width_px}x{w.source_height_px}",
                f"{w.output_width_px}x{w.output_height_px}",
                w.crop_x_px,
                w.crop_y_px,
                w.crop_width_px,
                w.crop_height_px,
                f"{w.center_of_interest_x:.4f}",
                f"{w.center_of_interest_y:.4f}",
                pan_s,
                f"{w.safe_zone_top_pct:.1f}",
                f"{w.safe_zone_bottom_pct:.1f}",
                f"{w.safe_zone_right_pct:.1f}",
                "PASS" if w.ui_clearance_ok else "WARN",
                w.clearance_notes,
            ])

    return buf.getvalue()


def generate_reframe_manifest_json(
    source: Union[DeliveryReframeManifestSpec, MasterProductionBible],
) -> str:
    """Serializes the DeliveryReframeManifestSpec to indented JSON."""
    manifest = _resolve_manifest(source)
    return json.dumps(manifest.model_dump(), indent=2)


def export_reframe_bundle(
    bible_or_manifest: Union[MasterProductionBible, DeliveryReframeManifestSpec],
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports all PM-FEAT-021 reframe & cutdown deliverables into output_dir.

    Writes:
    - reframe_crop_matrix.csv
    - cutdown_15s.edl
    - cutdown_06s.edl
    - reframe_9x16.fcpxml
    - delivery_reframe_manifest.json
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    manifest = _resolve_manifest(bible_or_manifest)

    csv_p = out_path / "reframe_crop_matrix.csv"
    edl15_p = out_path / "cutdown_15s.edl"
    edl06_p = out_path / "cutdown_06s.edl"
    fcpxml_p = out_path / "reframe_9x16.fcpxml"
    json_p = out_path / "delivery_reframe_manifest.json"

    csv_p.write_text(generate_reframe_matrix_csv(manifest), encoding="utf-8")
    edl15_p.write_text(generate_cutdown_edl(manifest, CutdownFormatType.CUTDOWN_15S), encoding="utf-8")
    edl06_p.write_text(generate_cutdown_edl(manifest, CutdownFormatType.BUMPER_06S), encoding="utf-8")
    fcpxml_p.write_text(generate_reframe_fcpxml(manifest, DeliverableAspectRatio.RATIO_9_16), encoding="utf-8")
    json_p.write_text(generate_reframe_manifest_json(manifest), encoding="utf-8")

    result: Dict[str, str] = {
        "reframe_crop_matrix_csv": str(csv_p),
        "cutdown_15s_edl": str(edl15_p),
        "cutdown_06s_edl": str(edl06_p),
        "reframe_9x16_fcpxml": str(fcpxml_p),
        "delivery_reframe_manifest_json": str(json_p),
    }

    has_30s = any(
        (c.cutdown_type.value if hasattr(c.cutdown_type, "value") else str(c.cutdown_type)) == CutdownFormatType.CUTDOWN_30S.value
        for c in manifest.cutdown_versions
    )
    if has_30s:
        edl30_p = out_path / "cutdown_30s.edl"
        edl30_p.write_text(generate_cutdown_edl(manifest, CutdownFormatType.CUTDOWN_30S), encoding="utf-8")
        result["cutdown_30s_edl"] = str(edl30_p)

    return result
