"""Cinematic Depth of Field & Optical Focus Simulator Suite (PM-FEAT-011).

Provides depth of field (DoF) calculations, hyperfocal distance mapping,
1st AC Focus Puller cue sheet synthesis, optical blur circles, rack-focus
interpolation curves, and post-production optical chart exporting.
"""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    ApertureIrisGeometry,
    DepthOfFieldSpec,
    DomainDofSpec,
    MasterProductionBible,
    OpticalAberrationProfile,
    RackFocusTransitionCurve,
    SensorFormat,
)


def resolve_circle_of_confusion(
    sensor_format: Optional[Union[SensorFormat, str]] = None,
) -> float:
    """Resolves standard optical Circle of Confusion (CoC) in millimeters by sensor format."""
    if sensor_format is None:
        return 0.030

    fmt_str = sensor_format.value if isinstance(sensor_format, SensorFormat) else str(sensor_format)
    fmt_clean = fmt_str.lower()

    if "super" in fmt_clean or "super_35" in fmt_clean or "s35" in fmt_clean:
        return 0.020
    if "arri" in fmt_clean or "large format" in fmt_clean or "lf" in fmt_clean:
        return 0.025
    if "imax" in fmt_clean or "70mm" in fmt_clean:
        return 0.045
    if "vistavision" in fmt_clean or "vista" in fmt_clean:
        return 0.030
    if "full" in fmt_clean or "frame" in fmt_clean:
        return 0.030

    return 0.030


def calculate_hyperfocal_distance(
    focal_length_mm: Union[int, float],
    aperture_f_stop: float,
    circle_of_confusion_mm: float = 0.030,
) -> float:
    """Calculates hyperfocal distance H in meters: H = (f^2 / (N * c)) / 1000."""
    if focal_length_mm <= 0:
        focal_length_mm = 35.0
    if aperture_f_stop <= 0:
        aperture_f_stop = 2.8
    if circle_of_confusion_mm <= 0:
        circle_of_confusion_mm = 0.030

    f_mm = float(focal_length_mm)
    N = float(aperture_f_stop)
    c_mm = float(circle_of_confusion_mm)

    h_mm = (f_mm * f_mm) / (N * c_mm)
    return round(h_mm / 1000.0, 3)


def calculate_dof_limits(
    focal_length_mm: Union[int, float],
    aperture_t_stop: float,
    subject_distance_m: float = 2.5,
    circle_of_confusion_mm: float = 0.030,
    focus_distance_m: Optional[float] = None,
) -> Tuple[float, float, float, float]:
    """Calculates near limit, far limit, total depth of field, and hyperfocal distance in meters.

    Returns:
        (near_limit_m, far_limit_m, total_dof_m, hyperfocal_distance_m)
    """
    if focus_distance_m is not None:
        subject_distance_m = focus_distance_m

    if focal_length_mm <= 0:
        focal_length_mm = 35
    if aperture_t_stop <= 0:
        aperture_t_stop = 2.8
    if subject_distance_m <= 0:
        subject_distance_m = 2.5

    H = calculate_hyperfocal_distance(focal_length_mm, aperture_t_stop, circle_of_confusion_mm)
    s = float(subject_distance_m)

    # Near focus limit: Dn = (H * s) / (H + (s - f/1000))
    f_m = float(focal_length_mm) / 1000.0
    denominator_near = H + (s - f_m)
    near_limit = (H * s) / denominator_near if denominator_near > 0 else 0.0

    # Far focus limit: Df = (H * s) / (H - (s - f/1000))
    denominator_far = H - (s - f_m)
    if denominator_far <= 0 or s >= H:
        far_limit = float("inf")
        total_dof = float("inf")
    else:
        far_limit = (H * s) / denominator_far
        total_dof = far_limit - near_limit

    return (
        round(near_limit, 2),
        round(far_limit, 2) if far_limit != float("inf") else 999.99,
        round(total_dof, 2) if total_dof != float("inf") else 999.99,
        round(H, 2),
    )


def interpolate_rack_focus(
    start_distance_m: float,
    target_distance_m: float,
    progress: float,
    curve: Union[RackFocusTransitionCurve, str] = RackFocusTransitionCurve.CUBIC_EASE_IN_OUT,
) -> float:
    """Interpolates focal plane distance between start and target focus points."""
    p = max(0.0, min(1.0, float(progress)))

    curve_key = curve.value if isinstance(curve, RackFocusTransitionCurve) else str(curve).lower()

    if "linear" in curve_key:
        t = p
    elif "snap" in curve_key:
        # Exponential snap: slow build, sharp snap
        t = math.pow(p, 3.5)
    elif "whip" in curve_key:
        # Whiplash / fast attack
        t = math.sin(p * math.pi / 2.0)
    else:
        # Cubic ease-in-out (smoothstep: 3*p^2 - 2*p^3)
        t = 3.0 * (p ** 2) - 2.0 * (p ** 3)

    interpolated = start_distance_m + (target_distance_m - start_distance_m) * t
    return round(interpolated, 3)


