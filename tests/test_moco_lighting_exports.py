"""Unit tests for MoCo Kinematics (PM-FEAT-009) and Lighting Rig Simulator (PM-FEAT-010) exports."""

from pathlib import Path
import json
import pytest

from omni_director.schemas import (
    DiffusionGrade,
    LightingFixtureRole,
    LightingRigSpec,
    MocoRigSpec,
    MotionControlRigType,
    ParticulateHazeType,
    StudioLightFixtureSpec,
    TrajectoryWaypoint6DOF,
)
from omni_director.presets import IKEA_ASMR_BIBLE
from omni_director.tools.moco_kinematics import (
    calculate_mean_acceleration,
    calculate_peak_velocity,
    calculate_trajectory_distance,
    export_moco_bundle,
    export_moco_fbx_ascii,
    export_moco_track_csv,
    export_moco_track_json,
    format_moco_prompt_token,
    interpolate_waypoints_6dof,
    synthesize_default_moco_rig,
)
from omni_director.tools.lighting_rig import (
    calculate_cct_deltas,
    calculate_key_to_fill_ratio,
    calculate_key_to_rim_ratio,
    calculate_lighting_photometrics,
    calculate_total_lux,
    export_gaffer_callsheet_csv,
    export_lighting_bundle,
    export_lighting_plot_json,
    format_lighting_prompt_token,
    synthesize_default_lighting_rig,
)
from omni_director.tools.nle_export import export_all_nle_artifacts
from omni_director.cli import main as cli_main


class TestMocoKinematicsSuite:
    def test_default_moco_rig_synthesis(self):
        rig = synthesize_default_moco_rig()
        assert rig.rig_type == MotionControlRigType.BOLT_CINEBOT
        assert len(rig.waypoints) == 5
        assert rig.track_length_meters == 6.0
        assert rig.max_velocity_mps == 4.5
        assert rig.locked_roll_stabilization is True

    def test_trajectory_distance_and_velocity_calculations(self):
        wps = [
            TrajectoryWaypoint6DOF(timecode_sec=0.0, x_meters=0.0, y_meters=0.0, z_meters=1.0, velocity_mps=0.0),
            TrajectoryWaypoint6DOF(timecode_sec=2.0, x_meters=3.0, y_meters=4.0, z_meters=1.0, velocity_mps=2.5),
            TrajectoryWaypoint6DOF(timecode_sec=4.0, x_meters=3.0, y_meters=4.0, z_meters=3.0, velocity_mps=1.0),
        ]
        # Leg 1: dx=3, dy=4, dz=0 => dist=5.0 m. dt=2.0s => avg v=2.5 m/s.
        # Leg 2: dx=0, dy=0, dz=2 => dist=2.0 m. dt=2.0s => avg v=1.0 m/s.
        # Total distance = 7.0 m
        dist = calculate_trajectory_distance(wps)
        assert dist == 7.0

        peak_v = calculate_peak_velocity(wps)
        assert peak_v == 2.5

        mean_a = calculate_mean_acceleration(wps)
        # dv1 = |2.5 - 0.0| = 2.5, dt=2.0 => 1.25 m/s²
        # dv2 = |1.0 - 2.5| = 1.5, dt=2.0 => 0.75 m/s²
        # mean a = (1.25 + 0.75) / 2 = 1.0 m/s²
        assert mean_a == 1.0

    def test_interpolate_waypoints_6dof(self):
        wps = [
            TrajectoryWaypoint6DOF(timecode_sec=0.0, x_meters=0.0, y_meters=0.0, z_meters=1.0, yaw_deg=0.0),
            TrajectoryWaypoint6DOF(timecode_sec=1.0, x_meters=10.0, y_meters=20.0, z_meters=3.0, yaw_deg=90.0),
        ]
        sampled = interpolate_waypoints_6dof(wps, sample_rate_hz=24.0)
        assert len(sampled) >= 24
        # Midpoint around frame 12 (0.5s)
        mid = sampled[12]
        assert pytest.approx(mid.timecode_sec, abs=0.05) == 0.5
        assert pytest.approx(mid.x_meters, abs=0.5) == 5.0
        assert pytest.approx(mid.y_meters, abs=1.0) == 10.0
        assert pytest.approx(mid.yaw_deg, abs=5.0) == 45.0

    def test_format_moco_prompt_token(self):
        rig = synthesize_default_moco_rig()
        token = format_moco_prompt_token(rig)
        assert "Robotic MoCo camera move on bolt_cinebot" in token
        assert "6-DOF precision track length" in token
        assert "peak velocity" in token
        assert "repeatability ±0.05mm" in token
        assert "stabilized 3-axis horizon lock" in token

    def test_export_moco_bundle(self, tmp_path):
        bible = IKEA_ASMR_BIBLE.model_copy(deep=True)
        bible.master_moco_rig = synthesize_default_moco_rig()

        bundle_files = export_moco_bundle(bible, tmp_path)
        assert "moco_json" in bundle_files
        assert "moco_csv" in bundle_files
        assert "moco_fbx" in bundle_files

        json_p = Path(bundle_files["moco_json"])
        csv_p = Path(bundle_files["moco_csv"])
        fbx_p = Path(bundle_files["moco_fbx"])

        assert json_p.exists() and json_p.stat().st_size > 0
        assert csv_p.exists() and csv_p.stat().st_size > 0
        assert fbx_p.exists() and fbx_p.stat().st_size > 0

        # Validate JSON content
        data = json.loads(json_p.read_text(encoding="utf-8"))
        assert "master_moco_rig" in data
        assert "summary_kinematics" in data["master_moco_rig"]
        assert len(data["scenes"]) == len(bible.scenes)

        # Validate CSV content
        csv_content = csv_p.read_text(encoding="utf-8")
        assert "scene_index,scene_title,timecode_sec" in csv_content

        # Validate FBX content
        fbx_content = fbx_p.read_text(encoding="utf-8")
        assert "FBXHeaderExtension" in fbx_content
        assert "Model::MoCo_Camera_Rig" in fbx_content


