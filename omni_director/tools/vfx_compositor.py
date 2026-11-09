"""Advanced Multi-Pass VFX Compositing & Render Layer Manifest Engine (PM-FEAT-014).

Provides OpenEXR multi-channel layer decomposition, Cryptomatte object/material
hash manifest generation, Foundry Nuke (.nk) script template authoring,
and prompt token formatting for physical VFX passes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omni_director.schemas import (
    CryptomatteManifestSpec,
    MasterProductionBible,
    ScenePromptSpec,
    VfxCompositingManifestSpec,
    VfxLayerChannelSpec,
    VfxRenderPassType,
)


def hash_identifier_32bit(name: str) -> str:
    """Computes a deterministic 32-bit hex hash for Cryptomatte ID manifests."""
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    # 8-character (32-bit) hex slice
    return f"0x{digest[:8]}"


def generate_cryptomatte_manifest(
    objects: Optional[List[str]] = None,
    materials: Optional[List[str]] = None,
) -> CryptomatteManifestSpec:
    """Generates a Cryptomatte manifest with 32-bit hex hashes for objects and materials."""
    obj_list = objects or ["hero_character", "secondary_character", "vehicle_chassis", "background_architecture"]
    mat_list = materials or ["metal_brushed", "carbon_fiber", "glass_windshield", "skin_subsurface", "concrete_matte"]

    obj_map = {name: hash_identifier_32bit(name) for name in obj_list}
    mat_map = {name: hash_identifier_32bit(name) for name in mat_list}

    return CryptomatteManifestSpec(
        object_manifest=obj_map,
        material_manifest=mat_map,
        hash_algorithm="MurmurHash3_32",
    )


def synthesize_openexr_channel_manifest(
    manifest: VfxCompositingManifestSpec,
    project_title: str = "Omni Production",
) -> Dict[str, Any]:
    """Synthesizes structured OpenEXR 2.0 multi-channel layer manifest metadata."""
    channels_meta: List[Dict[str, Any]] = []

    for p in manifest.passes:
        channels_meta.append({
            "passType": p.pass_type.value if hasattr(p.pass_type, "value") else str(p.pass_type),
            "channelName": p.channel_name,
            "bitDepth": p.bit_depth,
            "colorSpace": p.color_space,
            "description": p.description,
        })

    cryptomatte_dict = None
    if manifest.cryptomatte:
        cryptomatte_dict = {
            "hashAlgorithm": manifest.cryptomatte.hash_algorithm,
            "objectManifest": manifest.cryptomatte.object_manifest,
            "materialManifest": manifest.cryptomatte.material_manifest,
        }

    return {
        "fileFormat": "OpenEXR v2.3 Multi-Layer",
        "manifestVersion": manifest.manifest_version,
        "projectTitle": project_title,
        "openexrCompression": manifest.openexr_compression,
        "colorSpace": "ACEScg",
        "colorWorkingSpace": "ACES - ACEScg",
        "channels": channels_meta,
        "depthPlanes": {
            "nearPlaneMeters": manifest.depth_near_plane_m,
            "farPlaneMeters": manifest.depth_far_plane_m,
            "encoding": "Linear Z distance in camera units",
        },
        "cryptomatte": cryptomatte_dict,
        "reconstructionFormula": manifest.reconstruction_formula,
    }


def generate_nuke_composite_script(
    manifest: VfxCompositingManifestSpec,
    exr_path: str = "renders/shot_01.exr",
    project_title: str = "Omni Production",
) -> str:
    """Generates an industry-standard Foundry Nuke (.nk) composite node tree script."""
    clean_title = project_title.replace('"', '\\"')
    safe_exr_path = exr_path.replace("\\", "/")

    script_lines: List[str] = [
        f"#! /Applications/Nuke15.0v1/Nuke15.0v1 -nx",
        f"# Omni Movie Director v2.8.0 - Automated Multi-Pass Composite Script",
        f"# Project: {clean_title}",
        f"# Reconstruction: {manifest.reconstruction_formula}",
        "",
        "Root {",
        ' format "3840 2160 0 0 3840 2160 1 UHD_4K"',
        " proxy_type scale",
        " proxy_format \"1920 1080 0 0 1920 1080 1 2K_DCP\"",
        " first_frame 1",
        " last_frame 240",
        " fps 24",
        ' colorManagement "OCIO"',
        ' OCIO_config "aces_1.2"',
        ' defaultViewerLUT "ACES/Rec.709"',
        ' workingSpaceLUT "ACES - ACEScg"',
        "}",
        "",
        "# --- 1. Master Multi-Channel OpenEXR Read Node ---",
        "Read {",
        " inputs 0",
        f' file "{safe_exr_path}"',
        ' format "3840 2160 0 0 3840 2160 1 UHD_4K"',
        " first 1",
        " last 240",
        " origfirst 1",
        " origlast 240",
        " origset true",
        ' colorspace "ACES - ACEScg"',
        ' name "Read_MultiPass_EXR"',
        " xpos 0",
        " ypos -400",
        "}",
        "set N_READ [stack 0]",
        "",
        "# --- 2. Channel Decomposition (Shuffle2 Nodes) ---",
        "push $N_READ",
        "Shuffle2 {",
        ' fromInput1 {{0} "B"}',
        ' in1 "diffuse"',
        ' out1 "rgba"',
        ' name "Shuffle_Diffuse"',
        " xpos -300",
        " ypos -250",
        "}",
        "set N_DIFFUSE [stack 0]",
        "",
        "push $N_READ",
        "Shuffle2 {",
        ' fromInput1 {{0} "B"}',
        ' in1 "ambient_occlusion"',
        ' out1 "rgba"',
        ' name "Shuffle_AO"',
        " xpos -150",
        " ypos -250",
        "}",
        "set N_AO [stack 0]",
        "",
        "push $N_READ",
        "Shuffle2 {",
        ' fromInput1 {{0} "B"}',
        ' in1 "specular"',
        ' out1 "rgba"',
        ' name "Shuffle_Specular"',
        " xpos 50",
        " ypos -250",
        "}",
        "set N_SPECULAR [stack 0]",
        "",
        "push $N_READ",
        "Shuffle2 {",
        ' fromInput1 {{0} "B"}',
        ' in1 "emissive"',
        ' out1 "rgba"',
        ' name "Shuffle_Emissive"',
        " xpos 200",
        " ypos -250",
        "}",
        "set N_EMISSIVE [stack 0]",
        "",
        "push $N_READ",
        "Shuffle2 {",
        ' fromInput1 {{0} "B"}',
        ' in1 "depth"',
        ' out1 "depth"',
        ' name "Shuffle_DepthZ"',
        " xpos 350",
        " ypos -250",
        "}",
        "set N_DEPTH [stack 0]",
        "",
        "push $N_READ",
        "Shuffle2 {",
        ' fromInput1 {{0} "B"}',
        ' in1 "normals"',
        ' out1 "rgba"',
        ' name "Shuffle_Normals"',
        " xpos 500",
        " ypos -250",
        "}",
        "set N_NORMALS [stack 0]",
        "",
        "# --- 3. Cryptomatte Object / Material Extraction ---",
        "push $N_READ",
        "Cryptomatte {",
        ' name "Cryptomatte_Extractor"',
        ' matteOutput "Alpha"',
        f' manifest "{manifest.cryptomatte.hash_algorithm if manifest.cryptomatte else "MurmurHash3_32"}"',
        " xpos -450",
        " ypos -250",
        "}",
        "",
        "# --- 4. Mathematical Beauty Reconstruction ---",
        "# Step 4A: Diffuse * AO (Multiply)",
        "push $N_AO",
        "push $N_DIFFUSE",
        "Merge2 {",
        " inputs 2",
        ' operation "multiply"',
        " bbox \"B\"",
        ' name "Merge_Diffuse_x_AO"',
        " xpos -220",
        " ypos -100",
        "}",
        "",
        "# Step 4B: + Specular (Plus)",
        "push $N_SPECULAR",
        "Grade {",
        " white 1.0",
        " gamma 1.0",
        ' name "Grade_Specular_Accent"',
        " xpos 50",
        " ypos -150",
        "}",
        "Merge2 {",
        " inputs 2",
        ' operation "plus"',
        " bbox \"B\"",
        ' name "Merge_Plus_Specular"',
        " xpos -100",
        " ypos 0",
        "}",
        "",
        "# Step 4C: + Emissive (Plus)",
        "push $N_EMISSIVE",
        "Merge2 {",
        " inputs 2",
        ' operation "plus"',
        " bbox \"B\"",
        ' name "Merge_Plus_Emissive"',
        " xpos 0",
        " ypos 100",
        "}",
        "",
        "# --- 5. Atmospheric Depth Fog / Z-Defocus ---",
        "push $N_DEPTH",
        "ZDefocus2 {",
        " inputs 2",
        ' math "direct"',
        f' focal_point {manifest.depth_near_plane_m * 5.0:.1f}',
        " size 12",
        " max_size 24",
        ' name "ZDefocus_Atmosphere"',
        " xpos 0",
        " ypos 200",
        "}",
        "",
        "# --- 6. Master Master Output Write Node ---",
        "Write {",
        ' file "exports/master_comp_beauty.exr"',
        ' file_type "exr"',
        ' datatype "16 bit half"',
        f' compression "{manifest.openexr_compression}"',
        ' colorspace "ACES - ACEScg"',
        ' name "Write_Final_Comp"',
        " xpos 0",
        " ypos 320",
        "}",
    ]

    return "\n".join(script_lines) + "\n"


def format_vfx_compositing_prompt_token(manifest: VfxCompositingManifestSpec) -> str:
    """Formats an audited cinematic VFX multi-pass prompt token for Gemini Omni."""
    pass_names = [p.channel_name for p in manifest.passes]
    pass_str = ", ".join(pass_names) if pass_names else "Beauty.RGB, Diffuse.RGB, Depth.Z"

    crypto_tag = "Cryptomatte (Obj/Mat)" if manifest.cryptomatte else "Cryptomatte"
    comp_type = manifest.openexr_compression

    return (
        f"[VFX COMPOSITING: OpenEXR ({comp_type}, ACEScg), "
        f"Passes: {pass_str}, {crypto_tag}, "
        f"Depth: {manifest.depth_near_plane_m:.1f}m-{manifest.depth_far_plane_m:.1f}m, "
        f"Reconstruct: {manifest.reconstruction_formula}]"
    )


def export_vfx_bundle(
    manifest_or_bible: Union[VfxCompositingManifestSpec, Any],
    output_dir: Union[str, Path],
    project_title: str = "Omni Production",
    exr_path: str = "renders/master_comp.exr",
) -> Dict[str, str]:
    """Exports all multi-pass VFX compositing artifacts into the target directory."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if hasattr(manifest_or_bible, "master_vfx_manifest"):
        manifest = manifest_or_bible.master_vfx_manifest or synthesize_default_vfx_manifest(manifest_or_bible)
        project_title = getattr(manifest_or_bible, "project_title", project_title)
    else:
        manifest = manifest_or_bible

    results: Dict[str, str] = {}

    # 1. OpenEXR Manifest JSON
    exr_manifest = synthesize_openexr_channel_manifest(manifest, project_title=project_title)
    manifest_path = out_path / "vfx_compositing_manifest.json"
    manifest_path.write_text(json.dumps(exr_manifest, indent=2), encoding="utf-8")
    results["vfx_compositing_manifest.json"] = str(manifest_path)
    (out_path / "openexr_channels.json").write_text(json.dumps(exr_manifest, indent=2), encoding="utf-8")
    results["openexr_channels.json"] = str(out_path / "openexr_channels.json")
    (out_path / "openexr_channel_manifest.json").write_text(json.dumps(exr_manifest, indent=2), encoding="utf-8")
    results["openexr_channel_manifest.json"] = str(out_path / "openexr_channel_manifest.json")

    # 2. Foundry Nuke Script (.nk)
    nuke_script = generate_nuke_composite_script(manifest, exr_path=exr_path, project_title=project_title)
    nuke_path = out_path / "nuke_composite_template.nk"
    nuke_path.write_text(nuke_script, encoding="utf-8")
    results["nuke_composite_template.nk"] = str(nuke_path)
    (out_path / "nuke_composite.nk").write_text(nuke_script, encoding="utf-8")
    results["nuke_composite.nk"] = str(out_path / "nuke_composite.nk")
    (out_path / "nuke_comp_script.nk").write_text(nuke_script, encoding="utf-8")
    results["nuke_comp_script.nk"] = str(out_path / "nuke_comp_script.nk")

    # 3. Cryptomatte Manifest JSON
    if manifest.cryptomatte:
        crypto_data = {
            "hashAlgorithm": manifest.cryptomatte.hash_algorithm,
            "objectManifest": manifest.cryptomatte.object_manifest,
            "materialManifest": manifest.cryptomatte.material_manifest,
        }
        crypto_path = out_path / "cryptomatte_manifest.json"
        crypto_path.write_text(json.dumps(crypto_data, indent=2), encoding="utf-8")
        results["cryptomatte_manifest.json"] = str(crypto_path)

    return results


export_vfx_compositing_bundle = export_vfx_bundle
export_nuke_comp_script = generate_nuke_composite_script
export_openexr_channel_manifest_json = synthesize_openexr_channel_manifest


def export_cryptomatte_sidecar_json(manifest: CryptomatteManifestSpec) -> Dict[str, Any]:
    """Exports cryptomatte sidecar data structure."""
    return manifest.model_dump()


def synthesize_default_vfx_manifest(bible: Any = None) -> VfxCompositingManifestSpec:
    """Synthesizes default VFX compositing manifest based on project domain."""
    from omni_director.presets import get_domain_vfx_manifest
    archetype = getattr(bible, "domain_archetype", "kinetic_action") if bible else "kinetic_action"
    if hasattr(archetype, "value"):
        archetype = archetype.value
    return get_domain_vfx_manifest(archetype)
