"""SMPTE 12M Timecode Sync, Clapper Slate & ASC-MHL Offload Engine (PM-FEAT-018).

Provides SMPTE 12M broadcast/cinema timecode coordinate math (NDF and DF),
dual-system sound sync transient offset calculation, ASC-MHL (Media Hash List) v2.0
cryptographic manifest generation, production clapper slate logging, Avid Log
Exchange (ALE) sound sync tables, and Gemini Omni CRAFT clapper prompt tokens.
"""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    AscMhlHashEntry,
    AscMhlManifestSpec,
    ClapperSlateSpec,
    MasterProductionBible,
    MasterProductionSlateSpec,
    Smpte12MTimecodeSpec,
    TimecodeDropFrameMode,
)


# ==============================================================================
# SMPTE 12M Timecode Coordinate Mathematics
# ==============================================================================

def calculate_smpte12m_frames(
    tc_str: str,
    fps: float = 24.0,
    drop_frame: bool = False,
) -> int:
    """Calculates absolute frame count from a SMPTE 12M timecode string.

    Supports both colon (:) Non-Drop-Frame (NDF) and semicolon (;) Drop-Frame (DF)
    specifications.
    """
    cleaned = str(tc_str).strip()
    is_df = drop_frame or (";" in cleaned)

    # Normalize delimiters
    parts = re.split(r"[:;]", cleaned)
    if len(parts) != 4:
        raise ValueError(f"Invalid SMPTE 12M timecode format '{tc_str}': expected HH:MM:SS:FF or HH:MM:SS;FF")

    h, m, s, f = [int(p) for p in parts]
    nominal_fps = int(round(fps))

    if not is_df or nominal_fps not in (30, 60):
        # Non-Drop Frame calculation
        return (h * 3600 + m * 60 + s) * nominal_fps + f

    # Drop Frame SMPTE 12M calculation (standard 29.97 / 59.94)
    # Dropping 2 frames every minute except tens of minutes (or 4 frames for 60fps)
    drop_per_minute = 4 if nominal_fps == 60 else 2
    total_minutes = 60 * h + m
    dropped_frames = drop_per_minute * (total_minutes - (total_minutes // 10))

    return (h * 3600 + m * 60 + s) * nominal_fps + f - dropped_frames


def format_smpte12m_timecode(
    frame_count: int,
    fps: float = 24.0,
    drop_frame: bool = False,
) -> str:
    """Formats an absolute frame count into a standard SMPTE 12M timecode string."""
    nominal_fps = int(round(fps))
    frames = max(0, int(frame_count))

    if not drop_frame or nominal_fps not in (30, 60):
        # Non-Drop Frame format (HH:MM:SS:FF)
        f = frames % nominal_fps
        total_seconds = frames // nominal_fps
        s = total_seconds % 60
        total_minutes = total_seconds // 60
        m = total_minutes % 60
        h = total_minutes // 60
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

    # Drop Frame conversion (29.97 / 59.94)
    drop_per_min = 4 if nominal_fps == 60 else 2
    frames_per_10m = nominal_fps * 600 - drop_per_min * 9
    frames_per_m = nominal_fps * 60 - drop_per_min

    d = frames // frames_per_10m
    m_rem = frames % frames_per_10m

    if m_rem > drop_per_min:
        adjusted_frames = frames + (drop_per_min * 9) * d + drop_per_min * ((m_rem - drop_per_min) // frames_per_m)
    else:
        adjusted_frames = frames + (drop_per_min * 9) * d

    f = adjusted_frames % nominal_fps
    total_s = adjusted_frames // nominal_fps
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60

    return f"{h:02d}:{m:02d}:{s:02d};{f:02d}"


# ==============================================================================
# Dual-System Sound Sync Transient Offset
# ==============================================================================

def calculate_sound_sync_offset(
    video_tc: str,
    audio_tc: str,
    fps: float = 24.0,
) -> int:
    """Calculates frame sync offset between visual clapper sticks contact and audio transient.

    A positive offset means video leads audio (audio must be slipped forward).
    A negative offset means audio leads video (audio must be slipped backward).

    Returns:
        Frame offset delta (video_frames - audio_frames).
    """
    v_frames = calculate_smpte12m_frames(video_tc, fps=fps)
    a_frames = calculate_smpte12m_frames(audio_tc, fps=fps)
    return v_frames - a_frames


# ==============================================================================
# ASC-MHL v2.0 Cryptographic Manifest Generation
# ==============================================================================

def generate_asc_mhl_xml(manifest: Optional[AscMhlManifestSpec] = None) -> str:
    """Generates an American Society of Cinematographers Media Hash List (ASC-MHL) v2.0 XML string."""
    if manifest is None:
        manifest = AscMhlManifestSpec(
            project_title="Omni Director Production",
            creation_date=datetime.now(timezone.utc).isoformat(),
        )
    root = ET.Element(
        "hashlist",
        version=manifest.mhl_version,
        xmlns="urn:ASC:MHL:v2.0",
    )

    creator_info = ET.SubElement(root, "creatorinfo")
    ET.SubElement(creator_info, "creationdate").text = manifest.creation_date or datetime.now(timezone.utc).isoformat()
    ET.SubElement(creator_info, "project").text = manifest.project_title or "Omni Director Production"
    ET.SubElement(creator_info, "tool").text = "Omni Movie Director v2.8.0"

    hashes_elem = ET.SubElement(root, "hashes")

    for entry in manifest.hash_entries:
        hash_elem = ET.SubElement(hashes_elem, "hash")
        ET.SubElement(hash_elem, "file").text = entry.file_path
        ET.SubElement(hash_elem, "size").text = str(entry.file_size_bytes)
        if entry.xxhash64:
            ET.SubElement(hash_elem, "xxhash64").text = entry.xxhash64
        if entry.sha1:
            ET.SubElement(hash_elem, "sha1").text = entry.sha1
        if entry.md5:
            ET.SubElement(hash_elem, "md5").text = entry.md5
        ET.SubElement(hash_elem, "hashdate").text = entry.hash_timestamp or datetime.now(timezone.utc).isoformat()

    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    return xml_declaration + ET.tostring(root, encoding="utf-8").decode("utf-8")


# ==============================================================================
# Production Clapper Slate Log Exporter (CSV)
# ==============================================================================

def generate_clapper_slate_log_csv(bible: Any) -> str:
    """Generates standard Camera & Sound Department Clapper Slate log CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Scene #",
        "Take #",
        "Camera Roll",
        "Sound Roll",
        "Camera ID",
        "FPS",
        "Day/Night",
        "Int/Ext",
        "Filter Pack",
        "Shutter Angle",
        "Director",
        "DP",
        "Timecode In",
        "Timecode Out",
        "Duration Frames",
    ])

    scenes = getattr(bible, "scenes", [])
    master_slate = getattr(bible, "master_slate_spec", None) or getattr(bible, "slate_spec", None)
    director = getattr(bible, "director", "Director")
    dp = getattr(bible, "dp", "Cinematographer")

    if master_slate and master_slate.scenes:
        for sc in master_slate.scenes:
            writer.writerow([
                sc.scene_number,
                sc.take_number,
                sc.camera_roll,
                sc.sound_roll,
                sc.camera_id,
                f"{sc.fps:.1f}",
                sc.day_night,
                sc.int_ext,
                sc.filter_pack,
                f"{sc.shutter_angle:.1f}",
                sc.director or director,
                sc.dp or dp,
                sc.timecode.timecode_in,
                sc.timecode.timecode_out,
                sc.timecode.duration_frames,
            ])
    elif scenes:
        current_frame = 24 * 3600  # 01:00:00:00
        for idx, sc in enumerate(scenes):
            slate = getattr(sc, "clapper_slate", None)
            dur = getattr(sc, "duration_frames", 240)
            tc_in = format_smpte12m_timecode(current_frame, fps=24.0)
            tc_out = format_smpte12m_timecode(current_frame + dur, fps=24.0)
            current_frame += dur

            if slate:
                writer.writerow([
                    slate.scene_number,
                    slate.take_number,
                    slate.camera_roll,
                    slate.sound_roll,
                    slate.camera_id,
                    f"{slate.fps:.1f}",
                    slate.day_night,
                    slate.int_ext,
                    slate.filter_pack,
                    f"{slate.shutter_angle:.1f}",
                    slate.director or director,
                    slate.dp or dp,
                    slate.timecode.timecode_in or tc_in,
                    slate.timecode.timecode_out or tc_out,
                    slate.timecode.duration_frames or dur,
                ])
            else:
                writer.writerow([
                    idx + 1,
                    1,
                    f"A{idx+1:02d}",
                    f"SR{idx+1:02d}",
                    "A",
                    "24.0",
                    "DAY",
                    "INT",
                    "Clear",
                    "180.0",
                    director,
                    dp,
                    tc_in,
                    tc_out,
                    dur,
                ])
    else:
        # Default placeholder
        writer.writerow([
            1, 1, "A01", "SR01", "A", "24.0", "DAY", "INT", "Clear", "180.0", director, dp, "01:00:00:00", "01:00:10:00", 240
        ])

    return output.getvalue()


# ==============================================================================
# Dual-System Sound Sync Avid Log Exchange (ALE)
# ==============================================================================

def generate_sound_sync_ale(bible: Any) -> str:
    """Generates an Avid Log Exchange (ALE) manifest matching picture to sound rolls."""
    title = getattr(bible, "project_title", "Omni Sound Sync")
    lines: List[str] = [
        "Heading",
        "FIELD_DELIM\tTABS",
        "VIDEO_FORMAT\t1080",
        "FPS\t24",
        f"PROJECT\t{title}",
        "",
        "Column",
        "Name\tTracks\tStart\tEnd\tDuration\tCam Roll\tSound Roll\tAudio Start\tAudio End\tAudio Tracks\tSync Offset",
        "",
        "Data",
    ]

    scenes = getattr(bible, "scenes", [])
    master_slate = getattr(bible, "master_slate_spec", None) or getattr(bible, "slate_spec", None)

    current_frame = 24 * 3600
    if master_slate and master_slate.scenes:
        for sc in master_slate.scenes:
            dur = sc.timecode.duration_frames
            tc_in = sc.timecode.timecode_in
            tc_out = sc.timecode.timecode_out
            lines.append(
                f"Scene_{sc.scene_number:02d}_Take_{sc.take_number:02d}\tVA1A2\t{tc_in}\t{tc_out}\t{dur}\t{sc.camera_roll}\t{sc.sound_roll}\t{tc_in}\t{tc_out}\tA1A2\t0"
            )
    elif scenes:
        for idx, sc in enumerate(scenes):
            dur = getattr(sc, "duration_frames", 240)
            tc_in = format_smpte12m_timecode(current_frame, fps=24.0)
            tc_out = format_smpte12m_timecode(current_frame + dur, fps=24.0)
            current_frame += dur
            slate = getattr(sc, "clapper_slate", None)
            cam_roll = slate.camera_roll if slate else f"A{idx+1:02d}"
            snd_roll = slate.sound_roll if slate else f"SR{idx+1:02d}"
            lines.append(
                f"Scene_{idx+1:02d}_Take_01\tVA1A2\t{tc_in}\t{tc_out}\t{dur}\t{cam_roll}\t{snd_roll}\t{tc_in}\t{tc_out}\tA1A2\t0"
            )
    else:
        lines.append("Scene_01_Take_01\tVA1A2\t01:00:00:00\t01:00:10:00\t240\tA01\tSR01\t01:00:00:00\t01:00:10:00\tA1A2\t0")

    return "\n".join(lines) + "\n"


# ==============================================================================
# Slate Bundle Exporter
# ==============================================================================

def export_slate_bundle(
    slate_spec: MasterProductionSlateSpec,
    output_dir: Path,
    bible: Optional[MasterProductionBible] = None,
) -> Dict[str, Path]:
    """Exports the complete production clapper slate, ASC-MHL, and sound sync bundle."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Slate manifest JSON
    json_path = out_dir / "slate_manifest.json"
    json_path.write_text(json.dumps(slate_spec.model_dump(), indent=2), encoding="utf-8")

    # 2. ASC-MHL XML
    mhl_manifest = slate_spec.asc_mhl or AscMhlManifestSpec(
        project_title=slate_spec.project_title or "Omni Production",
        creation_date=datetime.now(timezone.utc).isoformat(),
        hash_entries=[
            AscMhlHashEntry(
                file_path="video/A01_C001.mov",
                file_size_bytes=1048576000,
                xxhash64="e3b0c44298fc1c14",
                sha1="2fd4e1c67a2d28fced849ee1bb76e7391b93eb12",
                md5="d41d8cd98f00b204e9800998ecf8427e",
                hash_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            AscMhlHashEntry(
                file_path="audio/SR01_T001.wav",
                file_size_bytes=52428800,
                xxhash64="cbf29ce484222325",
                sha1="de9f2c7fd25e1b3afad3e85a0bd17d9b100db4b3",
                md5="79054025255fb1a26e4bc422aef54eb4",
                hash_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        ],
    )
    mhl_path = out_dir / "asc_mhl_manifest.xml"
    mhl_path.write_text(generate_asc_mhl_xml(mhl_manifest), encoding="utf-8")

    # 3. Clapper slate log CSV
    csv_path = out_dir / "clapper_slate_log.csv"
    csv_path.write_text(generate_clapper_slate_log_csv(bible or slate_spec), encoding="utf-8")

    # 4. Sound Sync ALE
    ale_path = out_dir / "sound_sync.ale"
    ale_path.write_text(generate_sound_sync_ale(bible or slate_spec), encoding="utf-8")

    return {
        "mhl_xml": mhl_path,
        "sound_ale": ale_path,
        "slate_csv": csv_path,
        "slate_json": json_path,
        "slate_bundle": json_path,
    }


# ==============================================================================
# Prompt Token Authoring (Gemini Omni CRAFT Grammar)
# ==============================================================================

def format_clapper_slate_prompt_token(slate: ClapperSlateSpec) -> str:
    """Formats an architectural CRAFT clapper slate prompt token for Gemini Omni."""
    token = (
        f"[CLAPPER_SLATE: Scene {slate.scene_number}, Take {slate.take_number}, "
        f"Roll {slate.camera_roll}/{slate.sound_roll}, Cam {slate.camera_id} {slate.fps:.1f}fps, "
        f"{slate.int_ext} {slate.day_night}, Filter {slate.filter_pack}, "
        f"{slate.shutter_angle:.1f}° Shutter, TC {slate.timecode.timecode_in}]"
    )
    return token


# ==============================================================================
# Synthesizers
# ==============================================================================

def synthesize_default_clapper_slate(scene_number: int = 1) -> ClapperSlateSpec:
    """Synthesizes a production default clapper slate specification for a scene."""
    start_frame = 24 * 3600 + (scene_number - 1) * 240
    end_frame = start_frame + 240
    return ClapperSlateSpec(
        scene_number=scene_number,
        take_number=1,
        camera_roll=f"A{scene_number:02d}",
        sound_roll=f"SR{scene_number:02d}",
        camera_id="A",
        fps=24.0,
        day_night="DAY",
        int_ext="INT",
        filter_pack="Clear",
        shutter_angle=180.0,
        director="Director",
        dp="Cinematographer",
        timecode=Smpte12MTimecodeSpec(
            timecode_in=format_smpte12m_timecode(start_frame, fps=24.0),
            timecode_out=format_smpte12m_timecode(end_frame, fps=24.0),
            duration_frames=240,
            frame_rate=24.0,
            drop_frame=False,
        ),
    )


def synthesize_default_slate_spec(
    bible: Optional[MasterProductionBible] = None,
) -> MasterProductionSlateSpec:
    """Synthesizes a production default MasterProductionSlateSpec from a bible or defaults."""
    title = getattr(bible, "project_title", "Omni Production")
    scenes_list = getattr(bible, "scenes", [])
    slates: List[ClapperSlateSpec] = []

    if scenes_list:
        current_frame = 24 * 3600
        for idx, sc in enumerate(scenes_list):
            dur = getattr(sc, "duration_frames", 240)
            slate = getattr(sc, "clapper_slate", None)
            if slate:
                slates.append(slate)
            else:
                tc_in = format_smpte12m_timecode(current_frame, fps=24.0)
                tc_out = format_smpte12m_timecode(current_frame + dur, fps=24.0)
                slates.append(
                    ClapperSlateSpec(
                        scene_number=idx + 1,
                        take_number=1,
                        camera_roll=f"A{idx+1:02d}",
                        sound_roll=f"SR{idx+1:02d}",
                        camera_id="A",
                        fps=24.0,
                        day_night="DAY",
                        int_ext="INT",
                        filter_pack="Clear",
                        shutter_angle=180.0,
                        director="Director",
                        dp="Cinematographer",
                        timecode=Smpte12MTimecodeSpec(
                            timecode_in=tc_in,
                            timecode_out=tc_out,
                            duration_frames=dur,
                            frame_rate=24.0,
                            drop_frame=False,
                        ),
                    )
                )
            current_frame += dur
    else:
        slates.append(synthesize_default_clapper_slate(1))

    asc_mhl = AscMhlManifestSpec(
        project_title=title,
        creation_date=datetime.now(timezone.utc).isoformat(),
        hash_entries=[],
    )

    return MasterProductionSlateSpec(
        project_title=title,
        director="Director",
        dp="Cinematographer",
        scenes=slates,
        asc_mhl=asc_mhl,
    )
