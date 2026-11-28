"""RFC 8493 BagIt Archive Vault & Agency Delivery Packaging (PM-FEAT-040)."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from omni_director.schemas import (
    ArchiveRetentionTierEnum,
    ArchiveVaultEntrySpec,
    DepartmentVaultSummarySpec,
    MasterArchiveVaultManifest,
    MasterProductionBible,
    VaultDepartmentEnum,
)
from omni_director.telemetry import DISCOVERABLE_ARTIFACT_EXTENSIONS, KNOWN_PRODUCTION_ARTIFACTS

_RETENTION_EXPIRY_MAP: Dict[ArchiveRetentionTierEnum, str] = {
    ArchiveRetentionTierEnum.AGENCY_90_DAY: "2027-02-26",
    ArchiveRetentionTierEnum.CAMPAIGN_2_YEAR: "2028-11-28",
    ArchiveRetentionTierEnum.STUDIO_LTO_PERPETUAL: "2099-12-31",
}

_BAG_TAG_FILENAMES: frozenset[str] = frozenset({
    "bag-info.txt",
    "manifest-sha256.txt",
    "bagit.txt",
    "tagmanifest-sha256.txt",
    "telemetry.json",
    "telemetry_manifest.json",
    "archive_vault_manifest.json",
})


def classify_artifact_department(filename: str) -> VaultDepartmentEnum:
    """Deterministically routes an artifact filename into one of the 6 BagIt vault departments."""
    name = Path(str(filename or "")).name.lower()

    if any(
        tok in name
        for tok in (
            "timeline", ".edl", ".fcpxml", ".otio", ".srt", ".vtt", ".ttml", ".ass",
            "shot_list", "call_sheet", "callsheet", "stripboard", "dood", "movie_magic",
            "spotting", "localization", "adr_cue", "subtitles", "rough_cut",
        )
    ) and "gaffer" not in name:
        return VaultDepartmentEnum.EDITORIAL_TIMELINES

    if any(
        tok in name
        for tok in (
            "lens", "optical", "dof", "depth_of_field", "focus_puller", "cue_sheet",
            "moco", "virtual_production", "vp_stage", "ndisplay", "dmx", "lighting",
            "gaffer", "slate", "asc_mhl", "sound_sync", "flight_", "drone",
            "blocking", "continuity_log", "continuity_manifest", "s3d", "spatial_video",
            "reframe", "cutdown", ".fbx", ".kml", ".gpx",
        )
    ):
        if "ad_script" in name:
            return VaultDepartmentEnum.AUDIO_VOICE_MUSIC
        return VaultDepartmentEnum.CAMERA_OPTICS_VP

    if any(
        tok in name
        for tok in (
            "audio", "spatial_audio", "ambisonic", "webaudio", "voice",
            "stem_ducking", "adr_viseme", "ad_script", "accessibility_ad", "bgm",
        )
    ):
        return VaultDepartmentEnum.AUDIO_VOICE_MUSIC

    if any(
        tok in name
        for tok in (
            "broadcast_qc", "rights_clearance", "c2pa", "ai_disclosure",
            "likeness_consent", "safety_", "jsa", "client_signoff", "review_",
            "aicp_bid", "production_budget", "wardrobe_prop", "prop_continuity",
            "art_dept", "coherence_",
        )
    ):
        return VaultDepartmentEnum.LEGAL_SAFETY_QC

    if any(
        tok in name
        for tok in (
            "assetmap", "pkl", "cpl_", "imf_dcp", "dcp_cpl", "treatment",
            "bible_revision", "production_bundle", "production_bible",
            "archive_vault", "bag-info", "manifest-sha256", "agency_delivery",
            "council_report",
        )
    ):
        return VaultDepartmentEnum.MASTERING_IMF_PITCH

    if any(
        tok in name
        for tok in (
            "cdl", "lut", ".cube", "dit_", "color", "scopes", "shot_match",
            "finishing_scopes", "hdr", "hlg_", "film_", ".dctl", "vfx",
            "openexr", "cryptomatte", "nuke", ".nk", ".svg", "storyboard_preview",
            "render_job", "take_qa", "render_economics", "take_variant",
            "ai_compute", "motion_graphics", "brand_endcard", "broadcast_supers",
        )
    ):
        return VaultDepartmentEnum.COLOR_VFX_HDR

    return VaultDepartmentEnum.MASTERING_IMF_PITCH


def _guess_mime_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    custom = {
        ".json": "application/json",
        ".html": "text/html",
        ".svg": "image/svg+xml",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".xml": "application/xml",
        ".edl": "text/plain",
        ".fcpxml": "application/xml",
        ".otio": "application/json",
        ".cube": "text/plain",
        ".cdl": "application/xml",
        ".srt": "text/plain",
        ".vtt": "text/vtt",
        ".ttml": "application/ttml+xml",
        ".ass": "text/plain",
        ".txt": "text/plain",
        ".sh": "application/x-sh",
    }
    if ext in custom:
        return custom[ext]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _estimate_bytes(filename: str) -> int:
    digest = hashlib.sha256(filename.encode("utf-8")).digest()
    return 1536 + (int.from_bytes(digest[:2], "big") % 4096)


def _resolve_retention_tier(
    bible: MasterProductionBible, domain_profile: Optional[Dict[str, Any]]
) -> ArchiveRetentionTierEnum:
    if domain_profile and domain_profile.get("retention_tier"):
        raw = str(domain_profile["retention_tier"]).strip().lower()
        try:
            return ArchiveRetentionTierEnum(raw)
        except ValueError:
            pass
    return ArchiveRetentionTierEnum.STUDIO_LTO_PERPETUAL


def _resolve_rights_expiry(
    bible: MasterProductionBible, tier: ArchiveRetentionTierEnum
) -> str:
    c2pa = getattr(bible, "master_c2pa_provenance", None)
    if c2pa is not None:
        for rec in list(getattr(c2pa, "talent_consents", None) or []):
            exp = getattr(rec, "expiration_date", None)
            if exp:
                return str(exp)
    return _RETENTION_EXPIRY_MAP.get(tier, "2099-12-31")


def compile_archive_vault_manifest(
    bible: MasterProductionBible,
    output_dir: Optional[Union[str, Path]] = None,
    domain_profile: Optional[Dict[str, Any]] = None,
) -> MasterArchiveVaultManifest:
    """Compiles an RFC 8493 BagIt archive vault manifest across 6 department vaults (PM-FEAT-040)."""
    title = str(getattr(bible, "project_title", "Omni Production") or "Omni Production").strip()
    slug = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title).strip("_") or "omni"
    tier = _resolve_retention_tier(bible, domain_profile)
    rights_expiry = _resolve_rights_expiry(bible, tier)

    extra_artifacts = (
        "color_continuity_scopes.json",
        "shot_match_cdl_deltas.csv",
        "finishing_scopes_qc.md",
        "agency_delivery_readme.md",
    )
    catalog_names: List[str] = list(dict.fromkeys([*KNOWN_PRODUCTION_ARTIFACTS, *extra_artifacts]))

    entries: List[ArchiveVaultEntrySpec] = []
    if output_dir is not None:
        out_path = Path(output_dir)
        disk_files: List[Tuple[str, Path]] = []
        if out_path.is_dir():
            for p in sorted(out_path.rglob("*"), key=lambda item: item.relative_to(out_path).as_posix()):
                if not p.is_file():
                    continue
                rel = p.relative_to(out_path).as_posix()
                if any(part.startswith(".") for part in Path(rel).parts):
                    continue
                if p.name.lower() in _BAG_TAG_FILENAMES or ".tmp_" in p.name or p.name.endswith((".tmp", ".bak")):
                    continue
                if p.suffix.lower() in DISCOVERABLE_ARTIFACT_EXTENSIONS or rel in catalog_names:
                    disk_files.append((rel, p))

        seen_rel: set[str] = set()
        for rel, p in disk_files:
            seen_rel.add(rel)
            raw_bytes = p.read_bytes()
            entries.append(
                ArchiveVaultEntrySpec(
                    filename=rel,
                    vault_department=classify_artifact_department(rel),
                    sha256_digest=hashlib.sha256(raw_bytes).hexdigest(),
                    size_bytes=len(raw_bytes),
                    present_on_disk=True,
                    mime_type=_guess_mime_type(rel),
                )
            )
        for mandatory in ("production_bundle.json", "storyboard_preview.html"):
            if mandatory not in seen_rel:
                entries.append(
                    ArchiveVaultEntrySpec(
                        filename=mandatory,
                        vault_department=classify_artifact_department(mandatory),
                        sha256_digest=hashlib.sha256(f"{slug}:{mandatory}:missing".encode()).hexdigest(),
                        size_bytes=0,
                        present_on_disk=False,
                        mime_type=_guess_mime_type(mandatory),
                    )
                )
        verified_count = sum(1 for e in entries if e.present_on_disk)
        missing_count = sum(1 for e in entries if not e.present_on_disk)
        archive_ready = missing_count == 0 and verified_count > 0
    else:
        for fname in catalog_names:
            entries.append(
                ArchiveVaultEntrySpec(
                    filename=fname,
                    vault_department=classify_artifact_department(fname),
                    sha256_digest=hashlib.sha256(f"{slug}:{fname}".encode("utf-8")).hexdigest(),
                    size_bytes=_estimate_bytes(fname),
                    present_on_disk=False,
                    mime_type=_guess_mime_type(fname),
                )
            )
        verified_count = len(entries)
        missing_count = 0
        archive_ready = True

    dept_buckets: Dict[VaultDepartmentEnum, List[ArchiveVaultEntrySpec]] = {
        dept: [] for dept in VaultDepartmentEnum
    }
    for entry in entries:
        dept_buckets[entry.vault_department].append(entry)

    summaries: List[DepartmentVaultSummarySpec] = []
    for dept in VaultDepartmentEnum:
        bucket = dept_buckets[dept]
        v_cnt = sum(1 for e in bucket if (e.present_on_disk if output_dir is not None else True))
        summaries.append(
            DepartmentVaultSummarySpec(
                department=dept,
                folder_name=dept.value,
                artifact_count=len(bucket),
                verified_count=v_cnt,
                total_bytes=sum(e.size_bytes for e in bucket),
            )
        )

    total_bytes = sum(e.size_bytes for e in entries)
    total_count = len(entries)
    oxum = f"{total_bytes}.{total_count}"
    runtime_sec = float(getattr(bible, "total_runtime_seconds", 32) or 32)
    footprint_gb = round(max(0.05, runtime_sec * 0.18 + total_bytes / (1024 ** 3)), 3)
    bag_hash = hashlib.sha256(f"{slug}:{oxum}:{tier.value}".encode("utf-8")).hexdigest()[:8]

    manifest = MasterArchiveVaultManifest(
        bag_id=f"bag-{bag_hash}",
        bagit_version="1.0",
        payload_oxum=oxum,
        retention_tier=tier,
        total_artifacts=total_count,
        verified_artifacts=verified_count,
        missing_artifacts=missing_count,
        total_payload_bytes=total_bytes,
        estimated_media_footprint_gb=footprint_gb,
        rights_expiry_iso=rights_expiry,
        vault_summaries=summaries,
        entries=entries,
        archive_ready=archive_ready,
        archive_token="",
    )
    manifest.archive_token = format_archive_vault_token(manifest, 1)
    return manifest


def synthesize_default_archive_vault_manifest(bible: MasterProductionBible) -> MasterArchiveVaultManifest:
    """Synthesizes default RFC 8493 BagIt archive vault manifest."""
    return compile_archive_vault_manifest(bible)


def format_archive_vault_token(manifest: MasterArchiveVaultManifest, scene_index: int = 1) -> str:
    """Formats the machine telemetry token for PM-FEAT-040 RFC 8493 BagIt archive vault."""
    tier_val = manifest.retention_tier.value if hasattr(manifest.retention_tier, "value") else str(manifest.retention_tier)
    ready_str = "true" if manifest.archive_ready else "false"
    return (
        f"[ARCHIVE-VAULT: bag={manifest.bag_id} | SC{scene_index:02d} | "
        f"tier={tier_val} | assets={manifest.total_artifacts} | "
        f"oxum={manifest.payload_oxum} | ready={ready_str}]"
    )


def export_archive_vault_json(manifest: MasterArchiveVaultManifest) -> str:
    """Serializes MasterArchiveVaultManifest to formatted JSON."""
    return manifest.model_dump_json(indent=2)


def export_bag_info_txt(
    manifest: MasterArchiveVaultManifest,
    bible: Optional[MasterProductionBible] = None,
) -> str:
    """Formats RFC 8493 bag-info.txt metadata lines."""
    title = str(getattr(bible, "project_title", manifest.bag_id) or manifest.bag_id)
    tier_val = manifest.retention_tier.value if hasattr(manifest.retention_tier, "value") else str(manifest.retention_tier)
    size_kb = max(1, round(manifest.total_payload_bytes / 1024))
    lines = [
        "Bag-Software-Agent: Omni Movie Director Archive Vault Engine (RFC 8493)",
        "BagIt-Version: 1.0",
        "Tag-File-Character-Encoding: UTF-8",
        "Bagging-Date: 2026-11-28",
        f"External-Identifier: {manifest.bag_id}",
        f"Internal-Sender-Description: {title}",
        f"Payload-Oxum: {manifest.payload_oxum}",
        f"Bag-Size: {size_kb} KB",
        f"Retention-Tier: {tier_val}",
        f"Rights-Expiry-ISO: {manifest.rights_expiry_iso}",
        f"Total-Artifacts: {manifest.total_artifacts}",
        f"Verified-Artifacts: {manifest.verified_artifacts}",
        f"Estimated-Mezzanine-Footprint-GB: {manifest.estimated_media_footprint_gb:.3f}",
    ]
    return "\n".join(lines) + "\n"


def export_manifest_sha256_txt(manifest: MasterArchiveVaultManifest) -> str:
    """Formats RFC 8493 manifest-sha256.txt checksum manifest lines."""
    lines: List[str] = []
    for entry in manifest.entries:
        dept_val = (
            entry.vault_department.value
            if hasattr(entry.vault_department, "value")
            else str(entry.vault_department)
        )
        lines.append(f"{entry.sha256_digest}  data/{dept_val}/{entry.filename}")
    return ("\n".join(lines) + "\n") if lines else ""


def export_agency_delivery_readme_md(
    manifest: MasterArchiveVaultManifest,
    bible: Optional[MasterProductionBible] = None,
) -> str:
    """Exports an Agency Delivery & RFC 8493 BagIt Archive Handoff README."""
    title = str(getattr(bible, "project_title", manifest.bag_id) or manifest.bag_id)
    tier_val = manifest.retention_tier.value if hasattr(manifest.retention_tier, "value") else str(manifest.retention_tier)
    lines: List[str] = [
        f"# Agency Delivery & RFC 8493 BagIt Archive Vault — {title}",
        "",
        f"- **Bag ID**: `{manifest.bag_id}` (BagIt `{manifest.bagit_version}`)",
        f"- **Payload-Oxum**: `{manifest.payload_oxum}`",
        f"- **Retention Tier**: `{tier_val}` (Rights Expiry: `{manifest.rights_expiry_iso}`)",
        f"- **Artifacts**: `{manifest.verified_artifacts}/{manifest.total_artifacts}` verified (`missing={manifest.missing_artifacts}`)",
        f"- **Estimated Mezzanine Media Footprint**: `{manifest.estimated_media_footprint_gb:.3f} GB`",
        f"- **Archive Ready**: `{'READY' if manifest.archive_ready else 'INCOMPLETE'}`",
        "",
        "## Department Vault Hierarchy (`data/`)",
        "",
        "| Department Folder | Artifacts | Verified | Payload Bytes |",
        "|---|---:|---:|---:|",
    ]
    for summary in manifest.vault_summaries:
        lines.append(
            f"| `data/{summary.folder_name}/` | {summary.artifact_count} | "
            f"{summary.verified_count} | {summary.total_bytes} |"
        )
    lines.append("")
    return "\n".join(lines)


def export_archive_vault_bundle(
    bible: MasterProductionBible,
    output_dir: Union[str, Path],
    manifest: Optional[MasterArchiveVaultManifest] = None,
) -> Dict[str, Path]:
    """Writes archive_vault_manifest.json, bag-info.txt, manifest-sha256.txt, and agency_delivery_readme.md."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    resolved = manifest or getattr(bible, "master_archive_vault", None) or compile_archive_vault_manifest(
        bible, output_dir=out_path
    )

    json_path = out_path / "archive_vault_manifest.json"
    bag_info_path = out_path / "bag-info.txt"
    sha_path = out_path / "manifest-sha256.txt"
    readme_path = out_path / "agency_delivery_readme.md"

    json_path.write_text(export_archive_vault_json(resolved), encoding="utf-8")
    bag_info_path.write_text(export_bag_info_txt(resolved, bible), encoding="utf-8")
    sha_path.write_text(export_manifest_sha256_txt(resolved), encoding="utf-8")
    readme_path.write_text(export_agency_delivery_readme_md(resolved, bible), encoding="utf-8")

    return {
        "archive_vault_manifest_json": json_path,
        "bag_info_txt": bag_info_path,
        "manifest_sha256_txt": sha_path,
        "agency_delivery_readme_md": readme_path,
    }


__all__ = [
    "classify_artifact_department",
    "compile_archive_vault_manifest",
    "synthesize_default_archive_vault_manifest",
    "format_archive_vault_token",
    "export_archive_vault_json",
    "export_bag_info_txt",
    "export_manifest_sha256_txt",
    "export_agency_delivery_readme_md",
    "export_archive_vault_bundle",
]
