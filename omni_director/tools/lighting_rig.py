"""Volumetric Atmospheric & Studio Lighting Rig Simulator (PM-FEAT-010).

Provides photometric calculations for multi-fixture studio lighting setups (Key-to-Fill
contrast ratio, Key-to-Rim separation ratio, total incident scene Lux, CCT Kelvin deltas),
cinematic lighting prompt token synthesis, and post-production export of lighting plots
(JSON) and gaffer equipment call sheets (CSV).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    AtmosphericHazeSpec,
    DiffusionGrade,
    LightingFixtureRole,
    LightingRigSpec,
    MasterProductionBible,
    ParticulateHazeType,
    StudioLightFixtureSpec,
)


def synthesize_default_lighting_rig(
    style: str = "cinematic_commercial",
) -> LightingRigSpec:
    """Synthesizes a standardized calibrated multi-fixture studio lighting rig."""
    fixtures = [
        StudioLightFixtureSpec(
            fixture_id="KEY_01",
            role=LightingFixtureRole.KEY_LIGHT,
            fixture_type="ARRI SkyPanel S360-C",
            cct_kelvin=5600,
            lux_intensity=3500.0,
            beam_angle_deg=45.0,
            diffusion_grade=DiffusionGrade.HALF_GRID,
            distance_meters=3.5,
            dmx_channel=1,
        ),
        StudioLightFixtureSpec(
            fixture_id="FILL_01",
            role=LightingFixtureRole.FILL_LIGHT,
            fixture_type="ARRI SkyPanel S120-C",
            cct_kelvin=5200,
            lux_intensity=875.0,
            beam_angle_deg=60.0,
            diffusion_grade=DiffusionGrade.BLEACHED_MUSLIN,
            distance_meters=4.0,
            dmx_channel=16,
        ),
        StudioLightFixtureSpec(
            fixture_id="RIM_01",
            role=LightingFixtureRole.RIM_BACKLIGHT,
            fixture_type="Astera Titan Tube FP1",
            cct_kelvin=6000,
            lux_intensity=1750.0,
            beam_angle_deg=30.0,
            diffusion_grade=DiffusionGrade.QUARTER_GRID,
            distance_meters=2.5,
            dmx_channel=32,
        ),
        StudioLightFixtureSpec(
            fixture_id="KICKER_01",
            role=LightingFixtureRole.KICKER,
            fixture_type="Dedolight DLED9-BI",
            cct_kelvin=5600,
            lux_intensity=1200.0,
            beam_angle_deg=20.0,
            diffusion_grade=DiffusionGrade.HARD_SPECULAR,
            distance_meters=3.0,
            dmx_channel=48,
        ),
        StudioLightFixtureSpec(
            fixture_id="AMBIENT_01",
            role=LightingFixtureRole.OVERHEAD_AMBIENT,
            fixture_type="LiteMat Plus 4",
            cct_kelvin=5600,
            lux_intensity=500.0,
            beam_angle_deg=90.0,
            diffusion_grade=DiffusionGrade.CHIMERA_SOFTBOX,
            distance_meters=4.5,
            dmx_channel=64,
        ),
    ]

    haze = AtmosphericHazeSpec(
        haze_type=ParticulateHazeType.MINERAL_HAZE,
        particulate_density=0.15,
        scattering_coefficient=0.45,
        shaft_visibility=0.6,
    )

    return LightingRigSpec(
        fixtures=fixtures,
        key_to_fill_ratio=4.0,
        key_to_rim_ratio=2.0,
        total_lux=7825.0,
        atmospheric_haze=haze,
    )


def calculate_key_to_fill_ratio(rig: LightingRigSpec) -> float:
    """Calculates Key-to-Fill photometric contrast ratio (Key Lux / Fill Lux)."""
    if not rig.fixtures:
        return round(rig.key_to_fill_ratio, 2)

    key_lux = sum(
        f.lux_intensity
        for f in rig.fixtures
        if f.role == LightingFixtureRole.KEY_LIGHT or "key" in str(f.role).lower()
    )
    fill_lux = sum(
        f.lux_intensity
        for f in rig.fixtures
        if f.role == LightingFixtureRole.FILL_LIGHT or "fill" in str(f.role).lower()
    )

    if fill_lux > 0:
        return round(key_lux / fill_lux, 2)
    if key_lux > 0:
        return round(key_lux, 2)
    return round(rig.key_to_fill_ratio, 2)


def calculate_key_to_rim_ratio(rig: LightingRigSpec) -> float:
    """Calculates Key-to-Rim photometric accent ratio (Key Lux / Rim Lux)."""
    if not rig.fixtures:
        return round(rig.key_to_rim_ratio, 2)

    key_lux = sum(
        f.lux_intensity
        for f in rig.fixtures
        if f.role == LightingFixtureRole.KEY_LIGHT or "key" in str(f.role).lower()
    )
    rim_lux = sum(
        f.lux_intensity
        for f in rig.fixtures
        if f.role == LightingFixtureRole.RIM_BACKLIGHT or "rim" in str(f.role).lower()
    )

    if rim_lux > 0:
        return round(key_lux / rim_lux, 2)
    if key_lux > 0:
        return round(key_lux, 2)
    return round(rig.key_to_rim_ratio, 2)


def calculate_total_lux(rig: LightingRigSpec) -> float:
    """Calculates total scene incident illuminance in Lux."""
    if not rig.fixtures:
        return round(rig.total_lux, 1)
    tot = sum(f.lux_intensity for f in rig.fixtures)
    return round(tot, 1)


def calculate_cct_deltas(rig: LightingRigSpec) -> Dict[str, Any]:
    """Calculates CCT Kelvin deltas and range across active lighting fixtures."""
    if not rig.fixtures:
        return {
            "min_kelvin": 5600,
            "max_kelvin": 5600,
            "delta_kelvin": 0,
            "key_fill_delta_kelvin": 0,
        }

    ccts = [f.cct_kelvin for f in rig.fixtures]
    min_k = min(ccts)
    max_k = max(ccts)

    key_cct = next(
        (f.cct_kelvin for f in rig.fixtures if f.role == LightingFixtureRole.KEY_LIGHT or "key" in str(f.role).lower()),
        5600,
    )
    fill_cct = next(
        (f.cct_kelvin for f in rig.fixtures if f.role == LightingFixtureRole.FILL_LIGHT or "fill" in str(f.role).lower()),
        key_cct,
    )

    deltas: Dict[str, Any] = {
        "min_kelvin": min_k,
        "max_kelvin": max_k,
        "delta_kelvin": max_k - min_k,
        "key_fill_delta_kelvin": abs(key_cct - fill_cct),
    }
    for f in rig.fixtures:
        deltas[f.fixture_id] = f.cct_kelvin - key_cct

    return deltas


def calculate_lighting_photometrics(rig: LightingRigSpec) -> Dict[str, Any]:
    """Computes comprehensive photometric parameters for a studio lighting rig."""
    return {
        "key_to_fill_ratio": calculate_key_to_fill_ratio(rig),
        "key_to_rim_ratio": calculate_key_to_rim_ratio(rig),
        "total_lux": calculate_total_lux(rig),
        "cct_deltas": calculate_cct_deltas(rig),
        "fixture_count": len(rig.fixtures),
    }


def format_lighting_prompt_token(rig: LightingRigSpec) -> str:
    """Synthesizes a calibrated studio lighting and atmospheric prompt token."""
    kf = calculate_key_to_fill_ratio(rig)
    kr = calculate_key_to_rim_ratio(rig)
    tot_lux = calculate_total_lux(rig)
    cct_info = calculate_cct_deltas(rig)

    haze_str = ""
    if rig.atmospheric_haze:
        ht = (
            rig.atmospheric_haze.haze_type.value
            if hasattr(rig.atmospheric_haze.haze_type, "value")
            else str(rig.atmospheric_haze.haze_type)
        )
        haze_str = f", volumetric {ht} optical scattering"

    return (
        f"Calibrated studio lighting: Key:Fill {kf:.1f}:1 contrast ratio, "
        f"Key:Rim {kr:.1f}:1 separation, {tot_lux:.0f} Lux aggregate illuminance, "
        f"CCT {cct_info['min_kelvin']}K-{cct_info['max_kelvin']}K balance{haze_str}"
    )


def _resolve_bible_lighting_rig(bible: MasterProductionBible) -> LightingRigSpec:
    """Extracts master or scene lighting rig from bible, or synthesizes a standardized default."""
    rig = bible.master_lighting_rig
    if rig is None:
        for s in bible.scenes:
            if s.lighting_rig:
                rig = s.lighting_rig
                break
    if rig is None:
        rig = synthesize_default_lighting_rig(f"{bible.project_title} Lighting")
    return rig


def export_lighting_plot_json(
    bible: MasterProductionBible,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Exports photometric lighting plot and fixtures breakdown as JSON."""
    master_rig = _resolve_bible_lighting_rig(bible)
    photometrics = calculate_lighting_photometrics(master_rig)

    fixtures_data = []
    for f in master_rig.fixtures:
        fixtures_data.append(
            {
                "fixture_id": f.fixture_id,
                "role": f.role.value if hasattr(f.role, "value") else str(f.role),
                "fixture_type": f.fixture_type,
                "cct_kelvin": f.cct_kelvin,
                "lux_intensity": f.lux_intensity,
                "beam_angle_deg": f.beam_angle_deg,
                "diffusion_grade": f.diffusion_grade.value if hasattr(f.diffusion_grade, "value") else str(f.diffusion_grade),
                "distance_meters": f.distance_meters,
                "dmx_channel": f.dmx_channel,
            }
        )

    haze_data = None
    if master_rig.atmospheric_haze:
        hz = master_rig.atmospheric_haze
        haze_data = {
            "haze_type": hz.haze_type.value if hasattr(hz.haze_type, "value") else str(hz.haze_type),
            "particulate_density": hz.particulate_density,
            "scattering_coefficient": hz.scattering_coefficient,
            "shaft_visibility": hz.shaft_visibility,
        }

    scenes_data = []
    for s in bible.scenes:
        sc_rig = s.lighting_rig or master_rig
        scenes_data.append(
            {
                "scene_index": s.scene_index,
                "scene_title": s.scene_title,
                "timestamp_range": s.timestamp_range,
                "photometrics": calculate_lighting_photometrics(sc_rig),
                "fixtures_count": len(sc_rig.fixtures),
            }
        )

    master_dict = {
        "photometrics": photometrics,
        "fixtures": fixtures_data,
        "atmospheric_haze": haze_data,
    }

    plot = {
        "project_title": bible.project_title,
        "master_lighting_rig": master_dict,
        "lighting_rig": master_dict,
        "scenes": scenes_data,
    }

    json_str = json.dumps(plot, indent=2)
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json_str, encoding="utf-8")
    return json_str


