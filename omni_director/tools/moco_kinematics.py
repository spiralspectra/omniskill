"""Robotic Motion Control (MoCo) Rig & 6-DOF Camera Kinematics Engine (PM-FEAT-009).

Provides calculations for 6-DOF spatial waypoints (X, Y, Z translation and Roll, Pitch, Yaw rotation),
trajectory path distance, peak velocity, mean acceleration, sub-frame waypoint interpolation,
cinematic MoCo prompt token formatting, and export functions for JSON, CSV, and FBX ASCII
camera animation curves.
"""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    MasterProductionBible,
    MocoRigSpec,
    MotionControlRigType,
    TrajectoryWaypoint6DOF,
)


def synthesize_default_moco_rig(
    rig_type: Union[MotionControlRigType, str] = MotionControlRigType.BOLT_CINEBOT,
    track_length_meters: float = 6.0,
    max_velocity_mps: float = 4.5,
) -> MocoRigSpec:
    """Synthesizes a standardized industrial robotic motion control rig specification."""
    if isinstance(rig_type, str):
        for m in MotionControlRigType:
            if m.value == rig_type.lower():
                rig_type = m
                break
        else:
            rig_type = MotionControlRigType.BOLT_CINEBOT

    waypoints = [
        TrajectoryWaypoint6DOF(
            timecode_sec=0.0,
            x_meters=0.0,
            y_meters=-2.0,
            z_meters=1.2,
            roll_deg=0.0,
            pitch_deg=-5.0,
            yaw_deg=0.0,
            velocity_mps=0.0,
        ),
        TrajectoryWaypoint6DOF(
            timecode_sec=2.0,
            x_meters=1.5,
            y_meters=-0.8,
            z_meters=1.4,
            roll_deg=0.0,
            pitch_deg=-2.0,
            yaw_deg=15.0,
            velocity_mps=2.2,
        ),
        TrajectoryWaypoint6DOF(
            timecode_sec=5.0,
            x_meters=3.5,
            y_meters=0.5,
            z_meters=1.6,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=30.0,
            velocity_mps=4.2,
        ),
        TrajectoryWaypoint6DOF(
            timecode_sec=8.0,
            x_meters=5.0,
            y_meters=1.8,
            z_meters=1.5,
            roll_deg=0.0,
            pitch_deg=5.0,
            yaw_deg=45.0,
            velocity_mps=3.0,
        ),
        TrajectoryWaypoint6DOF(
            timecode_sec=10.0,
            x_meters=6.0,
            y_meters=2.2,
            z_meters=1.4,
            roll_deg=0.0,
            pitch_deg=2.0,
            yaw_deg=50.0,
            velocity_mps=0.5,
        ),
    ]

    return MocoRigSpec(
        rig_type=rig_type,
        payload_kg=15.0,
        track_length_meters=track_length_meters,
        max_velocity_mps=max_velocity_mps,
        waypoints=waypoints,
        locked_roll_stabilization=True,
        mechanical_backlash_mm=0.05,
    )


def calculate_trajectory_distance(waypoints: Union[List[TrajectoryWaypoint6DOF], MocoRigSpec]) -> float:
    """Calculates total Euclidean path distance in meters through 3D waypoints."""
    if isinstance(waypoints, MocoRigSpec):
        waypoints = waypoints.waypoints
    if len(waypoints) < 2:
        return 0.0

    total_dist = 0.0
    for i in range(len(waypoints) - 1):
        dx = waypoints[i + 1].x_meters - waypoints[i].x_meters
        dy = waypoints[i + 1].y_meters - waypoints[i].y_meters
        dz = waypoints[i + 1].z_meters - waypoints[i].z_meters
        total_dist += math.sqrt(dx * dx + dy * dy + dz * dz)

    return round(total_dist, 3)


def calculate_peak_velocity(waypoints: Union[List[TrajectoryWaypoint6DOF], MocoRigSpec]) -> float:
    """Calculates peak instantaneous velocity in meters per second across waypoints."""
    if isinstance(waypoints, MocoRigSpec):
        waypoints = waypoints.waypoints
    if not waypoints:
        return 0.0

    # Check explicit waypoint velocities
    peak = max((wp.velocity_mps for wp in waypoints), default=0.0)

    # Cross-verify with displacement over time between consecutive waypoints
    for i in range(len(waypoints) - 1):
        dt = waypoints[i + 1].timecode_sec - waypoints[i].timecode_sec
        if dt > 1e-4:
            dx = waypoints[i + 1].x_meters - waypoints[i].x_meters
            dy = waypoints[i + 1].y_meters - waypoints[i].y_meters
            dz = waypoints[i + 1].z_meters - waypoints[i].z_meters
            seg_v = math.sqrt(dx * dx + dy * dy + dz * dz) / dt
            if seg_v > peak:
                peak = seg_v

    return round(peak, 3)


