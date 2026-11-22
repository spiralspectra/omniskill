"""Editorial J-Cut / L-Cut Audio Bridge, BPM Beat-Grid Sync & Music/Foley Spotting Engine (PM-FEAT-028).

Pure-Python post-production editorial spotting suite providing:
- Exact 24fps BPM beat-grid quantization (frame indices, bar/beat markers, SMPTE HH:MM:SS:FF)
- Domain-calibrated J-Cut / L-Cut / JL-Overlap audio bridge synthesis across consecutive cuts
- Frame-accurate music stem, hard foley, room tone, and dialogue bridge spotting cues
- CMX 3600 split-edit EDL generation with staggered V / A / A2 pre-lap and overhang events
- Spotting Cue Sheet CSV, Markdown Spotting Sheet, and JSON manifest export bundle
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    AudioBridgeType,
    EditBridgeSpec,
    MasterProductionBible,
    ScenePromptSpec,
    SpottingCueEntry,
    SpottingManifestSpec,
)
from omni_director.tools.nle_export import _parse_scene_window


def _frames_to_smpte(total_frames: int, fps: int = 24) -> str:
    """Convert non-negative frame count to SMPTE non-drop HH:MM:SS:FF."""
    safe_fps = max(1, int(fps))
    frames = max(0, int(total_frames))
    ff = frames % safe_fps
    total_sec = frames // safe_fps
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def compute_bpm_beat_grid(
    tempo_bpm: float,
    total_duration_sec: float,
    fps: int = 24,
) -> List[Dict[str, Any]]:
    """Compute exact 24fps beat-grid frames, bar/beat coordinates, and SMPTE timecodes."""
    safe_bpm = float(tempo_bpm) if (tempo_bpm and tempo_bpm > 0.0) else 120.0
    safe_dur = max(1.0, float(total_duration_sec or 8.0))
    safe_fps = max(1, int(fps))
    total_frames = int(round(safe_dur * safe_fps))
    seconds_per_beat = 60.0 / safe_bpm

    grid: List[Dict[str, Any]] = []
    beat_idx = 0
    while True:
        frame_pos = int(round(beat_idx * seconds_per_beat * safe_fps))
        if beat_idx > 0 and frame_pos > total_frames:
            break
        grid.append(
            {
                "beat_index": beat_idx,
                "bar": (beat_idx // 4) + 1,
                "beat_in_bar": (beat_idx % 4) + 1,
                "is_downbeat": (beat_idx % 4) == 0,
                "frame": frame_pos,
                "time_sec": round(frame_pos / float(safe_fps), 4),
                "smpte_tc": _frames_to_smpte(frame_pos, safe_fps),
            }
        )
        beat_idx += 1
        if beat_idx > 4096:
            break
    return grid


def _resolve_tempo_and_calibration(
    bible: MasterProductionBible,
) -> Tuple[float, Dict[str, Any]]:
    from omni_director.presets import classify_brief_domain, get_domain_spotting_spec

    domain_key = bible.domain_archetype or classify_brief_domain(
        f"{bible.project_title} {getattr(bible, 'logline', '')}"
    )
    cal = get_domain_spotting_spec(domain_key)
    bgm_bpm = (
        float(bible.master_bgm.tempo_bpm)
        if (getattr(bible, "master_bgm", None) and getattr(bible.master_bgm, "tempo_bpm", 0) > 0)
        else 0.0
    )
    tempo_bpm = bgm_bpm if bgm_bpm > 0.0 else float(cal.get("default_bpm", 120.0))
    return tempo_bpm, cal


def _nearest_beat(beat_grid: List[Dict[str, Any]], target_frame: int) -> Dict[str, Any]:
    if not beat_grid:
        return {
            "beat_index": 0,
            "bar": 1,
            "beat_in_bar": 1,
            "is_downbeat": True,
            "frame": 0,
            "time_sec": 0.0,
            "smpte_tc": "00:00:00:00",
        }
    return min(beat_grid, key=lambda b: abs(int(b["frame"]) - target_frame))


def build_spotting_manifest(
    bible: MasterProductionBible,
    fps: int = 24,
) -> SpottingManifestSpec:
    """Build a beat-locked J-Cut/L-Cut audio bridge and music/foley spotting manifest (PM-FEAT-028)."""
    safe_fps = max(1, int(fps))
    tempo_bpm, cal = _resolve_tempo_and_calibration(bible)
    frames_per_beat = round((60.0 / tempo_bpm) * safe_fps, 4)
    bar_length_beats = int(cal.get("bar_length_beats", 4))

    scenes = list(bible.scenes or [])
    total_scenes = max(1, len(scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)

    scene_windows: List[Tuple[ScenePromptSpec, int, int]] = []
    max_end_frame = int(round(total_runtime * safe_fps))
    for idx, scene in enumerate(scenes, start=1):
        s_start, s_end = _parse_scene_window(scene, idx, total_scenes, total_runtime)
        start_f = max(0, int(round(s_start * safe_fps)))
        end_f = max(start_f + safe_fps, int(round(s_end * safe_fps)))
        scene_windows.append((scene, start_f, end_f))
        max_end_frame = max(max_end_frame, end_f)

    effective_dur_sec = max(1.0, max_end_frame / float(safe_fps))
    beat_grid = compute_bpm_beat_grid(tempo_bpm, effective_dur_sec, fps=safe_fps)
    beat_grid_tc = [str(b["smpte_tc"]) for b in beat_grid]

    default_bridge: AudioBridgeType = cal["default_bridge_type"]
    base_j_frames = int(cal.get("j_prelap_frames", 12))
    base_l_frames = int(cal.get("l_overhang_frames", 0))
    tolerance_frames = int(cal.get("beat_snap_tolerance_frames", 2))
    default_anchor = str(cal.get("sonic_anchor_cue", "Domain calibrated transient bridge"))
    default_rationale = str(cal.get("rationale", "Beat-locked split-edit audio transition."))

    bridges: List[EditBridgeSpec] = []
    for idx in range(len(scene_windows) - 1):
        sc_from, from_start_f, from_end_f = scene_windows[idx]
        sc_to, to_start_f, to_end_f = scene_windows[idx + 1]
        cut_frame = to_start_f if to_start_f >= from_end_f else from_end_f
        nearest = _nearest_beat(beat_grid, cut_frame)
        beat_offset = cut_frame - int(nearest["frame"])
        beat_locked = abs(beat_offset) <= tolerance_frames

        prev_dur_f = max(1, from_end_f - from_start_f)
        next_dur_f = max(1, to_end_f - to_start_f)

        j_frames = min(base_j_frames, max(0, prev_dur_f // 2))
        l_frames = min(base_l_frames, max(0, next_dur_f // 2))

        bridge_type = default_bridge
        if j_frames > 0 and l_frames > 0 and default_bridge == AudioBridgeType.JL_OVERLAP:
            bridge_type = AudioBridgeType.JL_OVERLAP
        elif j_frames > 0 and l_frames == 0:
            bridge_type = AudioBridgeType.J_CUT
        elif l_frames > 0 and j_frames == 0:
            bridge_type = AudioBridgeType.L_CUT
        elif j_frames == 0 and l_frames == 0:
            bridge_type = AudioBridgeType.HARD_BUTT_CUT

        to_foley = (
            sc_to.diegetic_sonic.foley_cues[0]
            if (sc_to.diegetic_sonic and sc_to.diegetic_sonic.foley_cues)
            else ""
        )
        from_foley = (
            sc_from.diegetic_sonic.foley_cues[-1]
            if (sc_from.diegetic_sonic and sc_from.diegetic_sonic.foley_cues)
            else ""
        )
        if bridge_type in (AudioBridgeType.J_CUT, AudioBridgeType.JL_OVERLAP) and to_foley:
            anchor_cue = f"{to_foley} ({default_anchor})"
        elif bridge_type == AudioBridgeType.L_CUT and from_foley:
            anchor_cue = f"{from_foley} ({default_anchor})"
        else:
            anchor_cue = default_anchor

        bridges.append(
            EditBridgeSpec(
                from_scene=sc_from.scene_index,
                to_scene=sc_to.scene_index,
                cut_tc=_frames_to_smpte(cut_frame, safe_fps),
                bridge_type=bridge_type,
                j_prelap_frames=j_frames,
                l_overhang_frames=l_frames,
                bridge_duration_sec=round((j_frames + l_frames) / float(safe_fps), 3),
                nearest_beat_index=int(nearest["beat_index"]),
                beat_offset_frames=beat_offset,
                beat_locked=beat_locked,
                sonic_anchor_cue=anchor_cue,
                rationale=default_rationale,
            )
        )

    bridge_by_to_scene: Dict[int, EditBridgeSpec] = {b.to_scene: b for b in bridges}
    bridge_by_from_scene: Dict[int, EditBridgeSpec] = {b.from_scene: b for b in bridges}

    spotting_cues: List[SpottingCueEntry] = []
    mixer = getattr(bible, "master_audio_mixer", None)
    music_lufs = float(mixer.channels["music"].target_lufs) if (mixer and "music" in mixer.channels) else -18.0
    foley_lufs = float(mixer.channels["foley"].target_lufs) if (mixer and "foley" in mixer.channels) else -20.0
    amb_lufs = float(mixer.channels["ambience"].target_lufs) if (mixer and "ambience" in mixer.channels) else -24.0
    dia_lufs = float(mixer.channels["dialogue"].target_lufs) if (mixer and "dialogue" in mixer.channels) else -18.0

    for idx, (scene, start_f, end_f) in enumerate(scene_windows, start=1):
        in_bridge = bridge_by_to_scene.get(scene.scene_index)
        out_bridge = bridge_by_from_scene.get(scene.scene_index)
        j_pre = in_bridge.j_prelap_frames if in_bridge else 0
        l_over = out_bridge.l_overhang_frames if out_bridge else 0

        downbeat = _nearest_beat(beat_grid, start_f)
        downbeat_bar = max(1, int(downbeat["bar"]))

        # 1. Music Stem cue
        mus_in_f = max(0, start_f - (j_pre // 2))
        mus_out_f = min(max_end_frame, end_f + (l_over // 2))
        bgm_title = (
            bible.master_bgm.track_title
            if getattr(bible, "master_bgm", None)
            else "Master Score"
        )
        spotting_cues.append(
            SpottingCueEntry(
                cue_id=f"SPOT-MUS-S{scene.scene_index:02d}",
                scene_number=scene.scene_index,
                cue_category="music_stem",
                in_tc=_frames_to_smpte(mus_in_f, safe_fps),
                out_tc=_frames_to_smpte(mus_out_f, safe_fps),
                duration_frames=max(0, mus_out_f - mus_in_f),
                stem_target="A4 (BGM Score)",
                downbeat_bar=downbeat_bar,
                lufs_target=music_lufs,
                description=f"{bgm_title} @ {int(round(tempo_bpm))} BPM | Bar {downbeat_bar}",
            )
        )

        # 2. Hard Foley cue (carries J-Cut pre-lap)
        foley_in_f = max(0, start_f - j_pre)
        foley_out_f = end_f
        foley_desc = (
            "; ".join(scene.diegetic_sonic.foley_cues[:2])
            if (scene.diegetic_sonic and scene.diegetic_sonic.foley_cues)
            else f"{scene.scene_title} tactile Foley"
        )
        spotting_cues.append(
            SpottingCueEntry(
                cue_id=f"SPOT-SFX-S{scene.scene_index:02d}",
                scene_number=scene.scene_index,
                cue_category="foley_hard",
                in_tc=_frames_to_smpte(foley_in_f, safe_fps),
                out_tc=_frames_to_smpte(foley_out_f, safe_fps),
                duration_frames=max(0, foley_out_f - foley_in_f),
                stem_target="A2 (Foley / SFX)",
                downbeat_bar=downbeat_bar,
                lufs_target=foley_lufs,
                description=f"{foley_desc} (J-prelap {j_pre}f)",
            )
        )

        # 3. Room Tone / Ambience cue (carries L-Cut overhang)
        amb_in_f = start_f
        amb_out_f = min(max_end_frame, end_f + l_over)
        room_desc = (
            scene.diegetic_sonic.room_acoustics
            if (scene.diegetic_sonic and scene.diegetic_sonic.room_acoustics)
            else "Calibrated production room tone"
        )
        spotting_cues.append(
            SpottingCueEntry(
                cue_id=f"SPOT-AMB-S{scene.scene_index:02d}",
                scene_number=scene.scene_index,
                cue_category="room_tone",
                in_tc=_frames_to_smpte(amb_in_f, safe_fps),
                out_tc=_frames_to_smpte(amb_out_f, safe_fps),
                duration_frames=max(0, amb_out_f - amb_in_f),
                stem_target="A3 (Room Ambience)",
                downbeat_bar=downbeat_bar,
                lufs_target=amb_lufs,
                description=f"{room_desc[:90]} (L-overhang {l_over}f)",
            )
        )

        # 4. Dialogue / VO Bridge cue (when dialogue exists)
        if scene.diegetic_sonic and scene.diegetic_sonic.dialogue_lines:
            dia_in_f = max(0, start_f - (j_pre if j_pre > 0 else 0))
            dia_out_f = min(max_end_frame, end_f + l_over)
            dia_text = " / ".join(scene.diegetic_sonic.dialogue_lines[:2])
            spotting_cues.append(
                SpottingCueEntry(
                    cue_id=f"SPOT-DIA-S{scene.scene_index:02d}",
                    scene_number=scene.scene_index,
                    cue_category="dialogue_bridge",
                    in_tc=_frames_to_smpte(dia_in_f, safe_fps),
                    out_tc=_frames_to_smpte(dia_out_f, safe_fps),
                    duration_frames=max(0, dia_out_f - dia_in_f),
                    stem_target="A1 (Dialogue)",
                    downbeat_bar=downbeat_bar,
                    lufs_target=dia_lufs,
                    description=dia_text[:110],
                )
            )

    if bridges:
        mean_abs_offset = sum(abs(b.beat_offset_frames) for b in bridges) / float(len(bridges))
        beat_alignment_score = round(max(0.0, min(100.0, 100.0 - mean_abs_offset * 3.5)), 2)
    else:
        beat_alignment_score = 100.0

    total_split_edits = sum(
        1 for b in bridges if b.bridge_type != AudioBridgeType.HARD_BUTT_CUT
    )

    return SpottingManifestSpec(
        fps=safe_fps,
        tempo_bpm=tempo_bpm,
        frames_per_beat=frames_per_beat,
        bar_length_beats=bar_length_beats,
        beat_grid_tc=beat_grid_tc,
        bridges=bridges,
        spotting_cues=spotting_cues,
        beat_alignment_score=beat_alignment_score,
        total_split_edits=total_split_edits,
        recommended_nle_track_count=int(cal.get("recommended_nle_track_count", 6)),
    )


def synthesize_default_spotting_manifest(
    bible: MasterProductionBible,
    fps: int = 24,
) -> SpottingManifestSpec:
    """Synthesize a default spotting manifest for a production bible (PM-FEAT-028)."""
    return build_spotting_manifest(bible, fps=fps)


def _resolve_spotting_manifest(
    bible: MasterProductionBible,
    fps: int = 24,
) -> SpottingManifestSpec:
    if getattr(bible, "spotting_manifest", None) is not None:
        return bible.spotting_manifest  # type: ignore[return-value]
    return build_spotting_manifest(bible, fps=fps)


def format_spotting_prompt_token(
    bible: MasterProductionBible,
    scene: Optional[ScenePromptSpec] = None,
) -> str:
    """Emit standardized Gemini Omni prompt-auditable spotting & split-edit token (PM-FEAT-028)."""
    manifest = _resolve_spotting_manifest(bible)
    bpm_int = int(round(manifest.tempo_bpm))

    bridge: Optional[EditBridgeSpec] = None
    if scene is not None:
        if getattr(scene, "edit_bridge_in", None) is not None:
            bridge = scene.edit_bridge_in
        else:
            for b in manifest.bridges:
                if b.to_scene == scene.scene_index:
                    bridge = b
                    break
    if bridge is None and manifest.bridges:
        bridge = manifest.bridges[0]

    if bridge is not None:
        b_type = (
            bridge.bridge_type.value
            if hasattr(bridge.bridge_type, "value")
            else str(bridge.bridge_type)
        )
        j_f = int(bridge.j_prelap_frames)
        l_f = int(bridge.l_overhang_frames)
        offset_f = int(bridge.beat_offset_frames)
    else:
        _, cal = _resolve_tempo_and_calibration(bible)
        raw_b = cal["default_bridge_type"]
        b_type = raw_b.value if hasattr(raw_b, "value") else str(raw_b)
        j_f = int(cal.get("j_prelap_frames", 8))
        l_f = int(cal.get("l_overhang_frames", 0))
        offset_f = 0

    return (
        f"[SPOTTING_SYNC: bpm={bpm_int} bridge={b_type} "
        f"jcut={j_f}f lcut={l_f}f beat_offset={offset_f}f]"
    )


def build_split_edit_edl_text(
    bible: MasterProductionBible,
    fps: int = 24,
) -> str:
    """Build a CMX 3600 split-edit EDL string with staggered V / A / A2 J-Cut and L-Cut events."""
    safe_fps = max(1, int(fps))
    manifest = _resolve_spotting_manifest(bible, fps=safe_fps)

    scenes = list(bible.scenes or [])
    total_scenes = max(1, len(scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)

    bridge_in_map = {b.to_scene: b for b in manifest.bridges}
    bridge_out_map = {b.from_scene: b for b in manifest.bridges}

    lines = [
        f"TITLE: {bible.project_title.upper()[:56]} SPLIT EDITS",
        "FCM: NON-DROP FRAME",
        f"* TEMPO: {manifest.tempo_bpm:.1f} BPM | FRAMES/BEAT: {manifest.frames_per_beat:.2f} | BEAT ALIGNMENT: {manifest.beat_alignment_score:.1f}%",
        "",
    ]

    event_num = 1
    for idx, scene in enumerate(scenes, start=1):
        s_start, s_end = _parse_scene_window(scene, idx, total_scenes, total_runtime)
        start_f = max(0, int(round(s_start * safe_fps)))
        end_f = max(start_f + safe_fps, int(round(s_end * safe_fps)))
        dur_f = end_f - start_f

        in_b = bridge_in_map.get(scene.scene_index)
        out_b = bridge_out_map.get(scene.scene_index)
        j_pre = in_b.j_prelap_frames if in_b else 0
        l_over = out_b.l_overhang_frames if out_b else 0

        v_src_in = _frames_to_smpte(0, safe_fps)
        v_src_out = _frames_to_smpte(dur_f, safe_fps)
        v_rec_in = _frames_to_smpte(start_f, safe_fps)
        v_rec_out = _frames_to_smpte(end_f, safe_fps)

        lines.append(
            f"{event_num:03d}  AX       V     C        {v_src_in} {v_src_out} {v_rec_in} {v_rec_out}"
        )
        event_num += 1

        a_rec_start = max(0, start_f - j_pre)
        a_rec_end = end_f + l_over
        actual_j = start_f - a_rec_start
        a_src_in = _frames_to_smpte(0, safe_fps)
        a_src_out = _frames_to_smpte(max(1, a_rec_end - a_rec_start), safe_fps)
        a_rec_in_tc = _frames_to_smpte(a_rec_start, safe_fps)
        a_rec_out_tc = _frames_to_smpte(a_rec_end, safe_fps)

        lines.append(
            f"{event_num:03d}  AX       A     C        {a_src_in} {a_src_out} {a_rec_in_tc} {a_rec_out_tc}"
        )
        event_num += 1

        lines.append(
            f"{event_num:03d}  AX       A2    C        {a_src_in} {a_src_out} {a_rec_in_tc} {a_rec_out_tc}"
        )
        event_num += 1

        lines.append(f"* FROM CLIP NAME: SCENE_{scene.scene_index:02d}_PLATE.MP4")
        if in_b and out_b:
            in_type = in_b.bridge_type.value if hasattr(in_b.bridge_type, "value") else str(in_b.bridge_type)
            out_type = out_b.bridge_type.value if hasattr(out_b.bridge_type, "value") else str(out_b.bridge_type)
            lines.append(
                f"* AUDIO BRIDGE: IN={in_type.upper()} (BEAT_OFFSET={in_b.beat_offset_frames:+d}F, {in_b.sonic_anchor_cue}) | "
                f"OUT={out_type.upper()} (BEAT_OFFSET={out_b.beat_offset_frames:+d}F, {out_b.sonic_anchor_cue}) | "
                f"J_PRELAP={actual_j}F | L_OVERHANG={l_over}F"
            )
        else:
            active_bridge = in_b or out_b
            b_type = (
                active_bridge.bridge_type.value
                if (active_bridge and hasattr(active_bridge.bridge_type, "value"))
                else str(active_bridge.bridge_type) if active_bridge else "hard_butt_cut"
            )
            beat_off = active_bridge.beat_offset_frames if active_bridge else 0
            anchor = active_bridge.sonic_anchor_cue if active_bridge else scene.scene_title
            lines.append(
                f"* AUDIO BRIDGE: {b_type.upper()} | J_PRELAP={actual_j}F | L_OVERHANG={l_over}F | "
                f"BEAT_OFFSET={beat_off:+d}F | {anchor}"
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def export_split_edit_edl(
    bible: MasterProductionBible,
    output_path: Union[str, Path],
    fps: int = 24,
) -> Path:
    """Export a CMX 3600 split-edit EDL with staggered V / A / A2 J-Cut and L-Cut events."""
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    edl_text = build_split_edit_edl_text(bible, fps=fps)
    out_p.write_text(edl_text, encoding="utf-8")
    return out_p


def export_spotting_cue_sheet_csv(
    bible: MasterProductionBible,
    output_path: Union[str, Path],
    fps: int = 24,
) -> Path:
    """Export Music & Foley Spotting Cue Sheet CSV (PM-FEAT-028)."""
    manifest = _resolve_spotting_manifest(bible, fps=fps)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "cue_id",
            "scene_number",
            "cue_category",
            "in_tc",
            "out_tc",
            "duration_frames",
            "stem_target",
            "downbeat_bar",
            "lufs_target",
            "description",
        ]
    )
    for cue in manifest.spotting_cues:
        writer.writerow(
            [
                cue.cue_id,
                cue.scene_number,
                cue.cue_category,
                cue.in_tc,
                cue.out_tc,
                cue.duration_frames,
                cue.stem_target,
                cue.downbeat_bar,
                f"{cue.lufs_target:.1f}",
                cue.description,
            ]
        )

    out_p.write_text(buffer.getvalue(), encoding="utf-8")
    return out_p


def export_spotting_sheet_md(
    bible: MasterProductionBible,
    output_path: Union[str, Path],
    fps: int = 24,
) -> Path:
    """Export Markdown Editorial Spotting & J-Cut/L-Cut Bridge Sheet (PM-FEAT-028)."""
    manifest = _resolve_spotting_manifest(bible, fps=fps)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Editorial Spotting & Audio Bridge Sheet: {bible.project_title}",
        "",
        f"- **FPS**: `{manifest.fps} fps` (Non-Drop Frame)",
        f"- **Tempo**: `{manifest.tempo_bpm:.1f} BPM` (`{manifest.frames_per_beat:.2f}` frames/beat, `{manifest.bar_length_beats}/4` meter)",
        f"- **Beat Alignment Score**: `{manifest.beat_alignment_score:.1f} / 100.0`",
        f"- **Total Split Edits**: `{manifest.total_split_edits}` | **Recommended NLE Audio Tracks**: `{manifest.recommended_nle_track_count}`",
        "",
        "## 1. J-Cut / L-Cut Scene Transitions",
        "",
        "| Cut | Timecode | Bridge Type | J-Prelap (f) | L-Overhang (f) | Beat Offset (f) | Locked | Sonic Anchor |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for b in manifest.bridges:
        b_type = b.bridge_type.value if hasattr(b.bridge_type, "value") else str(b.bridge_type)
        lines.append(
            f"| S{b.from_scene:02d}->S{b.to_scene:02d} | `{b.cut_tc}` | `{b_type}` | "
            f"{b.j_prelap_frames} | {b.l_overhang_frames} | {b.beat_offset_frames:+d} | "
            f"{'YES' if b.beat_locked else 'DRIFT'} | {b.sonic_anchor_cue} |"
        )

    lines.extend(
        [
            "",
            "## 2. Music, Foley & Room-Tone Spotting Cues",
            "",
            "| Cue ID | Scene | Category | In TC | Out TC | Dur (f) | Stem Target | Bar | LUFS | Description |",
            "|---|---:|---|---|---|---:|---|---:|---:|---|",
        ]
    )
    for c in manifest.spotting_cues:
        lines.append(
            f"| `{c.cue_id}` | {c.scene_number} | `{c.cue_category}` | `{c.in_tc}` | `{c.out_tc}` | "
            f"{c.duration_frames} | {c.stem_target} | {c.downbeat_bar} | {c.lufs_target:.1f} | {c.description} |"
        )

    out_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_p


def export_spotting_manifest_json(
    bible: MasterProductionBible,
    output_path: Union[str, Path],
    fps: int = 24,
) -> Path:
    """Export SpottingManifestSpec as formatted JSON to disk (PM-FEAT-028)."""
    manifest = _resolve_spotting_manifest(bible, fps=fps)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return out_p


def export_spotting_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    fps: int = 24,
) -> Dict[str, Path]:
    """Export complete PM-FEAT-028 spotting and split-edit EDL bundle into `output_dir`."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_p = export_spotting_manifest_json(bible, out_dir / "spotting_manifest.json", fps=fps)
    csv_p = export_spotting_cue_sheet_csv(bible, out_dir / "spotting_cue_sheet.csv", fps=fps)
    md_p = export_spotting_sheet_md(bible, out_dir / "spotting_sheet.md", fps=fps)
    edl_p = export_split_edit_edl(bible, out_dir / "timeline_split_edits.edl", fps=fps)

    return {
        "spotting_manifest_json": json_p,
        "spotting_cue_sheet_csv": csv_p,
        "spotting_sheet_md": md_p,
        "timeline_split_edits_edl": edl_p,
    }