def export_gaffer_callsheet_csv(
    bible: MasterProductionBible,
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """Exports Gaffer & Electric lighting fixture schedule as CSV."""
    master_rig = _resolve_bible_lighting_rig(bible)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "scene_index",
            "scene_title",
            "fixture_id",
            "role",
            "fixture_type",
            "cct_kelvin",
            "lux_intensity",
            "beam_angle_deg",
            "diffusion_grade",
            "distance_meters",
            "dmx_channel",
        ]
    )

    for s in bible.scenes:
        sc_rig = s.lighting_rig or master_rig
        for fix in sc_rig.fixtures:
            role_str = fix.role.value if hasattr(fix.role, "value") else str(fix.role)
            diff_str = fix.diffusion_grade.value if hasattr(fix.diffusion_grade, "value") else str(fix.diffusion_grade)
            writer.writerow(
                [
                    s.scene_index,
                    s.scene_title,
                    fix.fixture_id,
                    role_str,
                    fix.fixture_type,
                    fix.cct_kelvin,
                    fix.lux_intensity,
                    fix.beam_angle_deg,
                    diff_str,
                    fix.distance_meters,
                    fix.dmx_channel,
                ]
            )

    csv_str = buffer.getvalue()
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(csv_str, encoding="utf-8")
    return csv_str


def export_lighting_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports all Studio Lighting manifests (plot JSON, gaffer CSV) to output_dir."""
    out_p = Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    plot_p = out_p / "studio_lighting_plot.json"
    gaffer_p = out_p / "gaffer_call_sheet.csv"

    export_lighting_plot_json(bible, plot_p)
    export_gaffer_callsheet_csv(bible, gaffer_p)

    # Also create aliases
    (out_p / "lighting_plot.json").write_text(plot_p.read_text(encoding="utf-8"), encoding="utf-8")
    (out_p / "gaffer_callsheet.csv").write_text(gaffer_p.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "json": str(plot_p.resolve()),
        "callsheet_csv": str(gaffer_p.resolve()),
        "lighting_json": str(plot_p.resolve()),
        "gaffer_csv": str(gaffer_p.resolve()),
        "lighting": str(plot_p.resolve()),
    }
