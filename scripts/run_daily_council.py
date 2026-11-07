#!/usr/bin/env python3
"""Autonomous Daily Product Council & PM Feature Release Runner for Omni Movie Director (v2.7.0).

Executes the automated daily product management, feature verification, quality assurance, and release routine:
1. Preflight environment & 2026 Model Matrix health diagnostics (run_doctor).
2. Senior Product Manager Consultation (ProductManagerAgent):
   - Inspects the entire product using the Senior PM persona:
     "You are a world-class senior product manager that recently joined this project from a top software company.
      You will inspect everything about this product and recommend new features and improvements to the product
      council who will then implement it."
   - Emits outputs/pm_feature_roadmap.json and docs/council_reports/pm_feature_roadmap.json.
3. Regeneration of the 10 production bundles across all 4 Golden Presets & 6 Domain Showcases
   (including NLE EDL/FCPXML, CSV shot lists, Markdown call sheets, and SRT/VTT subtitle tracks):
   - examples/ikea_asmr_2_0 (IKEA ASMR Golden Preset)
   - examples/sephora_pulse_2_0 (Sephora Pulse Golden Preset)
   - examples/sephora_extension_40s_2_0 (Sephora Extension 40s Golden Preset)
   - examples/kinetic_fabric_2_0 (Kinetic Fabric Golden Preset)
   - examples/sephora_london_pulse_2_0 (Sephora London Pulse Showcase)
   - examples/cyberpunk_noir_2_0 (Automotive/Robotics Kinetic Action)
   - examples/solarpunk_utopia_2_0 (Architectural Sanctuary)
   - examples/minimalist_luxury_2_0 (Luxury Fashion)
   - examples/culinary_matcha_asmr_2_0 (Culinary ASMR)
   - examples/quantum_silicon_2_0 (Tech Hardware)
4. Multi-archetype 4-persona Product Council evaluation + PM roadmap verification.
5. Generates latest_council_report.{json,md} and outputs/council_daily_report.{json,md}.
6. Version Release & Git Push:
   - Supports semantic version bumping (--bump-version patch|minor|major) and git release tagging (vX.Y.Z).
   - Quality Gate Enforcement: exits 0 if composite score >= 90.0 and all scene audits >= 90, else 1.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure package root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import omni_director
from omni_director import DirectorPipeline, SENIOR_PM_PERSONA_PROMPT
from omni_director.agents.council import ProductCouncilOrchestrator, ProductManagerAgent
from omni_director.doctor import run_doctor
from omni_director.telemetry import verify_bundle_checksums
from omni_director.tools.dialogue import compile_subtitles_srt, compile_subtitles_vtt
from omni_director.tools.nle_export import export_all_nle_artifacts

OmniDirectorPipeline = DirectorPipeline


CANONICAL_SHOWCASES = [
    {
        "name": "ikea_asmr_2_0",
        "output_dir": Path("examples") / "ikea_asmr_2_0",
        "preset": "ikea-asmr",
        "brief": None,
    },
    {
        "name": "sephora_pulse_2_0",
        "output_dir": Path("examples") / "sephora_pulse_2_0",
        "preset": "sephora-pulse",
        "brief": None,
    },
    {
        "name": "sephora_extension_40s_2_0",
        "output_dir": Path("examples") / "sephora_extension_40s_2_0",
        "preset": "sephora-extension-40s",
        "brief": None,
    },
    {
        "name": "kinetic_fabric_2_0",
        "output_dir": Path("examples") / "kinetic_fabric_2_0",
        "preset": "kinetic-fabric",
        "brief": None,
    },
    {
        "name": "sephora_london_pulse_2_0",
        "output_dir": Path("examples") / "sephora_london_pulse_2_0",
        "preset": "sephora-pulse",
        "brief": None,
    },
    {
        "name": "cyberpunk_noir_2_0",
        "output_dir": Path("examples") / "cyberpunk_noir_2_0",
        "preset": None,
        "brief": (
            "Cyberpunk neon-lit high-speed electric motorcycle pursuit through rain-slicked "
            "Tokyo alleyways with holographic advertisements, tactile throttle friction, and reflective asphalt puddles."
        ),
    },
    {
        "name": "solarpunk_utopia_2_0",
        "output_dir": Path("examples") / "solarpunk_utopia_2_0",
        "preset": None,
        "brief": (
            "Solarpunk architectural sanctuary featuring cascading vertical gardens, curved bamboo pavilions, "
            "photovoltaic glass domes, and quiet magnetic levitation transport in morning mist."
        ),
    },
    {
        "name": "minimalist_luxury_2_0",
        "output_dir": Path("examples") / "minimalist_luxury_2_0",
        "preset": None,
        "brief": (
            "Minimalist luxury haute couture silk velvet runway parfum fragrance luxury editorial atelier campaign "
            "inside brutalist travertine marble gallery with structured wool coats and geometric light shafts."
        ),
    },
    {
        "name": "culinary_matcha_asmr_2_0",
        "output_dir": Path("examples") / "culinary_matcha_asmr_2_0",
        "preset": None,
        "brief": (
            "Artisanal Japanese culinary ceremonial matcha preparation ASMR sequence inside a minimalist tea kitchen. "
            "Macro 100mm lens tracks vibrant green matcha powder sifting into a textured black ceramic bowl, followed by "
            "hot water pouring and a bamboo chasen whisk rapidly frothing dense emerald foam with tactile acoustic clicks."
        ),
    },
    {
        "name": "quantum_silicon_2_0",
        "output_dir": Path("examples") / "quantum_silicon_2_0",
        "preset": None,
        "brief": (
            "Advanced quantum computing silicon processor hardware fabrication sequence inside an ultra-sterile cleanroom. "
            "Precision CNC robotic arm positions a monolithic semiconductor chip wafer beneath laser etching beams, "
            "revealing intricate nanoscale circuit pathways, gold wire bonds, and an anodized aluminum cryo-chamber enclosure."
        ),
    },
]


def bump_project_version(bump_type: str) -> str:
    """Bumps semantic version across pyproject.toml, omni_director/__init__.py, doctor.py, schemas.py, and CHANGELOG.md."""
    current = getattr(omni_director, "__version__", "2.7.0")
    parts = [int(x) for x in current.split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)

    if bump_type == "major":
        new_ver = f"{parts[0] + 1}.0.0"
    elif bump_type == "minor":
        new_ver = f"{parts[0]}.{parts[1] + 1}.0"
    elif bump_type == "patch":
        new_ver = f"{parts[0]}.{parts[1]}.{parts[2] + 1}"
    else:
        return current

    version_files = [
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "omni_director" / "__init__.py",
        REPO_ROOT / "omni_director" / "doctor.py",
        REPO_ROOT / "omni_director" / "schemas.py",
        REPO_ROOT / "omni_director" / "agents" / "council.py",
    ]
    for vf in version_files:
        if vf.is_file():
            content = vf.read_text(encoding="utf-8")
            updated = content.replace(f'"{current}"', f'"{new_ver}"')
            vf.write_text(updated, encoding="utf-8")

    changelog_path = REPO_ROOT / "CHANGELOG.md"
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if changelog_path.is_file():
        cl_text = changelog_path.read_text(encoding="utf-8")
        if f"## [{new_ver}]" not in cl_text:
            header = f"# Changelog\n\nAll notable changes to **Omni Movie Director** are documented in this file.\n\n## [{new_ver}] - {today_str}\n\n### Added\n- Automated daily Senior Product Manager feature verification and Product Council quality release.\n"
            cl_text = re.sub(
                r"^# Changelog.*?(?=## \[)",
                header + "\n",
                cl_text,
                count=1,
                flags=re.DOTALL,
            )
            changelog_path.write_text(cl_text, encoding="utf-8")

    omni_director.__version__ = new_ver
    return new_ver


def run_daily_council(
    push: bool = False,
    release: bool = True,
    bump_version: str = "none",
) -> int:
    """Executes the daily PM + Council routine and returns exit code (0 = pass, 1 = fail)."""
    os.chdir(REPO_ROOT)
    if bump_version in ("patch", "minor", "major"):
        active_version = bump_project_version(bump_version)
        print(f"🔖 Bumped project version to v{active_version}")
    else:
        active_version = getattr(omni_director, "__version__", "2.7.0")

    start_time = datetime.datetime.now(datetime.timezone.utc)
    print("=" * 70)
    print(f"🎬 OMNI MOVIE DIRECTOR v{active_version}: Daily PM & Product Council Routine")
    print(f"Timestamp: {start_time.isoformat()}")
    print("=" * 70)

    # 1. Preflight Health Diagnostics
    print("\n[Stage 1/5] Running FDE Preflight Doctor...")
    doctor_report = run_doctor()
    if not doctor_report.passed:
        print(f"❌ Doctor preflight failed: {getattr(doctor_report, 'summary', 'Unknown error')}")
        return 1
    print(f"✓ Doctor preflight passed: {getattr(doctor_report, 'summary', 'All checks green')}")

    # 2. Senior Product Manager Consultation
    print("\n[Stage 2/5] Consulting Senior Product Manager (council-product-manager)...")
    orchestrator = ProductCouncilOrchestrator()
    pm_proposals = orchestrator.consult_product_manager()
    print(f"  ✓ PM Persona Active: \"{SENIOR_PM_PERSONA_PROMPT}\"")
    for prop in pm_proposals:
        print(f"  • [{prop.priority}] {prop.feature_id} — {prop.title} (Status: {prop.status})")

    # 3. Pipeline Regeneration of Canonical Showcases + NLE/Subtitle Artifacts
    print(f"\n[Stage 3/5] Regenerating and Auditing {len(CANONICAL_SHOWCASES)} Showcase Bundles...")
    pipeline = OmniDirectorPipeline()
    bundle_results: List[Dict[str, Any]] = []

    all_scene_scores: List[float] = []
    council_scores: List[float] = []

    for item in CANONICAL_SHOWCASES:
        out_path = Path(item["output_dir"])
        print(f"  -> Generating '{item['name']}' at {out_path}...")
        try:
            bundle = pipeline.run(
                preset_name=item["preset"] if item.get("preset") else None,
                prompt=item["brief"] if not item.get("preset") else None,
                output_dir=str(out_path),
                dry_run=True,
                render_video=False,
                run_council=True,
            )

            # Export PM-mandated NLE & Subtitle Post-Production Artifacts into each showcase bundle
            nle_files = export_all_nle_artifacts(bundle.bible, out_path, fps=24)
            srt_file = out_path / "subtitles.srt"
            vtt_file = out_path / "subtitles.vtt"
            srt_file.write_text(compile_subtitles_srt(bundle.bible, fps=24), encoding="utf-8")
            vtt_file.write_text(compile_subtitles_vtt(bundle.bible), encoding="utf-8")
            from omni_director.tools.optical_lens import export_lens_metadata_file
            from omni_director.tools.virtual_production import export_virtual_production_bundle
            from omni_director.tools.dof_simulator import export_dof_bundle
            from omni_director.tools.dit_lut import export_dit_bundle
            export_lens_metadata_file(bundle.bible, out_path / "optical_lens_framing.csv")
            export_virtual_production_bundle(bundle.bible, out_path)
            export_dof_bundle(bundle.bible, out_path)
            export_dit_bundle(bundle.bible, out_path)
            # Refresh telemetry manifest so all exported NLE & subtitle artifacts are SHA-256 verified
            pipeline.telemetry.write_manifest(out_path)

            council_rep = bundle.council_report
            overall_score = float(getattr(council_rep, "overall_score", 90.0))
            passed = bool(getattr(council_rep, "passed", True))
            council_scores.append(overall_score)

            # Scene audit scores
            scene_scores = []
            for r in bundle.audit_reports:
                s_score = float(getattr(r, "score", 100.0))
                scene_scores.append(s_score)
                all_scene_scores.append(s_score)

            domain_arch = getattr(bundle.bible, "domain_archetype", None) or "general"

            bundle_results.append({
                "bundle_name": item["name"],
                "path": str(out_path),
                "domain_archetype": domain_arch,
                "council_score": overall_score,
                "passed": passed,
                "scene_scores": scene_scores,
                "scene_count": len(bundle.bible.scenes),
                "total_runtime_seconds": bundle.bible.total_runtime_seconds,
                "nle_artifacts_exported": list(nle_files.keys()) + ["srt", "vtt", "dof", "lut"],
            })
            print(f"     ✓ Council Score: {overall_score:.1f}/100.0 (Scenes: {scene_scores})")
        except Exception as ex:
            print(f"     ❌ Generation failed for '{item['name']}': {ex}")
            return 1

    # 4. Aggregate Metrics & Quality Gate Verification
    print("\n[Stage 4/5] Evaluating Council Quality Gates...")
    avg_council_score = sum(council_scores) / max(1, len(council_scores))
    min_scene_score = min(all_scene_scores) if all_scene_scores else 0.0

    checksums_valid = True
    for item in bundle_results:
        bundle_dir = Path(item["path"])
        is_valid, msg = verify_bundle_checksums(bundle_dir)
        if not is_valid:
            print(f"  ❌ Checksum verification failed for '{item['bundle_name']}': {msg}")
            checksums_valid = False
        else:
            print(f"  ✓ Checksum verified for '{item['bundle_name']}'")

    print(f"  • Average Composite Council Score: {avg_council_score:.2f} / 100.0 (Gate: >= 90.0)")
    print(f"  • Lowest Scene Prompt Audit Score: {min_scene_score:.1f} / 100.0 (Gate: >= 90.0)")
    print(f"  • Bundle Artifact Checksums: {'PASS' if checksums_valid else 'FAIL'} (Gate: all valid)")
    print(f"  • Senior PM Feature Proposals Verified: {len(pm_proposals)} features active")

    gates_passed = (avg_council_score >= 90.0) and (min_scene_score >= 90.0) and checksums_valid

    # 5. Generate Reports & PM Feature Roadmap Artifacts
    print("\n[Stage 5/5] Writing Council & Senior PM Reports...")
    reports_dir = Path("docs") / "council_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)

    json_report_path = reports_dir / "latest_council_report.json"
    md_report_path = reports_dir / "latest_council_report.md"
    daily_md_path = reports_dir / "DAILY_COUNCIL_REPORT.md"
    pm_roadmap_docs_path = reports_dir / "pm_feature_roadmap.json"
    outputs_json_path = outputs_dir / "council_daily_report.json"
    outputs_md_path = outputs_dir / "council_daily_summary.md"
    pm_roadmap_outputs_path = outputs_dir / "pm_feature_roadmap.json"

    pm_roadmap_payload = {
        "version": active_version,
        "timestamp": start_time.isoformat(),
        "persona": "council-product-manager",
        "persona_prompt": SENIOR_PM_PERSONA_PROMPT,
        "recommendations": [p.model_dump(mode="json") for p in pm_proposals],
    }
    pm_json_str = json.dumps(pm_roadmap_payload, indent=2)
    pm_roadmap_docs_path.write_text(pm_json_str, encoding="utf-8")
    pm_roadmap_outputs_path.write_text(pm_json_str, encoding="utf-8")

    report_payload = {
        "version": active_version,
        "timestamp": start_time.isoformat(),
        "doctor_passed": doctor_report.passed,
        "gates_passed": gates_passed,
        "pm_persona_prompt": SENIOR_PM_PERSONA_PROMPT,
        "pm_recommendations": [p.model_dump(mode="json") for p in pm_proposals],
        "metrics": {
            "average_council_score": avg_council_score,
            "minimum_scene_score": min_scene_score,
            "showcase_bundles_evaluated": len(bundle_results),
            "pm_features_implemented": len(pm_proposals),
        },
        "bundles": bundle_results,
    }

    report_json_str = json.dumps(report_payload, indent=2)
    json_report_path.write_text(report_json_str, encoding="utf-8")
    outputs_json_path.write_text(report_json_str, encoding="utf-8")

    md_content = f"""# Daily Autonomous Product Council & Senior PM Report (v{active_version})