def synthesize_default_dof_spec(
    focal_length_mm: int = 35,
    aperture_f_stop: float = 2.8,
    focus_distance_m: float = 2.5,
    sensor_format: Optional[Union[SensorFormat, str]] = None,
    iris_geometry: ApertureIrisGeometry = ApertureIrisGeometry.CIRCULAR,
    rack_focus_enabled: bool = False,
    rack_focus_start_m: Optional[float] = None,
    rack_focus_target_m: Optional[float] = None,
    rack_focus_curve: RackFocusTransitionCurve = RackFocusTransitionCurve.CUBIC_EASE_IN_OUT,
    rack_focus_duration_frames: int = 24,
) -> DepthOfFieldSpec:
    """Synthesizes a fully resolved, physically verified DepthOfFieldSpec."""
    coc = resolve_circle_of_confusion(sensor_format)
    near_l, far_l, total_d, hyper_m = calculate_dof_limits(
        focal_length_mm=focal_length_mm,
        aperture_t_stop=aperture_f_stop,
        subject_distance_m=focus_distance_m,
        circle_of_confusion_mm=coc,
    )

    return DepthOfFieldSpec(
        focal_length_mm=focal_length_mm,
        aperture_f_stop=aperture_f_stop,
        focus_distance_m=focus_distance_m,
        near_limit_m=near_l,
        far_limit_m=far_l if far_l != 999.99 else None,
        hyperfocal_distance_m=hyper_m,
        circle_of_confusion_mm=coc,
        iris_geometry=iris_geometry,
        aberration_profile=OpticalAberrationProfile(),
        rack_focus_enabled=rack_focus_enabled,
        rack_focus_start_m=rack_focus_start_m,
        rack_focus_target_m=rack_focus_target_m,
        rack_focus_curve=rack_focus_curve,
        rack_focus_duration_frames=rack_focus_duration_frames,
    )


def format_dof_prompt_token(
    dof_spec: Union[DepthOfFieldSpec, DomainDofSpec, Dict[str, Any]],
) -> str:
    """Synthesizes a cinematic optical depth of field prompt token for Gemini Omni."""
    if isinstance(dof_spec, DepthOfFieldSpec):
        f_mm = dof_spec.focal_length_mm
        t_stop = dof_spec.aperture_f_stop
        iris = dof_spec.iris_geometry.value if hasattr(dof_spec.iris_geometry, "value") else str(dof_spec.iris_geometry)
        dist = dof_spec.focus_distance_m

        if dof_spec.rack_focus_enabled and dof_spec.rack_focus_start_m and dof_spec.rack_focus_target_m:
            curve_str = dof_spec.rack_focus_curve.value if hasattr(dof_spec.rack_focus_curve, "value") else str(dof_spec.rack_focus_curve)
            return (
                f"rack focus from {dof_spec.rack_focus_start_m:.1f}m to {dof_spec.rack_focus_target_m:.1f}m "
                f"({curve_str}, T{t_stop:.1f}, {f_mm}mm, {iris}, shallow depth of field)"
            )
        else:
            style = "shallow focus" if t_stop <= 2.8 else "deep focus"
            return f"{style} at {dist:.1f}m (T{t_stop:.1f}, {f_mm}mm, {iris}, optical depth of field)"

    elif isinstance(dof_spec, DomainDofSpec):
        style = dof_spec.focus_style
        t_stop = dof_spec.aperture_t_stop
        f_mm = dof_spec.focal_length_mm
        iris = dof_spec.iris_geometry
        char = dof_spec.depth_character
        return f"{style} (T{t_stop:.1f}, {f_mm}mm, {iris}, {char})"

    elif isinstance(dof_spec, dict):
        style = dof_spec.get("focus_style", "shallow focus")
        t_stop = dof_spec.get("aperture_t_stop") or dof_spec.get("aperture_f_stop", 2.0)
        f_mm = dof_spec.get("focal_length_mm", 50)
        iris = dof_spec.get("iris_geometry", "circular iris")
        char = dof_spec.get("depth_character", "smooth falloff")
        return f"{style} (T{t_stop:.1f}, {f_mm}mm, {iris}, {char})"

    return "shallow depth of field (T2.0, 50mm, circular iris)"


