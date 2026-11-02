"""SMPTE Dialogue Pacing Guardrail & Closed Caption Suite (SRT & WebVTT)."""

from __future__ import annotations

import re
from typing import List, Tuple

from omni_director.schemas import MasterProductionBible, ScenePromptSpec
from omni_director.tools.nle_export import _parse_scene_window

MAX_RECOMMENDED_WPS = 2.5


def _extract_spoken_words(dialogue_lines: List[str]) -> List[str]:
    """Extract spoken words from dialogue lines, stripping speaker prefixes and quotes."""
    words: List[str] = []
    for line in dialogue_lines:
        cleaned = re.sub(r"^[A-Za-z0-9_\-\s]{1,25}:\s*", "", str(line).strip())
        cleaned = cleaned.strip("\"'“”‘’")
        tokens = [w for w in re.split(r"\s+", cleaned) if w]
        words.extend(tokens)
    return words


def audit_dialogue_pacing(
    scene: ScenePromptSpec,
    scene_duration_sec: float = 8.0,
) -> Tuple[bool, float, List[str]]:
    """Audit spoken dialogue rate (words per second) against the 2.5 WPS kinematic ceiling.

    Returns:
        Tuple of (passed, words_per_second, warnings).
    """
    duration = max(1.0, float(scene_duration_sec or 8.0))
    dialogue_lines: List[str] = []
    if scene.diegetic_sonic and scene.diegetic_sonic.dialogue_lines:
        dialogue_lines = list(scene.diegetic_sonic.dialogue_lines)

    words = _extract_spoken_words(dialogue_lines)
    wps = round(len(words) / duration, 2)
    warnings: List[str] = []
    passed = True

    if wps > MAX_RECOMMENDED_WPS:
        passed = False
        warnings.append(
            f"Scene {scene.scene_index} dialogue speech rate is {wps:.2f} WPS "
            f"({len(words)} words in {duration:.1f}s), exceeding the {MAX_RECOMMENDED_WPS} WPS "
            "cinematic lip-sync ceiling. Trim spoken dialogue to <= 20 words per 8s clip."
        )

    return passed, wps, warnings


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm for SubRip (.srt)."""
    total_ms = max(0, int(round(seconds * 1000)))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm for WebVTT (.vtt)."""
    total_ms = max(0, int(round(seconds * 1000)))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}"


def _build_scene_caption_cues(bible: MasterProductionBible) -> List[Tuple[float, float, str]]:
    """Build (start_sec, end_sec, caption_text) cues across all scenes."""
    cues: List[Tuple[float, float, str]] = []
    total_scenes = max(1, len(bible.scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)

    for idx, scene in enumerate(bible.scenes, start=1):
        scene_start, scene_end = _parse_scene_window(
            scene, idx, total_scenes, total_runtime
        )
        scene_dur = max(1.0, scene_end - scene_start)
        dialogue = (
            scene.diegetic_sonic.dialogue_lines
            if (scene.diegetic_sonic and scene.diegetic_sonic.dialogue_lines)
            else []
        )
        foley = (
            scene.diegetic_sonic.foley_cues
            if (scene.diegetic_sonic and scene.diegetic_sonic.foley_cues)
            else []
        )
        room = (
            scene.diegetic_sonic.room_acoustics
            if scene.diegetic_sonic
            else "Studio acoustics"
        )

        if dialogue:
            step = scene_dur / len(dialogue)
            for d_idx, line in enumerate(dialogue):
                c_start = scene_start + d_idx * step
                c_end = scene_start + (d_idx + 1) * step
                cues.append((c_start, c_end, str(line).strip()))
        else:
            primary_foley = foley[0] if foley else room
            cues.append(
                (
                    scene_start,
                    scene_end,
                    f"[SFX: {primary_foley}]",
                )
            )
    return cues


def compile_subtitles_srt(bible: MasterProductionBible, fps: int = 24) -> str:
    """Compile synchronized SubRip (.srt) closed captions for the production bible."""
    del fps
    cues = _build_scene_caption_cues(bible)
    blocks: List[str] = []
    for idx, (start_sec, end_sec, text) in enumerate(cues, start=1):
        blocks.append(
            f"{idx}\n"
            f"{_format_srt_timestamp(start_sec)} --> {_format_srt_timestamp(end_sec)}\n"
            f"{text}"
        )
    return "\n\n".join(blocks) + "\n"


def compile_subtitles_vtt(bible: MasterProductionBible) -> str:
    """Compile synchronized WebVTT (.vtt) closed captions for HTML5 players."""
    cues = _build_scene_caption_cues(bible)
    blocks: List[str] = ["WEBVTT", ""]
    for idx, (start_sec, end_sec, text) in enumerate(cues, start=1):
        blocks.append(
            f"cue-{idx}\n"
            f"{_format_vtt_timestamp(start_sec)} --> {_format_vtt_timestamp(end_sec)}\n"
            f"{text}\n"
        )
    return "\n".join(blocks).strip() + "\n"
