"""Virtual Production LED Volume & Unreal Engine Stage Manifest / In-Camera VFX Suite (PM-FEAT-008).

Provides tools for synthesizing StageCraft LED volumes, compiling Unreal Engine 5.4+
nDisplay stage configuration manifests, formatting DMX512 intelligent lighting patch
schedules, and packaging full Virtual Production production bundles.
"""

import csv
import io
import json
from pathlib import Path
from typing import Dict, Union

from omni_director.schemas import (
    DmxLightingFixture,
    LedWallGeometry,
    MasterProductionBible,
    VirtualProductionStageSpec,
)


def synthesize_default_vp_stage(stage_name: str = "StageCraft Volume Alpha") -> VirtualProductionStageSpec:
    """Synthesizes a standardized industrial Virtual Production volume stage specification."""
    fixtures = [
        DmxLightingFixture(
            fixture_id="KEY_SKY_01",
            fixture_type="Arri SkyPanel S360-C",
            dmx_universe=1,
            dmx_channel_start=1,
            intensity_percent=85.0,
            color_temp_kelvin=5600,
            gel_tint_cie_xy=(0.3127, 0.3290),
        ),
        DmxLightingFixture(
            fixture_id="FILL_SKY_02",
            fixture_type="Arri SkyPanel S120-C",
            dmx_universe=1,
            dmx_channel_start=16,
            intensity_percent=55.0,
            color_temp_kelvin=5200,
            gel_tint_cie_xy=(0.3150, 0.3320),
        ),
        DmxLightingFixture(
            fixture_id="RIM_ASTERA_01",
            fixture_type="Astera Titan Tube FP1",
            dmx_universe=2,
            dmx_channel_start=1,
            intensity_percent=70.0,
            color_temp_kelvin=6000,
            gel_tint_cie_xy=(0.3080, 0.3210),
        ),
        DmxLightingFixture(
            fixture_id="CEILING_LITEMAT_01",
            fixture_type="LiteMat Plus 4",
            dmx_universe=2,
            dmx_channel_start=32,
            intensity_percent=40.0,
            color_temp_kelvin=5600,
            gel_tint_cie_xy=(0.3127, 0.3290),
        ),
    ]

    return VirtualProductionStageSpec(
        stage_name=stage_name,
        led_wall=LedWallGeometry(),
        frustum_tracking_protocol="FreeD / OptiTrack Active Optical",
        ue_ndisplay_config_version="5.4",
        parallax_depth_planes={
            "foreground_prop_m": 1.5,
            "actor_stage_m": 3.5,
            "led_wall_m": 8.0,
            "virtual_bg_infinity_m": 500.0,
        },
        dmx_lighting_rig=fixtures,
        lut_calibration_profile="ACEScg_OCIO_v1.3",
    )


def export_ue_ndisplay_manifest(stage: VirtualProductionStageSpec) -> str:
    """Exports an Unreal Engine 5.4+ nDisplay cluster and projection stage configuration as JSON."""
    manifest = {
        "nDisplay": {
            "version": stage.ue_ndisplay_config_version,
            "stage_name": stage.stage_name,
            "cluster": {
                "master_node": {
                    "id": "Node_Primary_Controller",
                    "render_api": "DirectX12_D3D12RHI",
                    "sync_policy": "NVIDIA_Rivermax_PTP",
                },
                "render_nodes": [
                    {
                        "id": "Node_Inner_Frustum_01",
                        "gpu": "NVIDIA RTX 6000 Ada",
                        "display": "LED_Wall_Curved",
                    },
                    {
                        "id": "Node_Ceiling_Ambience_02",
                        "gpu": "NVIDIA RTX 6000 Ada",
                        "display": "LED_Ceiling_Panel",
                    },
                ],
            },
            "projection": {
                "geometry": {
                    "shape": stage.led_wall.shape,
                    "diameter_m": stage.led_wall.diameter_meters,
                    "height_m": stage.led_wall.height_meters,
                    "pixel_pitch_mm": stage.led_wall.pixel_pitch_mm,
                    "native_resolution": f"{stage.led_wall.resolution_width_px}x{stage.led_wall.resolution_height_px}",
                    "ceiling_active": stage.led_wall.has_ceiling_led,
                    "floor_active": stage.led_wall.has_floor_led,
                },
                "color_management": {
                    "ocio_config": stage.lut_calibration_profile,
                    "working_gamut": "ACEScg",
                    "display_gamut": "DCI-P3",
                },
            },
            "tracking": {
                "protocol": stage.frustum_tracking_protocol,
                "camera_subject": "Hero_Cinema_Camera",
                "latency_compensation_ms": 2.5,
                "lens_encoder": "Cooke_i_Data_Lens_Profile",
            },
            "parallax_depth_planes": stage.parallax_depth_planes,
        }
    }
    return json.dumps(manifest, indent=2)


def export_dmx_patch_csv(stage: VirtualProductionStageSpec) -> str:
    """Exports DMX512 intelligent lighting fixture patch list as CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "fixture_id",
            "fixture_type",
            "dmx_universe",
            "dmx_channel_start",
            "intensity_percent",
            "color_temp_kelvin",
            "cie_xy",
        ]
    )

    for fix in stage.dmx_lighting_rig:
        cie_str = (
            f"({fix.gel_tint_cie_xy[0]:.4f}, {fix.gel_tint_cie_xy[1]:.4f})"
            if fix.gel_tint_cie_xy
            else "D65"
        )
        writer.writerow(
            [
                fix.fixture_id,
                fix.fixture_type,
                fix.dmx_universe,
                fix.dmx_channel_start,
                fix.intensity_percent,
                fix.color_temp_kelvin,
                cie_str,
            ]
        )

    return buffer.getvalue()


def export_virtual_production_bundle(
    bible: MasterProductionBible,
    out_dir: Union[str, Path],
) -> Dict[str, str]:
    """Exports all Virtual Production manifests to out_dir and returns a file path dictionary."""
    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    stage = bible.virtual_production
    if stage is None:
        for s in bible.scenes:
            if s.virtual_production:
                stage = s.virtual_production
                break
    if stage is None:
        stage = synthesize_default_vp_stage(f"{bible.project_title} Volume")

    ndisplay_p = out_p / "ndisplay_stage_manifest.json"
    dmx_p = out_p / "dmx_patch.csv"
    stage_p = out_p / "vp_stage_spec.json"

    ndisplay_p.write_text(export_ue_ndisplay_manifest(stage), encoding="utf-8")
    dmx_p.write_text(export_dmx_patch_csv(stage), encoding="utf-8")
    stage_p.write_text(stage.model_dump_json(indent=2), encoding="utf-8")

    return {
        "ndisplay": str(ndisplay_p.resolve()),
        "dmx": str(dmx_p.resolve()),
        "stage_spec": str(stage_p.resolve()),
        "vp": str(ndisplay_p.resolve()),
    }
