"""Voice Casting, Preston Blair Viseme Lip-Sync Timing & Automated Stem Sidechain Ducking (PM-FEAT-038)."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.presets import classify_brief_domain
from omni_director.schemas import (
    MasterProductionBible,
    MasterVoiceDuckingManifest,
    ScenePromptSpec,
    SceneVoiceDuckingSpec,
    SidechainDuckingKeyframe,
    VisemeClassEnum,
    VisemeLipSyncCue,
    VocalRegisterEnum,
    VoiceCastingProfile,
)
from omni_director.tools.dialogue import MAX_RECOMMENDED_WPS, _extract_spoken_words
from omni_director.tools.nle_export import _parse_scene_window, _seconds_to_smpte_frames

_DOMAIN_VOICE_PRESETS: Dict[str, Dict[str, Any]] = {
    "culinary_asmr": {
        "register": VocalRegisterEnum.WHISPER_ASMR,
        "timbre": "Intimate close-mic breathy whisper with crisp consonant presence",
        "mic_perspective": "asmr_binaural_neumann_ku100",
        "target_wpm": 105.0,
        "pitch_hz_range": "130-210 Hz",
        "music_duck_db": -9.0,
        "ambience_duck_db": -4.0,
    },
    "automotive_robotics": {
        "register": VocalRegisterEnum.BARITONE,
        "timbre": "Grounded precision engineering baritone with authoritative chest resonance",
        "mic_perspective": "vo_booth_neumann_u87",
        "target_wpm": 130.0,
        "pitch_hz_range": "95-155 Hz",
        "music_duck_db": -8.0,
        "ambience_duck_db": -5.0,
    },
    "luxury_fashion": {
        "register": VocalRegisterEnum.MEZZO_SOPRANO,
        "timbre": "Velvet editorial poise with controlled breath and warm mid-band glow",
        "mic_perspective": "vo_booth_sony_c800g",
        "target_wpm": 115.0,
        "pitch_hz_range": "165-245 Hz",
        "music_duck_db": -7.5,
        "ambience_duck_db": -4.5,
    },
    "kinetic_action": {
        "register": VocalRegisterEnum.TENOR,
        "timbre": "Urgent percussive projection with transient punch and zero sibilance",
        "mic_perspective": "boom_schoeps_cmit5u",
        "target_wpm": 142.0,
        "pitch_hz_range": "125-195 Hz",
        "music_duck_db": -8.5,
        "ambience_duck_db": -5.5,
    },
    "tech_hardware": {
        "register": VocalRegisterEnum.SYNTHETIC_NEURAL,
        "timbre": "Clean studio-calibrated precision diction with micro-transient clarity",
        "mic_perspective": "vo_booth_sennheiser_mkh416",
        "target_wpm": 135.0,
        "pitch_hz_range": "120-185 Hz",
        "music_duck_db": -8.0,
        "ambience_duck_db": -4.5,
    },
    "architectural_sanctuary": {
        "register": VocalRegisterEnum.ALTO,
        "timbre": "Warm natural room-tone alto with unhurried spatial cadence",
        "mic_perspective": "vo_booth_neumann_u87",
        "target_wpm": 118.0,
        "pitch_hz_range": "145-220 Hz",
        "music_duck_db": -8.0,
        "ambience_duck_db": -4.0,
    },
}


def _safe_id_slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", (text or "").strip()).strip("_")
    return cleaned.upper() or "TALENT"


def _map_words_to_visemes(words: List[str], max_visemes: int = 12) -> List[VisemeClassEnum]:
    """Deterministically maps spoken English tokens to Preston Blair VisemeClassEnum sequences."""
    if not words:
        return [VisemeClassEnum.SIL]

    visemes: List[VisemeClassEnum] = []
    joined = " ".join(words).lower()
    i = 0
    while i < len(joined) and len(visemes) < max_visemes:
        two = joined[i : i + 2]
        ch = joined[i]
        v: Optional[VisemeClassEnum] = None
        if two == "th":
            v = VisemeClassEnum.TH
            i += 2
        elif two in ("ch", "sh", "zh"):
            v = VisemeClassEnum.CH
            i += 2
        elif two in ("oo", "ou", "ow"):
            v = VisemeClassEnum.OO
            i += 2
        elif two in ("ee", "ea", "ie"):
            v = VisemeClassEnum.EE
            i += 2
        else:
            i += 1
            if ch in ("p", "b", "m"):
                v = VisemeClassEnum.PP
            elif ch in ("f", "v"):
                v = VisemeClassEnum.FF
            elif ch in ("t", "d"):
                v = VisemeClassEnum.DD
            elif ch in ("k", "g", "q", "c"):
                v = VisemeClassEnum.KK
            elif ch in ("s", "z", "x"):
                v = VisemeClassEnum.SS
            elif ch in ("n", "l"):
                v = VisemeClassEnum.NN
            elif ch == "r":
                v = VisemeClassEnum.RR
            elif ch in ("a",):
                v = VisemeClassEnum.AA
            elif ch in ("e", "i", "y"):
                v = VisemeClassEnum.EE
            elif ch in ("o", "u", "w"):
                v = VisemeClassEnum.OO
            elif ch == " ":
                continue
        if v is not None and (not visemes or visemes[-1] != v):
            visemes.append(v)

    return visemes or [VisemeClassEnum.AA, VisemeClassEnum.NN, VisemeClassEnum.SIL]


def _extract_speaker_and_line(raw_line: str) -> Tuple[str, str]:
    text = str(raw_line or "").strip()
    m = re.match(r"^([A-Za-z0-9_\-\s]{1,25}):\s*(.+)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip().strip("\"'“”‘’")
    return "", text.strip("\"'“”‘’")


def _build_casting_roster(
    bible: MasterProductionBible,
    domain_cfg: Dict[str, Any],
) -> List[VoiceCastingProfile]:
    roster: List[VoiceCastingProfile] = []
    characters = list(getattr(bible, "characters", None) or [])
    base_wpm = min(150.0, float(domain_cfg.get("target_wpm", 125.0) or 125.0))
    base_reg = domain_cfg.get("register", VocalRegisterEnum.ALTO)
    alt_registers = [
        base_reg,
        VocalRegisterEnum.BARITONE if base_reg != VocalRegisterEnum.BARITONE else VocalRegisterEnum.MEZZO_SOPRANO,
        VocalRegisterEnum.TENOR,
    ]

    for idx, ch in enumerate(characters, start=1):
        name = str(getattr(ch, "name", f"Character {idx}") or f"Character {idx}").strip()
        char_id = f"CHAR_{idx:02d}_{_safe_id_slug(name)[:18]}"
        sil = str(getattr(ch, "silhouette", "") or "").lower()
        reg = alt_registers[(idx - 1) % len(alt_registers)]
        if "whisper" in sil or "asmr" in sil:
            reg = VocalRegisterEnum.WHISPER_ASMR
        pitch = "95-155 Hz" if reg in (VocalRegisterEnum.BARITONE, VocalRegisterEnum.BASS) else (
            "120-185 Hz" if reg in (VocalRegisterEnum.TENOR, VocalRegisterEnum.SYNTHETIC_NEURAL) else "155-235 Hz"
        )
        roster.append(
            VoiceCastingProfile(
                character_id=char_id,
                character_name=name,
                vocal_register=reg,
                timbre_descriptors=str(domain_cfg.get("timbre", "Balanced studio timbre")),
                mic_perspective=str(domain_cfg.get("mic_perspective", "vo_booth_neumann_u87")),
                target_wpm=base_wpm,
                pitch_hz_range=pitch,
                delivery_notes=f"Aligned to {getattr(ch, 'movement_signature', 'natural cadence')[:80]}",
            )
        )
    return roster


def _ensure_narrator_profile(
    roster: List[VoiceCastingProfile],
    domain_cfg: Dict[str, Any],
) -> VoiceCastingProfile:
    for p in roster:
        if p.character_id == "VO_NARRATOR":
            return p
    narrator = VoiceCastingProfile(
        character_id="VO_NARRATOR",
        character_name="Narrator / Audio Description VO",
        vocal_register=domain_cfg.get("register", VocalRegisterEnum.ALTO),
        timbre_descriptors=str(domain_cfg.get("timbre", "Warm calibrated studio narrator")),
        mic_perspective=str(domain_cfg.get("mic_perspective", "vo_booth_neumann_u87")),
        target_wpm=min(150.0, float(domain_cfg.get("target_wpm", 125.0) or 125.0)),
        pitch_hz_range=str(domain_cfg.get("pitch_hz_range", "110-190 Hz")),
        delivery_notes="Primary off-camera voiceover & CVAA audio description anchor.",
    )
    roster.append(narrator)
    return narrator


def _collect_ad_cues_for_scene(bible: MasterProductionBible, scene: ScenePromptSpec) -> List[Any]:
    sc_idx = int(getattr(scene, "scene_index", 1) or 1)
    cues: List[Any] = []
    sc_acc = getattr(scene, "accessibility_spec", None)
    if sc_acc is not None and getattr(sc_acc, "ad_cues", None):
        cues.extend(list(sc_acc.ad_cues))
    master_acc = getattr(bible, "master_accessibility_spec", None)
    if not cues and master_acc is not None:
        for prof in (getattr(master_acc, "scene_profiles", None) or []):
            if int(getattr(prof, "scene_number", 0) or 0) == sc_idx and getattr(prof, "ad_cues", None):
                cues.extend(list(prof.ad_cues))
                break
    return cues


def compile_voice_ducking_manifest(
    bible: MasterProductionBible,
    domain_profile: Optional[Dict[str, Any]] = None,
) -> MasterVoiceDuckingManifest:
    """Compiles Voice Casting, Preston Blair Viseme Lip-Sync & Sidechain Ducking Manifest (PM-FEAT-038)."""
    raw_domain = getattr(bible, "domain_archetype", None)
    if raw_domain is None:
        raw_domain = classify_brief_domain(
            f"{getattr(bible, 'project_title', '')} {getattr(bible, 'logline', '')}"
        ).value
    domain_str = raw_domain.value if hasattr(raw_domain, "value") else str(raw_domain)

    domain_cfg = dict(_DOMAIN_VOICE_PRESETS.get(domain_str, _DOMAIN_VOICE_PRESETS["architectural_sanctuary"]))
    if domain_profile:
        domain_cfg.update(domain_profile)

    music_duck_db = max(-24.0, min(-1.0, float(domain_cfg.get("music_duck_db", -8.0))))
    ambience_duck_db = max(-24.0, min(-0.5, float(domain_cfg.get("ambience_duck_db", -4.5))))
    snr_min_db = 6.0

    roster = _build_casting_roster(bible, domain_cfg)
    char_by_name = {p.character_name.lower(): p.character_id for p in roster}

    scenes = list(getattr(bible, "scenes", None) or [])
    total_scenes = max(1, len(scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)

    scene_profiles: List[SceneVoiceDuckingSpec] = []
    total_cues = 0
    passing_cues = 0
    used_narrator = len(roster) == 0

    for idx, scene in enumerate(scenes, start=1):
        sc_idx = int(getattr(scene, "scene_index", idx) or idx)
        sc_start, sc_end = _parse_scene_window(scene, idx, total_scenes, total_runtime)
        sc_start = max(0.0, sc_start)
        sc_dur = max(1.0, sc_end - sc_start)

        diegetic = getattr(scene, "diegetic_sonic", None)
        dialogue_lines = list(getattr(diegetic, "dialogue_lines", None) or []) if diegetic else []
        ad_cues = _collect_ad_cues_for_scene(bible, scene)

        viseme_cues: List[VisemeLipSyncCue] = []
        keyframes: List[SidechainDuckingKeyframe] = []
        active_speakers: List[str] = []

        if dialogue_lines:
            step = sc_dur / max(1, len(dialogue_lines))
            for d_idx, raw_line in enumerate(dialogue_lines):
                spk_name, clean_text = _extract_speaker_and_line(str(raw_line))
                speaker_id = ""
                on_camera = False
                if spk_name:
                    speaker_id = char_by_name.get(spk_name.lower(), "")
                    if not speaker_id:
                        for cname, cid in char_by_name.items():
                            if spk_name.lower() in cname or cname in spk_name.lower():
                                speaker_id = cid
                                break
                if not speaker_id and roster and spk_name.lower() not in ("narrator", "vo", "voiceover"):
                    speaker_id = roster[0].character_id
                if not speaker_id:
                    speaker_id = "VO_NARRATOR"
                    used_narrator = True
                else:
                    on_camera = speaker_id != "VO_NARRATOR"

                words = _extract_spoken_words([clean_text])
                c_start = round(sc_start + d_idx * step + 0.15, 3)
                c_end = round(min(sc_end, sc_start + (d_idx + 1) * step - 0.1), 3)
                if c_end <= c_start:
                    c_end = round(c_start + max(0.5, step * 0.8), 3)
                c_dur = max(0.5, c_end - c_start)
                wps = round(len(words) / c_dur, 2)

                total_cues += 1
                if wps <= MAX_RECOMMENDED_WPS:
                    passing_cues += 1

                if speaker_id not in active_speakers:
                    active_speakers.append(speaker_id)

                viseme_cues.append(
                    VisemeLipSyncCue(
                        scene_index=sc_idx,
                        speaker_id=speaker_id,
                        line_text=clean_text,
                        start_sec=c_start,
                        end_sec=c_end,
                        word_count=len(words),
                        wps=wps,
                        dominant_visemes=_map_words_to_visemes(words),
                        lip_sync_required_on_camera=on_camera,
                    )
                )
                keyframes.extend([
                    SidechainDuckingKeyframe(
                        time_sec=c_start,
                        trigger_stem="dialogue",
                        target_stem="music",
                        attenuation_db=music_duck_db,
                        attack_ms=40,
                        release_ms=300,
                        scene_index=sc_idx,
                    ),
                    SidechainDuckingKeyframe(
                        time_sec=c_start,
                        trigger_stem="dialogue",
                        target_stem="ambience",
                        attenuation_db=ambience_duck_db,
                        attack_ms=40,
                        release_ms=300,
                        scene_index=sc_idx,
                    ),
                    SidechainDuckingKeyframe(
                        time_sec=c_end,
                        trigger_stem="dialogue",
                        target_stem="music",
                        attenuation_db=0.0,
                        attack_ms=40,
                        release_ms=300,
                        scene_index=sc_idx,
                    ),
                    SidechainDuckingKeyframe(
                        time_sec=c_end,
                        trigger_stem="dialogue",
                        target_stem="ambience",
                        attenuation_db=0.0,
                        attack_ms=40,
                        release_ms=300,
                        scene_index=sc_idx,
                    ),
                ])

        # Also emit ducking & viseme cues for Audio Description cues if present (or as fallback when no dialogue)
        if ad_cues:
            used_narrator = True
            if "VO_NARRATOR" not in active_speakers:
                active_speakers.append("VO_NARRATOR")
            for ad in ad_cues:
                ad_text = str(getattr(ad, "descriptive_prose", "") or "").strip()
                ad_start = max(sc_start, float(getattr(ad, "start_time_sec", sc_start) or sc_start))
                ad_end = max(ad_start + 0.5, float(getattr(ad, "end_time_sec", min(sc_end, ad_start + 4.0)) or (ad_start + 4.0)))
                words = _extract_spoken_words([ad_text])
                ad_dur = max(0.5, ad_end - ad_start)
                wps = round(len(words) / ad_dur, 2)
                if wps > MAX_RECOMMENDED_WPS:
                    max_words = max(1, int(ad_dur * MAX_RECOMMENDED_WPS))
                    words = words[:max_words]
                    ad_text = " ".join(words)
                    wps = round(len(words) / ad_dur, 2)

                total_cues += 1
                if wps <= MAX_RECOMMENDED_WPS:
                    passing_cues += 1

                if not dialogue_lines:
                    viseme_cues.append(
                        VisemeLipSyncCue(
                            scene_index=sc_idx,
                            speaker_id="VO_NARRATOR",
                            line_text=ad_text,
                            start_sec=round(ad_start, 3),
                            end_sec=round(ad_end, 3),
                            word_count=len(words),
                            wps=wps,
                            dominant_visemes=_map_words_to_visemes(words),
                            lip_sync_required_on_camera=False,
                        )
                    )
                keyframes.extend([
                    SidechainDuckingKeyframe(
                        time_sec=round(ad_start, 3),
                        trigger_stem="audio_description",
                        target_stem="music",
                        attenuation_db=music_duck_db,
                        attack_ms=40,
                        release_ms=300,
                        scene_index=sc_idx,
                    ),
                    SidechainDuckingKeyframe(
                        time_sec=round(ad_start, 3),
                        trigger_stem="audio_description",
                        target_stem="ambience",
                        attenuation_db=ambience_duck_db,
                        attack_ms=40,
                        release_ms=300,
                        scene_index=sc_idx,
                    ),
                    SidechainDuckingKeyframe(
                        time_sec=round(ad_end, 3),
                        trigger_stem="audio_description",
                        target_stem="music",
                        attenuation_db=0.0,
                        attack_ms=40,
                        release_ms=300,
                        scene_index=sc_idx,
                    ),
                    SidechainDuckingKeyframe(
                        time_sec=round(ad_end, 3),
                        trigger_stem="audio_description",
                        target_stem="ambience",
                        attenuation_db=0.0,
                        attack_ms=40,
                        release_ms=300,
                        scene_index=sc_idx,
                    ),
                ])
        elif not dialogue_lines:
            # Fallback concise VO narrative cue derived from scene title/beats (strictly <= 2.5 WPS)
            used_narrator = True
            active_speakers.append("VO_NARRATOR")
            raw_title = str(getattr(scene, "scene_title", f"Scene {sc_idx}") or f"Scene {sc_idx}").strip()
            fallback_line = f"{raw_title} unfolds with precision."
            c_start = round(sc_start + 0.5, 3)
            c_end = round(max(c_start + 2.0, sc_end - 0.5), 3)
            c_dur = max(1.0, c_end - c_start)
            words = _extract_spoken_words([fallback_line])
            max_words = max(1, int(c_dur * MAX_RECOMMENDED_WPS))
            if len(words) > max_words:
                words = words[:max_words]
                fallback_line = " ".join(words)
            wps = round(len(words) / c_dur, 2)

            total_cues += 1
            if wps <= MAX_RECOMMENDED_WPS:
                passing_cues += 1

            viseme_cues.append(
                VisemeLipSyncCue(
                    scene_index=sc_idx,
                    speaker_id="VO_NARRATOR",
                    line_text=fallback_line,
                    start_sec=c_start,
                    end_sec=c_end,
                    word_count=len(words),
                    wps=wps,
                    dominant_visemes=_map_words_to_visemes(words),
                    lip_sync_required_on_camera=False,
                )
            )
            keyframes.extend([
                SidechainDuckingKeyframe(
                    time_sec=c_start,
                    trigger_stem="dialogue",
                    target_stem="music",
                    attenuation_db=music_duck_db,
                    attack_ms=40,
                    release_ms=300,
                    scene_index=sc_idx,
                ),
                SidechainDuckingKeyframe(
                    time_sec=c_start,
                    trigger_stem="dialogue",
                    target_stem="ambience",
                    attenuation_db=ambience_duck_db,
                    attack_ms=40,
                    release_ms=300,
                    scene_index=sc_idx,
                ),
                SidechainDuckingKeyframe(
                    time_sec=c_end,
                    trigger_stem="dialogue",
                    target_stem="music",
                    attenuation_db=0.0,
                    attack_ms=40,
                    release_ms=300,
                    scene_index=sc_idx,
                ),
                SidechainDuckingKeyframe(
                    time_sec=c_end,
                    trigger_stem="dialogue",
                    target_stem="ambience",
                    attenuation_db=0.0,
                    attack_ms=40,
                    release_ms=300,
                    scene_index=sc_idx,
                ),
            ])

        keyframes.sort(key=lambda kf: (kf.time_sec, kf.target_stem, kf.attenuation_db))
        snr_db = max(snr_min_db, round(abs(music_duck_db) + 1.5, 2))
        scene_profiles.append(
            SceneVoiceDuckingSpec(
                scene_index=sc_idx,
                active_speakers=active_speakers,
                viseme_cues=viseme_cues,
                ducking_keyframes=keyframes,
                dialogue_to_bgm_snr_db=snr_db,
            )
        )

    if used_narrator:
        _ensure_narrator_profile(roster, domain_cfg)

    pass_rate = round((passing_cues / float(total_cues)) * 100.0, 2) if total_cues > 0 else 100.0

    return MasterVoiceDuckingManifest(
        casting_roster=roster,
        scene_profiles=scene_profiles,
        default_music_duck_db=music_duck_db,
        default_ambience_duck_db=ambience_duck_db,
        dialogue_clarity_snr_min_db=snr_min_db,
        lip_sync_pass_rate_pct=pass_rate,
    )


def synthesize_default_voice_ducking_manifest(bible: MasterProductionBible) -> MasterVoiceDuckingManifest:
    """Synthesizes default Voice Casting, Viseme Lip-Sync & Sidechain Ducking Manifest."""
    return compile_voice_ducking_manifest(bible)


def format_voice_ducking_token(
    manifest: MasterVoiceDuckingManifest,
    scene_index: int = 1,
) -> str:
    """Formats the machine telemetry token for PM-FEAT-038 voice casting & sidechain ducking."""
    sc_profile: Optional[SceneVoiceDuckingSpec] = None
    for sp in manifest.scene_profiles:
        if sp.scene_index == scene_index:
            sc_profile = sp
            break

    speakers = (
        ",".join(sc_profile.active_speakers[:3])
        if sc_profile and sc_profile.active_speakers
        else (manifest.casting_roster[0].character_id if manifest.casting_roster else "VO_NARRATOR")
    )
    snr_db = sc_profile.dialogue_to_bgm_snr_db if sc_profile else max(6.0, abs(manifest.default_music_duck_db) + 1.5)
    cues_count = len(sc_profile.viseme_cues) if sc_profile else 0
    return (
        f"[VOICE-CAST: {speakers} | SC{scene_index:02d} | "
        f"DUCK: music={manifest.default_music_duck_db:.1f}dB,amb={manifest.default_ambience_duck_db:.1f}dB | "
        f"VISEME-SYNC: cues={cues_count},pass={manifest.lip_sync_pass_rate_pct:.0f}%,snr={snr_db:.1f}dB]"
    )


def export_voice_casting_json(manifest: MasterVoiceDuckingManifest) -> str:
    """Serializes MasterVoiceDuckingManifest to formatted JSON."""
    return manifest.model_dump_json(indent=2)


def export_stem_ducking_csv(manifest: MasterVoiceDuckingManifest, fps: int = 24) -> str:
    """Exports monotonic sidechain stem ducking automation keyframes with SMPTE timecodes as CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "scene_index",
        "time_sec",
        "smpte_tc",
        "trigger_stem",
        "target_stem",
        "attenuation_db",
        "attack_ms",
        "release_ms",
    ])
    all_keyframes: List[SidechainDuckingKeyframe] = []
    for sp in manifest.scene_profiles:
        all_keyframes.extend(sp.ducking_keyframes)
    all_keyframes.sort(key=lambda kf: (kf.time_sec, kf.scene_index, kf.target_stem, kf.attenuation_db))

    for kf in all_keyframes:
        writer.writerow([
            kf.scene_index,
            f"{kf.time_sec:.3f}",
            _seconds_to_smpte_frames(kf.time_sec, fps=fps),
            kf.trigger_stem,
            kf.target_stem,
            f"{kf.attenuation_db:.2f}",
            kf.attack_ms,
            kf.release_ms,
        ])
    return buf.getvalue()