def calculate_mean_acceleration(waypoints: Union[List[TrajectoryWaypoint6DOF], MocoRigSpec]) -> float:
    """Calculates mean acceleration magnitude in m/s² across consecutive waypoints."""
    if isinstance(waypoints, MocoRigSpec):
        waypoints = waypoints.waypoints
    if len(waypoints) < 2:
        return 0.0

    accels: List[float] = []
    for i in range(len(waypoints) - 1):
        dt = waypoints[i + 1].timecode_sec - waypoints[i].timecode_sec
        if dt > 1e-4:
            v0 = waypoints[i].velocity_mps
            v1 = waypoints[i + 1].velocity_mps
            dv = abs(v1 - v0)
            accels.append(dv / dt)

    if not accels:
        return 0.0
    return round(sum(accels) / len(accels), 3)


def interpolate_waypoints_6dof(
    waypoints: Union[List[TrajectoryWaypoint6DOF], MocoRigSpec],
    sample_rate_hz: float = 24.0,
) -> List[TrajectoryWaypoint6DOF]:
    """Interpolates 6-DOF waypoints at given sample rate (default: 24Hz SMPTE frames)."""
    if isinstance(waypoints, MocoRigSpec):
        waypoints = waypoints.waypoints
    if not waypoints:
        return []
    if len(waypoints) == 1 or sample_rate_hz <= 0:
        return [waypoints[0].model_copy()]

    sorted_wps = sorted(waypoints, key=lambda w: w.timecode_sec)
    t_start = sorted_wps[0].timecode_sec
    t_end = sorted_wps[-1].timecode_sec
    dt_step = 1.0 / sample_rate_hz

    def lerp(a: float, b: float, alpha: float) -> float:
        return a + alpha * (b - a)

    interpolated: List[TrajectoryWaypoint6DOF] = []
    current_t = t_start
    idx = 0

    while current_t <= t_end + 1e-4:
        while idx < len(sorted_wps) - 2 and sorted_wps[idx + 1].timecode_sec < current_t:
            idx += 1

        w0 = sorted_wps[idx]
        w1 = sorted_wps[idx + 1]
        span = w1.timecode_sec - w0.timecode_sec
        alpha = 0.0 if span <= 1e-5 else max(0.0, min(1.0, (current_t - w0.timecode_sec) / span))

        interpolated.append(
            TrajectoryWaypoint6DOF(
                timecode_sec=round(current_t, 4),
                x_meters=round(lerp(w0.x_meters, w1.x_meters, alpha), 4),
                y_meters=round(lerp(w0.y_meters, w1.y_meters, alpha), 4),
                z_meters=round(lerp(w0.z_meters, w1.z_meters, alpha), 4),
                roll_deg=round(lerp(w0.roll_deg, w1.roll_deg, alpha), 3),
                pitch_deg=round(lerp(w0.pitch_deg, w1.pitch_deg, alpha), 3),
                yaw_deg=round(lerp(w0.yaw_deg, w1.yaw_deg, alpha), 3),
                velocity_mps=round(lerp(w0.velocity_mps, w1.velocity_mps, alpha), 3),
            )
        )
        current_t += dt_step

    return interpolated


# Canonical alias for waypoint interpolation
interpolate_waypoints = interpolate_waypoints_6dof


def format_moco_prompt_token(moco: MocoRigSpec) -> str:
    """Synthesizes a robotic motion control (MoCo) camera grammar prompt token."""
    rig_str = moco.rig_type.value if hasattr(moco.rig_type, "value") else str(moco.rig_type)
    dist = moco.track_length_meters if moco.track_length_meters > 0 else (calculate_trajectory_distance(moco.waypoints) or 6.0)
    peak_v = moco.max_velocity_mps if moco.max_velocity_mps > 0 else (calculate_peak_velocity(moco.waypoints) or 4.5)
    stab_str = "stabilized 3-axis horizon lock" if moco.locked_roll_stabilization else "free-roll axis"

    return (
        f"Robotic MoCo camera move on {rig_str}, 6-DOF precision track length {dist:.1f}m, "
        f"peak velocity {peak_v:.1f}m/s, mechanical repeatability ±{moco.mechanical_backlash_mm:.2f}mm, {stab_str}"
    )


def _resolve_bible_moco_rig(bible: MasterProductionBible) -> MocoRigSpec:
    """Extracts master or scene MoCo rig from bible, or synthesizes a standardized default."""
    moco = bible.master_moco_rig
    if moco is None:
        for s in bible.scenes:
            if s.moco_rig:
                moco = s.moco_rig
                break
            if s.craft_camera and s.craft_camera.moco_rig:
                moco = s.craft_camera.moco_rig
                break
    if moco is None:
        moco = synthesize_default_moco_rig(f"{bible.project_title} Cinebot")
    return moco


