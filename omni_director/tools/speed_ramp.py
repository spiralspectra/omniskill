"""Dynamic speed ramping, SMPTE time-warp curve synthesis, and shutter physics."""

from __future__ import annotations

import re
from typing import List, Tuple, Union

from omni_director.schemas import (
    ScenePromptSpec,
    SpeedRampCurveSpec,
    SpeedRampMode,
)


def format_craft_shutter_tokens(shutter_angle_deg: float = 180.0, base_fps: int = 24) -> str:
    """Format physical shutter angle and equivalent exposure time token for CRAFT prompts."""
    safe_angle = max(11.25, min(360.0, float(shutter_angle_deg)))
    denom = int(round((360.0 * max(1, base_fps)) / safe_angle))
    angle_str = f"{safe_angle:.0f}" if safe_angle.is_integer() else f"{safe_angle:.1f}"
    return f"{angle_str}° optical shutter at 1/{denom}s exposure"


def synthesize_speed_ramp_curve(
    mode: Union[SpeedRampMode, str] = SpeedRampMode.CONSTANT_REALTIME,
    base_fps: int = 24,
    peak_capture_fps: int = 120,
    shutter_angle_deg: float = 180.0,
) -> SpeedRampCurveSpec:
    """Generates calibrated SMPTE time-warp keyframe curves for kinetic camera pacing."""
    if isinstance(mode, SpeedRampMode):
        norm_mode = mode
    else:
        key = str(mode).strip().lower().replace("-", "_")
        try:
            norm_mode = SpeedRampMode(key)
        except ValueError:
            norm_mode = SpeedRampMode.CONSTANT_REALTIME

    safe_base_fps = max(12, min(120, int(base_fps)))
    safe_peak_fps = max(safe_base_fps, min(1000, int(peak_capture_fps)))
    safe_angle = max(11.25, min(360.0, float(shutter_angle_deg)))

    if norm_mode == SpeedRampMode.DECELERATION_IMPACT:
        slow_factor = round(max(0.02, float(safe_base_fps) / float(safe_peak_fps)), 3)
        points: List[Tuple[float, float]] = [
            (0.0, 1.0),
            (0.3, 1.0),
            (0.5, slow_factor),
            (0.7, slow_factor),
            (1.0, 1.0),
        ]
        blur = f"High-speed {safe_peak_fps}fps capture decelerated to {safe_base_fps}fps playback at {safe_angle:.0f}-degree shutter"

    elif norm_mode == SpeedRampMode.ACCELERATION_BURST:
        points = [
            (0.0, 1.0),
            (0.2, 1.0),
            (0.45, 2.5),
            (0.7, 2.5),
            (1.0, 1.0),
        ]
        blur = f"Kinetic acceleration burst with {safe_angle:.0f}-degree motion streak"

    elif norm_mode == SpeedRampMode.SNAP_FREEZE_RESUME:
        points = [
            (0.0, 1.0),
            (0.35, 1.0),
            (0.4, 0.0),
            (0.65, 0.0),
            (0.7, 1.0),
            (1.0, 1.0),
        ]
        blur = f"Zero-velocity freeze frame transitioning into {safe_angle:.0f}-degree optical motion"

    elif norm_mode == SpeedRampMode.PULSE_TIME_DILATION:
        points = [
            (0.0, 1.0),
            (0.25, 0.35),
            (0.5, 1.25),
            (0.75, 0.35),
            (1.0, 1.0),
        ]
        blur = f"Pulsing temporal dilation with calibrated {safe_angle:.0f}-degree shutter"

    else:  # CONSTANT_REALTIME
        points = [(0.0, 1.0), (1.0, 1.0)]
        blur = f"Natural {safe_angle:.0f}-degree optical shutter motion blur"

    return SpeedRampCurveSpec(
        mode=norm_mode,
        base_fps=safe_base_fps,
        peak_capture_fps=safe_peak_fps,
        shutter_angle_deg=safe_angle,
        curve_keyframe_points=points,
        motion_blur_character=blur,
    )


def _parse_scene_duration(scene: ScenePromptSpec) -> float:
    """Helper to extract scene duration in seconds."""
    ts = getattr(scene, "timestamp_range", "") or ""
    match = re.search(r"(\d+):(\d+)\s*[-–—]\s*(\d+):(\d+)", ts)
    if match:
        m1, s1, m2, s2 = map(int, match.groups())
        dur = float((m2 * 60 + s2) - (m1 * 60 + s1))
        if dur > 0:
            return dur
    return 8.0


def export_fcpxml_timemap(scene: ScenePromptSpec, sequence_fps: float = 24.0) -> str:
    """Generates an FCPXML v1.10 <timeMap> keyframe structure for automated NLE speed ramping."""
    ramp = scene.speed_ramp
    dur_sec = _parse_scene_duration(scene)

    if not ramp or not ramp.curve_keyframe_points:
        return (
            "                            <timeMap>\n"
            f'                                <timept time="0s" value="0s" interp="smooth"/>\n'
            f'                                <timept time="{dur_sec:.3f}s" value="{dur_sec:.3f}s" interp="smooth"/>\n'
            "                            </timeMap>"
        )

    points = sorted(ramp.curve_keyframe_points, key=lambda p: p[0])
    
    # Ensure (0.0, ...) and (1.0, ...) are present
    if points[0][0] > 0.0:
        points.insert(0, (0.0, points[0][1]))
    if points[-1][0] < 1.0:
        points.append((1.0, points[-1][1]))

    lines = ["                            <timeMap>"]
    
    # Integrate source time across normalized timeline segments
    running_source_sec = 0.0
    lines.append(f'                                <timept time="0s" value="0s" interp="smooth"/>')

    for i in range(1, len(points)):
        t_prev, s_prev = points[i - 1]
        t_curr, s_curr = points[i]
        delta_t_sec = (t_curr - t_prev) * dur_sec
        avg_speed = (s_prev + s_curr) / 2.0
        running_source_sec += delta_t_sec * avg_speed
        timeline_sec = t_curr * dur_sec
        lines.append(
            f'                                <timept time="{timeline_sec:.3f}s" value="{running_source_sec:.3f}s" interp="smooth"/>'
        )

    lines.append("                            </timeMap>")
    return "\n".join(lines)