def export_adr_viseme_md(
    manifest: MasterVoiceDuckingManifest,
    bible: Optional[MasterProductionBible] = None,
) -> str:
    """Exports human-readable Markdown voice casting roster, ADR/viseme timing table, and ducking summary."""
    title = str(getattr(bible, "project_title", "Omni Production") or "Omni Production")
    lines: List[str] = [
        f"# Voice Casting, Viseme Lip-Sync & Sidechain Ducking Script — {title}",
        "",
        f"- **Music Duck Attenuation**: `{manifest.default_music_duck_db:.1f} dB`",
        f"- **Ambience Duck Attenuation**: `{manifest.default_ambience_duck_db:.1f} dB`",
        f"- **Minimum Dialogue Clarity SNR**: `{manifest.dialogue_clarity_snr_min_db:.1f} dB`",
        f"- **Lip-Sync <= 2.5 WPS Pass Rate**: `{manifest.lip_sync_pass_rate_pct:.1f}%`",
        "",
        "## Voice Casting Roster",
        "",
        "| Character ID | Name | Register | Mic Perspective | Target WPM | Pitch Range |",
        "|---|---|---|---|---:|---|",
    ]
    for p in manifest.casting_roster:
        reg_val = p.vocal_register.value if hasattr(p.vocal_register, "value") else str(p.vocal_register)
        lines.append(
            f"| `{p.character_id}` | {p.character_name} | `{reg_val}` | `{p.mic_perspective}` | "
            f"{p.target_wpm:.1f} | {p.pitch_hz_range} |"
        )

    lines.extend([
        "",
        "## Per-Scene Viseme Lip-Sync & Sidechain Ducking",
        "",
        "| Scene | Speaker | Window (s) | Words | WPS | On-Camera | Dominant Visemes | Line |",
        "|---:|---|---|---:|---:|:---:|---|---|",
    ])
    for sp in manifest.scene_profiles:
        for cue in sp.viseme_cues:
            vis_str = "-".join(v.value if hasattr(v, "value") else str(v) for v in cue.dominant_visemes[:6])
            lines.append(
                f"| {cue.scene_index} | `{cue.speaker_id}` | {cue.start_sec:.2f}-{cue.end_sec:.2f} | "
                f"{cue.word_count} | {cue.wps:.2f} | {'Yes' if cue.lip_sync_required_on_camera else 'No'} | "
                f"`{vis_str}` | {cue.line_text} |"
            )
    lines.append("")
    return "\n".join(lines)


