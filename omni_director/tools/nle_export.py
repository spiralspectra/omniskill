"""Industry NLE Timeline & Production Export Suite (CMX 3600 EDL, FCPXML 1.10, CSV, Call Sheet)."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Dict, Tuple, Union
from xml.sax.saxutils import escape as xml_escape

from omni_director.schemas import MasterProductionBible, ScenePromptSpec


def _seconds_to_smpte_frames(seconds: float, fps: int = 24) -> str:
    """Format seconds as SMPTE timecode HH:MM:SS:FF at given fps."""
    total_frames = max(0, int(round(seconds * fps)))
    ff = total_frames % fps
    total_seconds = total_frames // fps
    ss = total_seconds % 60
    mm = (total_seconds // 60) % 60
    hh = total_seconds // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _parse_scene_window(
    scene: ScenePromptSpec,
    scene_idx: int,
    total_scenes: int,
    total_runtime: float,
) -> Tuple[float, float]:
    """Extract (start_sec, end_sec) from scene.timestamp_range or proportional fallback."""
    ts = getattr(scene, "timestamp_range", "") or ""
    match = re.search(r"(\d+):(\d+)\s*[-–—]\s*(\d+):(\d+)", ts)
    if match:
        m1, s1, m2, s2 = map(int, match.groups())
        start_sec = float(m1 * 60 + s1)
        end_sec = float(m2 * 60 + s2)
        if end_sec > start_sec:
            return start_sec, end_sec

    per_scene = float(total_runtime) / max(1, total_scenes)
    start_sec = (scene_idx - 1) * per_scene
    end_sec = scene_idx * per_scene
    return start_sec, end_sec


def export_cmx3600_edl(bible: MasterProductionBible, fps: int = 24) -> str:
    """Generate an industry-standard CMX 3600 Edit Decision List (.edl) at 24fps."""
    lines = [
        f"TITLE: {bible.project_title.upper()[:60]}",
        "FCM: NON-DROP FRAME",
        "",
    ]

    total_scenes = max(1, len(bible.scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)

    for idx, scene in enumerate(bible.scenes, start=1):
        edit_num = f"{idx:03d}"
        rec_start_sec, rec_end_sec = _parse_scene_window(
            scene, idx, total_scenes, total_runtime
        )
        dur_sec = max(1.0, rec_end_sec - rec_start_sec)

        src_in = _seconds_to_smpte_frames(0.0, fps=fps)
        src_out = _seconds_to_smpte_frames(dur_sec, fps=fps)
        rec_in = _seconds_to_smpte_frames(rec_start_sec, fps=fps)
        rec_out = _seconds_to_smpte_frames(rec_end_sec, fps=fps)

        cam = scene.craft_camera
        focal = cam.focal_length_mm if cam else 35
        rig = cam.rig_type if cam else "Locked-off Tripod"
        comp = cam.composition if cam else "Centered Hero Framing"
        anchor = cam.action_anchor if cam else scene.scene_title

        lines.append(f"{edit_num}  AX       V     C        {src_in} {src_out} {rec_in} {rec_out}")
        lines.append(f"* FROM CLIP NAME: SCENE_{scene.scene_index:02d}_PLATE.MP4")
        lines.append(f"* COMMENT: CRAFT CAMERA: {focal}mm {rig} | {comp}")
        lines.append(f"* ACTION ANCHOR: {anchor}")
        lines.append("")

    edl_text = "\n".join(lines).strip() + "\n"

    # Embed CDL if master or scene color looks are defined
    has_color_look = (bible.master_color_look is not None) or any(
        getattr(s, "scene_color_look", None) is not None for s in bible.scenes
    )
    if has_color_look:
        from omni_director.tools.color_grade import embed_cdl_in_edl
        edl_text = embed_cdl_in_edl(edl_text, bible)

    return edl_text


def export_fcpxml(bible: MasterProductionBible, fps: int = 24) -> str:
    """Generate a valid Final Cut Pro / DaVinci Resolve FCPXML v1.10 timeline."""
    total_scenes = max(1, len(bible.scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)
    title_escaped = xml_escape(bible.project_title)

    resources_xml = [
        f'        <format id="r1" name="FFVideoFormat1080p{fps}" '
        f'frameDuration="1/{fps}s" width="1920" height="1080" '
        f'colorSpace="1-1-1 (Rec. 709)"/>'
    ]
    spine_xml = []

    offset_frames = 0
    for idx, scene in enumerate(bible.scenes, start=1):
        rec_start_sec, rec_end_sec = _parse_scene_window(
            scene, idx, total_scenes, total_runtime
        )
        dur_sec = max(1.0, rec_end_sec - rec_start_sec)
        clip_frames = int(round(dur_sec * fps))
        res_id = f"r{scene.scene_index + 1}"

        cam = scene.craft_camera
        focal = cam.focal_length_mm if cam else 35
        rig = cam.rig_type if cam else "Locked-off Tripod"
        anchor = cam.action_anchor if cam else scene.scene_title

        clip_name = xml_escape(f"Scene_{scene.scene_index:02d}_{scene.scene_title[:40]}")
        cam_note = xml_escape(f"{focal}mm {rig} - {anchor}")

        resources_xml.append(
            f'        <asset id="{res_id}" name="SCENE_{scene.scene_index:02d}" '
            f'start="0s" duration="{clip_frames}/{fps}s" hasVideo="1" hasAudio="1" format="r1"/>'
        )
        timemap_block = ""
        if getattr(scene, "speed_ramp", None) is not None:
            from omni_director.tools.speed_ramp import export_fcpxml_timemap
            timemap_block = "\n" + export_fcpxml_timemap(scene, sequence_fps=float(fps))

        spine_xml.append(
            f'                        <asset-clip name="{clip_name}" ref="{res_id}" '
            f'offset="{offset_frames}/{fps}s" duration="{clip_frames}/{fps}s" '
            f'start="0s" format="r1">\n'
            f'                            <note>{cam_note}</note>{timemap_block}\n'
            f'                        </asset-clip>'
        )
        offset_frames += clip_frames

    resources_block = "\n".join(resources_xml)
    spine_block = "\n".join(spine_xml)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<fcpxml version="1.10">\n'
        '    <resources>\n'
        f'{resources_block}\n'
        '    </resources>\n'
        '    <library>\n'
        f'        <event name="{title_escaped}">\n'
        f'            <project name="{title_escaped} Timeline">\n'
        f'                <sequence format="r1" duration="{offset_frames}/{fps}s" '
        'tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">\n'
        '                    <spine>\n'
        f'{spine_block}\n'
        '                    </spine>\n'
        '                </sequence>\n'
        '            </project>\n'
        '        </event>\n'
        '    </library>\n'
        '</fcpxml>\n'
    )


def export_shot_list_csv(bible: MasterProductionBible) -> str:
    """Export a structured CSV shot list for assistant directors and line producers."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "scene_index",
            "timecode_start",
            "timecode_end",
            "rig_type",
            "focal_length_mm",
            "composition",
            "action_beats",
            "audio_cues",
        ]
    )

    total_scenes = max(1, len(bible.scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)

    for idx, scene in enumerate(bible.scenes, start=1):
        rec_start_sec, rec_end_sec = _parse_scene_window(
            scene, idx, total_scenes, total_runtime
        )
        tc_start = _seconds_to_smpte_frames(rec_start_sec, fps=24)
        tc_end = _seconds_to_smpte_frames(rec_end_sec, fps=24)

        cam = scene.craft_camera
        rig = cam.rig_type if cam else "Locked-off Tripod"
        focal = cam.focal_length_mm if cam else 35
        comp = cam.composition if cam else "Centered Hero Framing"

        beats_str = " | ".join(str(b) for b in (scene.action_beats or []))
        audio_parts = []
        if scene.diegetic_sonic:
            audio_parts.extend(scene.diegetic_sonic.foley_cues or [])
            if scene.diegetic_sonic.dialogue_lines:
                audio_parts.extend(scene.diegetic_sonic.dialogue_lines)
        audio_str = " ; ".join(audio_parts)

        writer.writerow(
            [
                scene.scene_index,
                tc_start,
                tc_end,
                rig,
                focal,
                comp,
                beats_str,
                audio_str,
            ]
        )

    return buffer.getvalue()


def export_production_callsheet_md(bible: MasterProductionBible) -> str:
    """Export a clean Markdown production call sheet and director shoot brief."""
    env = bible.environment
    bgm = bible.master_bgm
    lines = [
        f"# Production Call Sheet: {bible.project_title}",
        "",
        f"- **Logline**: {bible.logline}",
        f"- **Domain Archetype**: `{bible.domain_archetype or 'cinematic_commercial'}`",
        f"- **Storytelling Mode**: `{bible.storytelling_mode.value}`",
        f"- **Creative Regime**: `{bible.creative_regime.value}`",
        f"- **Total Runtime**: `{bible.total_runtime_seconds}s` ({len(bible.scenes)} scenes)",
        f"- **Aspect Ratio**: `{bible.aspect_ratio.value}`",
        "",
        "## 1. Visual Continuity & Lighting Setup",
        f"- **Color Palette**: {', '.join(bible.color_palette)}",
        f"- **Master Location**: {env.location_name}",
        f"- **Spatial Architecture**: {env.spatial_architecture}",
        f"- **Lighting Setup**: {env.lighting_setup}",
        f"- **Atmospheric Particles**: {env.atmospheric_particles}",
        "",
        "## 2. Character & Subject Roster",
    ]
    for char in bible.characters:
        lines.append(
            f"- **{char.name}**: {char.silhouette} | "
            f"Wardrobe Polarity: {char.wardrobe_polarity} | "
            f"Movement: {char.movement_signature}"
        )

    lines.extend(
        [
            "",
            "## 3. Scene-by-Scene Shooting Schedule",
            "",
            "| Scene | Timestamp | Camera & Lens | Action Anchor | Key Foley / Audio |",
            "|---|---|---|---|---|",
        ]
    )
    for scene in bible.scenes:
        cam = scene.craft_camera
        focal = cam.focal_length_mm if cam else 35
        rig = cam.rig_type if cam else "Locked-off Tripod"
        anchor = cam.action_anchor if cam else scene.scene_title
        audio_summary = (
            ", ".join(scene.diegetic_sonic.foley_cues[:2])
            if (scene.diegetic_sonic and scene.diegetic_sonic.foley_cues)
            else "Tactile foley"
        )
        lines.append(
            f"| Scene {scene.scene_index:02d} ({scene.scene_title}) | `{scene.timestamp_range}` | "
            f"{focal}mm `{rig}` | {anchor} | {audio_summary} |"
        )

    lines.extend(
        [
            "",
            "## 4. Musical Score & Acoustic Direction",
            f"- **Track Title**: {bgm.track_title} ({bgm.genre_style})",
            f"- **Tempo & Key**: {bgm.tempo_bpm} BPM in {bgm.key_signature}",
            f"- **Instrumentation**: {', '.join(bgm.instrumentation)}",
            f"- **Dynamic Arc**: {bgm.dynamic_arc}",
            "",
        ]
    )
    return "\n".join(lines)


def export_all_nle_artifacts(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    fps: int = 24,
) -> Dict[str, str]:
    """Write timeline.edl, sequence.fcpxml, shot_list.csv, and call_sheet.md to output_dir."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    edl_path = out_path / "timeline.edl"
    fcpxml_path = out_path / "sequence.fcpxml"
    csv_path = out_path / "shot_list.csv"
    md_path = out_path / "call_sheet.md"

    edl_path.write_text(export_cmx3600_edl(bible, fps=fps), encoding="utf-8")
    fcpxml_path.write_text(export_fcpxml(bible, fps=fps), encoding="utf-8")
    csv_path.write_text(export_shot_list_csv(bible), encoding="utf-8")
    md_path.write_text(export_production_callsheet_md(bible), encoding="utf-8")

    res = {
        "edl": str(edl_path),
        "fcpxml": str(fcpxml_path),
        "csv": str(csv_path),
        "call_sheet": str(md_path),
    }

    try:
        from omni_director.tools.color_grade import export_asc_cdl_file
        from omni_director.tools.audio_mixer import export_audio_stems_file
        cdl_path = export_asc_cdl_file(bible, out_path / "production_grade.cdl")
        stems_path = export_audio_stems_file(bible, out_path / "audio_stems_manifest.json")
        res["cdl"] = str(cdl_path)
        res["audio_stems"] = str(stems_path)
    except Exception:
        pass

    return res