class TestLightingRigSuite:
    def test_default_lighting_rig_synthesis(self):
        rig = synthesize_default_lighting_rig()
        assert len(rig.fixtures) == 5
        assert rig.atmospheric_haze is not None
        assert rig.atmospheric_haze.haze_type == ParticulateHazeType.MINERAL_HAZE

    def test_photometric_calculations(self):
        fixtures = [
            StudioLightFixtureSpec(
                fixture_id="KEY",
                role=LightingFixtureRole.KEY_LIGHT,
                lux_intensity=4000.0,
                cct_kelvin=5600,
            ),
            StudioLightFixtureSpec(
                fixture_id="FILL",
                role=LightingFixtureRole.FILL_LIGHT,
                lux_intensity=1000.0,
                cct_kelvin=5200,
            ),
            StudioLightFixtureSpec(
                fixture_id="RIM",
                role=LightingFixtureRole.RIM_BACKLIGHT,
                lux_intensity=2000.0,
                cct_kelvin=6000,
            ),
        ]
        rig = LightingRigSpec(fixtures=fixtures)

        kf = calculate_key_to_fill_ratio(rig)
        assert kf == 4.0  # 4000 / 1000 = 4:1

        kr = calculate_key_to_rim_ratio(rig)
        assert kr == 2.0  # 4000 / 2000 = 2:1

        tot_lux = calculate_total_lux(rig)
        assert tot_lux == 7000.0  # 4000 + 1000 + 2000

        cct = calculate_cct_deltas(rig)
        assert cct["min_kelvin"] == 5200
        assert cct["max_kelvin"] == 6000
        assert cct["delta_kelvin"] == 800
        assert cct["key_fill_delta_kelvin"] == 400

        metrics = calculate_lighting_photometrics(rig)
        assert metrics["key_to_fill_ratio"] == 4.0
        assert metrics["key_to_rim_ratio"] == 2.0
        assert metrics["total_lux"] == 7000.0

    def test_format_lighting_prompt_token(self):
        rig = synthesize_default_lighting_rig()
        token = format_lighting_prompt_token(rig)
        assert "Calibrated studio lighting" in token
        assert "Key:Fill 4.0:1 contrast ratio" in token
        assert "Key:Rim 2.0:1 separation" in token
        assert "Lux aggregate illuminance" in token
        assert "mineral_haze" in token

    def test_export_lighting_bundle(self, tmp_path):
        bible = IKEA_ASMR_BIBLE.model_copy(deep=True)
        bible.master_lighting_rig = synthesize_default_lighting_rig()

        bundle_files = export_lighting_bundle(bible, tmp_path)
        assert "lighting_json" in bundle_files
        assert "gaffer_csv" in bundle_files

        json_p = Path(bundle_files["lighting_json"])
        csv_p = Path(bundle_files["gaffer_csv"])

        assert json_p.exists() and json_p.stat().st_size > 0
        assert csv_p.exists() and csv_p.stat().st_size > 0

        data = json.loads(json_p.read_text(encoding="utf-8"))
        assert "master_lighting_rig" in data
        assert "photometrics" in data["master_lighting_rig"]
        assert len(data["master_lighting_rig"]["fixtures"]) == 5

        csv_content = csv_p.read_text(encoding="utf-8")
        assert "scene_index,scene_title,fixture_id,role" in csv_content
        assert "KEY_01" in csv_content


class TestNLEAndCLIIntegration:
    def test_export_all_nle_artifacts_includes_moco_and_lighting(self, tmp_path):
        bible = IKEA_ASMR_BIBLE.model_copy(deep=True)
        bible.master_moco_rig = synthesize_default_moco_rig()
        bible.master_lighting_rig = synthesize_default_lighting_rig()

        res = export_all_nle_artifacts(bible, tmp_path)
        assert "edl" in res
        assert "fcpxml" in res
        assert "csv" in res
        assert "call_sheet" in res
        assert "moco_json" in res
        assert "moco_csv" in res
        assert "moco_fbx" in res
        assert "lighting_json" in res
        assert "gaffer_csv" in res

    def test_cli_export_moco_and_lighting(self, tmp_path):
        out_dir = tmp_path / "cli_out"

        # Test moco format
        ret = cli_main(["export", "--preset", "ikea-asmr", "--format", "moco", "-o", str(out_dir)])
        assert ret == 0
        assert (out_dir / "moco_track.json").exists()
        assert (out_dir / "moco_track.csv").exists()
        assert (out_dir / "moco_camera.fbx").exists()

        # Test lighting format
        ret = cli_main(["export", "--preset", "ikea-asmr", "--format", "lighting", "-o", str(out_dir)])
        assert ret == 0
        assert (out_dir / "lighting_plot.json").exists()
        assert (out_dir / "gaffer_callsheet.csv").exists()

        # Test all format includes moco and lighting
        ret = cli_main(["export", "--preset", "ikea-asmr", "--format", "all", "-o", str(out_dir)])
        assert ret == 0
        assert (out_dir / "timeline.edl").exists()
        assert (out_dir / "moco_track.json").exists()
        assert (out_dir / "lighting_plot.json").exists()
