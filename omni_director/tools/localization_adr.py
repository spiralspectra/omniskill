"""Multi-Territory Localization, ADR Dubbing Studio, Lip-Sync Timing & Safe-Supers Engine (PM-FEAT-027).

Pure-Python localization and dubbing suite providing:
- Deterministic 11-territory linguistic expansion/compression modeling (en-US, de-DE, fr-FR,
  es-419, ja-JP, zh-CN, it-IT, ko-KR, pt-BR, ar-SA [RTL], da-DK)
- Syllable/word count & WPS lip-sync drift evaluation against domain max_wps / 2.5 WPS ceiling
  (<=1.15x LOCKED, 1.15x-1.25x STRETCH_CAUTION, >1.25x RESCRIPT_REQUIRED)
- On-screen supers safe-zone expansion audit aligned with PLATFORM_SAFE_ZONES
- Frame-accurate 24fps SMPTE ADR spotting cues with 3-beep pre-roll
- IMSC1 TTML XML (SMPTE 24fps non-drop), ADR cue sheet CSV, localized SRT/VTT, and JSON exports
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from xml.sax.saxutils import escape as xml_escape

from omni_director.schemas import (
    AdrSpottingCueSpec,
    LocaleAdaptationSpec,
    LocaleSyncStatus,
    LocalizationManifestSpec,
    LocalizedLineSpec,
    MasterProductionBible,
    ScenePromptSpec,
    SupersSafeStatus,
)
from omni_director.tools.delivery_reframe import PLATFORM_SAFE_ZONES
from omni_director.tools.dialogue import (
    MAX_RECOMMENDED_WPS,
    _extract_spoken_words,
    _format_srt_timestamp,
    _format_vtt_timestamp,
)
from omni_director.tools.nle_export import _parse_scene_window, _seconds_to_smpte_frames


LOCALE_PROFILES: Dict[str, Dict[str, Any]] = {
    "en-US": {
        "bcp47_tag": "en-US",
        "territory_label": "United States (Source Master)",
        "direction": "ltr",
        "expansion_factor": 1.00,
        "syllable_per_word": 1.45,
        "cjk": False,
        "pad_tokens": ["now", "pure", "form"],
        "prefix": "",
        "supers_prefix": "",
    },
    "de-DE": {
        "bcp47_tag": "de-DE",
        "territory_label": "Germany / DACH",
        "direction": "ltr",
        "expansion_factor": 1.25,
        "syllable_per_word": 1.90,
        "cjk": False,
        "pad_tokens": ["jetzt", "präzise", "vollendet", "rein"],
        "prefix": "[DE]",
        "supers_prefix": "DE ·",
    },
    "fr-FR": {
        "bcp47_tag": "fr-FR",
        "territory_label": "France / Francophonie",
        "direction": "ltr",
        "expansion_factor": 1.20,
        "syllable_per_word": 1.68,
        "cjk": False,
        "pad_tokens": ["maintenant", "pur", "élan", "juste"],
        "prefix": "[FR]",
        "supers_prefix": "FR ·",
    },
    "es-419": {
        "bcp47_tag": "es-419",
        "territory_label": "Latin America (Neutral Spanish)",
        "direction": "ltr",
        "expansion_factor": 1.18,
        "syllable_per_word": 1.74,
        "cjk": False,
        "pad_tokens": ["ahora", "pulso", "puro", "vivo"],
        "prefix": "[ES]",
        "supers_prefix": "ES ·",
    },
    "ja-JP": {
        "bcp47_tag": "ja-JP",
        "territory_label": "Japan",
        "direction": "ltr",
        "expansion_factor": 0.72,
        "syllable_per_word": 2.15,
        "cjk": True,
        "pad_tokens": ["今", "響き", "美学"],
        "prefix": "[JA]",
        "supers_prefix": "JP・",
    },
    "zh-CN": {
        "bcp47_tag": "zh-CN",
        "territory_label": "Mainland China (Simplified)",
        "direction": "ltr",
        "expansion_factor": 0.68,
        "syllable_per_word": 1.80,
        "cjk": True,
        "pad_tokens": ["此刻", "纯粹", "匠心"],
        "prefix": "[ZH]",
        "supers_prefix": "CN・",
    },
    "it-IT": {
        "bcp47_tag": "it-IT",
        "territory_label": "Italy",
        "direction": "ltr",
        "expansion_factor": 1.16,
        "syllable_per_word": 1.78,
        "cjk": False,
        "pad_tokens": ["ora", "forma", "pura", "luce"],
        "prefix": "[IT]",
        "supers_prefix": "IT ·",
    },
    "ko-KR": {
        "bcp47_tag": "ko-KR",
        "territory_label": "South Korea",
        "direction": "ltr",
        "expansion_factor": 0.80,
        "syllable_per_word": 1.95,
        "cjk": True,
        "pad_tokens": ["지금", "순수", "리듬"],
        "prefix": "[KO]",
        "supers_prefix": "KR·",
    },
    "pt-BR": {
        "bcp47_tag": "pt-BR",
        "territory_label": "Brazil",
        "direction": "ltr",
        "expansion_factor": 1.17,
        "syllable_per_word": 1.72,
        "cjk": False,
        "pad_tokens": ["agora", "ritmo", "forma", "luz"],
        "prefix": "[PT]",
        "supers_prefix": "BR ·",
    },
    "ar-SA": {
        "bcp47_tag": "ar-SA",
        "territory_label": "Saudi Arabia / MENA (RTL)",
        "direction": "rtl",
        "expansion_factor": 1.12,
        "syllable_per_word": 1.85,
        "cjk": False,
        "pad_tokens": ["الآن", "نقاء", "إيقاع", "ضوء"],
        "prefix": "[AR]",
        "supers_prefix": "AR ·",
    },
    "da-DK": {
        "bcp47_tag": "da-DK",
        "territory_label": "Denmark / Nordics",
        "direction": "ltr",
        "expansion_factor": 1.08,
        "syllable_per_word": 1.60,
        "cjk": False,
        "pad_tokens": ["nu", "ro", "lys", "form"],
        "prefix": "[DA]",
        "supers_prefix": "DK ·",
    },
}

_LOCALE_ALIASES: Dict[str, str] = {
    "en": "en-US",
    "en-us": "en-US",
    "de": "de-DE",
    "de-de": "de-DE",
    "fr": "fr-FR",
    "fr-fr": "fr-FR",
    "es": "es-419",
    "es-419": "es-419",
    "es-es": "es-419",
    "ja": "ja-JP",
    "ja-jp": "ja-JP",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "it": "it-IT",
    "it-it": "it-IT",
    "ko": "ko-KR",
    "ko-kr": "ko-KR",
    "pt": "pt-BR",
    "pt-br": "pt-BR",
    "ar": "ar-SA",
    "ar-sa": "ar-SA",
    "da": "da-DK",
    "da-dk": "da-DK",
}


def _normalize_locale(tag: str) -> str:
    raw = str(tag or "en-US").strip()
    key = raw.lower().replace("_", "-")
    if key in _LOCALE_ALIASES:
        return _LOCALE_ALIASES[key]
    return raw if raw else "en-US"


def _get_locale_profile(tag: str) -> Dict[str, Any]:
    norm = _normalize_locale(tag)
    if norm in LOCALE_PROFILES:
        return LOCALE_PROFILES[norm]
    is_rtl = norm.lower().startswith(("ar", "he", "fa", "ur"))
    return {
        "bcp47_tag": norm,
        "territory_label": f"Territory ({norm})",
        "direction": "rtl" if is_rtl else "ltr",
        "expansion_factor": 1.12,
        "syllable_per_word": 1.65,
        "cjk": False,
        "pad_tokens": ["now", "pure"],
        "prefix": f"[{norm.upper()}]",
        "supers_prefix": f"{norm.split('-')[0].upper()} ·",
    }


def _estimate_syllables(words: List[str], syllable_per_word: float) -> int:
    if not words:
        return 0
    vowel_groups = 0
    for w in words:
        groups = re.findall(r"[aeiouyäöüéèêàâîôùûáíóúãõ]+", w.lower())
        vowel_groups += max(1, len(groups))
    heuristic = int(round(len(words) * syllable_per_word))
    return max(len(words), int(round((vowel_groups + heuristic) / 2.0)))


def _split_speaker_and_text(raw_line: str, fallback_speaker: str = "Narrator / VO") -> Tuple[str, str]:
    text = str(raw_line or "").strip()
    match = re.match(r"^([A-Za-z0-9_\-\s]{1,25}):\s*(.+)$", text)
    if match:
        speaker = match.group(1).strip() or fallback_speaker
        spoken = match.group(2).strip().strip("\"'“”‘’")
        return speaker, spoken
    return fallback_speaker, text.strip("\"'“”‘’")


def _adapt_dialogue_line(
    source_text: str,
    locale: str,
    profile: Dict[str, Any],
    target_word_count: int,
) -> str:
    """Deterministically produce adapted dialogue text aligned to target word budget."""
    clean = str(source_text or "").strip()
    if not clean:
        return ""
    if locale == "en-US":
        return clean

    tokens = [t for t in re.split(r"\s+", clean) if t]
    prefix = profile.get("prefix", f"[{locale}]")
    pad_tokens = list(profile.get("pad_tokens") or ["now"])

    if profile.get("cjk"):
        compact_count = max(1, target_word_count)
        core = " ".join(pad_tokens[i % len(pad_tokens)] for i in range(compact_count))
        return f"{prefix} {core}".strip()

    if profile.get("direction") == "rtl":
        rtl_words = [pad_tokens[i % len(pad_tokens)] for i in range(max(1, target_word_count))]
        return f"{prefix} {' '.join(rtl_words)}".strip()

    adapted = list(tokens)
    while len(adapted) < target_word_count:
        adapted.append(pad_tokens[(len(adapted) - len(tokens)) % len(pad_tokens)])
    if len(adapted) > max(1, target_word_count):
        adapted = adapted[: max(1, target_word_count)]
    return f"{prefix} {' '.join(adapted)}".strip()


def _adapt_supers_text(base_supers: str, locale: str, profile: Dict[str, Any]) -> str:
    clean = str(base_supers or "").strip()
    if locale == "en-US" or not clean:
        return clean
    factor = float(profile.get("expansion_factor", 1.0))
    prefix = str(profile.get("supers_prefix", ""))
    target_len = max(4, int(round(len(clean) * factor)))
    if profile.get("cjk"):
        pad = "".join(profile.get("pad_tokens") or ["美学"])
        combined = f"{prefix}{pad}"
        while len(combined) < target_len:
            combined += pad
        return combined[:target_len]
    candidate = f"{prefix} {clean}".strip()
    if len(candidate) < target_len:
        pad = " · " + " ".join(profile.get("pad_tokens") or ["EDITION"])
        candidate = (candidate + pad)[:target_len].strip()
    return candidate


def _resolve_supers_safe_budget(bible: MasterProductionBible, base_budget: int) -> int:
    """Scale supers character budget using PLATFORM_SAFE_ZONES when vertical/social targets exist."""
    reframe = getattr(bible, "master_reframe_manifest", None)
    if not reframe or not getattr(reframe, "scene_reframes", None):
        return base_budget
    narrowest_usable_pct = 80.0
    for sr in reframe.scene_reframes:
        for cw in getattr(sr, "crop_windows", []) or []:
            plat = cw.platform.value if hasattr(cw.platform, "value") else str(cw.platform)
            zone = PLATFORM_SAFE_ZONES.get(plat)
            if zone:
                usable = 100.0 - float(zone["left_pct"]) - float(zone["right_pct"])
                narrowest_usable_pct = min(narrowest_usable_pct, usable)
    scale = max(0.72, min(1.0, narrowest_usable_pct / 80.0))
    return max(14, int(round(base_budget * scale)))


def _classify_sync_status(lip_sync_ratio: float) -> Tuple[LocaleSyncStatus, bool]:
    if lip_sync_ratio <= 1.15:
        return LocaleSyncStatus.LOCKED, False
    if lip_sync_ratio <= 1.25:
        return LocaleSyncStatus.STRETCH_CAUTION, True
    return LocaleSyncStatus.RESCRIPT_REQUIRED, True


def _classify_supers_status(text_len: int, budget: int) -> SupersSafeStatus:
    if text_len <= budget:
        return SupersSafeStatus.CLEAR
    if text_len <= int(round(budget * 1.25)):
        return SupersSafeStatus.TIGHT_WRAP
    return SupersSafeStatus.SAFE_ZONE_OVERFLOW


def compile_localization_manifest(
    bible: MasterProductionBible,
    locales: Optional[List[str]] = None,
) -> LocalizationManifestSpec:
    """Compile a deterministic multi-territory localization, ADR, and safe-supers manifest (PM-FEAT-027)."""
    from omni_director.presets import classify_brief_domain, get_domain_localization_spec

    domain_key = bible.domain_archetype or classify_brief_domain(
        f"{bible.project_title} {getattr(bible, 'logline', '')}"
    )
    cal = get_domain_localization_spec(domain_key)
    source_locale = str(cal.get("source_locale", "en-US"))

    raw_locales = locales if (locales and len(locales) > 0) else list(cal["default_locales"])
    target_locales: List[str] = []
    for loc in raw_locales:
        norm = _normalize_locale(loc)
        if norm not in target_locales:
            target_locales.append(norm)
    if not target_locales:
        target_locales = ["en-US"]

    max_allowed_wps = float(cal.get("max_allowed_wps", MAX_RECOMMENDED_WPS))
    max_allowed_drift_ratio = float(cal.get("max_allowed_drift_ratio", 1.15))
    emotion_tag = str(cal.get("emotion_tag", "neutral"))
    imsc1_profile = str(cal.get("imsc1_profile", "imsc1-text-1.1"))

    base_supers = str(cal.get("default_supers_template") or bible.project_title[:28])
    if getattr(bible, "master_slate_spec", None) and getattr(
        bible.master_slate_spec, "broadcast_slate", None
    ):
        slate_title = bible.master_slate_spec.broadcast_slate.spot_title
        if slate_title and len(slate_title) <= 34:
            base_supers = slate_title
    supers_budget = _resolve_supers_safe_budget(bible, int(cal.get("supers_char_budget", 26)))

    scenes = list(bible.scenes or [])
    total_scenes = max(1, len(scenes))
    total_runtime = float(getattr(bible, "total_runtime_seconds", 32) or 32)
    fallback_speaker = (
        bible.characters[0].name
        if getattr(bible, "characters", None)
        else "Narrator / VO"
    )
    master_lines = (
        list(bible.master_dialogue.dialogue_lines)
        if (getattr(bible, "master_dialogue", None) and bible.master_dialogue.dialogue_lines)
        else []
    )

    # Build canonical per-scene cue sources
    scene_sources: List[Dict[str, Any]] = []
    any_spoken_dialogue = False
    for idx, scene in enumerate(scenes, start=1):
        s_start, s_end = _parse_scene_window(scene, idx, total_scenes, total_runtime)
        s_dur = max(1.0, s_end - s_start)
        raw_dialogue = (
            list(scene.diegetic_sonic.dialogue_lines)
            if (scene.diegetic_sonic and scene.diegetic_sonic.dialogue_lines)
            else []
        )
        if not raw_dialogue and idx <= len(master_lines):
            raw_dialogue = [master_lines[idx - 1]]

        if raw_dialogue:
            any_spoken_dialogue = True
            step = s_dur / len(raw_dialogue)
            for d_idx, raw_line in enumerate(raw_dialogue, start=1):
                c_start = s_start + (d_idx - 1) * step
                c_end = s_start + d_idx * step
                speaker, spoken = _split_speaker_and_text(raw_line, fallback_speaker=fallback_speaker)
                src_words = _extract_spoken_words([spoken])
                scene_sources.append(
                    {
                        "scene_number": scene.scene_index,
                        "cue_idx": d_idx,
                        "start_sec": c_start,
                        "end_sec": c_end,
                        "duration_sec": max(1.0, c_end - c_start),
                        "speaker": speaker,
                        "source_text": spoken,
                        "source_words": src_words,
                        "is_spoken": True,
                    }
                )
        else:
            foley = (
                scene.diegetic_sonic.foley_cues[0]
                if (scene.diegetic_sonic and scene.diegetic_sonic.foley_cues)
                else scene.scene_title
            )
            scene_sources.append(
                {
                    "scene_number": scene.scene_index,
                    "cue_idx": 1,
                    "start_sec": s_start,
                    "end_sec": s_end,
                    "duration_sec": s_dur,
                    "speaker": "M&E / Foley Cue",
                    "source_text": f"[SFX: {foley}]",
                    "source_words": [],
                    "is_spoken": False,
                }
            )

    if not scene_sources:
        scene_sources.append(
            {
                "scene_number": 1,
                "cue_idx": 1,
                "start_sec": 0.0,
                "end_sec": total_runtime,
                "duration_sec": max(1.0, total_runtime),
                "speaker": fallback_speaker,
                "source_text": bible.project_title,
                "source_words": _extract_spoken_words([bible.project_title]),
                "is_spoken": True,
            }
        )
        any_spoken_dialogue = True

    territories: List[LocaleAdaptationSpec] = []
    adr_cues: List[AdrSpottingCueSpec] = []

    for loc in target_locales:
        profile = _get_locale_profile(loc)
        bcp47 = str(profile["bcp47_tag"])
        exp_factor = float(profile["expansion_factor"])
        syl_per_word = float(profile["syllable_per_word"])
        direction = str(profile["direction"])

        locale_lines: List[LocalizedLineSpec] = []
        max_ratio_for_locale = 1.0

        for src in scene_sources:
            src_words: List[str] = src["source_words"]
            dur_sec = float(src["duration_sec"])
            is_spoken = bool(src["is_spoken"])

            if is_spoken and src_words:
                target_wc = max(1, int(round(len(src_words) * exp_factor)))
                adapted_text = _adapt_dialogue_line(src["source_text"], bcp47, profile, target_wc)
                target_wps = round(target_wc / dur_sec, 3)
                syllables = max(target_wc, int(round(target_wc * syl_per_word)))
                if not profile.get("cjk") and direction == "ltr":
                    syllables = _estimate_syllables(
                        _extract_spoken_words([adapted_text]), syl_per_word
                    )

                pace_ratio = target_wps / max(0.5, max_allowed_wps)
                if pace_ratio > 1.0:
                    lip_sync_ratio = round(pace_ratio, 3)
                elif exp_factor < 1.0:
                    lip_sync_ratio = round(max(0.75, exp_factor + (1.0 - exp_factor) * 0.35), 3)
                else:
                    lip_sync_ratio = round(
                        1.0 + max(0.0, exp_factor - 1.0) * min(1.0, pace_ratio) * 0.5,
                        3,
                    )
            else:
                target_wc = 0
                target_wps = 0.0
                syllables = 0
                lip_sync_ratio = 1.0
                adapted_text = (
                    src["source_text"]
                    if bcp47 == source_locale
                    else f"{profile['prefix']} {src['source_text']}".strip()
                )

            sync_status, requires_retime = _classify_sync_status(lip_sync_ratio)
            max_ratio_for_locale = max(max_ratio_for_locale, lip_sync_ratio)

            locale_lines.append(
                LocalizedLineSpec(
                    locale=bcp47,
                    bcp47_tag=bcp47,
                    translated_text=adapted_text,
                    syllable_count=syllables,
                    word_count=target_wc,
                    target_wps=target_wps,
                    duration_sec=round(dur_sec, 3),
                    lip_sync_ratio=lip_sync_ratio,
                    sync_status=sync_status,
                    requires_viseme_retime=requires_retime,
                )
            )

            in_tc = _seconds_to_smpte_frames(src["start_sec"], fps=24)
            out_tc = _seconds_to_smpte_frames(src["end_sec"], fps=24)
            lower_text = f"{src['speaker']} {src['source_text']}".lower()
            is_loop_group = any(k in lower_text for k in ("crowd", "group", "walla", "chatter"))

            adr_cues.append(
                AdrSpottingCueSpec(
                    cue_id=f"ADR-{bcp47.upper().replace('-', '')}-S{src['scene_number']:02d}-{src['cue_idx']:02d}",
                    scene_number=src["scene_number"],
                    character_name=src["speaker"],
                    locale=bcp47,
                    in_tc=in_tc,
                    out_tc=out_tc,
                    pre_roll_beeps=3,
                    source_line=src["source_text"],
                    adapted_line=adapted_text,
                    emotion_tag=emotion_tag,
                    lip_sync_ratio=lip_sync_ratio,
                    loop_group_flag=is_loop_group,
                )
            )

        loc_supers = _adapt_supers_text(base_supers, bcp47, profile)
        supers_exp_pct = round((exp_factor - 1.0) * 100.0, 1)
        supers_status = _classify_supers_status(len(loc_supers), supers_budget)

        notes: List[str] = [
            f"Expansion factor {exp_factor:.2f}x ({supers_exp_pct:+.1f}%) | direction={direction.upper()}.",
            str(cal.get("adr_environment_note", "")),
        ]
        if supers_status != SupersSafeStatus.CLEAR:
            notes.append(
                f"Supers '{loc_supers}' ({len(loc_supers)} chars) vs safe budget {supers_budget} chars -> {supers_status.value}."
            )
        if max_ratio_for_locale > max_allowed_drift_ratio:
            notes.append(
                f"Peak lip-sync ratio {max_ratio_for_locale:.2f}x exceeds {max_allowed_drift_ratio:.2f}x drift gate."
            )

        territories.append(
            LocaleAdaptationSpec(
                locale=bcp47,
                bcp47_tag=bcp47,
                territory_label=str(profile["territory_label"]),
                direction=direction,
                adr_required=any_spoken_dialogue and (bcp47 != source_locale),
                lines=locale_lines,
                localized_supers_text=loc_supers,
                supers_expansion_pct=supers_exp_pct,
                supers_status=supers_status,
                max_lip_sync_ratio=round(max_ratio_for_locale, 3),
                compliance_notes=notes,
            )
        )

    has_rescript = any(
        line.sync_status == LocaleSyncStatus.RESCRIPT_REQUIRED
        for t in territories
        for line in t.lines
    )
    has_overflow = any(
        t.supers_status == SupersSafeStatus.SAFE_ZONE_OVERFLOW
        for t in territories
    )
    broadcast_ready = (not has_rescript) and (not has_overflow)

    summary_notes = [
        f"Domain '{domain_key}' calibrated at max_wps={max_allowed_wps:.2f}, drift_ceiling={max_allowed_drift_ratio:.2f}x, supers_budget={supers_budget}ch.",
        f"Compiled {len(territories)} territories ({', '.join(target_locales)}) and {len(adr_cues)} ADR spotting cues (3-beep pre-roll).",
        f"Broadcast localization gate: {'READY' if broadcast_ready else 'HOLD_FOR_RESCRIPT_OR_SUPERS'}.",
    ]

    return LocalizationManifestSpec(
        source_locale=source_locale,
        target_locales=target_locales,
        territories=territories,
        adr_cues=adr_cues,
        imsc1_profile=imsc1_profile,
        max_allowed_wps=max_allowed_wps,
        max_allowed_drift_ratio=max_allowed_drift_ratio,
        broadcast_ready=broadcast_ready,
        summary_notes=summary_notes,
    )


def synthesize_default_localization_manifest(
    bible: MasterProductionBible,
    locales: Optional[List[str]] = None,
) -> LocalizationManifestSpec:
    """Synthesize a default multi-territory localization manifest for a production bible (PM-FEAT-027)."""
    return compile_localization_manifest(bible, locales=locales)


def _resolve_localization_manifest(bible: MasterProductionBible) -> LocalizationManifestSpec:
    if getattr(bible, "localization_manifest", None) is not None:
        return bible.localization_manifest  # type: ignore[return-value]
    return compile_localization_manifest(bible)


def audit_locale_lip_sync_and_supers(bible: MasterProductionBible) -> Dict[str, Any]:
    """Audit all localized territories for lip-sync drift and safe-zone supers compliance (PM-FEAT-027)."""
    manifest = _resolve_localization_manifest(bible)

    rescript_count = 0
    stretch_count = 0
    overflow_count = 0
    max_ratio = 1.0
    worst_supers = SupersSafeStatus.CLEAR
    warnings: List[str] = []
    territory_reports: List[Dict[str, Any]] = []

    supers_rank = {
        SupersSafeStatus.CLEAR: 0,
        SupersSafeStatus.TIGHT_WRAP: 1,
        SupersSafeStatus.SAFE_ZONE_OVERFLOW: 2,
    }

    for terr in manifest.territories:
        t_rescript = sum(1 for ln in terr.lines if ln.sync_status == LocaleSyncStatus.RESCRIPT_REQUIRED)
        t_stretch = sum(1 for ln in terr.lines if ln.sync_status == LocaleSyncStatus.STRETCH_CAUTION)
        rescript_count += t_rescript
        stretch_count += t_stretch
        max_ratio = max(max_ratio, float(terr.max_lip_sync_ratio))

        if supers_rank.get(terr.supers_status, 0) > supers_rank.get(worst_supers, 0):
            worst_supers = terr.supers_status
        if terr.supers_status == SupersSafeStatus.SAFE_ZONE_OVERFLOW:
            overflow_count += 1
            warnings.append(
                f"{terr.bcp47_tag}: Localized supers '{terr.localized_supers_text}' overflows safe-zone margins."
            )
        if t_rescript > 0:
            warnings.append(
                f"{terr.bcp47_tag}: {t_rescript} line(s) exceed 1.25x lip-sync ratio (RESCRIPT_REQUIRED)."
            )
        elif t_stretch > 0:
            warnings.append(
                f"{terr.bcp47_tag}: {t_stretch} line(s) in 1.15x-1.25x STRETCH_CAUTION window."
            )

        territory_reports.append(
            {
                "locale": terr.bcp47_tag,
                "direction": terr.direction,
                "max_lip_sync_ratio": terr.max_lip_sync_ratio,
                "supers_status": terr.supers_status.value,
                "supers_expansion_pct": terr.supers_expansion_pct,
                "rescript_required_lines": t_rescript,
                "stretch_caution_lines": t_stretch,
                "adr_required": terr.adr_required,
            }
        )

    passed = (rescript_count == 0) and (overflow_count == 0) and bool(manifest.broadcast_ready)
    return {
        "passed": passed,
        "broadcast_ready": manifest.broadcast_ready,
        "source_locale": manifest.source_locale,
        "target_locales": list(manifest.target_locales),
        "max_lip_sync_ratio": round(max_ratio, 3),
        "max_allowed_wps": manifest.max_allowed_wps,
        "max_allowed_drift_ratio": manifest.max_allowed_drift_ratio,
        "worst_supers_status": worst_supers.value,
        "rescript_required_count": rescript_count,
        "stretch_caution_count": stretch_count,
        "supers_overflow_count": overflow_count,
        "territory_reports": territory_reports,
        "warnings": warnings,
    }


def format_localization_prompt_token(
    bible: MasterProductionBible,
    scene: Optional[ScenePromptSpec] = None,
) -> str:
    """Emit standardized Gemini Omni prompt-auditable localization & ADR token (PM-FEAT-027)."""
    manifest = _resolve_localization_manifest(bible)
    locales_csv = ",".join(manifest.target_locales or [manifest.source_locale])

    if scene is not None and getattr(scene, "locale_tracks", None):
        tracks = scene.locale_tracks
        ratio = max((float(t.lip_sync_ratio) for t in tracks), default=1.0)
        wps = max((float(t.target_wps) for t in tracks), default=manifest.max_allowed_wps)
        if wps <= 0.0:
            wps = manifest.max_allowed_wps
    else:
        ratio = max((float(t.max_lip_sync_ratio) for t in manifest.territories), default=1.0)
        all_wps = [float(ln.target_wps) for t in manifest.territories for ln in t.lines if ln.target_wps > 0]
        wps = max(all_wps) if all_wps else manifest.max_allowed_wps

    supers_rank = {
        SupersSafeStatus.CLEAR: 0,
        SupersSafeStatus.TIGHT_WRAP: 1,
        SupersSafeStatus.SAFE_ZONE_OVERFLOW: 2,
    }
    worst_supers = SupersSafeStatus.CLEAR
    for terr in manifest.territories:
        if supers_rank.get(terr.supers_status, 0) > supers_rank.get(worst_supers, 0):
            worst_supers = terr.supers_status

    return (
        f"[LOCALIZATION_ADR: locales={locales_csv} "
        f"sync={ratio:.2f}x wps={wps:.2f} supers={worst_supers.value}]"
    )


def build_imsc1_ttml_xml(
    bible: MasterProductionBible,
    locale: Optional[str] = None,
) -> str:
    """Build IMSC1 TTML XML string with SMPTE 24fps non-drop timecodes (PM-FEAT-027)."""
    manifest = _resolve_localization_manifest(bible)

    target_loc = _normalize_locale(locale) if locale else (
        manifest.target_locales[0] if manifest.target_locales else manifest.source_locale
    )
    profile = _get_locale_profile(target_loc)
    direction = str(profile["direction"])

    cues = [c for c in manifest.adr_cues if _normalize_locale(c.locale) == target_loc]
    if not cues and manifest.adr_cues:
        first_loc = manifest.adr_cues[0].locale
        cues = [c for c in manifest.adr_cues if c.locale == first_loc]
        target_loc = first_loc
        direction = _get_locale_profile(first_loc)["direction"]

    p_lines: List[str] = []
    for idx, cue in enumerate(cues, start=1):
        text_escaped = xml_escape(cue.adapted_line or cue.source_line)
        p_lines.append(
            f'      <p xml:id="cue_{idx}" begin="{xml_escape(cue.in_tc)}" '
            f'end="{xml_escape(cue.out_tc)}" region="bottom_safe">{text_escaped}</p>'
        )

    if not p_lines:
        p_lines.append(
            f'      <p xml:id="cue_1" begin="00:00:00:00" end="00:00:08:00" region="bottom_safe">'
            f'{xml_escape(bible.project_title)}</p>'
        )

    body_xml = "\n".join(p_lines)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<tt xml:lang="{lang}" '
        'xmlns="http://www.w3.org/ns/ttml" '
        'xmlns:ttp="http://www.w3.org/ns/ttml#parameter" '
        'xmlns:tts="http://www.w3.org/ns/ttml#styling" '
        'xmlns:itts="http://www.w3.org/ns/ttml/profile/imsc1#styling" '
        'ttp:profile="http://www.w3.org/ns/ttml/profile/imsc1/text" '
        'ttp:timeBase="smpte" ttp:frameRate="24" ttp:dropMode="nonDrop" '
        'ttp:markerMode="continuous">\n'
        '  <head>\n'
        '    <metadata xmlns:ttm="http://www.w3.org/ns/ttml#metadata">\n'
        '      <ttm:title>{title}</ttm:title>\n'
        '      <ttm:desc>IMSC1 Timed Text ({profile_name}) | {title}</ttm:desc>\n'
        '    </metadata>\n'
        '    <styling>\n'
        '      <style xml:id="s_default" tts:fontFamily="proportionalSansSerif" '
        'tts:fontSize="100%" tts:color="#FFFFFF" tts:backgroundColor="#000000CC" '
        'tts:textAlign="center" tts:direction="{direction}"/>\n'
        '    </styling>\n'
        '    <layout>\n'
        '      <region xml:id="bottom_safe" tts:origin="10% 80%" tts:extent="80% 10%" '
        'tts:displayAlign="after" style="s_default"/>\n'
        '    </layout>\n'
        '  </head>\n'
        '  <body>\n'
        '    <div>\n'
        '{body_xml}\n'
        '    </div>\n'
        '  </body>\n'
        '</tt>\n'
    ).format(
        lang=xml_escape(target_loc),
        title=xml_escape(bible.project_title),
        profile_name=xml_escape(manifest.imsc1_profile),
        direction=xml_escape(direction),
        body_xml=body_xml,
    )


def export_imsc1_ttml(
    bible: MasterProductionBible,
    output_path: Union[str, Path],
    locale: Optional[str] = None,
) -> Path:
    """Export IMSC1 TTML XML with SMPTE 24fps non-drop timecodes (PM-FEAT-027)."""
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    ttml_xml = build_imsc1_ttml_xml(bible, locale=locale)
    out_p.write_text(ttml_xml, encoding="utf-8")
    return out_p


def export_adr_cue_sheet_csv(
    bible: MasterProductionBible,
    output_path: Union[str, Path],
) -> Path:
    """Export frame-accurate ADR dubbing cue sheet CSV with 3-beep pre-roll (PM-FEAT-027)."""
    manifest = _resolve_localization_manifest(bible)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "cue_id",
            "scene_number",
            "locale",
            "character_name",
            "in_tc",
            "out_tc",
            "pre_roll_beeps",
            "lip_sync_ratio",
            "emotion_tag",
            "loop_group_flag",
            "source_line",
            "adapted_line",
        ]
    )
    for cue in manifest.adr_cues:
        writer.writerow(
            [
                cue.cue_id,
                cue.scene_number,
                cue.locale,
                cue.character_name,
                cue.in_tc,
                cue.out_tc,
                cue.pre_roll_beeps,
                f"{cue.lip_sync_ratio:.3f}",
                cue.emotion_tag,
                str(cue.loop_group_flag).lower(),
                cue.source_line,
                cue.adapted_line,
            ]
        )

    out_p.write_text(buffer.getvalue(), encoding="utf-8")
    return out_p


def export_localization_manifest_json(
    bible: MasterProductionBible,
    output_path: Union[str, Path],
) -> Path:
    """Export LocalizationManifestSpec as formatted JSON to disk (PM-FEAT-027)."""
    manifest = _resolve_localization_manifest(bible)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_p


def _smpte_to_seconds(tc: str, fps: int = 24) -> float:
    if not tc or not isinstance(tc, str):
        return 0.0
    raw_parts = tc.strip().replace(";", ":").split(":")
    if len(raw_parts) != 4:
        return 0.0
    try:
        hh, mm, ss, ff = (int(p) for p in raw_parts)
    except (ValueError, TypeError):
        return 0.0
    if hh < 0 or mm < 0 or ss < 0 or ff < 0:
        return 0.0
    safe_fps = max(1, int(fps or 24))
    return float(hh * 3600 + mm * 60 + ss) + (float(ff) / float(safe_fps))


def export_localized_subtitles(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
) -> List[Path]:
    """Export localized SRT and WebVTT files (`subtitles_<locale>.srt`/`.vtt`) for all target locales."""
    manifest = _resolve_localization_manifest(bible)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for loc in manifest.target_locales:
        cues = [c for c in manifest.adr_cues if _normalize_locale(c.locale) == _normalize_locale(loc)]
        srt_blocks: List[str] = []
        vtt_blocks: List[str] = ["WEBVTT", f"NOTE Territory: {loc}", ""]

        for idx, cue in enumerate(cues, start=1):
            start_s = _smpte_to_seconds(cue.in_tc, fps=24)
            end_s = max(start_s + 0.5, _smpte_to_seconds(cue.out_tc, fps=24))
            text = cue.adapted_line or cue.source_line
            srt_blocks.append(
                f"{idx}\n"
                f"{_format_srt_timestamp(start_s)} --> {_format_srt_timestamp(end_s)}\n"
                f"{text}"
            )
            vtt_blocks.append(
                f"cue-{idx}\n"
                f"{_format_vtt_timestamp(start_s)} --> {_format_vtt_timestamp(end_s)}\n"
                f"{text}\n"
            )

        srt_path = out_dir / f"subtitles_{loc}.srt"
        vtt_path = out_dir / f"subtitles_{loc}.vtt"
        srt_path.write_text("\n\n".join(srt_blocks) + ("\n" if srt_blocks else ""), encoding="utf-8")
        vtt_path.write_text("\n".join(vtt_blocks).strip() + "\n", encoding="utf-8")
        written.extend([srt_path, vtt_path])

    return written


def export_localization_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
) -> Dict[str, Path]:
    """Export complete PM-FEAT-027 localization, ADR, and timed-text bundle into `output_dir`."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = export_localization_manifest_json(bible, out_dir / "localization_manifest.json")
    csv_path = export_adr_cue_sheet_csv(bible, out_dir / "adr_cue_sheet.csv")
    ttml_path = export_imsc1_ttml(bible, out_dir / "subtitles_localized.ttml")
    subtitle_paths = export_localized_subtitles(bible, out_dir)

    bundle: Dict[str, Path] = {
        "localization_manifest_json": json_path,
        "adr_cue_sheet_csv": csv_path,
        "subtitles_localized_ttml": ttml_path,
    }
    for sub_p in subtitle_paths:
        stem = sub_p.stem  # e.g. subtitles_en-US
        ext = sub_p.suffix.lstrip(".")
        bundle[f"{stem}_{ext}"] = sub_p

    return bundle