def export_optical_chart_json(
    bible: MasterProductionBible,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Exports optical depth-of-field hyperfocal chart as JSON."""
    scenes_data: List[Dict[str, Any]] = []

    master_dof = getattr(bible, "master_dof_spec", None) or getattr(bible, "dof_spec", None)
    default_f = getattr(master_dof, "focal_length_mm", 35) if master_dof else 35
    default_t = getattr(master_dof, "aperture_f_stop", None) or getattr(master_dof, "aperture_t_stop", 2.8) if master_dof else 2.8

    for s in bible.scenes:
        s_dof = getattr(s, "dof_spec", None) or master_dof
        f_mm = getattr(s_dof, "focal_length_mm", default_f) if s_dof else default_f
        t_stop = getattr(s_dof, "aperture_f_stop", None) or getattr(s_dof, "aperture_t_stop", default_t) if s_dof else default_t
        near_l, far_l, total_d, hyper_m = calculate_dof_limits(f_mm, t_stop, subject_distance_m=2.5)

        iris_geo = "circular iris"
        focus_style = "natural commercial focus"
        depth_char = "balanced depth"

        if s_dof:
            if hasattr(s_dof, "iris_geometry"):
                iris_geo = s_dof.iris_geometry.value if hasattr(s_dof.iris_geometry, "value") else str(s_dof.iris_geometry)
            if hasattr(s_dof, "focus_style"):
                focus_style = s_dof.focus_style
            if hasattr(s_dof, "depth_character"):
                depth_char = s_dof.depth_character

        scenes_data.append({
            "scene_index": s.scene_index,
            "scene_title": s.scene_title,
            "focal_length_mm": f_mm,
            "aperture_t_stop": t_stop,
            "iris_geometry": iris_geo,
            "focus_style": focus_style,
            "depth_character": depth_char,
            "hyperfocal_distance_m": hyper_m,
            "near_limit_m": near_l,
            "far_limit_m": far_l,
            "total_dof_m": total_d,
        })

    master_near, master_far, master_total, master_hyper = calculate_dof_limits(default_f, default_t, 2.5)

    master_iris = "circular iris"
    master_style = "Standard Cinematic"
    master_char = "balanced"
    if master_dof:
        if hasattr(master_dof, "iris_geometry"):
            master_iris = master_dof.iris_geometry.value if hasattr(master_dof.iris_geometry, "value") else str(master_dof.iris_geometry)
        if hasattr(master_dof, "focus_style"):
            master_style = master_dof.focus_style
        if hasattr(master_dof, "depth_character"):
            master_char = master_dof.depth_character

    chart = {
        "project_title": bible.project_title,
        "master_dof": {
            "focal_length_mm": default_f,
            "aperture_t_stop": default_t,
            "focus_style": master_style,
            "iris_geometry": master_iris,
            "depth_character": master_char,
            "hyperfocal_distance_m": master_hyper,
            "near_limit_m": master_near,
            "far_limit_m": master_far,
            "total_dof_m": master_total,
        },
        "scenes": scenes_data,
    }

    json_str = json.dumps(chart, indent=2)
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json_str, encoding="utf-8")
    return json_str


def export_focus_puller_cue_sheet(
    bible: MasterProductionBible,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Exports 1st AC Focus Puller cue sheet as CSV."""
    master_dof = getattr(bible, "master_dof_spec", None) or getattr(bible, "dof_spec", None)
    default_f = getattr(master_dof, "focal_length_mm", 35) if master_dof else 35
    default_t = getattr(master_dof, "aperture_f_stop", None) or getattr(master_dof, "aperture_t_stop", 2.8) if master_dof else 2.8

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "scene_index",
        "scene_title",
        "timestamp_range",
        "focal_length_mm",
        "t_stop",
        "focus_style",
        "iris_geometry",
        "near_limit_m",
        "far_limit_m",
        "total_dof_m",
        "hyperfocal_m",
    ])

    for s in bible.scenes:
        s_dof = getattr(s, "dof_spec", None) or master_dof
        f_mm = getattr(s_dof, "focal_length_mm", default_f) if s_dof else default_f
        t_stop = getattr(s_dof, "aperture_f_stop", None) or getattr(s_dof, "aperture_t_stop", default_t) if s_dof else default_t
        near_l, far_l, total_d, hyper_m = calculate_dof_limits(f_mm, t_stop, subject_distance_m=2.5)

        iris_geo = "circular iris"
        focus_style = "Standard Focus"
        if s_dof:
            if hasattr(s_dof, "iris_geometry"):
                iris_geo = s_dof.iris_geometry.value if hasattr(s_dof.iris_geometry, "value") else str(s_dof.iris_geometry)
            if hasattr(s_dof, "focus_style"):
                focus_style = s_dof.focus_style

        writer.writerow([
            s.scene_index,
            s.scene_title,
            s.timestamp_range,
            f_mm,
            f"T{t_stop:.1f}",
            focus_style,
            iris_geo,
            f"{near_l:.2f}",
            f"{far_l:.2f}" if far_l != 999.99 else "INF",
            f"{total_d:.2f}" if total_d != 999.99 else "INF",
            f"{hyper_m:.2f}",
        ])

    csv_str = buf.getvalue()
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(csv_str, encoding="utf-8")
    return csv_str


def export_dof_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports all Optical Depth-of-Field (DoF) manifests (JSON chart, CSV cue sheet) to output_dir."""
    out_p = Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    chart_p = out_p / "dof_chart.json"
    cue_p = out_p / "focus_puller_cue_sheet.csv"

    export_optical_chart_json(bible, chart_p)
    export_focus_puller_cue_sheet(bible, cue_p)

    return {
        "dof_chart": str(chart_p.resolve()),
        "cue_sheet": str(cue_p.resolve()),
    }
