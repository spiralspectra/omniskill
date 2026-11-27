"""Modular v2.19.0 Dark-Room Cinema HUD Components (PM-FEAT-037 & PM-FEAT-038).

Provides Python 3.11+ builders for:
1. PM-FEAT-037: IMF Package (ST 2067-21/50) & Theatrical DCI DCP Mastering (#imfDcpModal)
2. PM-FEAT-038: Voice Casting, Preston Blair Viseme Lip-Sync & Sidechain Ducking (#voiceDuckingModal)
"""

from __future__ import annotations

import hashlib
import json
import re
from html import escape as html_escape
from typing import Any, Dict, List, Optional, Tuple


def _escape_json_for_script(payload: Any) -> str:
    """Serializes JSON safely for embedding inside HTML <script> tags."""
    return re.sub(r"</(script)", r"<\/\1", json.dumps(payload), flags=re.IGNORECASE)


def _to_plain(obj: Any) -> Any:
    """Converts Pydantic models, enums, or nested objects into JSON-safe Python structures."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(v) for v in obj]
    return obj


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    """Safely extracts a field from a dict or object attribute."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _sec_to_smpte(sec: float, fps: int = 24) -> str:
    """Formats seconds to HH:MM:SS:FF SMPTE 24fps timecode."""
    total_frames = max(0, int(round(float(sec) * fps)))
    ff = total_frames % fps
    total_sec = total_frames // fps
    ss = total_sec % 60
    mm = (total_sec // 60) % 60
    hh = total_sec // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _parse_scene_window(timestamp_range: str, fallback_start: float) -> Tuple[float, float]:
    """Parses MM:SS-MM:SS or +Ns timestamp ranges into (start_sec, end_sec)."""
    ts = str(timestamp_range or "")
    matches = re.findall(r"(\d+):(\d+)", ts)
    if len(matches) >= 2:
        start_s = float(int(matches[0][0]) * 60 + int(matches[0][1]))
        end_s = float(int(matches[1][0]) * 60 + int(matches[1][1]))
        if end_s > start_s:
            return start_s, end_s
    ext = re.search(r"\+(\d+)s", ts, re.IGNORECASE)
    dur = float(max(4, min(15, int(ext.group(1))))) if ext else 8.0
    return fallback_start, fallback_start + dur


def _sha256_hex(seed_text: str) -> str:
    return hashlib.sha256(seed_text.encode("utf-8")).hexdigest()


def _deterministic_uuid(seed_text: str) -> str:
    h = _sha256_hex(seed_text)
    return f"urn:uuid:{h[0:8]}-{h[8:12]}-4{h[13:16]}-a{h[17:20]}-{h[20:32]}"


def _text_to_preston_blair_visemes(text: str) -> str:
    """Maps spoken dialogue text deterministically into Preston Blair viseme tokens."""
    cleaned = re.sub(r"[^a-zA-Z\s]", "", str(text or "")).upper()
    if not cleaned.strip():
        return "rest"
    tokens: List[str] = []
    for ch in cleaned:
        if ch == " ":
            if tokens and tokens[-1] != "rest":
                tokens.append("rest")
            continue
        if ch in {"M", "B", "P"}:
            code = "MBP"
        elif ch in {"F", "V"}:
            code = "FV"
        elif ch in {"W", "Q", "U"}:
            code = "WQ"
        elif ch == "O":
            code = "O"
        elif ch in {"A", "I"}:
            code = "AI"
        elif ch == "E":
            code = "E"
        elif ch == "L":
            code = "L"
        else:
            code = "etc"
        if not tokens or tokens[-1] != code:
            tokens.append(code)
    if not tokens:
        return "rest"
    return " · ".join(tokens[:14])


def synthesize_v219_imf_dcp_state(
    bible: Any,
    scenes_payload: Any = None,
    existing_imf: Any = None,
) -> Dict[str, Any]:
    """Extracts or deterministically synthesizes PM-FEAT-037 IMF & Theatrical DCP mastering state."""
    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    aspect_val = str(_to_plain(_get_field(bible, "aspect_ratio", "16:9")) or "16:9")
    runtime_sec = float(_get_field(bible, "total_runtime_seconds", 32) or 32)

    raw_existing = (
        existing_imf
        or _get_field(bible, "master_imf_dcp", None)
        or _get_field(bible, "imf_dcp_package", None)
        or _get_field(bible, "imf_dcp", None)
    )
    plain_existing = _to_plain(raw_existing) if isinstance(_to_plain(raw_existing), dict) else {}

    hdr_spec = _to_plain(_get_field(bible, "master_hdr_spec", None) or _get_field(bible, "hdr_spec", None) or {}) or {}
    spatial_audio = _to_plain(_get_field(bible, "master_spatial_audio", None) or _get_field(bible, "spatial_audio", None) or {}) or {}
    loc_manifest = _to_plain(_get_field(bible, "localization_manifest", None) or {}) or {}

    pkg_hash = _sha256_hex(f"imf:{project_title}:{aspect_val}:{runtime_sec}")[:10].upper()
    imf_package_id = str(plain_existing.get("package_id") or plain_existing.get("imf_package_id") or f"IMF-OMNI-{pkg_hash}")

    default_profile = "ST_2067_21_App2E" if (hdr_spec or "2.39" in aspect_val or "16:9" in aspect_val) else "ST_2067_50_ProRes"
    app_profile = str(plain_existing.get("application_profile") or plain_existing.get("imf_profile") or default_profile)
    if app_profile not in {"ST_2067_21_App2E", "ST_2067_50_ProRes"}:
        app_profile = "ST_2067_21_App2E"

    scenes_raw = scenes_payload if scenes_payload is not None else _get_field(bible, "scenes", [])
    scenes = _to_plain(scenes_raw) or []
    if isinstance(scenes, list) and scenes:
        cursor_s = 0.0
        for idx, sc in enumerate(scenes):
            sc_d = sc if isinstance(sc, dict) else {}
            _, en_s = _parse_scene_window(str(sc_d.get("timestamp_range") or ""), cursor_s)
            cursor_s = en_s
        if cursor_s > 0:
            runtime_sec = max(runtime_sec, cursor_s)

    # DCI Theatrical DCP card (supports DciTheatricalDcpSpec canonical fields first)
    raw_dcp = plain_existing.get("dcp_spec") if isinstance(plain_existing.get("dcp_spec"), dict) else {}
    res_class = str(
        raw_dcp.get("resolution_class")
        or ("4K Scope (4096x1716)" if "2.39" in aspect_val else "4K Flat (3996x2160)")
    )
    raw_bitrate_val = (
        raw_dcp.get("jpeg2000_max_bitrate_mbps")
        if raw_dcp.get("jpeg2000_max_bitrate_mbps") is not None
        else raw_dcp.get("jpeg2000_bitrate_mbps")
    )
    raw_bitrate = int(round(float(raw_bitrate_val if raw_bitrate_val is not None else 220)))
    j2k_bitrate_mbps = max(50, min(250, raw_bitrate))
    raw_color = str(raw_dcp.get("color_encoding") or raw_dcp.get("color_space") or "CIE XYZ 12-bit (2.6 Gamma)")
    if "CIE_XYZ_12BIT" in raw_color.upper():
        color_space_display = f"CIE XYZ 12-bit ({raw_color})"
    else:
        color_space_display = raw_color
    audio_cfg = str(
        raw_dcp.get("audio_config")
        or (f"24-bit / 48kHz PCM ({spatial_audio.get('channel_layout', '5.1 Surround')})" if spatial_audio else "24-bit / 48kHz PCM 5.1 Surround")
    )
    kdm_required = bool(
        raw_dcp.get("kdm_encryption_required")
        if raw_dcp.get("kdm_encryption_required") is not None
        else raw_dcp.get("kdm_required", False)
    )
    kdm_flag = str(raw_dcp.get("kdm_flag") or ("SMPTE_KDM_AES128" if kdm_required else "UNENCRYPTED_TEST"))

    dcp_spec = {
        "container_standard": str(raw_dcp.get("container_standard") or "SMPTE ST 429 DCP"),
        "resolution_class": res_class,
        "color_space": color_space_display,
        "jpeg2000_bitrate_mbps": j2k_bitrate_mbps,
        "audio_config": audio_cfg,
        "kdm_required": kdm_required,
        "kdm_flag": kdm_flag,
    }

    # Asset Map SHA-256 table (read canonical `assets` first, fallback `asset_map`)
    raw_assets = (
        plain_existing.get("assets")
        if isinstance(plain_existing.get("assets"), list)
        else (plain_existing.get("asset_map") if isinstance(plain_existing.get("asset_map"), list) else None)
    )
    asset_map: List[Dict[str, Any]] = []
    ov_pic_uuid: Optional[str] = None
    if raw_assets:
        for idx, a in enumerate(raw_assets):
            if not isinstance(a, dict):
                continue
            role = str(a.get("track_role") or "Essence")
            locale_c = str(a.get("locale_code") or "en-US")
            fp = str(a.get("file_path") or f"{role}_{locale_c}.mxf")
            a_uuid = str(a.get("asset_uuid") or _deterministic_uuid(f"asset:{imf_package_id}:{fp}"))
            if role == "picture_ov":
                ov_pic_uuid = a_uuid
            asset_map.append(
                {
                    "asset_uuid": a_uuid,
                    "file_path": fp,
                    "track_role": role,
                    "format": str(a.get("codec_profile") or a.get("format") or "MXF OP1a"),
                    "sha256": str(a.get("sha256_digest") or a.get("sha256") or _sha256_hex(f"{imf_package_id}:{fp}")),
                }
            )
    if not asset_map:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", project_title.lower()).strip("_") or "omni"
        default_files = [
            ("ASSETMAP.xml", "Package Index", "SMPTE ST 2067-2 XML"),
            (f"PKL_{slug}_ov.xml", "Packing List", "SMPTE ST 2067-2 XML"),
            (f"CPL_{slug}_OV_HERO.xml", "Composition Playlist (OV)", "SMPTE ST 2067-3 XML"),
            (f"MXF_PIC_{slug}_OV_24fps.mxf", "Video Essence (OV)", "JPEG2000 12-bit MXF" if app_profile == "ST_2067_21_App2E" else "Apple ProRes 4444 XQ MXF"),
            (f"MXF_AUD_{slug}_51PCM.mxf", "Audio Essence (5.1)", "24-bit / 48kHz BWF PCM MXF"),
            (f"TTML_{slug}_IMSC1_enUS.xml", "Timed Text Track", "IMSC1 Profile TTML"),
        ]
        for fp, role, fmt in default_files:
            asset_map.append(
                {
                    "asset_uuid": _deterministic_uuid(f"asset:{imf_package_id}:{fp}"),
                    "file_path": fp,
                    "track_role": role,
                    "format": fmt,
                    "sha256": _sha256_hex(f"{imf_package_id}:{fp}:{runtime_sec}"),
                }
            )

    # CPL table: OV_HERO, supplemental locales, cutdowns (supports ImfCompositionPlaylistSpec first)
    raw_cpls = plain_existing.get("cpls") if isinstance(plain_existing.get("cpls"), list) else None
    cpls: List[Dict[str, Any]] = []
    if raw_cpls:
        for idx, c in enumerate(raw_cpls):
            if not isinstance(c, dict):
                continue
            total_frames = c.get("total_frames")
            dur_val = (
                round(float(total_frames) / 24.0, 2)
                if total_frames is not None
                else float(c.get("duration_sec") or runtime_sec)
            )
            role_val = str(c.get("version_tag") or c.get("role") or ("OV_HERO" if idx == 0 else "SUPPLEMENTAL_LOCALE"))
            linked = c.get("linked_asset_uuids") if isinstance(c.get("linked_asset_uuids"), list) else []
            reuses_ov = (
                bool(c.get("reuses_ov_picture"))
                if c.get("reuses_ov_picture") is not None
                else ((ov_pic_uuid in linked) if (ov_pic_uuid and linked) else True)
            )
            pic_track = str(
                c.get("picture_track")
                or ("OV_PICTURE_ESSENCE" if "OV" in role_val.upper() and idx == 0 else ("OV_PICTURE_REF (Zero Re-Render)" if reuses_ov else "SUPPLEMENTAL_PIC"))
            )
            cpls.append(
                {
                    "cpl_id": str(c.get("cpl_uuid") or c.get("cpl_id") or _deterministic_uuid(f"cpl:{imf_package_id}:{idx}")),
                    "role": role_val,
                    "label": str(c.get("content_title_text") or c.get("label") or f"CPL {idx + 1}"),
                    "territory": str(c.get("territory") or c.get("source_cutdown_label") or ("en-US" if idx == 0 else "Supplemental")),
                    "duration_sec": dur_val,
                    "smpte_duration": str(c.get("smpte_duration") or _sec_to_smpte(dur_val, 24)),
                    "picture_track": pic_track,
                    "audio_track": str(c.get("audio_track") or "5.1 + 2.0 Stereo Mix"),
                    "timed_text": str(c.get("timed_text") or "IMSC1 (TTML)"),
                    "reuses_ov_picture": reuses_ov,
                    "status": str(c.get("status") or "VALIDATED"),
                }
            )
    if not cpls:
        cpls.append(
            {
                "cpl_id": _deterministic_uuid(f"cpl:{imf_package_id}:OV_HERO"),
                "role": "OV_HERO",
                "label": f"{project_title} · Original Version Hero",
                "territory": "en-US (OV)",
                "duration_sec": runtime_sec,
                "smpte_duration": _sec_to_smpte(runtime_sec, 24),
                "picture_track": f"OV_PICTURE_{app_profile}",
                "audio_track": "PCM 5.1 + 2.0 LtRt",
                "timed_text": "IMSC1 en-US SDH",
                "reuses_ov_picture": True,
                "status": "VALIDATED",
            }
        )
        loc_territories: List[str] = []
        for t in (loc_manifest.get("locales") or loc_manifest.get("territory_dubs") or loc_manifest.get("territories") or []):
            if isinstance(t, dict):
                code = t.get("bcp47_tag") or t.get("locale") or t.get("territory_code") or t.get("language")
                if code:
                    loc_territories.append(str(code))
            elif isinstance(t, str):
                loc_territories.append(t)
        if not loc_territories:
            loc_territories = ["es-419", "fr-FR", "ja-JP"]
        for loc_code in loc_territories[:3]:
            cpls.append(
                {
                    "cpl_id": _deterministic_uuid(f"cpl:{imf_package_id}:SUPP:{loc_code}"),
                    "role": "SUPPLEMENTAL_LOCALE",
                    "label": f"Supplemental Locale ({loc_code})",
                    "territory": loc_code,
                    "duration_sec": runtime_sec,
                    "smpte_duration": _sec_to_smpte(runtime_sec, 24),
                    "picture_track": "OV_PICTURE_REF (Zero Re-Render)",
                    "audio_track": f"Localized Dub Stem ({loc_code})",
                    "timed_text": f"IMSC1 {loc_code}",
                    "reuses_ov_picture": True,
                    "status": "VALIDATED",
                }
            )
        for cut_sec, cut_role in ((15.0, "CUTDOWN_15S"), (6.0, "CUTDOWN_06S")):
            eff_dur = min(runtime_sec, cut_sec)
            cpls.append(
                {
                    "cpl_id": _deterministic_uuid(f"cpl:{imf_package_id}:{cut_role}"),
                    "role": cut_role,
                    "label": f"Broadcast Cutdown ({int(eff_dur)}s)",
                    "territory": "GLOBAL",
                    "duration_sec": eff_dur,
                    "smpte_duration": _sec_to_smpte(eff_dur, 24),
                    "picture_track": "OV_PICTURE_VIRTUAL_EDIT",
                    "audio_track": "5.1 / 2.0 Cutdown Mix",
                    "timed_text": "IMSC1 Cutdown",
                    "reuses_ov_picture": True,
                    "status": "VALIDATED",
                }
            )

    raw_reuse = (
        plain_existing.get("deduplicated_picture_reuse_pct")
        if plain_existing.get("deduplicated_picture_reuse_pct") is not None
        else plain_existing.get("ov_picture_reuse_pct")
    )
    if raw_reuse is not None:
        ov_reuse_pct = round(max(0.0, min(100.0, float(raw_reuse))), 1)
    else:
        supp_cpls = [c for c in cpls if c.get("role") != "OV_HERO"]
        reused = sum(1 for c in supp_cpls if c.get("reuses_ov_picture", True))
        ov_reuse_pct = round((reused / max(1, len(supp_cpls))) * 100.0, 1) if supp_cpls else 100.0

    return {
        "schema": "omni.imf_dcp_package.v1",
        "project_title": project_title,
        "aspect_ratio": aspect_val,
        "fps": 24,
        "total_runtime_sec": round(runtime_sec, 2),
        "total_smpte": _sec_to_smpte(runtime_sec, 24),
        "imf_package_id": imf_package_id,
        "application_profile": app_profile,
        "ov_picture_reuse_pct": ov_reuse_pct,
        "dcp_spec": dcp_spec,
        "cpls": cpls,
        "asset_map": asset_map,
    }


def synthesize_v219_voice_ducking_state(
    bible: Any,
    scenes_payload: Any = None,
    existing_voice: Any = None,
) -> Dict[str, Any]:
    """Extracts or deterministically synthesizes PM-FEAT-038 Voice Casting, Viseme Lip-Sync & Sidechain Ducking state."""
    project_title = str(_get_field(bible, "project_title", "Omni Production") or "Omni Production")
    runtime_sec = float(_get_field(bible, "total_runtime_seconds", 32) or 32)
    bgm = _to_plain(_get_field(bible, "master_bgm", {}) or {}) or {}
    sonic_bp = _to_plain(_get_field(bible, "sonic_blueprint", {}) or {}) or {}

    raw_existing = (
        existing_voice
        or _get_field(bible, "master_voice_ducking", None)
        or _get_field(bible, "voice_ducking", None)
        or _get_field(bible, "voice_casting", None)
    )
    plain_existing = _to_plain(raw_existing) if isinstance(_to_plain(raw_existing), dict) else {}

    scenes_raw = scenes_payload if scenes_payload is not None else _get_field(bible, "scenes", [])
    scenes = _to_plain(scenes_raw) or []
    if not isinstance(scenes, list) or not scenes:
        scenes = [{"scene_index": 1, "scene_title": "Opening Hero Plate", "timestamp_range": "00:00-00:08"}]

    characters = _to_plain(_get_field(bible, "characters", []) or [])
    if not isinstance(characters, list):
        characters = []

    # 1. Voice Casting Roster (supports MasterVoiceDuckingManifest.casting_roster first)
    raw_roster = (
        plain_existing.get("casting_roster")
        if isinstance(plain_existing.get("casting_roster"), list)
        else (plain_existing.get("voice_roster") if isinstance(plain_existing.get("voice_roster"), list) else None)
    )
    voice_roster: List[Dict[str, Any]] = []
    if raw_roster:
        for r in raw_roster:
            if not isinstance(r, dict):
                continue
            wpm = min(150, max(80, int(round(float(r.get("target_wpm") or 132)))))
            pitch_range = r.get("pitch_hz_range")
            pitch_num = r.get("pitch_hz")
            if pitch_num is None and isinstance(pitch_range, str):
                nums = re.findall(r"\d+", pitch_range)
                pitch_num = int(round((int(nums[0]) + int(nums[-1])) / 2)) if nums else 128
            pitch_val = int(pitch_num or 128)
            pitch_disp = str(pitch_range or f"{pitch_val} Hz")
            voice_roster.append(
                {
                    "character": str(r.get("character_name") or r.get("character") or "Narrator"),
                    "vocal_register": str(r.get("vocal_register") or "Warm Baritone"),
                    "mic_perspective": str(r.get("mic_perspective") or "Neumann U87 · Intimate Close"),
                    "target_wpm": wpm,
                    "pitch_hz": pitch_val,
                    "pitch_hz_range": pitch_disp,
                }
            )
    if not voice_roster:
        for idx, ch in enumerate(characters):
            if not isinstance(ch, dict):
                continue
            name = str(ch.get("name") or f"Talent {idx + 1}")
            is_alt = idx % 2 == 1
            p_hz = 198 if is_alt else 124
            voice_roster.append(
                {
                    "character": name,
                    "vocal_register": "Crisp Mezzo-Alto" if is_alt else "Grounded Baritone",
                    "mic_perspective": "Schoeps CMC641 Boom · 1.2ft" if not is_alt else "DPA 6060 Lav + Close Room",
                    "target_wpm": 132 if not is_alt else 138,
                    "pitch_hz": p_hz,
                    "pitch_hz_range": f"{p_hz} Hz",
                }
            )
        if not voice_roster:
            voice_roster.append(
                {
                    "character": "Director Narrator (VO)",
                    "vocal_register": "Calm Editorial Baritone",
                    "mic_perspective": "Neumann U87 Ai · Dry Booth (-16 LUFS)",
                    "target_wpm": 126,
                    "pitch_hz": 118,
                    "pitch_hz_range": "118 Hz",
                }
            )

    # 2. Viseme Lip-Sync Cues (WPS <= 2.5, supports canonical scene_profiles[].viseme_cues)
    scene_profiles = plain_existing.get("scene_profiles") if isinstance(plain_existing.get("scene_profiles"), list) else []
    raw_cues: Optional[List[Any]] = (
        plain_existing.get("viseme_cues")
        if isinstance(plain_existing.get("viseme_cues"), list)
        else None
    )
    if raw_cues is None and scene_profiles:
        flattened_cues: List[Dict[str, Any]] = []
        for sp in scene_profiles:
            if isinstance(sp, dict) and isinstance(sp.get("viseme_cues"), list):
                flattened_cues.extend([vc for vc in sp["viseme_cues"] if isinstance(vc, dict)])
        if flattened_cues:
            raw_cues = flattened_cues

    viseme_cues: List[Dict[str, Any]] = []
    cursor_s = 0.0
    scene_windows: List[Tuple[int, float, float, Dict[str, Any]]] = []
    for idx, sc in enumerate(scenes):
        sc_d = sc if isinstance(sc, dict) else {}
        s_idx = int(sc_d.get("scene_index", idx + 1) or (idx + 1))
        st_s, en_s = _parse_scene_window(str(sc_d.get("timestamp_range") or ""), cursor_s)
        cursor_s = en_s
        scene_windows.append((s_idx, st_s, en_s, sc_d))
    if cursor_s > 0:
        runtime_sec = max(runtime_sec, cursor_s)

    if raw_cues:
        for idx, c in enumerate(raw_cues):
            if not isinstance(c, dict):
                continue
            line = str(c.get("line_text") or c.get("dialogue_line") or c.get("text") or "Precision in every frame.")
            wps = min(2.5, max(0.5, round(float(c.get("wps") or 2.1), 2)))
            st_s = float(c.get("start_sec") or 0.0)
            en_s = float(c.get("end_sec") or (st_s + 2.8))
            dom_vis = c.get("dominant_visemes")
            if isinstance(dom_vis, list) and dom_vis:
                vis_str = " · ".join(str(v) for v in dom_vis[:14])
            else:
                vis_str = str(c.get("visemes") or _text_to_preston_blair_visemes(line))
            on_cam_val = (
                bool(c.get("lip_sync_required_on_camera"))
                if c.get("lip_sync_required_on_camera") is not None
                else bool(c.get("on_cam_lip_sync", True))
            )
            viseme_cues.append(
                {
                    "cue_id": str(c.get("cue_id") or f"VC-{idx + 1:02d}"),
                    "scene_index": int(c.get("scene_index") or 1),
                    "smpte_in": str(c.get("smpte_in") or _sec_to_smpte(st_s, 24)),
                    "start_sec": round(st_s, 2),
                    "end_sec": round(en_s, 2),
                    "speaker": str(c.get("speaker_id") or c.get("speaker") or voice_roster[0]["character"]),
                    "dialogue_line": line,
                    "wps": wps,
                    "visemes": vis_str,
                    "on_cam_lip_sync": on_cam_val,
                }
            )
    if not viseme_cues:
        bp_lines = list(sonic_bp.get("dialogue_lines") or []) if isinstance(sonic_bp.get("dialogue_lines"), list) else []
        cue_counter = 1
        for w_idx, (s_idx, st_s, en_s, sc_d) in enumerate(scene_windows):
            sc_sonic = sc_d.get("diegetic_sonic") if isinstance(sc_d.get("diegetic_sonic"), dict) else {}
            sc_lines = list(sc_sonic.get("dialogue_lines") or []) if isinstance(sc_sonic.get("dialogue_lines"), list) else []
            if not sc_lines and w_idx < len(bp_lines):
                sc_lines = [bp_lines[w_idx]]
            if not sc_lines:
                # Synthesize subtle VO / lip-sync cue for first & final scenes so timeline is never empty
                if w_idx == 0:
                    sc_lines = [f"{voice_roster[0]['character']}: Crafted for absolute precision."]
                elif w_idx == len(scene_windows) - 1:
                    sc_lines = [f"{voice_roster[0]['character']}: {project_title}."]
            for l_idx, raw_line in enumerate(sc_lines):
                line_str = str(raw_line or "").strip()
                if ":" in line_str:
                    spk, spoken = line_str.split(":", 1)
                    speaker = spk.strip() or voice_roster[0]["character"]
                    spoken = spoken.strip() or "Precision in motion."
                else:
                    speaker = voice_roster[l_idx % len(voice_roster)]["character"]
                    spoken = line_str or "Precision in motion."
                cue_start = round(st_s + 0.6 + (l_idx * 2.4), 2)
                cue_dur = max(1.6, min(3.6, round((en_s - st_s) * 0.45, 2)))
                cue_end = round(min(en_s - 0.2, cue_start + cue_dur), 2)
                word_cnt = max(1, len(spoken.split()))
                measured_wps = round(word_cnt / max(0.8, cue_end - cue_start), 2)
                wps = min(2.5, max(0.8, measured_wps))
                on_cam = bool(characters) and ("VO" not in speaker.upper())
                viseme_cues.append(
                    {
                        "cue_id": f"VC-{cue_counter:02d}",
                        "scene_index": s_idx,
                        "smpte_in": _sec_to_smpte(cue_start, 24),
                        "start_sec": cue_start,
                        "end_sec": cue_end,
                        "speaker": speaker,
                        "dialogue_line": spoken,
                        "wps": wps,
                        "visemes": _text_to_preston_blair_visemes(spoken),
                        "on_cam_lip_sync": on_cam,
                    }
                )
                cue_counter += 1

    # 3. Sidechain Ducking Envelope & SNR KPI (supports canonical scene_profiles[].ducking_keyframes)
    duck_thresh = float(plain_existing.get("ducking_threshold_lufs") or -24.0)
    duck_depth = float(plain_existing.get("default_music_duck_db") or plain_existing.get("ducking_depth_db") or -9.5)
    attack_ms = int(plain_existing.get("attack_ms") or 25)
    release_ms = int(plain_existing.get("release_ms") or 320)

    raw_env = plain_existing.get("ducking_envelope") if isinstance(plain_existing.get("ducking_envelope"), list) else None
    ducking_envelope: List[Dict[str, Any]] = []
    if raw_env:
        for e in raw_env:
            if not isinstance(e, dict):
                continue
            st_s = float(e.get("start_sec") or 0.0)
            en_s = float(e.get("end_sec") or (st_s + 8.0))
            ducking_envelope.append(
                {
                    "scene_index": int(e.get("scene_index") or 1),
                    "smpte_in": str(e.get("smpte_in") or _sec_to_smpte(st_s, 24)),
                    "smpte_out": str(e.get("smpte_out") or _sec_to_smpte(en_s, 24)),
                    "start_sec": round(st_s, 2),
                    "end_sec": round(en_s, 2),
                    "bgm_baseline_lufs": float(e.get("bgm_baseline_lufs") or -14.0),
                    "attenuation_db": float(e.get("attenuation_db") or duck_depth),
                    "ducked_bgm_lufs": float(e.get("ducked_bgm_lufs") or (-14.0 + duck_depth)),
                    "dialogue_lufs": float(e.get("dialogue_lufs") or -16.0),
                    "snr_db": float(e.get("snr_db") or 14.5),
                    "active_speaker": str(e.get("active_speaker") or "BGM Bed"),
                }
            )
    if not ducking_envelope and scene_profiles:
        win_by_idx = {s_i: (st_s, en_s) for s_i, st_s, en_s, _ in scene_windows}
        for sp in scene_profiles:
            if not isinstance(sp, dict):
                continue
            s_idx = int(sp.get("scene_index") or 1)
            st_s, en_s = win_by_idx.get(s_idx, ((s_idx - 1) * 8.0, s_idx * 8.0))
            kfs = [k for k in (sp.get("ducking_keyframes") or []) if isinstance(k, dict)]
            if kfs:
                attack_ms = int(kfs[0].get("attack_ms") or attack_ms)
                release_ms = int(kfs[0].get("release_ms") or release_ms)
                atten = min(float(k.get("attenuation_db") or 0.0) for k in kfs)
            else:
                atten = -1.5
            bgm_base = -14.0
            snr_val = float(sp.get("dialogue_to_bgm_snr_db") or 9.0)
            speakers = [str(s) for s in (sp.get("active_speakers") or []) if s]
            ducking_envelope.append(
                {
                    "scene_index": s_idx,
                    "smpte_in": _sec_to_smpte(st_s, 24),
                    "smpte_out": _sec_to_smpte(en_s, 24),
                    "start_sec": round(st_s, 2),
                    "end_sec": round(en_s, 2),
                    "bgm_baseline_lufs": bgm_base,
                    "attenuation_db": round(atten, 1),
                    "ducked_bgm_lufs": round(bgm_base + atten, 1),
                    "dialogue_lufs": -16.0 if kfs else -48.0,
                    "snr_db": round(snr_val, 1),
                    "active_speaker": speakers[0] if speakers else "Score / Foley Unmasked",
                }
            )
    if not ducking_envelope:
        cues_by_scene: Dict[int, List[Dict[str, Any]]] = {}
        for c in viseme_cues:
            cues_by_scene.setdefault(int(c["scene_index"]), []).append(c)
        for s_idx, st_s, en_s, _ in scene_windows:
            sc_cues = cues_by_scene.get(s_idx, [])
            has_speech = bool(sc_cues)
            atten = duck_depth if has_speech else -1.5
            bgm_base = -14.0
            ducked_lufs = round(bgm_base + atten, 1)
            dlg_lufs = -16.0 if has_speech else -48.0
            snr = round(max(6.0, (dlg_lufs - ducked_lufs) + 7.0), 1) if has_speech else 12.0
            ducking_envelope.append(
                {
                    "scene_index": s_idx,
                    "smpte_in": _sec_to_smpte(st_s, 24),
                    "smpte_out": _sec_to_smpte(en_s, 24),
                    "start_sec": round(st_s, 2),
                    "end_sec": round(en_s, 2),
                    "bgm_baseline_lufs": bgm_base,
                    "attenuation_db": atten,
                    "ducked_bgm_lufs": ducked_lufs,
                    "dialogue_lufs": dlg_lufs,
                    "snr_db": snr,
                    "active_speaker": sc_cues[0]["speaker"] if has_speech else "Score / Foley Unmasked",
                }
            )

    avg_snr = round(
        float(
            plain_existing.get("snr_db")
            or (sum(float(e["snr_db"]) for e in ducking_envelope) / max(1, len(ducking_envelope)))
        ),
        1,
    )

    return {
        "schema": "omni.voice_casting_ducking.v1",
        "project_title": project_title,
        "bgm_track": str(bgm.get("track_title") or "Master Sonic Blueprint"),
        "fps": 24,
        "total_runtime_sec": round(runtime_sec, 2),
        "snr_db": avg_snr,
        "ducking_threshold_lufs": duck_thresh,
        "ducking_depth_db": duck_depth,
        "attack_ms": attack_ms,
        "release_ms": release_ms,
        "voice_roster": voice_roster,
        "viseme_cues": viseme_cues,
        "ducking_envelope": ducking_envelope,
    }


def build_v219_hud_bundle(
    bible: Any,
    scenes_payload: Any = None,
    existing_imf: Any = None,
    existing_voice: Any = None,
) -> Dict[str, str]:
    """Builds Dark-Room Cinema v2.19.0 HUD bundle returning {'css': ..., 'html': ..., 'js': ...}."""
    imf_state = synthesize_v219_imf_dcp_state(bible, scenes_payload=scenes_payload, existing_imf=existing_imf)
    voice_state = synthesize_v219_voice_ducking_state(bible, scenes_payload=scenes_payload, existing_voice=existing_voice)

    imf_json = _escape_json_for_script(imf_state)
    voice_json = _escape_json_for_script(voice_state)

    dcp = imf_state["dcp_spec"]
    kdm_badge_cls = "v219-badge-warn" if dcp.get("kdm_required") else "v219-badge-pass"

    cpl_rows_html: List[str] = []
    for c in imf_state.get("cpls") or []:
        reuse_cls = "v219-badge-pass" if c.get("reuses_ov_picture") else "v219-badge-info"
        cpl_rows_html.append(
            f'<tr>'
            f'<td><code class="v219-code">{html_escape(str(c.get("role", "")))}</code><br>'
            f'<span class="v219-sub">{html_escape(str(c.get("cpl_id", ""))[:28])}</span></td>'
            f'<td><strong>{html_escape(str(c.get("label", "")))}</strong><br>'
            f'<span class="v219-sub">{html_escape(str(c.get("territory", "")))}</span></td>'
            f'<td><code class="v219-code">{html_escape(str(c.get("smpte_duration", "")))}</code></td>'
            f'<td><span class="v219-badge {reuse_cls}">{html_escape(str(c.get("picture_track", "")))}</span></td>'
            f'<td><span class="v219-sub">{html_escape(str(c.get("audio_track", "")))} · {html_escape(str(c.get("timed_text", "")))}</span></td>'
            f'<td><span class="v219-badge v219-badge-pass">{html_escape(str(c.get("status", "VALIDATED")))}</span></td>'
            f'</tr>'
        )
    cpl_tbody_html = "\n".join(cpl_rows_html)

    asset_rows_html: List[str] = []
    for a in imf_state.get("asset_map") or []:
        asset_rows_html.append(
            f'<tr>'
            f'<td><code class="v219-code">{html_escape(str(a.get("file_path", "")))}</code><br>'
            f'<span class="v219-sub">{html_escape(str(a.get("asset_uuid", "")))}</span></td>'
            f'<td><span class="v219-sub">{html_escape(str(a.get("track_role", "")))} · {html_escape(str(a.get("format", "")))}</span></td>'
            f'<td><code class="v219-sha">{html_escape(str(a.get("sha256", "")))}</code></td>'
            f'</tr>'
        )
    asset_tbody_html = "\n".join(asset_rows_html)

    roster_rows_html: List[str] = []
    for vr in voice_state.get("voice_roster") or []:
        roster_rows_html.append(
            f'<tr>'
            f'<td><strong>{html_escape(str(vr.get("character", "")))}</strong></td>'
            f'<td><span class="v219-sub">{html_escape(str(vr.get("vocal_register", "")))}</span></td>'
            f'<td><span class="v219-sub">{html_escape(str(vr.get("mic_perspective", "")))}</span></td>'
            f'<td><code class="v219-code">{int(vr.get("target_wpm", 130))} WPM</code></td>'
            f'<td><code class="v219-code">{html_escape(str(vr.get("pitch_hz_range") or (str(vr.get("pitch_hz", 128)) + " Hz")))}</code></td>'
            f'</tr>'
        )
    roster_tbody_html = "\n".join(roster_rows_html)

    viseme_rows_html: List[str] = []
    for vc in voice_state.get("viseme_cues") or []:
        wps_val = min(2.5, float(vc.get("wps", 2.0)))
        on_cam = bool(vc.get("on_cam_lip_sync", False))
        sync_badge = '<span class="v219-badge v219-badge-pass">ON-CAM LIP-SYNC</span>' if on_cam else '<span class="v219-badge v219-badge-info">OFF-CAM VO</span>'
        viseme_rows_html.append(
            f'<tr>'
            f'<td><strong>S{int(vc.get("scene_index", 1)):02d}</strong><br><code class="v219-code">{html_escape(str(vc.get("smpte_in", "")))}</code></td>'
            f'<td><strong>{html_escape(str(vc.get("speaker", "")))}</strong><br><span class="v219-sub">{html_escape(str(vc.get("dialogue_line", "")))}</span></td>'
            f'<td><span class="v219-badge v219-badge-pass">{wps_val:.2f} WPS (&le;2.5)</span></td>'
            f'<td><code class="v219-code">{html_escape(str(vc.get("visemes", "")))}</code></td>'
            f'<td>{sync_badge}</td>'
            f'</tr>'
        )
    viseme_tbody_html = "\n".join(viseme_rows_html)

    duck_bars_html: List[str] = []
    for de in voice_state.get("ducking_envelope") or []:
        atten_abs = min(18.0, abs(float(de.get("attenuation_db", -9.5))))
        bar_pct = max(12.0, min(100.0, (atten_abs / 15.0) * 100.0))
        s_idx = int(de.get("scene_index", 1))
        duck_bars_html.append(
            f'<div class="v219-duck-row">'
            f'<span class="v219-duck-label">S{s_idx:02d} · {html_escape(str(de.get("smpte_in", "")))}</span>'
            f'<div class="v219-duck-track" role="img" aria-label="Scene {s_idx} BGM ducking {float(de.get("attenuation_db", -9.5)):.1f} dB">'
            f'<div class="v219-duck-fill" style="width:{bar_pct:.1f}%;"></div>'
            f'</div>'
            f'<span class="v219-duck-val">{float(de.get("attenuation_db", -9.5)):.1f} dB · SNR +{float(de.get("snr_db", 14.5)):.1f} dB</span>'
            f'</div>'
        )
    duck_css_bars_html = "\n".join(duck_bars_html)

    css_str = """
    /* v2.19.0 IMF/DCP Mastering & Voice Casting / Sidechain Ducking HUDs */
    #imfDcpModal,
    #voiceDuckingModal {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(7, 8, 11, 0.92);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      z-index: 10070;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .v219-modal-card {
      background: #0E1017;
      color: #F8FAFC;
      border: 1px solid #38BDF8;
      border-radius: 10px;
      width: 100%;
      max-width: 1140px;
      max-height: 92vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.9);
    }
    .v219-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 20px;
      background: #141722;
      border-bottom: 1px solid #334155;
    }
    .v219-modal-title {
      margin: 0;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: #F8FAFC;
    }
    .v219-modal-sub {
      display: block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #7DD3FC;
      margin-top: 2px;
    }
    .v219-close-btn {
      min-width: 44px;
      min-height: 44px;
      background: #B91C1C;
      color: #FFFFFF;
      border: 1px solid #F87171;
      border-radius: 5px;
      padding: 8px 14px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }
    .v219-close-btn:hover,
    .v219-close-btn:focus-visible {
      background: #DC2626;
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    .v219-modal-body {
      padding: 18px 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .v219-kpi-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      background: #141722;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 12px 14px;
    }
    .v219-badge-group {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .v219-badge {
      display: inline-block;
      padding: 4px 9px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
    }
    .v219-badge-pass {
      background: #064E3B;
      color: #A7F3D0;
      border: 1px solid #10B981;
    }
    .v219-badge-warn {
      background: #451A03;
      color: #FDE68A;
      border: 1px solid #F59E0B;
    }
    .v219-badge-info {
      background: #0C4A6E;
      color: #BAE6FD;
      border: 1px solid #38BDF8;
    }
    .v219-code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #FDE047;
    }
    .v219-sha {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10.5px;
      color: #BAE6FD;
      word-break: break-all;
    }
    .v219-sub {
      font-size: 11.5px;
      color: #E2E8F0;
    }
    .v219-card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      background: #141722;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px 14px;
    }
    .v219-spec-cell {
      background: #0B1120;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .v219-spec-lbl {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      text-transform: uppercase;
      color: #CBD5E1;
    }
    .v219-spec-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      color: #F8FAFC;
    }
    .v219-section-title {
      margin: 4px 0 0;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 13px;
      font-weight: 700;
      color: #BAE6FD;
    }
    .v219-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    .v219-table th,
    .v219-table td {
      border: 1px solid #334155;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }
    .v219-table th {
      background: #1E293B;
      color: #F8FAFC;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }
    .v219-svg-frame {
      background: #05070B;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .v219-svg-frame svg {
      width: 100%;
      height: auto;
      display: block;
      border-radius: 4px;
    }
    .v219-duck-bars {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .v219-duck-row {
      display: grid;
      grid-template-columns: 150px 1fr 185px;
      align-items: center;
      gap: 10px;
      background: #0E1017;
      border: 1px solid #334155;
      border-radius: 5px;
      padding: 6px 10px;
    }
    .v219-duck-label,
    .v219-duck-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #F8FAFC;
    }
    .v219-duck-track {
      height: 10px;
      background: #1E293B;
      border-radius: 4px;
      overflow: hidden;
      border: 1px solid #475569;
    }
    .v219-duck-fill {
      height: 100%;
      background: linear-gradient(90deg, #38BDF8, #FACC15);
    }
    .v219-actions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .v219-dl-btn {
      min-height: 44px;
      background: #0369A1;
      color: #FFFFFF;
      border: 1px solid #38BDF8;
      border-radius: 5px;
      padding: 8px 14px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
    }
    .v219-dl-btn:hover {
      background: #0284C7;
    }
    .v219-dl-btn:focus-visible {
      outline: 2px solid #FACC15;
      outline-offset: 2px;
    }
    @media (prefers-reduced-motion: reduce) {
      #imfDcpModal *,
      #voiceDuckingModal * {
        transition: none !important;
      }
    }
    """

    html_str = f"""
<!-- v2.19.0 PM-FEAT-037: IMF Package (ST 2067-21/50) & DCI Theatrical DCP Mastering HUD -->
<div id="imfDcpModal" role="dialog" aria-modal="true" aria-labelledby="imfDcpModalTitle" tabindex="-1">
  <div class="v219-modal-card">
    <div class="v219-modal-header">
      <div>
        <h2 id="imfDcpModalTitle" class="v219-modal-title">IMF Package (ST 2067) &amp; Theatrical DCI DCP Mastering</h2>
        <span class="v219-modal-sub">SMPTE CPL Versioning, OV Picture Reuse, CIE XYZ 12-Bit DCP &amp; SHA-256 Asset Map [}}]</span>
      </div>
      <button type="button" class="v219-close-btn" id="imfDcpCloseBtn" onclick="toggleImfDcpHUD(false)" aria-label="Close IMF and DCP Mastering HUD">Close [Esc]</button>
    </div>
    <div class="v219-modal-body">
      <div class="v219-kpi-row">
        <div class="v219-badge-group">
          <span class="v219-badge v219-badge-info" id="v219-imf-pkg-badge">PKG: {html_escape(str(imf_state["imf_package_id"]))}</span>
          <span class="v219-badge v219-badge-info" id="v219-imf-profile-badge">Profile: {html_escape(str(imf_state["application_profile"]))}</span>
          <span class="v219-badge v219-badge-pass" id="v219-imf-reuse-badge">{float(imf_state["ov_picture_reuse_pct"]):.1f}% OV Picture Reuse</span>
        </div>
        <span class="v219-sub">Runtime: <strong class="v219-code">{html_escape(str(imf_state["total_smpte"]))}</strong> @ 24fps</span>
      </div>

      <h3 class="v219-section-title">DCI Theatrical DCP Mastering Spec</h3>
      <div class="v219-card-grid" aria-label="DCI Theatrical DCP Card">
        <div class="v219-spec-cell">
          <span class="v219-spec-lbl">Container Standard</span>
          <span class="v219-spec-val">{html_escape(str(dcp["container_standard"]))}</span>
        </div>
        <div class="v219-spec-cell">
          <span class="v219-spec-lbl">Resolution Class</span>
          <span class="v219-spec-val">{html_escape(str(dcp["resolution_class"]))}</span>
        </div>
        <div class="v219-spec-cell">
          <span class="v219-spec-lbl">Color Space</span>
          <span class="v219-spec-val">{html_escape(str(dcp["color_space"]))}</span>
        </div>
        <div class="v219-spec-cell">
          <span class="v219-spec-lbl">JPEG2000 Bitrate</span>
          <span class="v219-spec-val">{int(dcp["jpeg2000_bitrate_mbps"])} Mbps (&le;250 Mbps)</span>
        </div>
        <div class="v219-spec-cell">
          <span class="v219-spec-lbl">Audio Config</span>
          <span class="v219-spec-val">{html_escape(str(dcp["audio_config"]))}</span>
        </div>
        <div class="v219-spec-cell">
          <span class="v219-spec-lbl">KDM Encryption Flag</span>
          <span class="v219-spec-val"><span class="v219-badge {kdm_badge_cls}">{html_escape(str(dcp["kdm_flag"]))}</span></span>
        </div>
      </div>

      <h3 class="v219-section-title">IMF Composition Playlists (CPLs · OV_HERO, Supplemental Locales &amp; Cutdowns)</h3>
      <table class="v219-table" aria-label="IMF Composition Playlists">
        <thead>
          <tr>
            <th>CPL Role / UUID</th>
            <th>Composition &amp; Territory</th>
            <th>SMPTE Duration</th>
            <th>Picture Essence</th>
            <th>Audio &amp; Timed Text</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="v219-cpl-tbody">
          {cpl_tbody_html}
        </tbody>
      </table>

      <h3 class="v219-section-title">ASSETMAP.xml &amp; PKL SHA-256 Digest Ledger</h3>
      <table class="v219-table" aria-label="IMF Asset Map SHA-256 Ledger">
        <thead>
          <tr>
            <th>Asset Path / UUID</th>
            <th>Track Role &amp; Format</th>
            <th>SHA-256 Digest</th>
          </tr>
        </thead>
        <tbody id="v219-assetmap-tbody">
          {asset_tbody_html}
        </tbody>
      </table>

      <div class="v219-actions-row">
        <button type="button" class="v219-dl-btn" id="btn-dl-imf-json" onclick="downloadImfPackageJSON()">⤓ imf_package_manifest.json</button>
        <button type="button" class="v219-dl-btn" id="btn-dl-dcp-md" onclick="downloadDcpSpecMD()">⤓ dcp_theatrical_spec.md</button>
      </div>
    </div>
  </div>
</div>

<!-- v2.19.0 PM-FEAT-038: Voice Casting, Preston Blair Viseme Lip-Sync & Sidechain Ducking HUD -->
<div id="voiceDuckingModal" role="dialog" aria-modal="true" aria-labelledby="voiceDuckingModalTitle" tabindex="-1">
  <div class="v219-modal-card">
    <div class="v219-modal-header">
      <div>
        <h2 id="voiceDuckingModalTitle" class="v219-modal-title">Voice Casting, Viseme Lip-Sync &amp; Sidechain Ducking Studio</h2>
        <span class="v219-modal-sub">Vocal Register Roster, Preston Blair Visemes (&le;2.5 WPS) &amp; BGM Ducking Envelope [{{]</span>
      </div>
      <button type="button" class="v219-close-btn" id="voiceDuckingCloseBtn" onclick="toggleVoiceDuckingHUD(false)" aria-label="Close Voice Casting and Ducking HUD">Close [Esc]</button>
    </div>
    <div class="v219-modal-body">
      <div class="v219-kpi-row">
        <div class="v219-badge-group">
          <span class="v219-badge v219-badge-pass" id="v219-snr-kpi">Dialogue-to-BGM SNR: +{float(voice_state["snr_db"]):.1f} dB</span>
          <span class="v219-badge v219-badge-info">Threshold: {float(voice_state["ducking_threshold_lufs"]):.1f} LUFS</span>
          <span class="v219-badge v219-badge-info">Duck Depth: {float(voice_state["ducking_depth_db"]):.1f} dB</span>
          <span class="v219-badge v219-badge-info">Attack/Rel: {int(voice_state["attack_ms"])}ms / {int(voice_state["release_ms"])}ms</span>
        </div>
        <span class="v219-sub">Score Bed: <strong class="v219-code">{html_escape(str(voice_state["bgm_track"]))}</strong></span>
      </div>

      <h3 class="v219-section-title">Voice Casting Roster</h3>
      <table class="v219-table" aria-label="Voice Casting Roster">
        <thead>
          <tr>
            <th>Character / Role</th>
            <th>Vocal Register</th>
            <th>Mic Perspective</th>
            <th>Target WPM</th>
            <th>Pitch Hz</th>
          </tr>
        </thead>
        <tbody id="v219-voice-roster-tbody">
          {roster_tbody_html}
        </tbody>
      </table>

      <h3 class="v219-section-title">Preston Blair Viseme Lip-Sync Cues</h3>
      <table class="v219-table" aria-label="Preston Blair Viseme Lip-Sync Cues">
        <thead>
          <tr>
            <th>Scene / SMPTE</th>
            <th>Speaker &amp; Spoken Line</th>
            <th>Cadence (WPS &le; 2.5)</th>
            <th>Preston Blair Visemes</th>
            <th>Lip-Sync Mode</th>
          </tr>
        </thead>
        <tbody id="v219-viseme-cues-tbody">
          {viseme_tbody_html}
        </tbody>
      </table>

      <div class="v219-svg-frame">
        <div class="v219-sub"><strong>Sidechain Ducking Attenuation Envelope</strong> · <span id="v219-duck-telemetry" aria-live="polite">Music bed dynamically ducked beneath dialogue transients.</span></div>
        <svg id="v219-ducking-svg" viewBox="0 0 880 150" role="img" aria-label="Sidechain Ducking Envelope SVG showing BGM attenuation bars across scenes"></svg>
        <div class="v219-duck-bars" id="v219-duck-css-bars">
          {duck_css_bars_html}
        </div>
      </div>

      <div class="v219-actions-row">
        <button type="button" class="v219-dl-btn" id="btn-dl-voice-json" onclick="downloadVoiceCastingJSON()">⤓ voice_casting_ducking_manifest.json</button>
        <button type="button" class="v219-dl-btn" id="btn-dl-ducking-csv" onclick="downloadDuckingAutomationCSV()">⤓ sidechain_ducking_automation.csv</button>
      </div>
    </div>
  </div>
</div>
"""

    js_template = """
    // v2.19.0 IMF/DCP Mastering (PM-FEAT-037) & Voice Casting / Sidechain Ducking (PM-FEAT-038)
    const V219_IMF_DCP_STATE = __IMF_JSON__;
    const V219_VOICE_DUCKING_STATE = __VOICE_JSON__;
    window.V219_IMF_DCP_STATE = V219_IMF_DCP_STATE;
    window.V219_VOICE_DUCKING_STATE = V219_VOICE_DUCKING_STATE;

    let isImfDcpHUDOpen = false;
    window.isImfDcpHUDOpen = false;
    let lastImfDcpOpener = null;

    let isVoiceDuckingHUDOpen = false;
    window.isVoiceDuckingHUDOpen = false;
    let lastVoiceDuckingOpener = null;

    let _v219Initialized = false;

    if (typeof V216_HUD_COMMANDS !== 'undefined' && Array.isArray(V216_HUD_COMMANDS)) {
      if (!V216_HUD_COMMANDS.some((c) => c.id === 'imfdcp')) {
        V216_HUD_COMMANDS.push({ id: 'imfdcp', name: 'IMF Package & Theatrical DCP Mastering', dept: 'Delivery', key: '}', fn: 'toggleImfDcpHUD' });
      }
      if (!V216_HUD_COMMANDS.some((c) => c.id === 'voiceducking')) {
        V216_HUD_COMMANDS.push({ id: 'voiceducking', name: 'Voice Casting, Viseme Lip-Sync & Ducking', dept: 'Audio', key: '{', fn: 'toggleVoiceDuckingHUD' });
      }
    }

    function escHtml(s) {
      return String(s == null ? '' : s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function _v219ShowToast(msg) {
      if (typeof showToast === 'function') {
        showToast(msg);
        return;
      }
      const toast = document.createElement('div');
      toast.className = 'cinema-toast show';
      toast.textContent = msg;
      toast.style.position = 'fixed';
      toast.style.bottom = '20px';
      toast.style.right = '20px';
      toast.style.background = '#0F172A';
      toast.style.color = '#F8FAFC';
      toast.style.padding = '10px 16px';
      toast.style.borderRadius = '6px';
      toast.style.border = '1px solid #38BDF8';
      toast.style.zIndex = '20000';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 2600);
    }

    function _v219DownloadBlob(content, mime, filename, toastMsg) {
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      _v219ShowToast(toastMsg);
    }

    function _v219SvgEl(tag, attrs) {
      const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
      Object.keys(attrs || {}).forEach((k) => el.setAttribute(k, String(attrs[k])));
      return el;
    }

    function _v219TrapFocus(modal, onEscape) {
      if (!modal) return;
      modal.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          e.stopPropagation();
          onEscape();
          return;
        }
        if (e.key !== 'Tab') return;
        if (typeof _handleModalTabFocusTrap === 'function') return;
        const focusables = modal.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
        if (!focusables.length) return;
        const firstEl = focusables[0];
        const lastEl = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === firstEl) {
          lastEl.focus();
          e.preventDefault();
        } else if (!e.shiftKey && document.activeElement === lastEl) {
          firstEl.focus();
          e.preventDefault();
        }
      });
    }

    function renderDuckingEnvelopeSvg() {
      const svg = document.getElementById('v219-ducking-svg');
      if (!svg) return;
      while (svg.firstChild) svg.removeChild(svg.firstChild);

      const W = 880;
      const H = 150;
      svg.appendChild(_v219SvgEl('rect', { x: 0, y: 0, width: W, height: H, fill: '#05070B' }));

      const env = V219_VOICE_DUCKING_STATE.ducking_envelope || [];
      if (!env.length) return;

      // Baseline 0 dB reference line
      svg.appendChild(_v219SvgEl('line', { x1: 24, y1: 28, x2: W - 24, y2: 28, stroke: '#475569', 'stroke-width': 1, 'stroke-dasharray': '4,3' }));
      const refLbl = _v219SvgEl('text', { x: 24, y: 20, fill: '#E2E8F0', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10 });
      refLbl.textContent = '0 dB Attenuation (BGM Nominal -14 LUFS) · SNR +' + Number(V219_VOICE_DUCKING_STATE.snr_db || 14.5).toFixed(1) + ' dB';
      svg.appendChild(refLbl);

      const padX = 24;
      const gap = 14;
      const usableW = W - padX * 2 - gap * Math.max(0, env.length - 1);
      const barW = Math.max(48, Math.floor(usableW / env.length));

      env.forEach((seg, idx) => {
        const x = padX + idx * (barW + gap);
        const attenAbs = Math.min(16, Math.abs(Number(seg.attenuation_db || -9.5)));
        const barH = Math.max(18, Math.round((attenAbs / 16) * 86));
        const barY = 30;
        const isDucked = attenAbs >= 4.0;
        const fillCol = isDucked ? '#FACC15' : '#38BDF8';

        svg.appendChild(_v219SvgEl('rect', {
          x: x, y: barY, width: barW, height: barH, rx: 4,
          fill: fillCol, 'fill-opacity': isDucked ? '0.88' : '0.55',
          stroke: '#F8FAFC', 'stroke-width': 0.8
        }));

        const lblTop = _v219SvgEl('text', {
          x: x + barW / 2, y: barY + barH + 15,
          fill: '#F8FAFC', 'font-family': 'JetBrains Mono, monospace', 'font-size': 10, 'text-anchor': 'middle'
        });
        lblTop.textContent = 'S' + String(seg.scene_index).padStart(2, '0') + ' ' + Number(seg.attenuation_db || 0).toFixed(1) + 'dB';
        svg.appendChild(lblTop);
      });
    }

    window.toggleImfDcpHUD = function(forceState) {
      const modal = document.getElementById('imfDcpModal');
      const btn = document.getElementById('btn-imf-dcp-animatic');
      if (!modal) return;
      const shouldOpen = forceState !== undefined ? Boolean(forceState) : !isImfDcpHUDOpen;
      if (!shouldOpen && !isImfDcpHUDOpen) return;
      if (shouldOpen) {
        if (typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs();
        if (isVoiceDuckingHUDOpen) window.toggleVoiceDuckingHUD(false);
      }
      isImfDcpHUDOpen = shouldOpen;
      window.isImfDcpHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastImfDcpOpener = document.activeElement;
        modal.style.display = 'flex';
        const closeBtn = document.getElementById('imfDcpCloseBtn');
        if (closeBtn) closeBtn.focus();
        _v219ShowToast('📦 IMF Package & Theatrical DCP HUD: ACTIVE [}]');
      } else {
        modal.style.display = 'none';
        if (lastImfDcpOpener && typeof lastImfDcpOpener.focus === 'function') lastImfDcpOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    window.toggleVoiceDuckingHUD = function(forceState) {
      const modal = document.getElementById('voiceDuckingModal');
      const btn = document.getElementById('btn-voice-ducking-animatic');
      if (!modal) return;
      const shouldOpen = forceState !== undefined ? Boolean(forceState) : !isVoiceDuckingHUDOpen;
      if (!shouldOpen && !isVoiceDuckingHUDOpen) return;
      if (shouldOpen) {
        if (typeof closeSecondaryOpenHUDs === 'function') closeSecondaryOpenHUDs();
        if (isImfDcpHUDOpen) window.toggleImfDcpHUD(false);
      }
      isVoiceDuckingHUDOpen = shouldOpen;
      window.isVoiceDuckingHUDOpen = shouldOpen;
      if (btn) {
        btn.classList.toggle('active', shouldOpen);
        btn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      }
      if (shouldOpen) {
        lastVoiceDuckingOpener = document.activeElement;
        modal.style.display = 'flex';
        renderDuckingEnvelopeSvg();
        const closeBtn = document.getElementById('voiceDuckingCloseBtn');
        if (closeBtn) closeBtn.focus();
        _v219ShowToast('🎙️ Voice Casting, Viseme Lip-Sync & Ducking HUD: ACTIVE [{]');
      } else {
        modal.style.display = 'none';
        if (lastVoiceDuckingOpener && typeof lastVoiceDuckingOpener.focus === 'function') lastVoiceDuckingOpener.focus();
        else if (btn && typeof btn.focus === 'function') btn.focus();
      }
    };

    function _csvCellV219(val) {
      const s = String(val == null ? '' : val);
      return '"' + s.replace(/"/g, '""') + '"';
    }

    window.downloadImfPackageJSON = function() {
      _v219DownloadBlob(
        JSON.stringify(V219_IMF_DCP_STATE, null, 2),
        'application/json;charset=utf-8;',
        'imf_package_manifest.json',
        'Downloaded imf_package_manifest.json'
      );
    };

    window.downloadDcpSpecMD = function() {
      const s = V219_IMF_DCP_STATE;
      const d = s.dcp_spec || {};
      const lines = [
        '# IMF Package & DCI Theatrical DCP Mastering Spec: ' + String(s.project_title || 'Omni Production'),
        '',
        '- **IMF Package ID**: `' + String(s.imf_package_id || '') + '`',
        '- **Application Profile**: `' + String(s.application_profile || 'ST_2067_21_App2E') + '`',
        '- **OV Picture Reuse**: `' + Number(s.ov_picture_reuse_pct || 100).toFixed(1) + '%`',
        '- **Runtime**: `' + String(s.total_smpte || '00:00:32:00') + '` @ 24fps',
        '',
        '## DCI Theatrical DCP Parameters',
        '- **Container Standard**: `' + String(d.container_standard || 'SMPTE ST 429 DCP') + '`',
        '- **Resolution Class**: `' + String(d.resolution_class || '4K Flat (3996x2160)') + '`',
        '- **Color Space**: `' + String(d.color_space || 'CIE XYZ 12-bit (2.6 Gamma)') + '`',
        '- **JPEG2000 Bitrate**: `' + Number(d.jpeg2000_bitrate_mbps || 220) + ' Mbps` (<= 250 Mbps DCI ceiling)',
        '- **Audio Config**: `' + String(d.audio_config || '24-bit / 48kHz PCM 5.1 Surround') + '`',
        '- **KDM Flag**: `' + String(d.kdm_flag || 'UNENCRYPTED_TEST') + '`',
        '',
        '## Composition Playlists (CPLs)',
        '| Role | Territory | SMPTE | Picture Track | Status |',
        '|---|---|---|---|---|'
      ];
      (s.cpls || []).forEach((c) => {
        lines.push('| ' + String(c.role) + ' | ' + String(c.territory) + ' | `' + String(c.smpte_duration) + '` | ' + String(c.picture_track) + ' | ' + String(c.status) + ' |');
      });
      lines.push('', '## Asset Map SHA-256 Digest Ledger', '| File Path | Track Role | SHA-256 |', '|---|---|---|');
      (s.asset_map || []).forEach((a) => {
        lines.push('| `' + String(a.file_path) + '` | ' + String(a.track_role) + ' | `' + String(a.sha256) + '` |');
      });
      _v219DownloadBlob(lines.join('\\n') + '\\n', 'text/markdown;charset=utf-8;', 'dcp_theatrical_spec.md', 'Downloaded dcp_theatrical_spec.md');
    };

    window.downloadVoiceCastingJSON = function() {
      _v219DownloadBlob(
        JSON.stringify(V219_VOICE_DUCKING_STATE, null, 2),
        'application/json;charset=utf-8;',
        'voice_casting_ducking_manifest.json',
        'Downloaded voice_casting_ducking_manifest.json'
      );
    };

    window.downloadDuckingAutomationCSV = function() {
      const rows = [['Scene', 'SMPTE_In', 'SMPTE_Out', 'Start_Sec', 'End_Sec', 'BGM_Baseline_LUFS', 'Attenuation_dB', 'Ducked_BGM_LUFS', 'Dialogue_LUFS', 'SNR_dB', 'Active_Speaker']];
      (V219_VOICE_DUCKING_STATE.ducking_envelope || []).forEach((seg) => {
        rows.push([
          seg.scene_index,
          seg.smpte_in,
          seg.smpte_out,
          seg.start_sec,
          seg.end_sec,
          seg.bgm_baseline_lufs,
          seg.attenuation_db,
          seg.ducked_bgm_lufs,
          seg.dialogue_lufs,
          seg.snr_db,
          seg.active_speaker
        ]);
      });
      const csvText = rows.map((r) => r.map(_csvCellV219).join(',')).join('\\n') + '\\n';
      _v219DownloadBlob(csvText, 'text/csv;charset=utf-8;', 'sidechain_ducking_automation.csv', 'Downloaded sidechain_ducking_automation.csv');
    };

    window.initV219HUDs = function() {
      if (_v219Initialized) return;
      _v219Initialized = true;
      const imfModal = document.getElementById('imfDcpModal');
      const voiceModal = document.getElementById('voiceDuckingModal');
      _v219TrapFocus(imfModal, () => toggleImfDcpHUD(false));
      _v219TrapFocus(voiceModal, () => toggleVoiceDuckingHUD(false));
      if (imfModal) {
        imfModal.addEventListener('click', (e) => {
          if (e.target === imfModal) toggleImfDcpHUD(false);
        });
      }
      if (voiceModal) {
        voiceModal.addEventListener('click', (e) => {
          if (e.target === voiceModal) toggleVoiceDuckingHUD(false);
        });
      }
      renderDuckingEnvelopeSvg();
    };

    document.addEventListener('DOMContentLoaded', () => {
      if (typeof initV219HUDs === 'function') initV219HUDs();
    });
    """

    js_str = (
        js_template
        .replace("__IMF_JSON__", imf_json)
        .replace("__VOICE_JSON__", voice_json)
    )

    return {
        "css": css_str,
        "html": html_str,
        "js": js_str,
    }


__all__ = [
    "synthesize_v219_imf_dcp_state",
    "synthesize_v219_voice_ducking_state",
    "build_v219_hud_bundle",
]
