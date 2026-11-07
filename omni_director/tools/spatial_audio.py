"""Spatial Audio & Binaural Soundfield Acoustic Simulation Suite (PM-FEAT-013).

Provides Sabine and Eyring reverberation decay (RT60) physics calculations,
Room Impulse Response (RIR) modeling, 3D Vector Base Amplitude Panning (VBAP)
across Dolby Atmos 7.1.4 bed layouts, Higher-Order Ambisonics (HOA) B-format encoding,
Web Audio API spatial PannerNode configuration, and prompt token generation.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    AcousticMaterialType,
    AcousticRoomImpulseResponse,
    DolbyAtmosBedFormat,
    MasterProductionBible,
    ScenePromptSpec,
    SpatialAudioObjectSpec,
    SpatialAudioSoundfieldSpec,
    SpatialCoordinate3D,
    StemType,
)


SPEED_OF_SOUND_MPS = 343.0

# Material absorption coefficients (broadband Sabine/Eyring average)
ACOUSTIC_ABSORPTION_COEFFICIENTS: Dict[str, float] = {
    AcousticMaterialType.MARBLE_GLASS.value: 0.03,
    AcousticMaterialType.HARDWOOD_CONCRETE.value: 0.08,
    AcousticMaterialType.STUDIO_ACOUSTIC_FOAM.value: 0.75,
    AcousticMaterialType.FURNISHED_RESIDENTIAL.value: 0.30,
    AcousticMaterialType.AUTOMOTIVE_CABIN.value: 0.45,
    AcousticMaterialType.OPEN_OUTDOOR_DIFFUSE.value: 0.95,
}

# Standard 7.1.4 Dolby Atmos speaker layout azimuth/elevation (degrees)
# Azimuth: 0=Front, -30=L, +30=R, -90=Ls, +90=Rs, -150=Rls, +150=Rrs
# Elevation: 0=Listener plane, +45=Top/Height speakers
ATMOS_7_1_4_SPEAKER_GEOMETRY: Dict[str, Tuple[float, float]] = {
    "L": (-30.0, 0.0),
    "C": (0.0, 0.0),
    "R": (30.0, 0.0),
    "Ls": (-90.0, 0.0),
    "Rs": (90.0, 0.0),
    "Rls": (-150.0, 0.0),
    "Rrs": (150.0, 0.0),
    "Ltf": (-30.0, 45.0),
    "Rtf": (30.0, 45.0),
    "Ltr": (-150.0, 45.0),
    "Rtr": (150.0, 45.0),
}


def get_material_absorption(material: Union[str, AcousticMaterialType, float, int]) -> float:
    """Returns the broadband acoustic absorption coefficient (0.0 to 1.0) for a material."""
    if isinstance(material, (int, float)):
        return max(0.01, min(1.0, float(material)))
    if isinstance(material, AcousticMaterialType):
        key = material.value
    else:
        key = str(material).strip().lower().replace("-", "_").replace(" ", "_")
    return ACOUSTIC_ABSORPTION_COEFFICIENTS.get(key, 0.30)


def calculate_sabine_rt60(
    volume_m3: float,
    surface_area_m2: float,
    material: Union[str, AcousticMaterialType],
) -> float:
    """Calculates Sabine reverberation decay time to -60 dB (RT60) in seconds.

    Formula: RT60 = 0.161 * V / (S * alpha)
    Suitable for live, lightly damped enclosures (alpha < 0.35).
    """
    alpha = get_material_absorption(material)
    effective_absorption = max(surface_area_m2 * alpha, 0.01)
    rt60 = 0.161 * volume_m3 / effective_absorption
    return round(float(rt60), 3)


def calculate_eyring_rt60(
    volume_m3: float,
    surface_area_m2: float,
    material: Union[str, AcousticMaterialType],
) -> float:
    """Calculates Eyring reverberation decay time to -60 dB (RT60) in seconds.

    Formula: RT60 = 0.161 * V / (-S * ln(1 - alpha))
    Accurate for dead, heavily damped or studio acoustic rooms (alpha >= 0.35).
    """
    alpha = min(max(get_material_absorption(material), 0.001), 0.99)
    denominator = -surface_area_m2 * math.log(1.0 - alpha)
    rt60 = 0.161 * volume_m3 / max(denominator, 0.01)
    return round(float(rt60), 3)


def calculate_early_reflection_delay_ms(
    volume_m3: float,
    speed_of_sound_mps: float = SPEED_OF_SOUND_MPS,
) -> float:
    """Estimates the arrival time of the first prominent early specular reflection."""
    char_dim_m = max(1.0, volume_m3 ** (1.0 / 3.0))
    delay_ms = (char_dim_m * 1.2 / speed_of_sound_mps) * 1000.0
    return round(float(delay_ms), 1)


def calculate_ambisonic_b_format(
    azimuth_deg: float,
    elevation_deg: float,
) -> Dict[str, float]:
    """Encodes a 3D direction into 1st-Order Ambisonic B-format spherical harmonics (W, X, Y, Z).

    W: Omnidirectional pressure = 1 / sqrt(2)
    X: Front-Back velocity = cos(theta) * cos(phi)
    Y: Left-Right velocity = sin(theta) * cos(phi)
    Z: Up-Down velocity = sin(phi)
    """
    theta = math.radians(azimuth_deg)
    phi = math.radians(elevation_deg)

    w = 1.0 / math.sqrt(2.0)
    x = math.cos(theta) * math.cos(phi)
    y = math.sin(theta) * math.cos(phi)
    z = math.sin(phi)

    return {
        "W": round(w, 4),
        "X": round(x, 4),
        "Y": round(y, 4),
        "Z": round(z, 4),
    }


calculate_ambisonic_b_format_weights = calculate_ambisonic_b_format


def calculate_vbap_gains_7_1_4(coord: SpatialCoordinate3D) -> Dict[str, float]:
    """Calculates 3D Vector Base Amplitude Panning (VBAP) gains across Dolby Atmos 7.1.4 bed."""
    # Convert source spherical coordinates to unit Cartesian vector
    # Coordinate system: +Y = Front, +X = Right, +Z = Up
    theta = math.radians(coord.azimuth_deg)
    phi = math.radians(coord.elevation_deg)

    sx = math.sin(theta) * math.cos(phi)
    sy = math.cos(theta) * math.cos(phi)
    sz = math.sin(phi)

    gains: Dict[str, float] = {}
    sum_sq = 0.0

    for ch_name, (spk_az, spk_el) in ATMOS_7_1_4_SPEAKER_GEOMETRY.items():
        spk_theta = math.radians(spk_az)
        spk_phi = math.radians(spk_el)

        px = math.sin(spk_theta) * math.cos(spk_phi)
        py = math.cos(spk_theta) * math.cos(spk_phi)
        pz = math.sin(spk_phi)

        dot = sx * px + sy * py + sz * pz
        # Directional sharpness exponent
        gain_raw = max(0.0, dot) ** 3.0
        gains[ch_name] = gain_raw
        sum_sq += gain_raw * gain_raw

    # Energy normalization across bed speakers
    norm_factor = math.sqrt(sum_sq) if sum_sq > 1e-6 else 1.0
    for ch_name in gains:
        gains[ch_name] = round(gains[ch_name] / norm_factor, 4)

    # Subwoofer LFE channel (discrete send)
    gains["LFE"] = 0.05
    return gains


def export_dolby_atmos_adm_manifest(
    spec: SpatialAudioSoundfieldSpec,
    project_title: str = "Omni Production",
) -> Dict[str, Any]:
    """Generates an Audio Definition Model (ADM / ITU-R BS.2076) spatial audio manifest."""
    audio_objects_meta: List[Dict[str, Any]] = []

    for obj in spec.audio_objects:
        b_format = calculate_ambisonic_b_format(
            obj.initial_position.azimuth_deg,
            obj.initial_position.elevation_deg,
        )
        vbap = calculate_vbap_gains_7_1_4(obj.initial_position)

        audio_objects_meta.append({
            "audioObjectID": obj.object_id,
            "audioObjectName": obj.label or obj.object_id,
            "stemType": obj.stem_type.value if hasattr(obj.stem_type, "value") else str(obj.stem_type),
            "position": {
                "azimuth": obj.initial_position.azimuth_deg,
                "elevation": obj.initial_position.elevation_deg,
                "distance": obj.initial_position.distance_meters,
                "spread": obj.initial_position.spread_deg,
            },
            "trajectoryWaypointsCount": len(obj.trajectory_waypoints),
            "lfeSendDb": obj.lfe_send_db,
            "directivityConeDeg": obj.directivity_cone_deg,
            "ambisonicBFormat": b_format,
            "vbapBedGains": vbap,
        })

    return {
        "admVersion": "ITU-R BS.2076-2",
        "projectTitle": project_title,
        "soundfieldBedFormat": spec.bed_format.value if hasattr(spec.bed_format, "value") else str(spec.bed_format),
        "binauralRendering": spec.binaural_rendering_enabled,
        "audioObjects": audio_objects_meta,
        "acoustics": {
            "roomVolumeM3": spec.room_acoustics.room_volume_m3,
            "surfaceAreaM2": spec.room_acoustics.surface_area_m2,
            "rt60DecaySec": spec.room_acoustics.rt60_decay_sec,
            "earlyReflectionsMs": spec.room_acoustics.early_reflections_ms,
            "wallMaterial": spec.room_acoustics.wall_material.value if hasattr(spec.room_acoustics.wall_material, "value") else str(spec.room_acoustics.wall_material),
            "airAbsorptionHfDbPerM": spec.room_acoustics.air_absorption_hf_db_per_m,
        },
        "audioProgramme": {
            "programmeName": f"{project_title} Spatial Master",
            "audioContents": [
                {
                    "contentName": "Master Spatial Mix",
                    "audioObjects": audio_objects_meta,
                }
            ],
        },
    }


def export_ambisonic_panning_table(spec: SpatialAudioSoundfieldSpec) -> str:
    """Exports Ambisonic B-format spatial panning table as standard CSV."""
    rows = [
        "object_id,stem_type,label,azimuth_deg,elevation_deg,distance_m,spread_deg,W,X,Y,Z"
    ]

    for obj in spec.audio_objects:
        pos = obj.initial_position
        b_fmt = calculate_ambisonic_b_format(pos.azimuth_deg, pos.elevation_deg)
        stem_str = obj.stem_type.value if hasattr(obj.stem_type, "value") else str(obj.stem_type)
        label_clean = (obj.label or obj.object_id).replace(",", ";")
        rows.append(
            f"{obj.object_id},{stem_str},{label_clean},{pos.azimuth_deg:.1f},{pos.elevation_deg:.1f},"
            f"{pos.distance_meters:.2f},{pos.spread_deg:.1f},{b_fmt['W']:.4f},{b_fmt['X']:.4f},{b_fmt['Y']:.4f},{b_fmt['Z']:.4f}"
        )

    return "\n".join(rows) + "\n"


def export_webaudio_spatial_config(spec: SpatialAudioSoundfieldSpec) -> Dict[str, Any]:
    """Exports Web Audio API PannerNode and ConvolverNode configuration parameters."""
    panner_nodes: List[Dict[str, Any]] = []

    for obj in spec.audio_objects:
        pos = obj.initial_position
        theta = math.radians(pos.azimuth_deg)
        phi = math.radians(pos.elevation_deg)
        d = pos.distance_meters

        # Web Audio Cartesian: +X Right, +Y Up, +Z Back (towards listener)
        # In listener-relative space, 0 deg front = -Z
        x = d * math.sin(theta) * math.cos(phi)
        y = d * math.sin(phi)
        z = -d * math.cos(theta) * math.cos(phi)

        panner_nodes.append({
            "nodeId": f"panner_{obj.object_id}",
            "objectId": obj.object_id,
            "panningModel": "HRTF" if spec.binaural_rendering_enabled else "equalpower",
            "distanceModel": "inverse",
            "refDistance": 1.0,
            "maxDistance": 50.0,
            "rolloffFactor": 1.0,
            "coneInnerAngle": obj.directivity_cone_deg * 0.5,
            "coneOuterAngle": obj.directivity_cone_deg,
            "coneOuterGain": 0.2,
            "position": {
                "x": round(x, 4),
                "y": round(y, 4),
                "z": round(z, 4),
            },
            "orientation": {
                "x": 0.0,
                "y": 0.0,
                "z": 1.0,
            },
        })

    return {
        "panningModel": "HRTF" if spec.binaural_rendering_enabled else "equalpower",
        "audioContextSampleRate": 48000,
        "listener": {
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "forward": {"x": 0.0, "y": 0.0, "z": -1.0},
            "up": {"x": 0.0, "y": 1.0, "z": 0.0},
        },
        "convolverReverb": {
            "rt60Seconds": spec.room_acoustics.rt60_decay_sec,
            "earlyReflectionsMs": spec.room_acoustics.early_reflections_ms,
            "wallMaterial": spec.room_acoustics.wall_material.value if hasattr(spec.room_acoustics.wall_material, "value") else str(spec.room_acoustics.wall_material),
            "wetDryRatio": 0.25,
        },
        "pannerNodes": panner_nodes,
    }


def format_spatial_audio_prompt_token(spec: SpatialAudioSoundfieldSpec) -> str:
    """Formats an audited cinematic spatial audio prompt token for Gemini Omni."""
    bed_name = spec.bed_format.value if hasattr(spec.bed_format, "value") else str(spec.bed_format)
    mat_name = spec.room_acoustics.wall_material.value if hasattr(spec.room_acoustics.wall_material, "value") else str(spec.room_acoustics.wall_material)
    rt60 = spec.room_acoustics.rt60_decay_sec

    obj_tokens = []
    for obj in spec.audio_objects[:3]:
        pos = obj.initial_position
        obj_tokens.append(f"{obj.object_id} (az:{pos.azimuth_deg:+.0f}°, el:{pos.elevation_deg:+.0f}°, {pos.distance_meters:.1f}m)")

    obj_summary = "; ".join(obj_tokens) if obj_tokens else "surround diffuse"
    binaural_tag = "Binaural HRTF" if spec.binaural_rendering_enabled else "Stereo Folddown"

    return f"[SPATIAL AUDIO: {bed_name.replace('_', ' ').title()}, RT60={rt60:.2f}s ({mat_name.replace('_', ' ').title()}), Objects: {obj_summary}, {binaural_tag}]"


def export_spatial_audio_bundle(
    spec_or_bible: Union[SpatialAudioSoundfieldSpec, Any],
    output_dir: Union[str, Path],
    project_title: str = "Omni Production",
) -> Dict[str, str]:
    """Exports all spatial audio artifacts into the target directory."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if hasattr(spec_or_bible, "master_spatial_audio"):
        spec = spec_or_bible.master_spatial_audio or synthesize_default_spatial_audio(spec_or_bible)
        project_title = getattr(spec_or_bible, "project_title", project_title)
    else:
        spec = spec_or_bible

    results: Dict[str, str] = {}

    # 1. ADM Manifest JSON
    adm_data = export_dolby_atmos_adm_manifest(spec, project_title=project_title)
    adm_path = out_path / "spatial_audio_adm_manifest.json"
    adm_path.write_text(json.dumps(adm_data, indent=2), encoding="utf-8")
    results["spatial_audio_adm_manifest.json"] = str(adm_path)
    (out_path / "spatial_audio_adm.json").write_text(json.dumps(adm_data, indent=2), encoding="utf-8")
    results["spatial_audio_adm.json"] = str(out_path / "spatial_audio_adm.json")

    # 2. Ambisonic CSV
    amb_csv = export_ambisonic_panning_table(spec)
    amb_path = out_path / "spatial_audio_ambisonic_channels.csv"
    amb_path.write_text(amb_csv, encoding="utf-8")
    results["spatial_audio_ambisonic_channels.csv"] = str(amb_path)
    (out_path / "ambisonic_b_format.csv").write_text(amb_csv, encoding="utf-8")
    results["ambisonic_b_format.csv"] = str(out_path / "ambisonic_b_format.csv")

    # 3. Web Audio JSON Config
    webaudio_data = export_webaudio_spatial_config(spec)
    wa_path = out_path / "spatial_webaudio_nodes.json"
    wa_path.write_text(json.dumps(webaudio_data, indent=2), encoding="utf-8")
    results["spatial_webaudio_nodes.json"] = str(wa_path)
    (out_path / "webaudio_spatial_panner.json").write_text(json.dumps(webaudio_data, indent=2), encoding="utf-8")
    results["webaudio_spatial_panner.json"] = str(out_path / "webaudio_spatial_panner.json")

    return results


calculate_vbap_714_gains = calculate_vbap_gains_7_1_4
export_adm_spatial_json = export_dolby_atmos_adm_manifest
export_ambisonic_track_csv = export_ambisonic_panning_table
export_web_audio_spatial_config = export_webaudio_spatial_config


def synthesize_default_spatial_audio(bible: Any = None) -> SpatialAudioSoundfieldSpec:
    """Synthesizes default spatial audio specification based on project domain."""
    from omni_director.presets import get_domain_spatial_audio_spec
    archetype = getattr(bible, "domain_archetype", "kinetic_action") if bible else "kinetic_action"
    if hasattr(archetype, "value"):
        archetype = archetype.value
    return get_domain_spatial_audio_spec(archetype)
