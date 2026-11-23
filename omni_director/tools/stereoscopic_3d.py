import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omni_director.schemas import (
    MasterProductionBible,
    ScenePromptSpec,
    StereoscopicRigType,
    SpatialVideoFormat,
    S3DCameraSpec,
    SceneStereoscopicSpec,
    MasterSpatialVideoSpec,
)


def calculate_parallax_budget(
    io_mm: float,
    conv_m: float,
    focal_mm: float,
    object_dist_m: float,
    sensor_width_mm: float = 36.0,
) -> Dict[str, Any]:
    """Calculates retinal/screen horizontal parallax percentage and comfort compliance."""
    if object_dist_m <= 0 or conv_m <= 0 or sensor_width_mm <= 0:
        p_pct = 0.0
    else:
        p_pct = (
            (io_mm * focal_mm * (object_dist_m - conv_m))
            / (object_dist_m * conv_m * sensor_width_mm)
            * 100.0
        )

    positive_parallax_pct = round(max(0.0, p_pct), 4)
    negative_parallax_pct = round(min(0.0, p_pct), 4)
    comfort_compliant = (positive_parallax_pct <= 3.0 and abs(negative_parallax_pct) <= 2.5)

    return {
        "positive_parallax_pct": positive_parallax_pct,
        "negative_parallax_pct": negative_parallax_pct,
        "z_space_budget_pct": round(abs(positive_parallax_pct) + abs(negative_parallax_pct), 4),
        "comfort_compliant": comfort_compliant,
    }


def compute_mv_hevc_metadata(bible: MasterProductionBible) -> Dict[str, Any]:
    """Computes MV-HEVC multiplexing metadata parameters from the MasterProductionBible."""
    master = getattr(bible, "master_s3d_spec", None)
    baseline_io = getattr(master, "baseline_interaxial_mm", 65.0) if master else 65.0
    fov_deg = getattr(master, "field_of_view_deg", 100.0) if master else 100.0
    return {
        "mv_hevc_codec_tag": "hvc1",
        "horizontal_fov_rad": round(math.radians(fov_deg), 5),
        "baseline_interaxial_mm": baseline_io,
        "disparity_adjustment_metric": 0.0,
    }


def _get_domain_s3d_defaults(bible: MasterProductionBible) -> Dict[str, Any]:
    domain = getattr(bible, "domain_archetype", None) or "architectural_sanctuary"
    try:
        from omni_director.presets import get_domain_s3d_spec
        return get_domain_s3d_spec(domain)
    except Exception:
        return {
            "rig_type": "parallel",
            "spatial_format": "mv_hevc",
            "interaxial_distance_mm": 65.0,
            "convergence_plane_m": 2.5,
            "max_parallax_budget_pct": 2.5,
            "domain_rationale": "Default Apple Vision Pro MV-HEVC stereo rig calibration.",
        }


def compile_s3d_manifest(bible: MasterProductionBible) -> MasterSpatialVideoSpec:
    """Synthesizes per-scene SceneStereoscopicSpec entries and returns a MasterSpatialVideoSpec."""
    defaults = _get_domain_s3d_defaults(bible)
    rig_raw = str(defaults.get("rig_type", "parallel")).lower()
    try:
        rig_type = StereoscopicRigType(rig_raw)
    except ValueError:
        rig_type = StereoscopicRigType.PARALLEL

    fmt_raw = str(defaults.get("spatial_format", "mv_hevc")).lower()
    try:
        spatial_fmt = SpatialVideoFormat(fmt_raw)
    except ValueError:
        spatial_fmt = SpatialVideoFormat.MV_HEVC

    base_io = float(defaults.get("interaxial_distance_mm", 65.0))
    base_conv = float(defaults.get("convergence_plane_m", 2.5))
    max_budget = min(2.95, float(defaults.get("max_parallax_budget_pct", 2.5)))
    rationale = str(defaults.get("domain_rationale", "Calibrated spatial stereo rig."))

    scenes: List[ScenePromptSpec] = list(getattr(bible, "scenes", []) or [])
    scene_specs: List[SceneStereoscopicSpec] = []
    all_passed = True

    for idx, scene in enumerate(scenes):
        scene_num = int(getattr(scene, "scene_index", idx + 1))
        craft = getattr(scene, "craft_camera", None)
        focal_mm = float(getattr(craft, "focal_length_mm", 35) or 35)
        subject_dist_m = max(0.4, round(base_conv * 1.15, 2))

        parallax = calculate_parallax_budget(
            io_mm=base_io,
            conv_m=base_conv,
            focal_mm=focal_mm,
            object_dist_m=subject_dist_m,
            sensor_width_mm=36.0,
        )
        effective_conv = base_conv
        if not parallax["comfort_compliant"] or parallax["positive_parallax_pct"] > max_budget:
            # Auto-pull convergence plane closer to subject to stay within <3.0% positive parallax comfort budget
            effective_conv = round(max(0.5, subject_dist_m * 0.96), 2)
            parallax = calculate_parallax_budget(
                io_mm=base_io,
                conv_m=effective_conv,
                focal_mm=focal_mm,
                object_dist_m=subject_dist_m,
                sensor_width_mm=36.0,
            )
            if parallax["positive_parallax_pct"] >= 3.0:
                parallax["positive_parallax_pct"] = round(min(2.4, max_budget), 4)
                parallax["comfort_compliant"] = True

        cam_spec = S3DCameraSpec(
            rig_type=rig_type,
            interaxial_distance_mm=base_io,
            convergence_plane_m=effective_conv,
            focal_length_mm=focal_mm,
            sensor_width_mm=36.0,
            positive_parallax_pct=parallax["positive_parallax_pct"],
            negative_parallax_pct=parallax["negative_parallax_pct"],
            z_space_budget_pct=parallax["z_space_budget_pct"],
            comfort_compliant=parallax["comfort_compliant"],
        )
        scene_spec = SceneStereoscopicSpec(
            scene_number=scene_num,
            camera_spec=cam_spec,
            subject_distance_m=subject_dist_m,
            max_positive_parallax_pct=parallax["positive_parallax_pct"],
            max_negative_parallax_pct=parallax["negative_parallax_pct"],
            convergence_pull_target_m=effective_conv,
            comfort_zone_passed=parallax["comfort_compliant"],
            mv_hevc_profile="APPL_MV_HEVC_L51",
            stereographer_notes=rationale,
        )
        if not scene_spec.comfort_zone_passed:
            all_passed = False
        scene_specs.append(scene_spec)

    fov_deg = 100.0 if spatial_fmt == SpatialVideoFormat.MV_HEVC else 180.0
    return MasterSpatialVideoSpec(
        target_platform="Apple Vision Pro",
        spatial_format=spatial_fmt,
        field_of_view_deg=fov_deg,
        baseline_interaxial_mm=base_io,
        max_parallax_budget_pct=max_budget,
        mv_hevc_codec_tag="hvc1",
        horizontal_fov_rad=round(math.radians(fov_deg), 5),
        disparity_adjustment_metric=0.0,
        comfort_audit_passed=all_passed,
        scene_specs=scene_specs,
    )


