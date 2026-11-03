"""Post-production diegetic audio stem mixing, Fairlight / Premiere routing, and loudness suite."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Union

from omni_director.schemas import (
    AudioStemMixerSpec,
    MasterProductionBible,
    StemChannelStrip,
    StemType,
)


def synthesize_default_stem_mixer(master_lufs_target: float = -23.0) -> AudioStemMixerSpec:
    """Creates a 4-channel studio mixing console specification (Dialogue, Foley, Ambience, Music)."""
    return AudioStemMixerSpec(
        master_gain_db=0.0,
        master_lufs_target=float(master_lufs_target),
        channels={
            "dialogue": StemChannelStrip(
                stem=StemType.DIALOGUE,
                label="Dialogue",
                gain_db=0.0,
                pan=0.0,
                muted=False,
                solo=False,
                target_lufs=-18.0,
            ),
            "foley": StemChannelStrip(
                stem=StemType.FOLEY,
                label="Foley / SFX",
                gain_db=0.0,
                pan=0.0,
                muted=False,
                solo=False,
                target_lufs=-20.0,
            ),
            "ambience": StemChannelStrip(
                stem=StemType.AMBIENCE,
                label="Room Ambience",
                gain_db=-3.0,
                pan=0.0,
                muted=False,
                solo=False,
                target_lufs=-24.0,
            ),
            "music": StemChannelStrip(
                stem=StemType.MUSIC,
                label="BGM Score",
                gain_db=-2.0,
                pan=0.0,
                muted=False,
                solo=False,
                target_lufs=-18.0,
            ),
        },
    )


def estimate_broadcast_loudness(mixer: AudioStemMixerSpec) -> Dict[str, float]:
    """Calculates estimated integrated LUFS and True Peak dBFS across active mixer channels."""
    has_solo = any(ch.solo for ch in mixer.channels.values())

    total_power = 0.0
    for ch in mixer.channels.values():
        if ch.muted:
            continue
        if has_solo and not ch.solo:
            continue
        # Effective channel power = target_lufs + gain_db
        effective_db = ch.target_lufs + ch.gain_db
        power = 10.0 ** (effective_db / 10.0)
        total_power += power

    if total_power <= 0.0:
        integrated_lufs = -70.0
    else:
        integrated_lufs = 10.0 * math.log10(total_power) + mixer.master_gain_db

    crest_factor_db = 14.0
    true_peak_dbfs = min(0.0, integrated_lufs + crest_factor_db)

    return {
        "integrated_lufs": round(integrated_lufs, 2),
        "true_peak_dbfs": round(true_peak_dbfs, 2),
        "target_lufs": round(mixer.master_lufs_target, 2),
        "compliant_ebu_r128": float(abs(integrated_lufs - (-23.0)) <= 1.0),
        "compliant_atsc_a85": float(abs(integrated_lufs - (-24.0)) <= 1.0),
    }


def export_audio_stems_manifest(bible: MasterProductionBible) -> Dict[str, Any]:
    """Author DaVinci Resolve / Fairlight and Adobe Premiere Pro 4-stem track routing layout."""
    mixer = bible.master_audio_mixer or synthesize_default_stem_mixer()
    loudness = estimate_broadcast_loudness(mixer)

    tracks = []
    track_num = 1
    for stem_key in ["dialogue", "foley", "ambience", "music"]:
        strip = mixer.get(stem_key)
        if not strip:
            continue
        stem_val = strip.stem.value if hasattr(strip.stem, "value") else str(strip.stem)
        tracks.append({
            "track_index": track_num,
            "stem_type": stem_val,
            "label": strip.label,
            "gain_db": strip.gain_db,
            "pan": strip.pan,
            "muted": strip.muted,
            "solo": strip.solo,
            "target_lufs": strip.target_lufs,
            "channel_format": "stereo",
            "fairlight_bus": f"Submix {track_num} ({strip.label[:3].upper()})",
            "premiere_track": f"A{track_num} ({strip.label})",
        })
        track_num += 1

    dia_strip = mixer.get("dialogue")
    sfx_strip = mixer.get("foley")
    amb_strip = mixer.get("ambience")
    mus_strip = mixer.get("music")

    return {
        "project_title": bible.project_title,
        "master_lufs_target": mixer.master_lufs_target,
        "master_gain_db": mixer.master_gain_db,
        "loudness_estimate": loudness,
        "stems": tracks,
        "fairlight_routing": {
            "bus_format": "5.1 Surround / Stereo Folddown",
            "submixes": [
                {"bus": "Sub 1 (DIA)", "tracks": ["A1"], "target": "Dialogue Clarity"},
                {"bus": "Sub 2 (SFX)", "tracks": ["A2"], "target": "Tactile Dynamics"},
                {"bus": "Sub 3 (AMB)", "tracks": ["A3"], "target": "Acoustic Bed"},
                {"bus": "Sub 4 (MUS)", "tracks": ["A4"], "target": "Sidechained Score"},
            ],
            "master_bus": "Main 1 (Stereo)",
        },
        "premiere_layout": {
            "master_track_type": "Stereo",
            "tracks": [
                {"name": "Dialogue", "type": "Standard", "gain_db": dia_strip.gain_db if dia_strip else 0.0},
                {"name": "Foley / SFX", "type": "Standard", "gain_db": sfx_strip.gain_db if sfx_strip else 0.0},
                {"name": "Ambience", "type": "Standard", "gain_db": amb_strip.gain_db if amb_strip else -3.0},
                {"name": "Music", "type": "Standard", "gain_db": mus_strip.gain_db if mus_strip else -2.0},
            ],
        },
    }


def export_audio_stems_file(bible: MasterProductionBible, output_path: Union[str, Path]) -> Path:
    """Writes the audio stems manifest JSON to disk and returns the Path."""
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    manifest = export_audio_stems_manifest(bible)
    out_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_p
