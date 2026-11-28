"""SMPTE IMF (ST 2067) Supplemental Packaging & DCI Theatrical DCP Mastering (PM-FEAT-037)."""

from __future__ import annotations

import hashlib
import uuid
import xml.dom.minidom
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.presets import classify_brief_domain
from omni_director.schemas import (
    AspectRatio,
    DciTheatricalDcpSpec,
    ImfApplicationProfileEnum,
    ImfAssetTrackSpec,
    ImfCompositionPlaylistSpec,
    MasterImfDcpManifest,
    MasterProductionBible,
)

_IMF_NAMESPACE_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "omni-director.smpte-imf.2026")
_MAX_DCI_JPEG2000_MBPS = 250.0


def _deterministic_uuid(key: str) -> str:
    return str(uuid.uuid5(_IMF_NAMESPACE_UUID, key))


def _deterministic_sha256(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _safe_slug(text: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in (text or "").strip())
    return cleaned.strip("_") or "omni_production"


def _resolve_dci_resolution_class(bible: MasterProductionBible) -> str:
    ar = getattr(bible, "aspect_ratio", AspectRatio.RATIO_16_9)
    ar_val = ar.value if hasattr(ar, "value") else str(ar)
    if ar_val == "2.39:1":
        return "2K_SCOPE_2048x858"
    if ar_val == "16:9":
        return "2K_FLAT_1998x1080"
    if ar_val == "9:16":
        return "2K_VERTICAL_1080x1920"
    return "2K_SCOPE_2048x858"


def _extract_localization_locales(bible: MasterProductionBible) -> List[str]:
    loc_manifest = getattr(bible, "localization_manifest", None)
    if loc_manifest is None:
        return []

    source_locale = str(getattr(loc_manifest, "source_locale", "en-US") or "en-US").strip()
    raw_items: List[Any] = []
    for attr in ("locales", "target_locales", "territories"):
        val = getattr(loc_manifest, attr, None)
        if val:
            raw_items.extend(list(val))

    locales: List[str] = []
    seen = {source_locale.lower()}
    for item in raw_items:
        if isinstance(item, str):
            code = item.strip()
        elif isinstance(item, dict):
            code = str(item.get("bcp47_tag") or item.get("locale") or item.get("code") or "").strip()
        else:
            code = str(
                getattr(item, "bcp47_tag", None)
                or getattr(item, "locale", None)
                or ""
            ).strip()
        if code and code.lower() not in seen:
            seen.add(code.lower())
            locales.append(code)
    return locales


def _extract_cutdowns(bible: MasterProductionBible) -> List[Tuple[str, float]]:
    reframe = getattr(bible, "master_reframe_manifest", None) or getattr(bible, "reframe_manifest", None)
    if reframe is None:
        return []

    raw_cutdowns: List[Any] = []
    for attr in ("cutdowns", "cutdown_versions"):
        val = getattr(reframe, attr, None)
        if val:
            raw_cutdowns.extend(list(val))

    results: List[Tuple[str, float]] = []
    seen_labels: set[str] = set()
    for item in raw_cutdowns:
        if isinstance(item, dict):
            label = str(item.get("label") or item.get("cutdown_type") or "").strip()
            dur = float(item.get("target_duration_sec") or item.get("actual_duration_sec") or 15.0)
        else:
            ct = getattr(item, "cutdown_type", None)
            ct_val = ct.value if hasattr(ct, "value") else (str(ct) if ct else "")
            label = str(getattr(item, "label", "") or ct_val).strip()
            dur = float(getattr(item, "target_duration_sec", None) or getattr(item, "actual_duration_sec", 15.0) or 15.0)
        if label and label not in seen_labels:
            seen_labels.add(label)
            results.append((label, max(1.0, dur)))
    return results


def _has_accessibility_ad(bible: MasterProductionBible) -> Tuple[bool, str]:
    acc = getattr(bible, "master_accessibility_spec", None)
    if acc is None:
        return False, "en-US"
    ad_lang = str(getattr(acc, "ad_track_language", "en-US") or "en-US").strip()
    total_cues = int(getattr(acc, "total_ad_cues", 0) or 0)
    profiles = list(getattr(acc, "scene_profiles", None) or [])
    has_cues = total_cues > 0 or any(bool(getattr(p, "ad_cues", None)) for p in profiles)
    if not has_cues:
        has_cues = any(getattr(sc, "accessibility_spec", None) is not None for sc in (getattr(bible, "scenes", None) or []))
    return has_cues or acc is not None, ad_lang


def compile_imf_dcp_manifest(
    bible: MasterProductionBible,
    domain_profile: Optional[Dict[str, Any]] = None,
) -> MasterImfDcpManifest:
    """Compiles a deduplicated SMPTE IMF (ST 2067) supplemental package & DCI DCP manifest (PM-FEAT-037)."""
    title = str(getattr(bible, "project_title", "Omni Production") or "Omni Production").strip()
    slug = _safe_slug(title)
    scenes = list(getattr(bible, "scenes", None) or [])
    segment_count = max(1, len(scenes))
    runtime_sec = float(getattr(bible, "total_runtime_seconds", 32) or 32)
    total_frames = max(24, int(round(runtime_sec * 24)))

    cal = dict(domain_profile or {})
    raw_domain = getattr(bible, "domain_archetype", None)
    if raw_domain is None:
        raw_domain = classify_brief_domain(f"{title} {getattr(bible, 'logline', '')}").value
    domain_str = raw_domain.value if hasattr(raw_domain, "value") else str(raw_domain)

    raw_profile = cal.get("application_profile", ImfApplicationProfileEnum.APP_2_EXTENDED)
    if isinstance(raw_profile, ImfApplicationProfileEnum):
        app_profile = raw_profile
    else:
        try:
            app_profile = ImfApplicationProfileEnum(str(raw_profile))
        except ValueError:
            app_profile = ImfApplicationProfileEnum.APP_2_EXTENDED

    # Core Original Version (OV) assets — picture_ov is shared & deduplicated across all CPLs
    pic_ov_uuid = _deterministic_uuid(f"{slug}:asset:picture_ov")
    aud_ov_uuid = _deterministic_uuid(f"{slug}:asset:audio_ov:en-US")
    tt_ov_uuid = _deterministic_uuid(f"{slug}:asset:timed_text_ov:en-US")

    assets: List[ImfAssetTrackSpec] = [
        ImfAssetTrackSpec(
            asset_uuid=pic_ov_uuid,
            track_role="picture_ov",
            locale_code="en-US",
            codec_profile="JPEG2000_App2E_12bit",
            edit_rate="24/1",
            duration_frames=total_frames,
            sha256_digest=_deterministic_sha256(f"{slug}:picture_ov:{total_frames}"),
            is_supplemental=False,
        ),
        ImfAssetTrackSpec(
            asset_uuid=aud_ov_uuid,
            track_role="audio_ov",
            locale_code="en-US",
            codec_profile="PCM_24bit_48kHz_5.1",
            edit_rate="24/1",
            duration_frames=total_frames,
            sha256_digest=_deterministic_sha256(f"{slug}:audio_ov:en-US:{total_frames}"),
            is_supplemental=False,
        ),
        ImfAssetTrackSpec(
            asset_uuid=tt_ov_uuid,
            track_role="timed_text_ov",
            locale_code="en-US",
            codec_profile="IMSC1_TTML",
            edit_rate="24/1",
            duration_frames=total_frames,
            sha256_digest=_deterministic_sha256(f"{slug}:timed_text_ov:en-US:{total_frames}"),
            is_supplemental=False,
        ),
    ]

    # Audio Description supplemental track if accessibility manifest exists
    ad_uuid: Optional[str] = None
    has_ad, ad_lang = _has_accessibility_ad(bible)
    if has_ad:
        ad_uuid = _deterministic_uuid(f"{slug}:asset:audio_ad:{ad_lang}")
        assets.append(
            ImfAssetTrackSpec(
                asset_uuid=ad_uuid,
                track_role="audio_ad",
                locale_code=ad_lang,
                codec_profile="PCM_24bit_48kHz_AD",
                edit_rate="24/1",
                duration_frames=total_frames,
                sha256_digest=_deterministic_sha256(f"{slug}:audio_ad:{ad_lang}:{total_frames}"),
                is_supplemental=True,
            )
        )

    ov_linked = [pic_ov_uuid, aud_ov_uuid, tt_ov_uuid]
    if ad_uuid:
        ov_linked.append(ad_uuid)

    cpls: List[ImfCompositionPlaylistSpec] = [
        ImfCompositionPlaylistSpec(
            cpl_uuid=_deterministic_uuid(f"{slug}:cpl:ov_master"),
            content_title_text=f"{title} (OV Master)",
            version_tag="OV_MASTER",
            application_profile=app_profile,
            segment_count=segment_count,
            total_frames=total_frames,
            linked_asset_uuids=list(ov_linked),
            source_cutdown_label=None,
        )
    ]

    # Supplemental locale CPLs reusing picture_ov without duplicating video essence
    for loc_code in _extract_localization_locales(bible):
        loc_aud_uuid = _deterministic_uuid(f"{slug}:asset:audio_supp:{loc_code}")
        loc_tt_uuid = _deterministic_uuid(f"{slug}:asset:timed_text_supp:{loc_code}")
        assets.extend([
            ImfAssetTrackSpec(
                asset_uuid=loc_aud_uuid,
                track_role="audio_supplemental",
                locale_code=loc_code,
                codec_profile="PCM_24bit_48kHz_5.1",
                edit_rate="24/1",
                duration_frames=total_frames,
                sha256_digest=_deterministic_sha256(f"{slug}:audio_supp:{loc_code}:{total_frames}"),
                is_supplemental=True,
            ),
            ImfAssetTrackSpec(
                asset_uuid=loc_tt_uuid,
                track_role="timed_text_supplemental",
                locale_code=loc_code,
                codec_profile="IMSC1_TTML",
                edit_rate="24/1",
                duration_frames=total_frames,
                sha256_digest=_deterministic_sha256(f"{slug}:timed_text_supp:{loc_code}:{total_frames}"),
                is_supplemental=True,
            ),
        ])
        supp_links = [pic_ov_uuid, loc_aud_uuid, loc_tt_uuid]
        if ad_uuid:
            supp_links.append(ad_uuid)
        cpls.append(
            ImfCompositionPlaylistSpec(
                cpl_uuid=_deterministic_uuid(f"{slug}:cpl:supp:{loc_code}"),
                content_title_text=f"{title} ({loc_code} Supplemental)",
                version_tag=f"SUPP_{loc_code.upper().replace('-', '_')}",
                application_profile=app_profile,
                segment_count=segment_count,
                total_frames=total_frames,
                linked_asset_uuids=supp_links,
                source_cutdown_label=None,
            )
        )

    # Cutdown CPLs (:30 / :15 / :06) reusing picture_ov & audio_ov segments
    for cut_label, cut_dur_sec in _extract_cutdowns(bible):
        cut_frames = max(24, int(round(cut_dur_sec * 24)))
        cpls.append(
            ImfCompositionPlaylistSpec(
                cpl_uuid=_deterministic_uuid(f"{slug}:cpl:cutdown:{cut_label}"),
                content_title_text=f"{title} ({cut_label})",
                version_tag=f"CUTDOWN_{_safe_slug(cut_label).upper()}",
                application_profile=app_profile,
                segment_count=min(segment_count, max(1, int(round(cut_dur_sec / 8.0)))),
                total_frames=cut_frames,
                linked_asset_uuids=list(ov_linked),
                source_cutdown_label=cut_label,
            )
        )

    # DCI Theatrical DCP CPL referencing OV picture & audio essence
    cpls.append(
        ImfCompositionPlaylistSpec(
            cpl_uuid=_deterministic_uuid(f"{slug}:cpl:dci_theatrical_dcp"),
            content_title_text=f"{title} (DCI Theatrical DCP)",
            version_tag="DCI_THEATRICAL_DCP",
            application_profile=ImfApplicationProfileEnum.DCI_DCP_SMPTE,
            segment_count=segment_count,
            total_frames=total_frames,
            linked_asset_uuids=list(ov_linked),
            source_cutdown_label=None,
        )
    )

    # Compute deduplicated picture essence reuse %
    picture_refs = sum(1 for cpl in cpls if pic_ov_uuid in cpl.linked_asset_uuids)
    if picture_refs > 1:
        dedup_pct = round(((picture_refs - 1) / float(picture_refs)) * 100.0, 2)
    else:
        dedup_pct = 0.0

    raw_bitrate = float(cal.get("jpeg2000_max_bitrate_mbps", _MAX_DCI_JPEG2000_MBPS) or _MAX_DCI_JPEG2000_MBPS)
    capped_bitrate = round(min(_MAX_DCI_JPEG2000_MBPS, max(50.0, raw_bitrate)), 2)

    audio_cfg = str(cal.get("audio_config", "ATMOS_IAB" if domain_str != "culinary_asmr" else "5.1_PCM_24BIT") or "ATMOS_IAB")
    dcp_spec = DciTheatricalDcpSpec(
        container_standard="SMPTE ST 429-2",
        resolution_class=_resolve_dci_resolution_class(bible),
        color_encoding="CIE_XYZ_12BIT_D65",
        jpeg2000_max_bitrate_mbps=capped_bitrate,
        audio_config=audio_cfg,
        kdm_encryption_required=bool(cal.get("kdm_encryption_required", False)),
        reel_count=max(1, min(segment_count, 4)),
    )

    pkg_hash = _deterministic_sha256(f"{slug}:{len(assets)}:{len(cpls)}")[:12]
    return MasterImfDcpManifest(
        package_id=f"imf-pkg-{pkg_hash}",
        assetmap_uuid=_deterministic_uuid(f"{slug}:assetmap"),
        pkl_uuid=_deterministic_uuid(f"{slug}:pkl"),
        application_profile=app_profile,
        assets=assets,
        cpls=cpls,
        dcp_spec=dcp_spec,
        deduplicated_picture_reuse_pct=dedup_pct,
    )


def synthesize_default_imf_dcp_manifest(bible: MasterProductionBible) -> MasterImfDcpManifest:
    """Synthesizes default SMPTE IMF & DCI Theatrical DCP manifest for a MasterProductionBible."""
    return compile_imf_dcp_manifest(bible)


def format_imf_dcp_token(manifest: MasterImfDcpManifest, scene_index: int = 1) -> str:
    """Formats the machine telemetry token for PM-FEAT-037 IMF CPL & DCI DCP mastering."""
    primary_cpl = manifest.cpls[0] if manifest.cpls else None
    cpl_ref = (primary_cpl.cpl_uuid[:12] if primary_cpl else manifest.package_id[:12])
    profile_val = (
        manifest.application_profile.value
        if hasattr(manifest.application_profile, "value")
        else str(manifest.application_profile)
    )
    return (
        f"[IMF-CPL: {cpl_ref} | SC{scene_index:02d} | profile={profile_val} | "
        f"cpls={len(manifest.cpls)} | reuse={manifest.deduplicated_picture_reuse_pct:.1f}% | "
        f"DCP: {manifest.dcp_spec.resolution_class} @ {manifest.dcp_spec.jpeg2000_max_bitrate_mbps:.1f}Mbps]"
    )


def _pretty_xml(elem: ET.Element) -> str:
    raw_bytes = ET.tostring(elem, encoding="utf-8")
    parsed = xml.dom.minidom.parseString(raw_bytes)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def export_imf_assetmap_xml(manifest: MasterImfDcpManifest) -> str:
    """Generates a SMPTE ST 429-9 / ST 2067-2 compliant ASSETMAP.xml string."""
    ns = "http://www.smpte-ra.org/schemas/429-9/2007/AM"
    root = ET.Element("AssetMap", {"xmlns": ns})
    ET.SubElement(root, "Id").text = f"urn:uuid:{manifest.assetmap_uuid}"
    ET.SubElement(root, "Creator").text = "OmniMovieDirector/2.20.0"
    ET.SubElement(root, "VolumeCount").text = "1"
    ET.SubElement(root, "IssueDate").text = "2026-11-27T00:00:00-00:00"
    ET.SubElement(root, "Issuer").text = "Omni Movie Director IMF Packager"

    asset_list = ET.SubElement(root, "AssetList")

    # PKL entry
    pkl_el = ET.SubElement(asset_list, "Asset")
    ET.SubElement(pkl_el, "Id").text = f"urn:uuid:{manifest.pkl_uuid}"
    ET.SubElement(pkl_el, "PackingList").text = "true"
    pkl_chunks = ET.SubElement(pkl_el, "ChunkList")
    pkl_chunk = ET.SubElement(pkl_chunks, "Chunk")
    ET.SubElement(pkl_chunk, "Path").text = "PKL.xml"
    ET.SubElement(pkl_chunk, "VolumeIndex").text = "1"

    # CPL entries
    for idx, cpl in enumerate(manifest.cpls):
        cpl_el = ET.SubElement(asset_list, "Asset")
        ET.SubElement(cpl_el, "Id").text = f"urn:uuid:{cpl.cpl_uuid}"
        ET.SubElement(cpl_el, "AnnotationText").text = cpl.content_title_text
        chunks = ET.SubElement(cpl_el, "ChunkList")
        chunk = ET.SubElement(chunks, "Chunk")
        ET.SubElement(chunk, "Path").text = "CPL_master.xml" if idx == 0 else f"CPL_{_safe_slug(cpl.version_tag)}.xml"
        ET.SubElement(chunk, "VolumeIndex").text = "1"

    # Essence track entries
    for asset in manifest.assets:
        a_el = ET.SubElement(asset_list, "Asset")
        ET.SubElement(a_el, "Id").text = f"urn:uuid:{asset.asset_uuid}"
        ET.SubElement(a_el, "AnnotationText").text = f"{asset.track_role} ({asset.locale_code})"
        chunks = ET.SubElement(a_el, "ChunkList")
        chunk = ET.SubElement(chunks, "Chunk")
        ext = "xml" if "timed_text" in asset.track_role else "mxf"
        ET.SubElement(chunk, "Path").text = f"{asset.track_role}_{asset.locale_code}_{asset.asset_uuid[:8]}.{ext}"
        ET.SubElement(chunk, "VolumeIndex").text = "1"

    return _pretty_xml(root)


def export_imf_pkl_xml(manifest: MasterImfDcpManifest) -> str:
    """Generates a SMPTE ST 2067-2 / ST 429-8 compliant PKL.xml string."""
    ns = "http://www.smpte-ra.org/schemas/2067-2/2016/PKL"
    root = ET.Element("PackingList", {"xmlns": ns})
    ET.SubElement(root, "Id").text = f"urn:uuid:{manifest.pkl_uuid}"
    ET.SubElement(root, "AnnotationText").text = f"IMF Packing List {manifest.package_id}"
    ET.SubElement(root, "IssueDate").text = "2026-11-27T00:00:00-00:00"
    ET.SubElement(root, "Issuer").text = "Omni Movie Director IMF Packager"
    ET.SubElement(root, "Creator").text = "OmniMovieDirector/2.20.0"

    asset_list = ET.SubElement(root, "AssetList")
    for asset in manifest.assets:
        a_el = ET.SubElement(asset_list, "Asset")
        ET.SubElement(a_el, "Id").text = f"urn:uuid:{asset.asset_uuid}"
        ET.SubElement(a_el, "AnnotationText").text = f"{asset.track_role} [{asset.codec_profile}]"
        ET.SubElement(a_el, "Hash").text = asset.sha256_digest
        ET.SubElement(a_el, "HashAlgorithm", {"Algorithm": "http://www.w3.org/2001/04/xmlenc#sha256"})
        est_size = max(4096, asset.duration_frames * (65536 if "picture" in asset.track_role else 8192))
        ET.SubElement(a_el, "Size").text = str(est_size)
        is_tt = "timed_text" in asset.track_role
        ET.SubElement(a_el, "Type").text = "application/ttml+xml" if is_tt else "application/mxf"
        ext = "xml" if is_tt else "mxf"
        ET.SubElement(a_el, "OriginalFileName").text = f"{asset.track_role}_{asset.locale_code}.{ext}"

    return _pretty_xml(root)


def export_imf_cpl_xml(manifest: MasterImfDcpManifest) -> str:
    """Generates a SMPTE ST 2067-3 compliant CompositionPlaylist XML for the primary CPL."""
    ns = "http://www.smpte-ra.org/schemas/2067-3/2016"
    cpl = manifest.cpls[0] if manifest.cpls else ImfCompositionPlaylistSpec(
        cpl_uuid=_deterministic_uuid(f"{manifest.package_id}:cpl:default"),
        content_title_text=manifest.package_id,
        version_tag="OV_MASTER",
        application_profile=manifest.application_profile,
        linked_asset_uuids=[a.asset_uuid for a in manifest.assets],
    )
    profile_val = (
        cpl.application_profile.value
        if hasattr(cpl.application_profile, "value")
        else str(cpl.application_profile)
    )

    root = ET.Element("CompositionPlaylist", {"xmlns": ns})
    ET.SubElement(root, "Id").text = f"urn:uuid:{cpl.cpl_uuid}"
    ET.SubElement(root, "AnnotationText").text = f"{cpl.content_title_text} [{cpl.version_tag}]"
    ET.SubElement(root, "IssueDate").text = "2026-11-27T00:00:00-00:00"
    ET.SubElement(root, "Issuer").text = "Omni Movie Director IMF Packager"
    ET.SubElement(root, "Creator").text = "OmniMovieDirector/2.20.0"
    ET.SubElement(root, "ContentTitleText").text = cpl.content_title_text
    ET.SubElement(root, "ApplicationIdentification").text = f"http://www.smpte-ra.org/ns/2067-21/2016#{profile_val}"
    ET.SubElement(root, "EditRate").text = "24 1"

    asset_map = {a.asset_uuid: a for a in manifest.assets}
    seg_list = ET.SubElement(root, "SegmentList")
    seg = ET.SubElement(seg_list, "Segment")
    ET.SubElement(seg, "Id").text = f"urn:uuid:{_deterministic_uuid(f'{cpl.cpl_uuid}:segment:1')}"
    seq_list = ET.SubElement(seg, "SequenceList")

    for linked_uuid in cpl.linked_asset_uuids:
        asset = asset_map.get(linked_uuid)
        role = asset.track_role if asset else "essence"
        if "picture" in role:
            seq_tag = "MainImageSequence"
        elif "timed_text" in role:
            seq_tag = "SubtitlesSequence"
        else:
            seq_tag = "MainAudioSequence"

        seq_el = ET.SubElement(seq_list, seq_tag)
        ET.SubElement(seq_el, "Id").text = f"urn:uuid:{_deterministic_uuid(f'{cpl.cpl_uuid}:seq:{linked_uuid}')}"
        ET.SubElement(seq_el, "TrackId").text = f"urn:uuid:{_deterministic_uuid(f'{role}:{linked_uuid}')}"
        res_list = ET.SubElement(seq_el, "ResourceList")
        res = ET.SubElement(res_list, "Resource")
        ET.SubElement(res, "Id").text = f"urn:uuid:{_deterministic_uuid(f'{cpl.cpl_uuid}:res:{linked_uuid}')}"
        ET.SubElement(res, "EditRate").text = asset.edit_rate.replace("/", " ") if asset else "24 1"
        ET.SubElement(res, "IntrinsicDuration").text = str(cpl.total_frames)
        ET.SubElement(res, "SourceDuration").text = str(cpl.total_frames)
        ET.SubElement(res, "TrackFileId").text = f"urn:uuid:{linked_uuid}"

    return _pretty_xml(root)


def export_imf_dcp_manifest_json(manifest: MasterImfDcpManifest) -> str:
    """Serializes MasterImfDcpManifest to formatted JSON."""
    return manifest.model_dump_json(indent=2)


def export_dcp_cpl_spec_md(
    manifest: MasterImfDcpManifest,
    bible: Optional[MasterProductionBible] = None,
) -> str:
    """Exports a human-readable Markdown specification of the IMF package, CPLs, and DCI DCP mastering."""
    title = str(getattr(bible, "project_title", manifest.package_id) or manifest.package_id)
    profile_val = (
        manifest.application_profile.value
        if hasattr(manifest.application_profile, "value")
        else str(manifest.application_profile)
    )
    lines: List[str] = [
        f"# SMPTE IMF & DCI Theatrical DCP Mastering Spec — {title}",
        "",
        f"- **Package ID**: `{manifest.package_id}`",
        f"- **Application Profile**: `{profile_val}`",
        f"- **ASSETMAP UUID**: `urn:uuid:{manifest.assetmap_uuid}`",
        f"- **PKL UUID**: `urn:uuid:{manifest.pkl_uuid}`",
        f"- **Deduplicated OV Picture Reuse**: `{manifest.deduplicated_picture_reuse_pct:.2f}%`",
        "",
        "## DCI Theatrical DCP Specification",
        "",
        f"- **Container Standard**: {manifest.dcp_spec.container_standard}",
        f"- **Resolution Class**: `{manifest.dcp_spec.resolution_class}`",
        f"- **Color Encoding**: `{manifest.dcp_spec.color_encoding}`",
        f"- **JPEG2000 Max Bitrate**: `{manifest.dcp_spec.jpeg2000_max_bitrate_mbps:.1f} Mbps` (SMPTE DCI cap <= 250.0 Mbps)",
        f"- **Audio Configuration**: `{manifest.dcp_spec.audio_config}`",
        f"- **KDM Encryption Required**: `{manifest.dcp_spec.kdm_encryption_required}`",
        f"- **Reel Count**: `{manifest.dcp_spec.reel_count}`",
        "",
        "## Composition Playlists (CPLs)",
        "",
        "| Version Tag | Content Title | Profile | Frames | Linked Assets | Cutdown |",
        "|---|---|---|---:|---:|---|",
    ]
    for cpl in manifest.cpls:
        p_val = cpl.application_profile.value if hasattr(cpl.application_profile, "value") else str(cpl.application_profile)
        lines.append(
            f"| `{cpl.version_tag}` | {cpl.content_title_text} | `{p_val}` | "
            f"{cpl.total_frames} | {len(cpl.linked_asset_uuids)} | {cpl.source_cutdown_label or '—'} |"
        )

    lines.extend([
        "",
        "## IMF Track Essence Assets",
        "",
        "| Track Role | Locale | Codec Profile | Frames | Supplemental | SHA-256 (prefix) |",
        "|---|---|---|---:|:---:|---|",
    ])
    for asset in manifest.assets:
        lines.append(
            f"| `{asset.track_role}` | `{asset.locale_code}` | `{asset.codec_profile}` | "
            f"{asset.duration_frames} | {'Yes' if asset.is_supplemental else 'No'} | `{asset.sha256_digest[:16]}...` |"
        )
    lines.append("")
    return "\n".join(lines)


def export_imf_dcp_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    manifest: Optional[MasterImfDcpManifest] = None,
) -> Dict[str, Path]:
    """Writes ASSETMAP.xml, PKL.xml, CPL_master.xml, imf_dcp_manifest.json, and dcp_cpl_spec.md into output_dir."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    resolved_manifest = manifest or getattr(bible, "master_imf_dcp", None)
    if resolved_manifest is None:
        resolved_manifest = compile_imf_dcp_manifest(bible)

    assetmap_path = out_path / "ASSETMAP.xml"
    pkl_path = out_path / "PKL.xml"
    cpl_path = out_path / "CPL_master.xml"
    json_path = out_path / "imf_dcp_manifest.json"
    spec_md_path = out_path / "dcp_cpl_spec.md"

    assetmap_path.write_text(export_imf_assetmap_xml(resolved_manifest), encoding="utf-8")
    pkl_path.write_text(export_imf_pkl_xml(resolved_manifest), encoding="utf-8")
    cpl_path.write_text(export_imf_cpl_xml(resolved_manifest), encoding="utf-8")
    json_path.write_text(export_imf_dcp_manifest_json(resolved_manifest), encoding="utf-8")
    spec_md_path.write_text(export_dcp_cpl_spec_md(resolved_manifest, bible), encoding="utf-8")

    return {
        "assetmap_xml": assetmap_path,
        "pkl_xml": pkl_path,
        "cpl_master_xml": cpl_path,
        "imf_dcp_manifest_json": json_path,
        "dcp_cpl_spec_md": spec_md_path,
    }


__all__ = [
    "compile_imf_dcp_manifest",
    "synthesize_default_imf_dcp_manifest",
    "format_imf_dcp_token",
    "export_imf_assetmap_xml",
    "export_imf_pkl_xml",
    "export_imf_cpl_xml",
    "export_imf_dcp_manifest_json",
    "export_dcp_cpl_spec_md",
    "export_imf_dcp_bundle",
]