def export_moco_track_json(
    bible: MasterProductionBible,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Exports full 6-DOF motion control trajectory track and kinematics metadata as JSON."""
    master_moco = _resolve_bible_moco_rig(bible)
    dist = calculate_trajectory_distance(master_moco.waypoints)
    peak_v = calculate_peak_velocity(master_moco.waypoints)
    mean_a = calculate_mean_acceleration(master_moco.waypoints)

    scenes_data = []
    for s in bible.scenes:
        sc_moco = s.moco_rig or (s.craft_camera.moco_rig if s.craft_camera else None) or master_moco
        scenes_data.append(
            {
                "scene_index": s.scene_index,
                "scene_title": s.scene_title,
                "timestamp_range": s.timestamp_range,
                "rig_type": sc_moco.rig_type.value if hasattr(sc_moco.rig_type, "value") else str(sc_moco.rig_type),
                "track_length_meters": sc_moco.track_length_meters,
                "max_velocity_mps": sc_moco.max_velocity_mps,
                "waypoints": [wp.model_dump() for wp in sc_moco.waypoints],
                "kinematics": {
                    "distance_meters": calculate_trajectory_distance(sc_moco.waypoints),
                    "peak_velocity_mps": calculate_peak_velocity(sc_moco.waypoints),
                    "mean_acceleration_mps2": calculate_mean_acceleration(sc_moco.waypoints),
                },
            }
        )

    moco_dict = {
        "rig_type": master_moco.rig_type.value if hasattr(master_moco.rig_type, "value") else str(master_moco.rig_type),
        "payload_kg": master_moco.payload_kg,
        "track_length_meters": master_moco.track_length_meters,
        "max_velocity_mps": master_moco.max_velocity_mps,
        "locked_roll_stabilization": master_moco.locked_roll_stabilization,
        "mechanical_backlash_mm": master_moco.mechanical_backlash_mm,
        "waypoints_count": len(master_moco.waypoints),
        "waypoints": [wp.model_dump() for wp in master_moco.waypoints],
        "summary_kinematics": {
            "total_distance_meters": dist,
            "peak_velocity_mps": peak_v,
            "mean_acceleration_mps2": mean_a,
        },
    }

    manifest = {
        "project_title": bible.project_title,
        "master_moco_rig": moco_dict,
        "motion_control_rig": moco_dict,
        "scenes": scenes_data,
    }

    json_str = json.dumps(manifest, indent=2)
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json_str, encoding="utf-8")
    return json_str


def export_moco_track_csv(
    bible: MasterProductionBible,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Exports 6-DOF camera track waypoints as CSV for Nuke/Maya/Blender integration."""
    master_moco = _resolve_bible_moco_rig(bible)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "scene_index",
            "scene_title",
            "timecode_sec",
            "x_meters",
            "y_meters",
            "z_meters",
            "roll_deg",
            "pitch_deg",
            "yaw_deg",
            "velocity_mps",
            "rig_type",
        ]
    )

    for s in bible.scenes:
        sc_moco = s.moco_rig or (s.craft_camera.moco_rig if s.craft_camera else None) or master_moco
        rig_str = sc_moco.rig_type.value if hasattr(sc_moco.rig_type, "value") else str(sc_moco.rig_type)
        for wp in sc_moco.waypoints:
            writer.writerow(
                [
                    s.scene_index,
                    s.scene_title,
                    f"{wp.timecode_sec:.3f}",
                    f"{wp.x_meters:.4f}",
                    f"{wp.y_meters:.4f}",
                    f"{wp.z_meters:.4f}",
                    f"{wp.roll_deg:.3f}",
                    f"{wp.pitch_deg:.3f}",
                    f"{wp.yaw_deg:.3f}",
                    f"{wp.velocity_mps:.3f}",
                    rig_str,
                ]
            )

    csv_str = buffer.getvalue()
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(csv_str, encoding="utf-8")
    return csv_str


