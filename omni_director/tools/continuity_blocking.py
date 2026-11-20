"""180-Degree Continuity Axis, 30-Degree Rule, Eyeline Match & Overhead Blocking Floorplan Engine (PM-FEAT-023).

Pure-Python cinematography blocking & continuity engine providing:
- Inter-scene 180-degree line-of-action axis verification (detects A/B side flips & >135 deg reversals)
- 30-degree rule jump-cut detection (unchanged shot scale with <30 deg camera aim delta)
- Color temperature (Kelvin) continuity check (>1500K shift detection)
- Per-scene and master 2D overhead stage blocking synthesis (entities, eyelines, camera FOV cones)
- Dark-room SVG overhead blocking floorplan with 180-degree dashed line-of-action, camera wedges, and motion vectors
- CSV continuity log, SVG floorplan, and JSON manifest export bundle
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from xml.sax.saxutils import escape as xml_escape

from omni_director.schemas import (
    CameraAxisPlacement,
    EditorialCutType,
    InterSceneCutCheckSpec,
    MasterContinuityBlockingSpec,
    MasterProductionBible,
    SceneBlockingSpec,
    ScenePromptSpec,
    ScreenDirection,
    ShotScaleSize,
    StageBlockingEntity,
    StorytellingMode,
)


_DOMAIN_DEFAULT_KELVIN: Dict[str, int] = {
    "culinary_asmr": 3600,
    "luxury_fashion": 4800,
    "automotive_robotics": 5600,
    "kinetic_action": 5200,
    "tech_hardware": 6000,
    "architectural_sanctuary": 5400,
}

_SCALE_PROGRESSION: List[ShotScaleSize] = [
    ShotScaleSize.WS,
    ShotScaleSize.MS,
    ShotScaleSize.MCU,
    ShotScaleSize.CU,
]


def _circular_angle_delta(a_deg: float, b_deg: float) -> float:
    """Returns shortest angular separation in degrees in [0.0, 180.0]."""
    diff = (float(b_deg) - float(a_deg) + 180.0) % 360.0 - 180.0
    return abs(diff)


def _infer_shot_scale(scene: Optional[ScenePromptSpec], scene_index: int) -> ShotScaleSize:
    if scene is not None:
        comp = (getattr(scene.craft_camera, "composition", "") if getattr(scene, "craft_camera", None) else "") or ""
        corpus = f"{scene.scene_title} {comp} {scene.omni_prose_prompt}".lower()
        if re.search(r"\bextreme\s+close-?up\b|\becu\b|\bmacro\b", corpus):
            return ShotScaleSize.ECU
        if re.search(r"\bmedium\s+close-?up\b|\bmcu\b", corpus):
            return ShotScaleSize.MCU
        if re.search(r"\bclose-?up\b|\bcu\b", corpus):
            return ShotScaleSize.CU
        if re.search(r"\bmedium\s+long\b|\bmls\b|\bcowboy\b", corpus):
            return ShotScaleSize.MLS
        if re.search(r"\bmedium\s+shot\b|\bms\b", corpus):
            return ShotScaleSize.MS
        if re.search(r"\bextreme\s+wide\b|\bews\b|\baerial\b|\bestablishing\b", corpus):
            return ShotScaleSize.EWS
        if re.search(r"\bwide\b|\bws\b", corpus):
            return ShotScaleSize.WS
        focal = getattr(scene.craft_camera, "focal_length_mm", 35) if getattr(scene, "craft_camera", None) else 35
        if focal <= 24:
            return ShotScaleSize.WS
        if focal <= 40:
            return ShotScaleSize.MS
        if focal <= 65:
            return ShotScaleSize.MCU
        return ShotScaleSize.CU
    return _SCALE_PROGRESSION[(max(1, scene_index) - 1) % len(_SCALE_PROGRESSION)]


def _infer_screen_direction(scene: Optional[ScenePromptSpec], prev_blocking: Optional[SceneBlockingSpec]) -> ScreenDirection:
    if prev_blocking is not None:
        return prev_blocking.screen_direction
    if scene is not None:
        corpus = f"{scene.scene_title} {scene.omni_prose_prompt}".lower()
        if "right to left" in corpus or "right-to-left" in corpus:
            return ScreenDirection.RIGHT_TO_LEFT
        if "toward camera" in corpus or "approaching camera" in corpus:
            return ScreenDirection.TOWARD_CAMERA
        if "away from camera" in corpus or "receding" in corpus:
            return ScreenDirection.AWAY_FROM_CAMERA
        if "static" in corpus or "locked" in corpus or "symmetrical" in corpus:
            return ScreenDirection.STATIC_CENTERED
    return ScreenDirection.LEFT_TO_RIGHT


def _infer_scene_kelvin(scene: Optional[ScenePromptSpec], domain: str, prev_blocking: Optional[SceneBlockingSpec]) -> int:
    if scene is not None:
        lighting = getattr(scene, "lighting_rig", None)
        if lighting is not None and getattr(lighting, "fixtures", None):
            k_vals = [
                float(k)
                for f in lighting.fixtures
                for k in (getattr(f, "cct_kelvin", getattr(f, "color_temp_k", None)),)
                if k is not None
            ]
            if k_vals:
                return int(round(sum(k_vals) / len(k_vals)))
        m = re.search(r"\b(\d{4})K\b", getattr(scene, "omni_prose_prompt", "") or "")
        if m:
            val = int(m.group(1))
            if 2000 <= val <= 12000:
                return val
    if prev_blocking is not None:
        return prev_blocking.color_temp_kelvin
    return _DOMAIN_DEFAULT_KELVIN.get(domain, 5600)


def _calc_fov_deg(focal_length_mm: int, sensor_width_mm: float = 36.0) -> float:
    focal = max(8.0, float(focal_length_mm))
    return round(math.degrees(2.0 * math.atan(sensor_width_mm / (2.0 * focal))), 1)


def format_continuity_prompt_token(
    spec: Union[SceneBlockingSpec, MasterContinuityBlockingSpec, Dict[str, Any]],
) -> str:
    """Formats a concise Gemini Omni prompt-auditable 180-degree continuity token."""
    if isinstance(spec, dict):
        direction = str(spec.get("screen_direction", "left_to_right"))
        scale = str(spec.get("shot_scale", "MS"))
        axis_side = str(spec.get("axis_side", "A_SIDE"))
        axis_deg = float(spec.get("line_of_action_deg", 0.0))
        lock_ok = bool(spec.get("one_eighty_lock_ok", True))
        eyeline = float(spec.get("eyeline_angle_deg", 15.0))
    elif isinstance(spec, MasterContinuityBlockingSpec):
        direction = spec.dominant_screen_direction.value if hasattr(spec.dominant_screen_direction, "value") else str(spec.dominant_screen_direction)
        scale = spec.scene_blockings[0].shot_scale.value if spec.scene_blockings else "MS"
        axis_side = spec.master_axis_side
        axis_deg = spec.master_axis_deg
        lock_ok = spec.all_180_axis_locked
        eyeline = spec.scene_blockings[0].eyeline_angle_deg if spec.scene_blockings else 15.0
    else:
        direction = spec.screen_direction.value if hasattr(spec.screen_direction, "value") else str(spec.screen_direction)
        scale = spec.shot_scale.value if hasattr(spec.shot_scale, "value") else str(spec.shot_scale)
        axis_side = spec.axis_side
        axis_deg = spec.line_of_action_deg
        lock_ok = spec.one_eighty_lock_ok
        eyeline = spec.eyeline_angle_deg

    lock_str = "PASS" if lock_ok else "FAIL"
    return (
        f"[CONTINUITY_AXIS: dir={direction} scale={scale} "
        f"axis={axis_side}@{axis_deg:.0f}deg 180_deg_lock={lock_str} eyeline={eyeline:+.0f}deg]"
    )


def evaluate_180_axis_and_30_rule(
    prev_scene_blocking: SceneBlockingSpec,
    next_scene_blocking: SceneBlockingSpec,
    prev_kelvin: Optional[int] = None,
    next_kelvin: Optional[int] = None,
) -> InterSceneCutCheckSpec:
    """Audits inter-scene continuity across 180-degree axis lock, 30-degree rule, and Kelvin shift.

    Flags:
    - 180-degree axis side flips (A_SIDE <-> B_SIDE) or >135-degree camera aim reversals
    - 30-degree rule jump-cut violations when shot scale is unchanged and aim delta < 30 deg
    - Color temperature continuity violations when Kelvin shifts > 1500K
    """
    side_from = (prev_scene_blocking.axis_side or "A_SIDE").strip().upper()
    side_to = (next_scene_blocking.axis_side or "A_SIDE").strip().upper()

    aim_from = prev_scene_blocking.camera.aim_azimuth_deg
    aim_to = next_scene_blocking.camera.aim_azimuth_deg
    aim_delta = round(_circular_angle_delta(aim_from, aim_to), 2)

    violations: List[str] = []
    warnings: List[str] = []

    axis_side_flipped = side_from != side_to
    large_reversal = aim_delta > 135.0
    axis_preserved = (not axis_side_flipped) and (not large_reversal)

    if axis_side_flipped:
        violations.append(
            f"180-degree axis violation: camera crossed line of action ({side_from} -> {side_to}) "
            f"between Scene {prev_scene_blocking.scene_index} and Scene {next_scene_blocking.scene_index}."
        )
    if large_reversal:
        violations.append(
            f"180-degree axis reversal: camera aim shifted {aim_delta:.1f}deg (> 135.0deg ceiling) "
            f"between Scene {prev_scene_blocking.scene_index} and Scene {next_scene_blocking.scene_index}."
        )

    cut_type = next_scene_blocking.cut_type_in
    scale_from = prev_scene_blocking.shot_scale
    scale_to = next_scene_blocking.shot_scale

    if cut_type == EditorialCutType.CONTINUOUS_EXTENSION:
        thirty_degree_ok = True
    else:
        thirty_degree_ok = (scale_from != scale_to) or (aim_delta >= 30.0)
        if not thirty_degree_ok:
            violations.append(
                f"30-degree rule jump-cut violation: shot scale unchanged ({scale_to.value}) "
                f"with camera aim delta {aim_delta:.1f}deg (< 30.0deg minimum separation)."
            )

    prev_dir = prev_scene_blocking.screen_direction
    next_dir = next_scene_blocking.screen_direction
    dir_flip = (
        (prev_dir == ScreenDirection.LEFT_TO_RIGHT and next_dir == ScreenDirection.RIGHT_TO_LEFT)
        or (prev_dir == ScreenDirection.RIGHT_TO_LEFT and next_dir == ScreenDirection.LEFT_TO_RIGHT)
    )
    screen_dir_ok = (not axis_side_flipped) and (not dir_flip)
    if dir_flip:
        warnings.append(
            f"Screen direction reversed ({prev_dir.value} -> {next_dir.value}) across cut."
        )

    eyeline_match_ok = axis_preserved
    if not eyeline_match_ok:
        warnings.append("Eyeline match disrupted due to 180-degree axis crossing.")

    eff_prev_k = int(prev_kelvin if prev_kelvin is not None else getattr(prev_scene_blocking, "color_temp_kelvin", 5600))
    eff_next_k = int(next_kelvin if next_kelvin is not None else getattr(next_scene_blocking, "color_temp_kelvin", 5600))
    kelvin_delta = float(abs(eff_next_k - eff_prev_k))
    kelvin_ok = kelvin_delta <= 1500.0
    if not kelvin_ok:
        violations.append(
            f"Color temperature continuity violation: Kelvin delta {kelvin_delta:.0f}K "
            f"({eff_prev_k}K -> {eff_next_k}K) exceeds 1500K threshold."
        )

    passed = axis_preserved and thirty_degree_ok and kelvin_ok

    return InterSceneCutCheckSpec(
        from_scene_index=prev_scene_blocking.scene_index,
        to_scene_index=next_scene_blocking.scene_index,
        cut_type=cut_type,
        axis_preserved=axis_preserved,
        axis_side_from=side_from,
        axis_side_to=side_to,
        camera_angle_delta_deg=aim_delta,
        thirty_degree_rule_ok=thirty_degree_ok,
        shot_scale_from=scale_from,
        shot_scale_to=scale_to,
        screen_direction_consistent=screen_dir_ok,
        eyeline_match_ok=eyeline_match_ok,
        kelvin_delta_k=kelvin_delta,
        kelvin_continuity_ok=kelvin_ok,
        warnings=warnings,
        violations=violations,
        passed=passed,
    )


def synthesize_scene_blocking(
    scene: Optional[ScenePromptSpec] = None,
    scene_index: int = 1,
    domain: str = "architectural_sanctuary",
    prev_blocking: Optional[SceneBlockingSpec] = None,
) -> SceneBlockingSpec:
    """Synthesizes a calibrated SceneBlockingSpec anchored to the 180-degree stage axis."""
    eff_idx = scene.scene_index if scene is not None else max(1, int(scene_index))
    eff_title = (scene.scene_title if scene is not None else "") or f"Scene {eff_idx}"

    screen_dir = _infer_screen_direction(scene, prev_blocking)
    shot_scale = _infer_shot_scale(scene, eff_idx)
    kelvin = _infer_scene_kelvin(scene, domain, prev_blocking)

    # Keep camera anchored on A_SIDE with >= 35 deg separation or scale shift
    axis_side = prev_blocking.axis_side if prev_blocking is not None else "A_SIDE"
    line_deg = prev_blocking.line_of_action_deg if prev_blocking is not None else 0.0

    focal_mm = 35
    if scene is not None and getattr(scene, "craft_camera", None) is not None:
        focal_mm = int(getattr(scene.craft_camera, "focal_length_mm", 35) or 35)
    fov_deg = _calc_fov_deg(focal_mm)

    if prev_blocking is not None:
        base_aim = prev_blocking.camera.aim_azimuth_deg
        # Offset aim by 36 deg within the A_SIDE arc [55..125] so 30-deg rule always passes without crossing 180 axis
        aim_deg = 54.0 + ((eff_idx - 1) * 36.0) % 72.0
        if _circular_angle_delta(base_aim, aim_deg) < 32.0 and shot_scale == prev_blocking.shot_scale:
            if prev_blocking.shot_scale in _SCALE_PROGRESSION:
                shot_scale = _SCALE_PROGRESSION[
                    (_SCALE_PROGRESSION.index(prev_blocking.shot_scale) + 1) % len(_SCALE_PROGRESSION)
                ]
            else:
                shot_scale = _SCALE_PROGRESSION[0]
    else:
        aim_deg = 72.0

    # Place camera on A_SIDE (-Y half-plane looking toward +Y / 90 deg)
    rad = math.radians(aim_deg)
    cam_dist = 3.8 if shot_scale in (ShotScaleSize.EWS, ShotScaleSize.WS) else (2.8 if shot_scale in (ShotScaleSize.MLS, ShotScaleSize.MS) else 2.0)
    cam_x = round(-cam_dist * math.cos(rad), 2)
    cam_y = round(-abs(cam_dist * math.sin(rad)) - 0.5, 2)

    is_ext = bool(scene is not None and re.search(r"\+10s|extension", getattr(scene, "timestamp_range", "") or "", re.IGNORECASE))
    cut_in = (
        EditorialCutType.CONTINUOUS_EXTENSION
        if is_ext
        else (EditorialCutType.MATCH_ON_ACTION if eff_idx > 1 else EditorialCutType.HARD_CUT)
    )

    eyeline_deg = 15.0 if screen_dir == ScreenDirection.LEFT_TO_RIGHT else (-15.0 if screen_dir == ScreenDirection.RIGHT_TO_LEFT else 0.0)

    motion_dx = 1.8 if screen_dir == ScreenDirection.LEFT_TO_RIGHT else (-1.8 if screen_dir == ScreenDirection.RIGHT_TO_LEFT else 0.0)
    motion_dy = 1.2 if screen_dir == ScreenDirection.TOWARD_CAMERA else (-1.2 if screen_dir == ScreenDirection.AWAY_FROM_CAMERA else 0.0)

    entities = [
        StageBlockingEntity(
            entity_id=f"hero_s{eff_idx}",
            label="Hero Subject",
            role="talent",
            x_meters=-0.8 if screen_dir == ScreenDirection.LEFT_TO_RIGHT else 0.0,
            y_meters=0.2,
            facing_deg=0.0 if screen_dir == ScreenDirection.LEFT_TO_RIGHT else 180.0,
            eyeline_deg=eyeline_deg,
            motion_dx_meters=motion_dx,
            motion_dy_meters=motion_dy,
            screen_direction=screen_dir,
            color_hex="#38BDF8",
        ),
        StageBlockingEntity(
            entity_id=f"anchor_s{eff_idx}",
            label="Hero Product / Anchor",
            role="hero_product",
            x_meters=1.4,
            y_meters=0.6,
            facing_deg=180.0,
            eyeline_deg=-eyeline_deg,
            motion_dx_meters=0.0,
            motion_dy_meters=0.0,
            screen_direction=ScreenDirection.STATIC_CENTERED,
            color_hex="#F59E0B",
        ),
    ]

    cam = CameraAxisPlacement(
        camera_id=f"CAM_S{eff_idx}",
        x_meters=cam_x,
        y_meters=cam_y,
        aim_azimuth_deg=round(aim_deg, 1),
        fov_deg=fov_deg,
        focal_length_mm=focal_mm,
        axis_side=axis_side,
        axis_angle_deg=line_deg,
        height_meters=1.55,
    )

    spec = SceneBlockingSpec(
        scene_index=eff_idx,
        scene_title=eff_title,
        screen_direction=screen_dir,
        shot_scale=shot_scale,
        cut_type_in=cut_in,
        line_of_action_deg=line_deg,
        axis_side=axis_side,
        eyeline_angle_deg=eyeline_deg,
        one_eighty_lock_ok=True,
        color_temp_kelvin=kelvin,
        stage_width_meters=12.0,
        stage_depth_meters=10.0,
        camera=cam,
        entities=entities,
        blocking_notes=f"Camera on {axis_side} at {aim_deg:.0f}deg ({shot_scale.value}, {focal_mm}mm) preserving {screen_dir.value} travel.",
    )
    spec.prompt_token = format_continuity_prompt_token(spec)
    return spec


def synthesize_default_continuity_blocking(
    bible: Union[MasterProductionBible, str, None],
) -> MasterContinuityBlockingSpec:
    """Synthesizes a complete MasterContinuityBlockingSpec with inter-scene cut audits."""
    if isinstance(bible, MasterProductionBible):
        title = bible.project_title
        domain = getattr(bible, "domain_archetype", None) or "architectural_sanctuary"
        scenes = list(bible.scenes or [])
        is_mode_b = bible.storytelling_mode == StorytellingMode.MODE_B_CONTINUOUS_CHAIN
    else:
        title = str(bible or "Commercial Production")
        domain = "architectural_sanctuary"
        scenes = []
        is_mode_b = False

    blockings: List[SceneBlockingSpec] = []
    prev: Optional[SceneBlockingSpec] = None
    for idx, sc in enumerate(scenes, start=1):
        blk = synthesize_scene_blocking(sc, scene_index=sc.scene_index, domain=domain, prev_blocking=prev)
        if is_mode_b and idx > 1:
            blk.cut_type_in = EditorialCutType.CONTINUOUS_EXTENSION
        blockings.append(blk)
        prev = blk

    if not blockings:
        blockings = [synthesize_scene_blocking(None, scene_index=1, domain=domain)]

    cut_checks: List[InterSceneCutCheckSpec] = []
    for i in range(len(blockings) - 1):
        chk = evaluate_180_axis_and_30_rule(
            blockings[i],
            blockings[i + 1],
            prev_kelvin=blockings[i].color_temp_kelvin,
            next_kelvin=blockings[i + 1].color_temp_kelvin,
        )
        if not chk.axis_preserved:
            blockings[i + 1].one_eighty_lock_ok = False
            blockings[i + 1].prompt_token = format_continuity_prompt_token(blockings[i + 1])
        cut_checks.append(chk)

    axis_violations_count = sum(len(c.violations) for c in cut_checks)
    warnings_count = sum(len(c.warnings) for c in cut_checks)
    all_180 = all(b.one_eighty_lock_ok for b in blockings) and all(c.axis_preserved for c in cut_checks)
    all_30 = all(c.thirty_degree_rule_ok for c in cut_checks)
    all_kelvin = all(c.kelvin_continuity_ok for c in cut_checks)
    passed = all_180 and all_30 and all_kelvin and axis_violations_count == 0
    overall_continuity_score = round(
        max(0.0, 100.0 - (15.0 * axis_violations_count) - (2.0 * warnings_count)),
        2,
    )

    manifest = MasterContinuityBlockingSpec(
        project_title=title,
        dominant_screen_direction=blockings[0].screen_direction,
        master_axis_deg=blockings[0].line_of_action_deg,
        master_axis_side=blockings[0].axis_side,
        scene_blockings=blockings,
        cut_checks=cut_checks,
        all_180_axis_locked=all_180,
        all_30_rule_passed=all_30,
        all_kelvin_continuous=all_kelvin,
        continuity_passed=passed,
        overall_continuity_score=overall_continuity_score,
        axis_violations_count=axis_violations_count,
    )
    manifest.prompt_token = format_continuity_prompt_token(manifest)
    return manifest


def _resolve_continuity_manifest(
    spec_or_bible: Union[MasterContinuityBlockingSpec, SceneBlockingSpec, MasterProductionBible],
) -> MasterContinuityBlockingSpec:
    if isinstance(spec_or_bible, MasterContinuityBlockingSpec):
        return spec_or_bible
    if isinstance(spec_or_bible, SceneBlockingSpec):
        m = MasterContinuityBlockingSpec(
            project_title=spec_or_bible.scene_title or f"Scene {spec_or_bible.scene_index}",
            dominant_screen_direction=spec_or_bible.screen_direction,
            master_axis_deg=spec_or_bible.line_of_action_deg,
            master_axis_side=spec_or_bible.axis_side,
            scene_blockings=[spec_or_bible],
            cut_checks=[],
            all_180_axis_locked=spec_or_bible.one_eighty_lock_ok,
            all_30_rule_passed=True,
            all_kelvin_continuous=True,
            continuity_passed=spec_or_bible.one_eighty_lock_ok,
        )
        m.prompt_token = format_continuity_prompt_token(m)
        return m
    existing = getattr(spec_or_bible, "master_continuity_blocking", None) or getattr(spec_or_bible, "continuity_blocking", None)
    if isinstance(existing, MasterContinuityBlockingSpec):
        return existing
    return synthesize_default_continuity_blocking(spec_or_bible)


def generate_continuity_log_csv(
    spec_or_bible: Union[MasterContinuityBlockingSpec, SceneBlockingSpec, MasterProductionBible],
) -> str:
    """Exports per-scene 180-degree axis, 30-degree rule, and Kelvin continuity log as CSV."""
    manifest = _resolve_continuity_manifest(spec_or_bible)
    check_by_to: Dict[int, InterSceneCutCheckSpec] = {c.to_scene_index: c for c in manifest.cut_checks}

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "scene_index",
        "scene_title",
        "screen_direction",
        "shot_scale",
        "cut_type_in",
        "axis_side",
        "line_of_action_deg",
        "camera_x_m",
        "camera_y_m",
        "camera_aim_deg",
        "fov_deg",
        "focal_length_mm",
        "eyeline_deg",
        "color_temp_kelvin",
        "180_deg_lock",
        "30_deg_rule_ok",
        "kelvin_continuity_ok",
    ])

    for b in manifest.scene_blockings:
        chk = check_by_to.get(b.scene_index)
        thirty_ok = chk.thirty_degree_rule_ok if chk is not None else True
        kelvin_ok = chk.kelvin_continuity_ok if chk is not None else True
        dir_val = b.screen_direction.value if hasattr(b.screen_direction, "value") else str(b.screen_direction)
        scale_val = b.shot_scale.value if hasattr(b.shot_scale, "value") else str(b.shot_scale)
        cut_val = b.cut_type_in.value if hasattr(b.cut_type_in, "value") else str(b.cut_type_in)
        writer.writerow([
            b.scene_index,
            b.scene_title,
            dir_val,
            scale_val,
            cut_val,
            b.axis_side,
            f"{b.line_of_action_deg:.1f}",
            f"{b.camera.x_meters:.2f}",
            f"{b.camera.y_meters:.2f}",
            f"{b.camera.aim_azimuth_deg:.1f}",
            f"{b.camera.fov_deg:.1f}",
            b.camera.focal_length_mm,
            f"{b.eyeline_angle_deg:+.1f}",
            b.color_temp_kelvin,
            "PASS" if b.one_eighty_lock_ok else "FAIL",
            "PASS" if thirty_ok else "FAIL",
            "PASS" if kelvin_ok else "FAIL",
        ])

    return buf.getvalue()


def generate_blocking_floorplan_svg(
    spec_or_bible: Union[MasterContinuityBlockingSpec, SceneBlockingSpec, MasterProductionBible],
) -> str:
    """Generates an overhead 2D stage floorplan SVG with 180-deg axis line, camera FOV wedges, and actor vectors."""
    manifest = _resolve_continuity_manifest(spec_or_bible)
    w, h = 840, 520
    cx, cy = 420.0, 260.0
    scale_px = 45.0  # pixels per meter

    def to_px(xm: float, ym: float) -> Tuple[float, float]:
        # +X right, +Y upstage (rendered toward top of floorplan)
        return round(cx + xm * scale_px, 1), round(cy - ym * scale_px, 1)

    svg_parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Overhead 180-Degree Continuity Blocking Floorplan">',
        '  <defs>',
        '    <marker id="arrow-motion" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38BDF8"/>',
        '    </marker>',
        '  </defs>',
        f'  <rect width="{w}" height="{h}" fill="#0B0F17" rx="10"/>',
        '  <rect x="24" y="54" width="792" height="420" fill="#111827" stroke="#1F2937" stroke-width="1.5" rx="6"/>',
    ]

    # Meter grid lines
    for gx in range(-7, 8):
        px_x, _ = to_px(float(gx), 0.0)
        if 30 <= px_x <= w - 30:
            svg_parts.append(f'  <line x1="{px_x}" y1="54" x2="{px_x}" y2="474" stroke="#1E293B" stroke-width="0.7"/>')
    for gy in range(-4, 5):
        _, px_y = to_px(0.0, float(gy))
        if 60 <= px_y <= 470:
            svg_parts.append(f'  <line x1="24" y1="{px_y}" x2="816" y2="{px_y}" stroke="#1E293B" stroke-width="0.7"/>')

    # Header & status badge
    status_color = "#10B981" if manifest.continuity_passed else "#EF4444"
    status_label = "180° AXIS LOCKED" if manifest.continuity_passed else "CONTINUITY VIOLATION"
    title_esc = xml_escape(manifest.project_title[:54])
    svg_parts.append(
        f'  <text x="28" y="34" fill="#F8FAFC" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="14" font-weight="700">'
        f'OVERHEAD BLOCKING FLOORPLAN — {title_esc}</text>'
    )
    svg_parts.append(
        f'  <rect x="630" y="16" width="186" height="24" rx="4" fill="{status_color}" fill-opacity="0.18" stroke="{status_color}" stroke-width="1"/>'
    )
    svg_parts.append(
        f'  <text x="723" y="32" text-anchor="middle" fill="{status_color}" font-family="ui-monospace, monospace" font-size="11" font-weight="700">{status_label}</text>'
    )

    # 180-degree dashed line of action
    axis_rad = math.radians(manifest.master_axis_deg)
    ax_dx = math.cos(axis_rad) * 7.8
    ax_dy = math.sin(axis_rad) * 7.8
    ax1_x, ax1_y = to_px(-ax_dx, -ax_dy)
    ax2_x, ax2_y = to_px(ax_dx, ax_dy)
    svg_parts.append(
        f'  <line x1="{ax1_x}" y1="{ax1_y}" x2="{ax2_x}" y2="{ax2_y}" '
        f'stroke="#F59E0B" stroke-width="2" stroke-dasharray="8 6" opacity="0.9"/>'
    )
    svg_parts.append(
        f'  <text x="44" y="{ax1_y - 8:.1f}" fill="#F59E0B" font-family="ui-monospace, monospace" font-size="10" font-weight="600">'
        f'180° LINE OF ACTION ({manifest.master_axis_side})</text>'
    )

    # Camera FOV wedges and markers
    cam_palette = ["#38BDF8", "#A78BFA", "#34D399", "#FB7185", "#FBBF24"]
    cone_len_m = 4.2
    for idx, blk in enumerate(manifest.scene_blockings):
        cam = blk.camera
        color = cam_palette[idx % len(cam_palette)] if blk.one_eighty_lock_ok else "#EF4444"
        cam_px_x, cam_px_y = to_px(cam.x_meters, cam.y_meters)

        half_fov = cam.fov_deg / 2.0
        a1 = math.radians(cam.aim_azimuth_deg - half_fov)
        a2 = math.radians(cam.aim_azimuth_deg + half_fov)
        w1_x, w1_y = to_px(cam.x_meters + cone_len_m * math.cos(a1), cam.y_meters + cone_len_m * math.sin(a1))
        w2_x, w2_y = to_px(cam.x_meters + cone_len_m * math.cos(a2), cam.y_meters + cone_len_m * math.sin(a2))

        svg_parts.append(
            f'  <polygon points="{cam_px_x},{cam_px_y} {w1_x},{w1_y} {w2_x},{w2_y}" '
            f'fill="{color}" fill-opacity="0.14" stroke="{color}" stroke-width="1" stroke-opacity="0.55"/>'
        )
        svg_parts.append(
            f'  <circle cx="{cam_px_x}" cy="{cam_px_y}" r="7" fill="{color}" stroke="#0B0F17" stroke-width="1.5"/>'
        )
        scale_s = blk.shot_scale.value if hasattr(blk.shot_scale, "value") else str(blk.shot_scale)
        svg_parts.append(
            f'  <text x="{cam_px_x + 10:.1f}" y="{cam_px_y + 4:.1f}" fill="{color}" font-family="ui-monospace, monospace" font-size="10" font-weight="700">'
            f'S{blk.scene_index} {scale_s} ({cam.focal_length_mm}mm)</text>'
        )

    # Entities / actors + motion vectors (deduplicate by position/first scene + motion arrows)
    seen_entities: Dict[str, StageBlockingEntity] = {}
    for blk in manifest.scene_blockings:
        for ent in blk.entities:
            if ent.entity_id not in seen_entities:
                seen_entities[ent.entity_id] = ent

    for ent in seen_entities.values():
        ex, ey = to_px(ent.x_meters, ent.y_meters)
        svg_parts.append(
            f'  <circle cx="{ex}" cy="{ey}" r="9" fill="{xml_escape(ent.color_hex)}" fill-opacity="0.85" stroke="#F8FAFC" stroke-width="1.5"/>'
        )
        if abs(ent.motion_dx_meters) > 0.05 or abs(ent.motion_dy_meters) > 0.05:
            mx, my = to_px(ent.x_meters + ent.motion_dx_meters, ent.y_meters + ent.motion_dy_meters)
            svg_parts.append(
                f'  <line x1="{ex}" y1="{ey}" x2="{mx}" y2="{my}" stroke="#38BDF8" stroke-width="2" marker-end="url(#arrow-motion)"/>'
            )
        svg_parts.append(
            f'  <text x="{ex}" y="{ey - 13:.1f}" text-anchor="middle" fill="#E2E8F0" font-family="ui-sans-serif, system-ui, sans-serif" font-size="10" font-weight="600">'
            f'{xml_escape(ent.label)}</text>'
        )

    # Footer legend
    svg_parts.append(
        '  <text x="28" y="498" fill="#94A3B8" font-family="ui-monospace, monospace" font-size="10">'
        'Legend: Dashed Amber = 180° Axis | Shaded Wedges = Camera FOV Cones | Blue Arrow = Screen Direction Motion Vector</text>'
    )
    svg_parts.append('</svg>')
    return "\n".join(svg_parts) + "\n"


def generate_continuity_manifest_json(
    spec_or_bible: Union[MasterContinuityBlockingSpec, SceneBlockingSpec, MasterProductionBible],
) -> str:
    """Serializes the MasterContinuityBlockingSpec to indented JSON."""
    manifest = _resolve_continuity_manifest(spec_or_bible)
    return json.dumps(manifest.model_dump(), indent=2)


def export_continuity_bundle(
    bible_or_spec: Union[MasterProductionBible, MasterContinuityBlockingSpec, SceneBlockingSpec],
    output_dir: Union[str, Path],
) -> Dict[str, Path]:
    """Exports all PM-FEAT-023 continuity blocking artifacts into output_dir.

    Writes:
    - continuity_log.csv
    - blocking_floorplan.svg
    - continuity_manifest.json
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    manifest = _resolve_continuity_manifest(bible_or_spec)

    csv_p = out_path / "continuity_log.csv"
    svg_p = out_path / "blocking_floorplan.svg"
    json_p = out_path / "continuity_manifest.json"

    csv_p.write_text(generate_continuity_log_csv(manifest), encoding="utf-8")
    svg_p.write_text(generate_blocking_floorplan_svg(manifest), encoding="utf-8")
    json_p.write_text(generate_continuity_manifest_json(manifest), encoding="utf-8")

    return {
        "continuity_log_csv": csv_p,
        "blocking_floorplan_svg": svg_p,
        "continuity_manifest_json": json_p,
    }