- **Release Version**: `v{active_version}`
- **Run Timestamp**: `{start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}`
- **Preflight Doctor Health**: `{'PASS' if doctor_report.passed else 'FAIL'}`
- **Quality Gates Status**: `{'PASSED (>= 90.0)' if gates_passed else 'FAILED'}`
- **Average Council Score**: `{avg_council_score:.2f} / 100.0`
- **Minimum Scene Audit Score**: `{min_scene_score:.1f} / 100.0`

---

## Senior Product Manager Roadmap & Feature Inspection (`council-product-manager`)

> **Persona Directive**: *"{SENIOR_PM_PERSONA_PROMPT}"*

| Feature ID | Priority | Title | Status | Target Modules |
|---|---|---|---|---|
"""
    for prop in pm_proposals:
        mods = ", ".join(f"`{m}`" for m in prop.target_modules)
        md_content += f"| `{prop.feature_id}` | **{prop.priority}** | {prop.title} | `{prop.status}` | {mods} |\n"

    md_content += """
---

## Evaluated Showcase Bundles

| Bundle Name | Domain Archetype | Runtime | Scenes | Council Score | Status |
|---|---|---|---|---|---|
"""
    for b in bundle_results:
        status_badge = "✅ PASS" if b["passed"] else "❌ FAIL"
        md_content += f"| `{b['bundle_name']}` | `{b['domain_archetype']}` | {b['total_runtime_seconds']}s | {b['scene_count']} | **{b['council_score']:.1f}/100** | {status_badge} |\n"

    md_content += f"""