def export_voice_ducking_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    fps: int = 24,
    manifest: Optional[MasterVoiceDuckingManifest] = None,
) -> Dict[str, Path]:
    """Writes voice_casting_script.json, stem_ducking_automation.csv, and adr_viseme_timing.md into output_dir."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    resolved_manifest = manifest or getattr(bible, "master_voice_ducking", None)
    if resolved_manifest is None:
        resolved_manifest = compile_voice_ducking_manifest(bible)

    json_path = out_path / "voice_casting_script.json"
    csv_path = out_path / "stem_ducking_automation.csv"
    md_path = out_path / "adr_viseme_timing.md"

    json_path.write_text(export_voice_casting_json(resolved_manifest), encoding="utf-8")
    csv_path.write_text(export_stem_ducking_csv(resolved_manifest, fps=fps), encoding="utf-8")
    md_path.write_text(export_adr_viseme_md(resolved_manifest, bible), encoding="utf-8")

    return {
        "voice_casting_script_json": json_path,
        "stem_ducking_automation_csv": csv_path,
        "adr_viseme_timing_md": md_path,
    }


__all__ = [
    "compile_voice_ducking_manifest",
    "synthesize_default_voice_ducking_manifest",
    "format_voice_ducking_token",
    "export_voice_casting_json",
    "export_stem_ducking_csv",
    "export_adr_viseme_md",
    "export_voice_ducking_bundle",
]