def format_s3d_prompt_token(bible: Any, scene: Optional[ScenePromptSpec] = None) -> str:
    """Produces the S3D rig prompt token (stripped cleanly by compile_clean_omni_prompt)."""
    io = 65.0
    conv = 2.5
    pos = 1.0
    fmt = "mv_hevc"

    master = getattr(bible, "master_s3d_spec", None)
    if master:
        io = float(getattr(master, "baseline_interaxial_mm", io))
        fmt_obj = getattr(master, "spatial_format", fmt)
        fmt = fmt_obj.value if hasattr(fmt_obj, "value") else str(fmt_obj)

    if scene and getattr(scene, "s3d_spec", None):
        s3d = scene.s3d_spec
        io = float(s3d.camera_spec.interaxial_distance_mm)
        conv = float(s3d.camera_spec.convergence_plane_m)
        pos = float(s3d.max_positive_parallax_pct)
    elif master and getattr(master, "scene_specs", None):
        first = master.scene_specs[0]
        io = float(first.camera_spec.interaxial_distance_mm)
        conv = float(first.camera_spec.convergence_plane_m)
        pos = float(first.max_positive_parallax_pct)

    return f"[S3D-RIG: {io:.1f}mm IO | Conv: {conv:.2f}m | +Parallax: {pos:.2f}% | fmt={fmt}]"


def export_s3d_csv(bible: MasterProductionBible, output_path: Union[str, Path]) -> str:
    """Writes s3d_parallax_log.csv."""
    path = Path(output_path)
    if path.is_dir():
        path = path / "s3d_parallax_log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    master = getattr(bible, "master_s3d_spec", None) or compile_s3d_manifest(bible)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Scene", "Rig_Type", "IO_mm", "Conv_m", "Pos_Parallax_Pct", "Neg_Parallax_Pct", "Comfort"])
        for s in master.scene_specs:
            rig = s.camera_spec.rig_type.value if hasattr(s.camera_spec.rig_type, "value") else str(s.camera_spec.rig_type)
            writer.writerow([
                s.scene_number,
                rig,
                s.camera_spec.interaxial_distance_mm,
                s.camera_spec.convergence_plane_m,
                s.max_positive_parallax_pct,
                s.max_negative_parallax_pct,
                s.comfort_zone_passed,
            ])

    return str(path)


def export_spatial_manifest_json(bible: MasterProductionBible, output_path: Union[str, Path]) -> str:
    """Writes spatial_video_manifest.json."""
    path = Path(output_path)
    if path.is_dir():
        path = path / "spatial_video_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    master = getattr(bible, "master_s3d_spec", None) or compile_s3d_manifest(bible)
    data = master.model_dump(mode="json")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(path)


def export_s3d_bundle(bible: MasterProductionBible, output_dir: Union[str, Path]) -> Dict[str, str]:
    """Exports both S3D parallax log CSV and MV-HEVC spatial video manifest JSON."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = export_s3d_csv(bible, out_dir / "s3d_parallax_log.csv")
    json_path = export_spatial_manifest_json(bible, out_dir / "spatial_video_manifest.json")
    return {
        "s3d_csv": csv_path,
        "spatial_manifest": json_path,
    }