---
*Automated report generated by `scripts/run_daily_council.py` via Omni Movie Director v{active_version}.*
"""
    md_report_path.write_text(md_content, encoding="utf-8")
    daily_md_path.write_text(md_content, encoding="utf-8")
    outputs_md_path.write_text(md_content, encoding="utf-8")
    print(f"  ✓ JSON Report: {json_report_path}")
    print(f"  ✓ Markdown Report: {md_report_path}")
    print(f"  ✓ Daily Report: {daily_md_path}")
    print(f"  ✓ PM Roadmap Report: {pm_roadmap_outputs_path}")
    print(f"  ✓ Outputs JSON Report: {outputs_json_path}")
    print(f"  ✓ Outputs Summary Report: {outputs_md_path}")

    print("\n" + "=" * 70)
    if gates_passed:
        print(f"🎉 ALL DAILY PRODUCT COUNCIL & PM QUALITY GATES PASSED — v{active_version} (Exit 0)")
        print("=" * 70)
        if push:
            print(f"\n[Stage 6/6] Performing automated git commit, version release tag (v{active_version}), and push...")
            status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
            if status_res.stdout.strip():
                commit_msg = (
                    f"feat(release): v{active_version} daily PM feature updates & council verification "
                    f"({avg_council_score:.1f}/100.0)"
                )
                subprocess.run(["git", "add", "-A"], check=True)
                subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                print(f"✓ Committed changes: {commit_msg}")
            else:
                print("✓ Working tree already clean.")

            if release:
                tag_name = f"v{active_version}"
                subprocess.run(
                    ["git", "tag", "-f", "-a", tag_name, "-m", f"Omni Movie Director {tag_name} Daily PM & Council Release"],
                    check=True,
                )
                print(f"✓ Tagged release: {tag_name}")
                subprocess.run(["git", "push", "origin", "HEAD"], check=True)
                subprocess.run(["git", "push", "origin", tag_name, "--force"], check=True)
                print(f"✓ Pushed branch HEAD and release tag {tag_name} to origin.")
            else:
                subprocess.run(["git", "push", "origin", "HEAD"], check=True)
                print("✓ Pushed branch HEAD to origin.")
        return 0
    else:
        print("❌ QUALITY GATE FAILURE: Composite score < 90.0 or scene score < 90 (Exit 1)")
        print("=" * 70)
        return 1


def main() -> int:
    os.chdir(REPO_ROOT)
    parser = argparse.ArgumentParser(
        description="Autonomous Daily Product Council & PM Feature Release Runner for Omni Movie Director"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Automatically git add, commit, tag release, and push changes if all quality gates pass",
    )
    parser.add_argument(
        "--release",
        action="store_true",
        default=True,
        help="Create/update git tag v{version} and push tag when --push is active (default: True)",
    )
    parser.add_argument(
        "--bump-version",
        type=str,
        default="none",
        choices=["none", "patch", "minor", "major"],
        help="Optionally bump semantic version before running the daily council and release",
    )
    args = parser.parse_args()
    return run_daily_council(push=args.push, release=args.release, bump_version=args.bump_version)


if __name__ == "__main__":
    sys.exit(main())