def export_moco_fbx_ascii(
    bible: MasterProductionBible,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Exports 6-DOF camera motion control animation curve as ASCII FBX for 3D DCC tools."""
    master_moco = _resolve_bible_moco_rig(bible)
    lines = [
        "; FBX 7.4.0 project file",
        f"; Generated by Omni Movie Director v2.4.0 MoCo Kinematics Engine for '{bible.project_title}'",
        "; ----------------------------------------------------",
        "",
        "FBXHeaderExtension:  {",
        "    FBXHeaderVersion: 1003",
        "    FBXVersion: 7400",
        "    CreationTimeStamp: {",
        "        Version: 1000",
        "        Year: 2026",
        "        Month: 11",
        "        Day: 5",
        "    }",
        '    Creator: "Omni Movie Director MoCo Kinematics Engine"',
        "}",
        "",
        "GlobalSettings:  {",
        "    Version: 1000",
        "    Properties70:  {",
        '        P: "UpAxis", "int", "Integer", "", 2',
        '        P: "UpAxisSign", "int", "Integer", "", 1',
        '        P: "FrontAxis", "int", "Integer", "", 1',
        '        P: "FrontAxisSign", "int", "Integer", "", -1',
        '        P: "CoordAxis", "int", "Integer", "", 0',
        '        P: "CoordAxisSign", "int", "Integer", "", 1',
        '        P: "UnitScaleFactor", "double", "Number", "", 100.0',
        "    }",
        "}",
        "",
        "Definitions:  {",
        "    Version: 100",
        "    Count: 2",
        '    ObjectType: "Model" {',
        "        Count: 1",
        "    }",
        '    ObjectType: "NodeAttribute" {',
        "        Count: 1",
        "    }",
        "}",
        "",
        "Objects:  {",
        '    NodeAttribute: 1000001, "NodeAttribute::Camera", "Camera" {',
        "        Properties70:  {",
        '            P: "FocalLength", "double", "Number", "", 35.0',
        "        }",
        "    }",
        '    Model: 2000001, "Model::MoCo_Camera_Rig", "Camera" {',
        '    ; Model: "Camera::MocoCamera"',
        "        Version: 232",
        "        Properties70:  {",
    ]

    first_wp = master_moco.waypoints[0] if master_moco.waypoints else TrajectoryWaypoint6DOF()
    lines.extend(
        [
            f'            P: "Lcl Translation", "Lcl Translation", "", "A", {first_wp.x_meters * 100.0:.2f}, {first_wp.y_meters * 100.0:.2f}, {first_wp.z_meters * 100.0:.2f}',
            f'            P: "Lcl Rotation", "Lcl Rotation", "", "A", {first_wp.pitch_deg:.2f}, {first_wp.yaw_deg:.2f}, {first_wp.roll_deg:.2f}',
            "        }",
            '        C: "OP", 1000001, "NodeAttribute::Camera"',
            "    }",
            "",
            "    ; --- 6-DOF Camera Waypoints Keyframe Track ---",
        ]
    )

    for idx, wp in enumerate(master_moco.waypoints):
        frame_idx = int(round(wp.timecode_sec * 24))
        lines.append(
            f"    ; Keyframe {idx:03d} (Time: {wp.timecode_sec:.3f}s / Frame: {frame_idx})"
        )
        lines.append(
            f"    Key: {frame_idx}, Translation: ({wp.x_meters * 100.0:.2f}, {wp.y_meters * 100.0:.2f}, {wp.z_meters * 100.0:.2f}), "
            f"Rotation: ({wp.pitch_deg:.2f}, {wp.yaw_deg:.2f}, {wp.roll_deg:.2f}), Velocity: {wp.velocity_mps:.2f} m/s"
        )

    lines.extend(
        [
            "}",
            "",
            "Connections:  {",
            '    C: "OO", 2000001, 0',
            '    C: "OO", 1000001, 2000001',
            "}",
            "",
        ]
    )

    fbx_str = "\n".join(lines) + "\n"
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(fbx_str, encoding="utf-8")
    return fbx_str


def export_moco_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports all Motion Control (MoCo) kinematic manifests (JSON, CSV, FBX) to output_dir."""
    out_p = Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    json_p = out_p / "moco_camera_track.json"
    csv_p = out_p / "moco_waypoints.csv"
    fbx_p = out_p / "moco_trajectory.fbx"

    export_moco_track_json(bible, json_p)
    export_moco_track_csv(bible, csv_p)
    export_moco_fbx_ascii(bible, fbx_p)

    # Also write alias filenames
    (out_p / "moco_track.json").write_text(json_p.read_text(encoding="utf-8"), encoding="utf-8")
    (out_p / "moco_track.csv").write_text(csv_p.read_text(encoding="utf-8"), encoding="utf-8")
    (out_p / "moco_camera.fbx").write_text(fbx_p.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "json": str(json_p.resolve()),
        "csv": str(csv_p.resolve()),
        "fbx": str(fbx_p.resolve()),
        "moco_json": str(json_p.resolve()),
        "moco_csv": str(csv_p.resolve()),
        "moco_fbx": str(fbx_p.resolve()),
        "moco": str(json_p.resolve()),
    }
