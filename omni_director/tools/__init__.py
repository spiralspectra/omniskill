"""Tools module exports for omni-movie-director."""

from omni_director.tools.audio_mixer import (
    estimate_broadcast_loudness,
    export_audio_stems_file,
    export_audio_stems_manifest,
    synthesize_default_stem_mixer,
)
from omni_director.tools.color_grade import (
    cdl_to_svg_matrix_filter,
    embed_cdl_in_edl,
    export_asc_cdl_file,
    export_asc_cdl_xml,
    get_preset_color_look,
)
from omni_director.tools.coverage import (
    CoverageType,
    CoverageVariant,
    generate_scene_coverage,
    synthesize_conversational_deltas,
)
from omni_director.tools.dialogue import (
    audit_dialogue_pacing,
    compile_subtitles_srt,
    compile_subtitles_vtt,
)
from omni_director.tools.html_compiler import compile_storyboard_html
from omni_director.tools.nano_banana import (
    NanoBananaStoryboardEngine,
    generate_svg_storyboard_frame,
)
from omni_director.tools.nle_export import (
    export_all_nle_artifacts,
    export_cmx3600_edl,
    export_fcpxml,
    export_production_callsheet_md,
    export_shot_list_csv,
)
from omni_director.tools.omni_video import GeminiOmniVideoEngine
from omni_director.tools.optical_lens import (
    calculate_hyperfocal_distance,
    calculate_sensor_fov,
    export_lens_metadata_csv,
    export_lens_metadata_file,
    format_optical_prompt_token,
)
from omni_director.tools.prompt_auditor import (
    audit_omni_scene_prompt,
    heal_omni_scene_prompt,
)
from omni_director.tools.speed_ramp import (
    export_fcpxml_timemap,
    format_craft_shutter_tokens,
    synthesize_speed_ramp_curve,
)
from omni_director.tools.virtual_production import (
    export_dmx_patch_csv,
    export_ue_ndisplay_manifest,
    export_virtual_production_bundle,
    synthesize_default_vp_stage,
)
from omni_director.tools.moco_kinematics import (
    calculate_mean_acceleration,
    calculate_peak_velocity,
    calculate_trajectory_distance,
    export_moco_bundle,
    export_moco_fbx_ascii,
    export_moco_track_csv,
    export_moco_track_json,
    format_moco_prompt_token,
    interpolate_waypoints,
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
from omni_director.tools.dof_simulator import (
    calculate_dof_limits,
    calculate_hyperfocal_distance as calculate_dof_hyperfocal_distance,
    export_dof_bundle,
    export_focus_puller_cue_sheet,
    export_optical_chart_json,
    format_dof_prompt_token,
    interpolate_rack_focus,
    resolve_circle_of_confusion,
    synthesize_default_dof_spec,
)
from omni_director.tools.dit_lut import (
    calculate_color_continuity_audit,
    export_dit_bundle,
    export_dit_cart_manifest_json,
    export_lut_bundle,
    export_master_cube_lut,
    export_scene_cube_lut,
    format_lut_prompt_token,
    generate_3d_cube_lut,
    generate_3d_lut_cube_data,
    synthesize_default_3d_lut,
    verify_color_continuity,
)

__all__ = [
    "audit_omni_scene_prompt",
    "heal_omni_scene_prompt",
    "compile_storyboard_html",
    "generate_svg_storyboard_frame",
    "NanoBananaStoryboardEngine",
    "GeminiOmniVideoEngine",
    "export_cmx3600_edl",
    "export_fcpxml",
    "export_shot_list_csv",
    "export_production_callsheet_md",
    "export_all_nle_artifacts",
    "audit_dialogue_pacing",
    "compile_subtitles_srt",
    "compile_subtitles_vtt",
    "CoverageType",
    "CoverageVariant",
    "generate_scene_coverage",
    "synthesize_conversational_deltas",
    # Color grading
    "get_preset_color_look",
    "export_asc_cdl_xml",
    "export_asc_cdl_file",
    "embed_cdl_in_edl",
    "cdl_to_svg_matrix_filter",
    # Speed ramp
    "synthesize_speed_ramp_curve",
    "format_craft_shutter_tokens",
    "export_fcpxml_timemap",
    # Audio mixer
    "synthesize_default_stem_mixer",
    "export_audio_stems_manifest",
    "export_audio_stems_file",
    "estimate_broadcast_loudness",
    # Optical lens suite (PM-FEAT-007)
    "calculate_sensor_fov",
    "calculate_hyperfocal_distance",
    "format_optical_prompt_token",
    "export_lens_metadata_csv",
    "export_lens_metadata_file",
    # Virtual production suite (PM-FEAT-008)
    "synthesize_default_vp_stage",
    "export_ue_ndisplay_manifest",
    "export_dmx_patch_csv",
    "export_virtual_production_bundle",
    # MoCo kinematics suite (PM-FEAT-009)
    "synthesize_default_moco_rig",
    "calculate_trajectory_distance",
    "calculate_peak_velocity",
    "calculate_mean_acceleration",
    "interpolate_waypoints_6dof",
    "interpolate_waypoints",
    "format_moco_prompt_token",
    "export_moco_track_json",
    "export_moco_track_csv",
    "export_moco_fbx_ascii",
    "export_moco_bundle",
    # Lighting rig suite (PM-FEAT-010)
    "synthesize_default_lighting_rig",
    "calculate_key_to_fill_ratio",
    "calculate_key_to_rim_ratio",
    "calculate_total_lux",
    "calculate_cct_deltas",
    "calculate_lighting_photometrics",
    "format_lighting_prompt_token",
    "export_lighting_plot_json",
    "export_gaffer_callsheet_csv",
    "export_lighting_bundle",
    # Depth of field simulator suite (PM-FEAT-011)
    "calculate_dof_limits",
    "calculate_dof_hyperfocal_distance",
    "format_dof_prompt_token",
    "interpolate_rack_focus",
    "resolve_circle_of_confusion",
    "synthesize_default_dof_spec",
    "export_optical_chart_json",
    "export_focus_puller_cue_sheet",
    "export_dof_bundle",
    # DIT 3D LUT suite (PM-FEAT-012)
    "generate_3d_cube_lut",
    "generate_3d_lut_cube_data",
    "synthesize_default_3d_lut",
    "format_lut_prompt_token",
    "verify_color_continuity",
    "calculate_color_continuity_audit",
    "export_master_cube_lut",
    "export_scene_cube_lut",
    "export_dit_cart_manifest_json",
    "export_dit_bundle",
    "export_lut_bundle",
]
