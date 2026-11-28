"""CLI entry point for omni-director and omni commands."""

from __future__ import annotations

import argparse
import inspect
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rich import print as rprint
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from pydantic import ValidationError

from omni_director import __version__
from omni_director.agents.agent import DirectorPipeline
from omni_director.agents.council import ProductCouncilOrchestrator
from omni_director.config import DirectorConfig, cfg, get_settings
from omni_director.doctor import DoctorReport, run_doctor
from omni_director.presets import (
    CURATED_PRESETS,
    PRESETS,
    get_preset_bible,
)
from omni_director.schemas import (
    MasterProductionBible,
    ProductCouncilReport,
    StorytellingMode,
    load_bible_from_json,
)


def print_banner() -> None:
    banner_text = (
        f"[bold cyan]OMNI MOVIE DIRECTOR {__version__}[/bold cyan] [dim]| ADK 2.0 Multi-Agent Cinema Engine[/dim]\n"
        "[italic]Gemini 4 Argon (Lead) • Gemini 3.8 Flash • Nano Banana • Gemini Omni[/italic]"
    )
    if HAS_RICH:
        console = Console()
        console.print(Panel(banner_text, border_style="cyan"))
    else:
        print("=" * 70)
        print(f"OMNI MOVIE DIRECTOR {__version__} | ADK 2.0 Multi-Agent Cinema Engine")
        print("=" * 70)


def list_presets() -> None:
    print_banner()
    if HAS_RICH:
        console = Console()
        table = Table(title="Built-in Production Bible Presets", border_style="dim")
        table.add_column("Preset Name", style="bold green")
        table.add_column("Creative Regime", style="yellow")
        table.add_column("Mode", style="cyan")
        table.add_column("Title & Logline", style="white")

        for key, bible in PRESETS.items():
            table.add_row(
                key,
                "Regime 2 (Kinetic)" if "Regime 2" in bible.creative_regime.value else "Regime 1 (Atmos)",
                "Mode B (Extension)" if "Mode B" in bible.storytelling_mode.value else "Mode A (Montage)",
                f"[bold]{bible.project_title}[/bold]\n[dim]{bible.logline[:100]}...[/dim]",
            )
        console.print(table)
    else:
        print("\nAvailable Presets:")
        for key, bible in PRESETS.items():
            print(f"- {key}: {bible.project_title} ({bible.creative_regime.value})")


def print_doctor_table(report: DoctorReport, console: Console) -> None:
    table = Table(title=f"Omni Director System Doctor (v{report.version})", border_style="cyan")
    table.add_column("Diagnostic Check", style="bold white")
    table.add_column("Status", style="bold")
    table.add_column("Message", style="dim")
    table.add_column("Remediation", style="yellow")
    for check in report.checks:
        status_style = "green" if check.status.value == "PASS" else ("yellow" if check.status.value == "WARN" else "red")
        table.add_row(
            check.name,
            f"[{status_style}]{check.status.value}[/{status_style}]",
            check.message,
            check.remediation or "None",
        )
    console.print(table)


def print_council_table(report: ProductCouncilReport, console: Console) -> None:
    status_tag = f"[green]PASS ({report.overall_score:.1f}/100.0)[/green]" if report.passed else f"[red]FAIL ({report.overall_score:.1f}/100.0)[/red]"
    table = Table(
        title=f"Autonomous Product Council Scorecard: {report.project_title} — {status_tag}",
        border_style="magenta",
    )
    table.add_column("Council Persona", style="bold white")
    table.add_column("Weight", style="cyan")
    table.add_column("Score", style="bold")
    table.add_column("Findings", style="dim")
    table.add_column("Status", style="bold")

    for persona, review in report.persona_reviews.items():
        status_str = "[green]APPROVED[/green]" if review.passed else "[red]REJECTED[/red]"
        score_str = f"{review.score:.1f} / {review.max_score:.1f}"
        findings_summary = f"{len(review.findings)} finding(s)"
        if review.findings:
            findings_summary += f" ({review.critical_count} critical)"
        table.add_row(
            review.persona_title or persona,
            f"{review.max_score:.0f} pts",
            score_str,
            findings_summary,
            status_str,
        )
    console.print(table)


def handle_doctor(args_list: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="omni doctor", description="Omni Director Environment & Configuration Doctor")
    parser.add_argument("--output-dir", "-o", type=str, default="./output", help="Directory to verify write access")
    parser.add_argument("--json", action="store_true", help="Output doctor report as JSON to stdout")
    args, _ = parser.parse_known_args(args_list)

    report = run_doctor(output_dir=args.output_dir)

    if args.json:
        print(report.model_dump_json(indent=2))
    elif HAS_RICH:
        console = Console()
        print_banner()
        print_doctor_table(report, console)
        if report.passed:
            console.print("\n[bold green]✓ System doctor diagnostics passed: All core dependencies and models ready.[/bold green]")
        else:
            console.print("\n[bold red]✗ System doctor diagnostics failed: Correct issues listed above.[/bold red]")
    else:
        print(f"\n--- Omni Director System Doctor (v{report.version}) ---")
        for check in report.checks:
            print(f"[{check.status.value}] {check.name}: {check.message}")
            if check.remediation:
                print(f"  Remediation: {check.remediation}")
        print("Status:", "PASSED" if report.passed else "FAILED")

    return 0 if report.passed else 1


def handle_council(args_list: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="omni council", description="Autonomous Product Council Quality Audit")
    parser.add_argument("--preset", type=str, default=None, choices=list(PRESETS.keys()), help="Audit a specific preset")
    parser.add_argument("--bible-file", "-b", type=str, default=None, help="Audit a custom MasterProductionBible JSON file")
    parser.add_argument("--all-presets", action="store_true", default=False, help="Explicitly audit all golden presets")
    parser.add_argument("--output-dir", "-o", type=str, default="./output", help="Output directory for reports")
    parser.add_argument("--council-strict", action="store_true", default=False, help="Exit with code 2 if overall score < 88.0 or critical findings > 0")
    parser.add_argument("--json", action="store_true", default=False, help="Emit JSON audit report")
    parser.add_argument("--no-heal", action="store_true", default=False, help="Disable auto-healing of defective scene prompts")

    args = parser.parse_args(args_list)
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pipeline = DirectorPipeline()
    orchestrator = ProductCouncilOrchestrator(config=pipeline.config)

    targets: List[tuple[str, Optional[MasterProductionBible]]] = []
    if args.bible_file:
        bible_p = Path(args.bible_file)
        if not bible_p.exists() or not bible_p.is_file():
            print(f"Error: Bible file does not exist at '{args.bible_file}'", file=sys.stderr)
            return 1
        try:
            bible = load_bible_from_json(args.bible_file)
            targets.append((Path(args.bible_file).stem, bible))
        except Exception as exc:
            print(f"Error loading bible file '{args.bible_file}': {exc}", file=sys.stderr)
            return 1
    elif args.preset:
        targets.append((args.preset, get_preset_bible(args.preset)))
    else:
        # Default: audit canonical golden presets (deduplicate alias unless --all-presets is passed)
        preset_keys = list(CURATED_PRESETS.keys())
        if not args.all_presets:
            preset_keys = [k for k in preset_keys if k != "sephora-london-pulse"]
        for key in preset_keys:
            targets.append((key, get_preset_bible(key)))

    overall_success = True
    reports: List[ProductCouncilReport] = []

    for name, bible in targets:
        bundle = pipeline.run(
            preset_name=name if name in PRESETS else None,
            bible=bible,
            output_dir=args.output_dir,
            render_video=False,
            dry_run=True,
            run_council=False,
        )
        report = orchestrator.audit(
            bundle=bundle,
            bible=bundle.bible,
            auto_heal=not args.no_heal,
            output_dir=output_path,
        )
        bundle.council_report = report
        telemetry_obj = getattr(pipeline, "telemetry", None)
        if telemetry_obj is None:
            from omni_director.telemetry import RuntimeTelemetry
            telemetry_obj = RuntimeTelemetry(project_title=bundle.bible.project_title)
        bundle.telemetry = telemetry_obj.to_dict()
        bundle_json_file = Path(bundle.bundle_json_path) if bundle.bundle_json_path else (output_path / "production_bundle.json")
        bundle_json_file.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
        telemetry_obj.write_manifest(output_path)
        bundle.telemetry = telemetry_obj.to_dict()
        reports.append(report)

        if not report.passed or report.overall_score < 88.0 or report.critical_findings_count > 0:
            overall_success = False

    if args.json:
        if len(reports) == 1:
            print(reports[0].model_dump_json(indent=2))
        else:
            print(json.dumps([r.model_dump(mode="json") for r in reports], indent=2))
    elif HAS_RICH:
        console = Console()
        print_banner()
        for report in reports:
            print_council_table(report, console)
            console.print("")
    else:
        for report in reports:
            print(f"\nCouncil Report for {report.project_title}: {report.overall_score:.1f}/100.0 (Passed: {report.passed})")
            for persona, review in report.persona_reviews.items():
                print(f"  {persona}: {review.score:.1f}/{review.max_score:.1f} ({len(review.findings)} findings)")

    if args.council_strict and not overall_success:
        if HAS_RICH:
            Console().print("[bold red]✗ Council Strict Check Failed: Score < 88.0 or Critical Findings present.[/bold red]")
        else:
            print("Council Strict Check Failed: Score < 88.0 or Critical Findings present.", file=sys.stderr)
        return 2

    return 0


def handle_export(args_list: List[str]) -> int:
    """Exports NLE timeline, shot list CSV, call sheet MD, and SRT/VTT subtitles for a preset or Bible file."""
    from omni_director.tools.dialogue import compile_subtitles_srt, compile_subtitles_vtt
    from omni_director.tools.nle_export import (
        export_all_nle_artifacts,
        export_cmx3600_edl,
        export_fcpxml,
        export_production_callsheet_md,
        export_shot_list_csv,
    )
    from omni_director.tools.color_grade import export_asc_cdl_file
    from omni_director.tools.audio_mixer import export_audio_stems_file
    from omni_director.tools.optical_lens import export_lens_metadata_file
    from omni_director.tools.virtual_production import export_virtual_production_bundle
    from omni_director.tools.moco_kinematics import export_moco_bundle
    from omni_director.tools.lighting_rig import export_lighting_bundle
    from omni_director.tools.dof_simulator import (
        export_dof_bundle,
        export_focus_puller_cue_sheet,
        export_optical_chart_json,
    )
    from omni_director.tools.dit_lut import (
        export_dit_cart_manifest_json,
        export_lut_bundle,
        export_master_cube_lut,
    )
    from omni_director.tools.spatial_audio import (
        export_adm_spatial_json,
        export_ambisonic_track_csv,
        export_spatial_audio_bundle,
        export_web_audio_spatial_config,
        synthesize_default_spatial_audio,
    )
    from omni_director.tools.vfx_compositor import (
        export_cryptomatte_sidecar_json,
        export_nuke_comp_script,
        export_openexr_channel_manifest_json,
        export_vfx_compositing_bundle,
    )
    from omni_director.tools.hdr_signal import (
        export_hdr10_metadata_json,
        export_hlg_broadcast_xml,
        export_resolve_hdr_xml,
        export_hdr_bundle,
    )
    from omni_director.tools.stripboard_scheduler import (
        export_movie_magic_xml,
        export_stripboard_csv,
        export_dood_csv,
        export_stripboard_bundle,
        generate_stripboard_schedule,
    )
    from omni_director.tools.film_emulation import (
        export_film_emulation_bundle,
        generate_davinci_dctl_shader,
        export_film_stock_ale,
        synthesize_default_film_stock,
    )
    from omni_director.tools.clapper_slate import (
        export_slate_bundle,
        generate_asc_mhl_xml,
        generate_clapper_slate_log_csv,
        generate_sound_sync_ale,
        synthesize_default_slate_spec,
    )
    from omni_director.tools.drone_flight import (
        export_drone_flight_bundle,
        generate_drone_flight_kml,
        generate_drone_flight_gpx,
        synthesize_default_drone_flight,
    )
    from omni_director.tools.aicp_budget import (
        export_aicp_budget_bundle,
        generate_aicp_bid_sheet_csv,
        generate_aicp_bid_manifest_json,
        synthesize_default_aicp_bid,
    )
    from omni_director.tools.delivery_reframe import (
        export_reframe_bundle,
        generate_cutdown_edl,
        generate_reframe_fcpxml,
        generate_reframe_manifest_json,
        generate_reframe_matrix_csv,
    )
    from omni_director.tools.broadcast_qc import (
        export_broadcast_qc_bundle,
        generate_clearance_matrix_csv,
        generate_qc_certificate_md,
        generate_qc_manifest_json,
    )
    from omni_director.tools.continuity_blocking import (
        export_continuity_bundle,
        generate_blocking_floorplan_svg,
        generate_continuity_log_csv,
        generate_continuity_manifest_json,
    )
    from omni_director.tools.review_notes import (
        export_review_bundle,
        generate_client_signoff_md,
        generate_frameio_review_json,
        generate_resolve_marker_edl,
        generate_review_fcpxml_markers,
        generate_review_notes_csv,
    )

    parser = argparse.ArgumentParser(prog="omni export", description="Export NLE timelines (EDL/FCPXML/OTIO), shot lists, call sheets, subtitles, CDL color grades, audio stem manifests, lens packages, virtual production stage manifests, MoCo kinematics tracks, lighting plots, optical DoF charts, DIT 3D LUT suites, spatial audio packages, VFX compositing manifests, HDR broadcast color volume packages, 1st AD stripboard production schedules, film stock emulation bundles, clapper slate packages, drone flight paths (KML/GPX), AICP commercial production bids, multi-aspect social reframe cutdowns, Broadcast QC / PSE / Rights clearance packages, 180-degree continuity blocking floorplans, client review marker/signoff packages, C2PA Content Credentials / AI disclosure / likeness consent packages, on-set safety JSA / risk manifests, multi-territory localization / ADR / IMSC1 TTML packages, editorial J-Cut / L-Cut spotting & beat-grid split-edit bundles, stereoscopic 3D (s3d / MV-HEVC) spatial manifests, audio description (ad / ad-vtt) accessibility tracks, wardrobe & prop art department (art-dept) continuity bibles, Gemini compute render economics (economics), Motion Graphics MOGRT/ASS/end-card specs (motion-graphics), OpenTimelineIO 7-track & cross-department coherence matrices (coherence), digital colorimetry scopes & shot-match CDL continuity (color-scopes), and RFC 8493 BagIt archive vault packages (archive-vault)")
    parser.add_argument("--preset", type=str, default=None, choices=list(PRESETS.keys()), help="Preset name to export")
    parser.add_argument("--bible-file", "-b", type=str, default=None, help="Path to MasterProductionBible or ProductionBundle JSON")
    parser.add_argument("--baseline-bible", type=str, default=None, help="Path to baseline MasterProductionBible or ProductionBundle JSON for revision diff generation")
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="all",
        choices=[
            "all", "edl", "fcpxml", "csv", "md", "srt", "vtt", "cdl", "stems", "lens", "vp", "moco",
            "lighting", "dof", "lut", "spatial", "vfx", "hdr", "stripboard", "film", "slate", "drone",
            "aicp", "reframe", "qc", "continuity", "review", "c2pa", "safety", "i18n", "spotting",
            "s3d", "ad", "ad-vtt", "art-dept", "economics", "motion-graphics", "mogrt-json",
            "supers-ass", "endcard-md", "coherence", "otio", "coherence-json", "coherence-md",
            "render-jobs", "render-manifest", "take-qa", "rough-cut",
            "treatment", "lookbook", "treatment-md", "treatment-json",
            "imf-dcp", "imf-assetmap", "imf-pkl", "imf-cpl", "dcp-spec",
            "voice-ducking", "voice-cast", "ducking-csv", "viseme-md",
            "color-scopes", "scopes-json", "shot-match-csv", "scopes-md",
            "archive-vault", "bag-info", "bag-manifest", "vault-json", "delivery-readme",
        ],
        help="Artifact format to export (default: all; includes render-jobs, rough-cut, treatment, imf-dcp, voice-ducking, color-scopes, archive-vault, etc.)",
    )
    parser.add_argument("--dof-chart", action="store_true", help="Export optical hyperfocal chart JSON (dof_chart.json)")
    parser.add_argument("--cue-sheet", action="store_true", help="Export 1st AC Focus Puller cue sheet CSV (focus_puller_cue_sheet.csv)")
    parser.add_argument("--cube-lut", action="store_true", help="Export master 3D LUT .cube file (production_look.cube)")
    parser.add_argument("--dit-manifest", action="store_true", help="Export DIT cart offload manifest JSON (dit_cart_manifest.json)")
    parser.add_argument("--spatial-adm", action="store_true", help="Export ADM spatial audio metadata JSON (spatial_audio_adm.json)")
    parser.add_argument("--ambisonic-csv", action="store_true", help="Export HOA 3rd-order ambisonic track CSV (ambisonic_b_format.csv)")
    parser.add_argument("--webaudio-config", action="store_true", help="Export Web Audio HRTF spatial panner config JSON (webaudio_spatial_config.json)")
    parser.add_argument("--vfx-manifest", action="store_true", help="Export OpenEXR channel manifest JSON (openexr_channels.json)")
    parser.add_argument("--cryptomatte-sidecar", action="store_true", help="Export Cryptomatte sidecar JSON (cryptomatte_manifest.json)")
    parser.add_argument("--nuke-script", action="store_true", help="Export Foundry Nuke compositing script (nuke_composite.nk)")
    parser.add_argument("--hdr-json", action="store_true", help="Export HDR10 / SMPTE ST 2086 metadata JSON (hdr10_metadata.json)")
    parser.add_argument("--hlg-xml", action="store_true", help="Export ARIB STD-B67 / BT.2100 HLG broadcast XML (hlg_broadcast.xml)")
    parser.add_argument("--resolve-hdr", action="store_true", help="Export DaVinci Resolve HDR color management XML (resolve_hdr_rcm.xml)")
    parser.add_argument("--movie-magic-xml", action="store_true", help="Export Movie Magic Scheduling XML (movie_magic_schedule.xml)")
    parser.add_argument("--stripboard-csv", action="store_true", help="Export 1st AD Stripboard schedule CSV (stripboard_schedule.csv)")
    parser.add_argument("--dood-csv", action="store_true", help="Export SAG-AFTRA Day-Out-of-Days matrix CSV (dood_matrix.csv)")
    parser.add_argument("--film-dctl", action="store_true", help="Export DaVinci Resolve DCTL film emulation shader (film_emulation.dctl & film_stock_shader.dctl)")
    parser.add_argument("--film-ale", action="store_true", help="Export film stock Avid Log Exchange (film_stock.ale)")
    parser.add_argument("--mhl-xml", action="store_true", help="Export ASC-MHL media hash list XML (asc_mhl_manifest.xml)")
    parser.add_argument("--sound-ale", action="store_true", help="Export sound sync Avid Log Exchange (sound_sync.ale)")
    parser.add_argument("--slate-csv", action="store_true", help="Export clapper slate log CSV (clapper_slate_log.csv)")
    parser.add_argument("--drone-kml", action="store_true", help="Export Google Earth / DJI Pilot 2 flight path KML (flight_path.kml)")
    parser.add_argument("--drone-gpx", action="store_true", help="Export GPS Exchange format waypoint GPX (flight_waypoints.gpx)")
    parser.add_argument("--aicp-csv", action="store_true", help="Export AICP commercial production bid sheet CSV (aicp_bid_sheet.csv)")
    parser.add_argument("--aicp-json", action="store_true", help="Export AICP bid manifest JSON (aicp_bid_manifest.json)")
    parser.add_argument("--reframe-csv", action="store_true", help="Export multi-aspect reframe crop & UI safe-zone CSV (reframe_crop_matrix.csv)")
    parser.add_argument("--cutdown-edl", action="store_true", help="Export :15s and :06s editorial cutdown CMX 3600 EDLs (cutdown_15s.edl, cutdown_06s.edl)")
    parser.add_argument("--reframe-fcpxml", action="store_true", help="Export 9:16 social reframe FCPXML v1.10 timeline (reframe_9x16.fcpxml)")
    parser.add_argument("--reframe-json", action="store_true", help="Export multi-aspect reframe manifest JSON (delivery_reframe_manifest.json)")
    parser.add_argument("--qc-cert", action="store_true", help="Export Broadcast QC & PSE safety certificate Markdown (broadcast_qc_certificate.md)")
    parser.add_argument("--clearance-csv", action="store_true", help="Export legal & rights clearance matrix CSV (rights_clearance_matrix.csv)")
    parser.add_argument("--qc-json", action="store_true", help="Export Broadcast QC & rights manifest JSON (broadcast_qc_manifest.json)")
    parser.add_argument("--continuity-csv", action="store_true", help="Export 180-degree continuity blocking log CSV (continuity_log.csv)")
    parser.add_argument("--blocking-svg", action="store_true", help="Export overhead 2D blocking floorplan SVG (blocking_floorplan.svg)")
    parser.add_argument("--continuity-json", action="store_true", help="Export continuity blocking manifest JSON (continuity_manifest.json)")
    parser.add_argument("--review-edl", action="store_true", help="Export DaVinci Resolve / Avid locator marker EDL (review_markers.edl)")
    parser.add_argument("--review-fcpxml", action="store_true", help="Export FCPXML v1.10 timeline markers (review_markers.fcpxml)")
    parser.add_argument("--review-json", action="store_true", help="Export Frame.io-compatible review annotations JSON (review_notes_frameio.json)")
    parser.add_argument("--review-csv", action="store_true", help="Export client review annotations ledger CSV (review_notes.csv)")
    parser.add_argument("--signoff-md", action="store_true", help="Export client review & live-render signoff report Markdown (client_signoff_report.md)")
    parser.add_argument("--c2pa-json", action="store_true", help="Export C2PA Content Credentials manifest JSON (c2pa_manifest.json)")
    parser.add_argument("--disclosure-md", action="store_true", help="Export synthetic AI disclosure certificate Markdown (ai_disclosure_certificate.md)")
    parser.add_argument("--likeness-csv", action="store_true", help="Export talent likeness & voice consent ledger CSV (likeness_consent_ledger.csv)")
    parser.add_argument("--safety-md", action="store_true", help="Export on-set safety bulletin Markdown (safety_bulletin.md)")
    parser.add_argument("--safety-csv", action="store_true", help="Export Job Safety Analysis (JSA) matrix CSV (safety_jsa_matrix.csv)")
    parser.add_argument("--safety-json", action="store_true", help="Export on-set safety risk manifest JSON (safety_risk_manifest.json)")
    parser.add_argument("--i18n-json", action="store_true", help="Export multi-territory localization manifest JSON (localization_manifest.json)")
    parser.add_argument("--adr-csv", action="store_true", help="Export ADR dubbing cue sheet CSV (adr_cue_sheet.csv)")
    parser.add_argument("--ttml", action="store_true", help="Export IMSC1 TTML timed-text subtitles (subtitles_localized.ttml)")
    parser.add_argument("--locales", type=str, default=None, help="Comma-separated BCP-47 locale list for localization/ADR export (e.g. en-US,de-DE,fr-FR,ja-JP)")
    parser.add_argument("--spotting-json", action="store_true", help="Export editorial spotting & beat-grid manifest JSON (spotting_manifest.json)")
    parser.add_argument("--spotting-csv", action="store_true", help="Export music & foley spotting cue sheet CSV (spotting_cue_sheet.csv)")
    parser.add_argument("--spotting-md", action="store_true", help="Export editorial J-Cut / L-Cut spotting sheet Markdown (spotting_sheet.md)")
    parser.add_argument("--split-edl", action="store_true", help="Export CMX 3600 split-edit EDL with staggered V/A/A2 J/L-Cut events (timeline_split_edits.edl)")
    s3d_group = parser.add_argument_group("Export Subsystem: Stereoscopic 3D & Spatial Video (PM-FEAT-029)")
    s3d_group.add_argument("--s3d-csv", action="store_true", help="Export S3D IO/Convergence parallax log CSV (s3d_parallax_log.csv)")
    s3d_group.add_argument("--spatial-manifest", action="store_true", help="Export MV-HEVC spatial video manifest JSON (spatial_video_manifest.json)")
    ad_group = parser.add_argument_group("Export Subsystem: Accessibility & Audio Description (PM-FEAT-030)")
    ad_group.add_argument("--ad-vtt", action="store_true", help="Export Audio Description WebVTT track (subtitles_ad.vtt)")
    ad_group.add_argument("--ad-csv", action="store_true", help="Export Audio Description cue sheet CSV (ad_script_cue_sheet.csv)")
    ad_group.add_argument("--ad-manifest", action="store_true", help="Export WCAG/CVAA accessibility manifest JSON (accessibility_ad_manifest.json)")
    art_group = parser.add_argument_group("Export Subsystem: Art Dept, Wardrobe & Prop Continuity (PM-FEAT-031)")
    art_group.add_argument("--art-dept", action="store_true", help="Export full Art Dept, Wardrobe & Prop continuity bundle (wardrobe_prop_bible.json, prop_continuity_matrix.csv, art_dept_pull_list.md)")
    art_group.add_argument("--wardrobe-json", action="store_true", help="Export Wardrobe & Prop continuity bible JSON (wardrobe_prop_bible.json)")
    art_group.add_argument("--prop-csv", action="store_true", help="Export Prop action-state continuity matrix CSV (prop_continuity_matrix.csv)")
    art_group.add_argument("--pull-list-md", action="store_true", help="Export Art Department pull list Markdown (art_dept_pull_list.md)")
    econ_group = parser.add_argument_group("Export Subsystem: AI Render Economics & Take Budget (PM-FEAT-032)")
    econ_group.add_argument("--economics", action="store_true", help="Export full AI Render Economics bundle (render_economics_manifest.json, take_variant_ledger.csv, ai_compute_estimate.md)")
    econ_group.add_argument("--economics-json", action="store_true", help="Export AI Render Economics manifest JSON (render_economics_manifest.json)")
    econ_group.add_argument("--takes-csv", action="store_true", help="Export Take Variant & Seed Ledger CSV (take_variant_ledger.csv)")
    econ_group.add_argument("--compute-md", action="store_true", help="Export AI Compute Estimate summary Markdown (ai_compute_estimate.md)")
    gfx_group = parser.add_argument_group("Export Subsystem: Motion Graphics, Supers & Brand End-Card (PM-FEAT-033)")
    gfx_group.add_argument("--motion-graphics", action="store_true", help="Export full Motion Graphics bundle (motion_graphics_mogrt.json, broadcast_supers.ass, brand_endcard_spec.md)")
    gfx_group.add_argument("--mogrt-json", action="store_true", help="Export Premiere/AE MOGRT JSON cue manifest (motion_graphics_mogrt.json)")
    gfx_group.add_argument("--supers-ass", action="store_true", help="Export SubStation Alpha v4+ broadcast supers (broadcast_supers.ass)")
    gfx_group.add_argument("--endcard-md", action="store_true", help="Export Brand End-Card & Legal Super spec Markdown (brand_endcard_spec.md)")
    otio_group = parser.add_argument_group("Export Subsystem: OpenTimelineIO (.otio) & Cross-Dept Coherence (PM-FEAT-034)")
    otio_group.add_argument("--coherence", action="store_true", help="Export full OTIO & Cross-Department Coherence bundle (production_timeline.otio, coherence_matrix.json, coherence_readiness_report.md)")
    otio_group.add_argument("--otio", action="store_true", help="Export ASWF OpenTimelineIO 0.16 Timeline.1 (production_timeline.otio)")
    otio_group.add_argument("--coherence-json", action="store_true", help="Export Cross-Department Coherence Matrix JSON (coherence_matrix.json)")
    otio_group.add_argument("--coherence-md", action="store_true", help="Export Cross-Department Coherence & Shoot-Day Readiness Report Markdown (coherence_readiness_report.md)")
    render_group = parser.add_argument_group("Export Subsystem: Live-Render Jobs, Take QA & Rough Cut Assembly (PM-FEAT-035)")
    render_group.add_argument("--render-jobs", action="store_true", help="Export full Render Orchestrator bundle (render_job_manifest.json, take_qa_scorecard.csv, rough_cut_assembly.sh)")
    render_group.add_argument("--render-manifest", action="store_true", help="Export Render Job Orchestrator manifest JSON (render_job_manifest.json)")
    render_group.add_argument("--take-qa-csv", action="store_true", help="Export Multi-Take Visual QA scorecard CSV (take_qa_scorecard.csv)")
    render_group.add_argument("--assembly-sh", action="store_true", help="Export ffmpeg rough-cut concat assembly script (rough_cut_assembly.sh)")
    treatment_group = parser.add_argument_group("Export Subsystem: Director Treatment Lookbook & Pitch Deck (PM-FEAT-036)")
    treatment_group.add_argument("--treatment", action="store_true", help="Export full Director Pitch Treatment bundle (director_treatment_lookbook.html, director_treatment_brief.md, pitch_treatment_manifest.json)")
    treatment_group.add_argument("--treatment-html", action="store_true", help="Export printable Director's Pitch Lookbook HTML5 (director_treatment_lookbook.html)")
    treatment_group.add_argument("--treatment-md", action="store_true", help="Export Executive Director's Treatment brief Markdown (director_treatment_brief.md)")
    treatment_group.add_argument("--treatment-json", action="store_true", help="Export Pitch Treatment manifest JSON (pitch_treatment_manifest.json)")
    imf_group = parser.add_argument_group("Export Subsystem: SMPTE IMF Supplemental Package & DCI Theatrical DCP (PM-FEAT-037)")
    imf_group.add_argument("--imf-dcp", action="store_true", help="Export full SMPTE IMF & DCI DCP bundle (ASSETMAP.xml, PKL.xml, CPL_master.xml, imf_dcp_manifest.json, dcp_cpl_spec.md)")
    imf_group.add_argument("--imf-assetmap", action="store_true", help="Export SMPTE ST 429-9 / ST 2067-2 ASSETMAP XML (ASSETMAP.xml)")
    imf_group.add_argument("--imf-pkl", action="store_true", help="Export SMPTE ST 2067-2 Packing List XML (PKL.xml)")
    imf_group.add_argument("--imf-cpl", action="store_true", help="Export SMPTE ST 2067-3 Composition Playlist XML (CPL_master.xml)")
    imf_group.add_argument("--dcp-spec", action="store_true", help="Export IMF & DCI Theatrical DCP mastering specification Markdown (dcp_cpl_spec.md)")
    voice_group = parser.add_argument_group("Export Subsystem: Voice Casting, Viseme Lip-Sync & Stem Sidechain Ducking (PM-FEAT-038)")
    voice_group.add_argument("--voice-ducking", action="store_true", help="Export full Voice Casting, Viseme Lip-Sync & Sidechain Ducking bundle (voice_casting_script.json, stem_ducking_automation.csv, adr_viseme_timing.md)")
    voice_group.add_argument("--voice-cast", action="store_true", help="Export Voice Casting & Viseme Lip-Sync manifest JSON (voice_casting_script.json)")
    voice_group.add_argument("--ducking-csv", action="store_true", help="Export Sidechain Stem Ducking automation keyframes CSV (stem_ducking_automation.csv)")
    voice_group.add_argument("--viseme-md", action="store_true", help="Export Voice Casting, ADR & Preston Blair Viseme timing script Markdown (adr_viseme_timing.md)")
    scopes_group = parser.add_argument_group("Export Subsystem: Digital Colorimetry Scopes & Shot-Match Continuity (PM-FEAT-039)")
    scopes_group.add_argument("--color-scopes", action="store_true", help="Export full Digital Colorimetry Scopes & Shot-Match CDL bundle (color_continuity_scopes.json, shot_match_cdl_deltas.csv, finishing_scopes_qc.md)")
    scopes_group.add_argument("--scopes-json", action="store_true", help="Export Digital Colorimetry Scopes manifest JSON (color_continuity_scopes.json)")
    scopes_group.add_argument("--shot-match-csv", action="store_true", help="Export Adjacent-Cut CIEDE2000 & CDL trim deltas CSV (shot_match_cdl_deltas.csv)")
    scopes_group.add_argument("--scopes-md", action="store_true", help="Export Finishing Colorimetry Scopes QC report Markdown (finishing_scopes_qc.md)")
    vault_group = parser.add_argument_group("Export Subsystem: RFC 8493 BagIt Archive Vault & Agency Delivery (PM-FEAT-040)")
    vault_group.add_argument("--archive-vault", action="store_true", help="Export full RFC 8493 BagIt Archive Vault bundle (archive_vault_manifest.json, bag-info.txt, manifest-sha256.txt, agency_delivery_readme.md)")
    vault_group.add_argument("--bag-info", action="store_true", help="Export RFC 8493 BagIt metadata tag file (bag-info.txt)")
    vault_group.add_argument("--bag-manifest", action="store_true", help="Export RFC 8493 SHA-256 payload checksum manifest (manifest-sha256.txt)")
    vault_group.add_argument("--vault-json", action="store_true", help="Export Archive Vault manifest JSON (archive_vault_manifest.json)")
    vault_group.add_argument("--delivery-readme", action="store_true", help="Export Agency Delivery & BagIt Vault Handoff README Markdown (agency_delivery_readme.md)")
    parser.add_argument("--output-dir", "-o", type=str, default="./output", help="Target directory for exported files")
    parser.add_argument("--fps", type=int, default=24, help="Frame rate for timecode calculations (default: 24)")
    parser.add_argument("--refresh-telemetry", action="store_true", default=False, help="Refresh telemetry.json SHA-256 artifact checksums after export")
    parser.add_argument("--json", action="store_true", help="Output exported file manifest as JSON")

    args = parser.parse_args(args_list)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.bible_file:
        bible_p = Path(args.bible_file)
        if not bible_p.exists() or not bible_p.is_file():
            print(f"Error: Bible file does not exist at '{args.bible_file}'", file=sys.stderr)
            return 1
        try:
            bible = load_bible_from_json(args.bible_file)
        except Exception as exc:
            print(f"Error loading bible file '{args.bible_file}': {exc}", file=sys.stderr)
            return 1
    else:
        preset_key = args.preset or "ikea-asmr"
        bible = get_preset_bible(preset_key)

    baseline_path: Optional[Path] = None
    if args.baseline_bible:
        baseline_path = Path(args.baseline_bible)
        if not baseline_path.exists() or not baseline_path.is_file():
            print(f"Error: Baseline bible file does not exist at '{args.baseline_bible}'", file=sys.stderr)
            return 1

    target_locales: Optional[List[str]] = None
    if args.locales:
        target_locales = [loc.strip() for loc in args.locales.split(",") if loc.strip()]
        if target_locales:
            from omni_director.tools.localization_adr import compile_localization_manifest
            bible = bible.model_copy(
                update={"localization_manifest": compile_localization_manifest(bible, locales=target_locales)}
            )

    exported_files: Dict[str, str] = {}
    fmt = args.format.lower()

    def _write_motion_graphics_artifact(kind: str) -> None:
        from omni_director.tools.motion_graphics import (
            compile_motion_graphics_manifest,
            export_brand_endcard_md,
            export_broadcast_supers_ass,
            export_mogrt_json,
        )
        manifest = getattr(bible, "master_motion_graphics", None) or compile_motion_graphics_manifest(bible)
        if kind == "mogrt-json":
            p = out_dir / "motion_graphics_mogrt.json"
            p.write_text(export_mogrt_json(manifest, bible), encoding="utf-8")
            exported_files["motion_graphics_mogrt_json"] = str(p.resolve())
        elif kind == "supers-ass":
            p = out_dir / "broadcast_supers.ass"
            p.write_text(export_broadcast_supers_ass(manifest, fps=args.fps), encoding="utf-8")
            exported_files["broadcast_supers_ass"] = str(p.resolve())
        elif kind == "endcard-md":
            p = out_dir / "brand_endcard_spec.md"
            p.write_text(export_brand_endcard_md(manifest), encoding="utf-8")
            exported_files["brand_endcard_spec_md"] = str(p.resolve())

    def _write_otio_coherence_artifact(kind: str) -> None:
        from omni_director.tools.otio_coherence import (
            compile_otio_coherence_manifest,
            export_coherence_matrix_json,
            export_coherence_readiness_md,
            export_otio_file,
        )
        if kind == "otio":
            p = out_dir / "production_timeline.otio"
            p.write_text(export_otio_file(bible, fps=float(args.fps)), encoding="utf-8")
            exported_files["production_timeline_otio"] = str(p.resolve())
            return
        manifest = getattr(bible, "master_otio_coherence", None) or compile_otio_coherence_manifest(bible)
        if kind == "coherence-json":
            p = out_dir / "coherence_matrix.json"
            p.write_text(export_coherence_matrix_json(manifest), encoding="utf-8")
            exported_files["coherence_matrix_json"] = str(p.resolve())
        elif kind == "coherence-md":
            p = out_dir / "coherence_readiness_report.md"
            p.write_text(export_coherence_readiness_md(manifest), encoding="utf-8")
            exported_files["coherence_readiness_report_md"] = str(p.resolve())

    def _write_render_jobs_artifact(kind: str) -> None:
        from omni_director.tools.render_orchestrator import (
            compile_render_job_manifest,
            export_render_job_manifest_json,
            export_take_qa_csv,
            generate_rough_cut_assembly_script,
        )
        manifest = getattr(bible, "master_render_jobs", None)
        if manifest is None or not getattr(manifest, "jobs", None):
            manifest = compile_render_job_manifest(bible, dry_run=True)
        if kind == "render-manifest":
            p = out_dir / "render_job_manifest.json"
            p.write_text(export_render_job_manifest_json(manifest), encoding="utf-8")
            exported_files["render_job_manifest_json"] = str(p.resolve())
        elif kind == "take-qa":
            p = out_dir / "take_qa_scorecard.csv"
            p.write_text(export_take_qa_csv(manifest), encoding="utf-8")
            exported_files["take_qa_scorecard_csv"] = str(p.resolve())
        elif kind == "rough-cut":
            p = out_dir / "rough_cut_assembly.sh"
            p.write_text(generate_rough_cut_assembly_script(manifest, bible, fps=args.fps), encoding="utf-8")
            p.chmod(0o755)
            exported_files["rough_cut_assembly_sh"] = str(p.resolve())

    def _write_treatment_artifact(kind: str) -> None:
        from omni_director.tools.pitch_treatment import (
            compile_pitch_treatment,
            export_treatment_brief_md,
            export_treatment_lookbook_html,
            export_treatment_manifest_json,
        )
        manifest = getattr(bible, "master_pitch_treatment", None) or compile_pitch_treatment(bible)
        if kind == "lookbook":
            p = out_dir / "director_treatment_lookbook.html"
            p.write_text(export_treatment_lookbook_html(manifest, bible), encoding="utf-8")
            exported_files["director_treatment_lookbook_html"] = str(p.resolve())
        elif kind == "treatment-md":
            p = out_dir / "director_treatment_brief.md"
            p.write_text(export_treatment_brief_md(manifest), encoding="utf-8")
            exported_files["director_treatment_brief_md"] = str(p.resolve())
        elif kind == "treatment-json":
            p = out_dir / "pitch_treatment_manifest.json"
            p.write_text(export_treatment_manifest_json(manifest), encoding="utf-8")
            exported_files["pitch_treatment_manifest_json"] = str(p.resolve())

    def _write_imf_dcp_artifact(kind: str) -> None:
        from omni_director.tools.imf_dcp_packager import (
            compile_imf_dcp_manifest,
            export_dcp_cpl_spec_md,
            export_imf_assetmap_xml,
            export_imf_cpl_xml,
            export_imf_pkl_xml,
        )
        manifest = getattr(bible, "master_imf_dcp", None) or compile_imf_dcp_manifest(bible)
        if kind == "imf-assetmap":
            p = out_dir / "ASSETMAP.xml"
            p.write_text(export_imf_assetmap_xml(manifest), encoding="utf-8")
            exported_files["assetmap_xml"] = str(p.resolve())
        elif kind == "imf-pkl":
            p = out_dir / "PKL.xml"
            p.write_text(export_imf_pkl_xml(manifest), encoding="utf-8")
            exported_files["pkl_xml"] = str(p.resolve())
        elif kind == "imf-cpl":
            p = out_dir / "CPL_master.xml"
            p.write_text(export_imf_cpl_xml(manifest), encoding="utf-8")
            exported_files["cpl_master_xml"] = str(p.resolve())
        elif kind == "dcp-spec":
            p = out_dir / "dcp_cpl_spec.md"
            p.write_text(export_dcp_cpl_spec_md(manifest, bible), encoding="utf-8")
            exported_files["dcp_cpl_spec_md"] = str(p.resolve())

    def _write_voice_ducking_artifact(kind: str) -> None:
        from omni_director.tools.voice_ducking import (
            compile_voice_ducking_manifest,
            export_adr_viseme_md,
            export_stem_ducking_csv,
            export_voice_casting_json,
        )
        manifest = getattr(bible, "master_voice_ducking", None) or compile_voice_ducking_manifest(bible)
        if kind == "voice-cast":
            p = out_dir / "voice_casting_script.json"
            p.write_text(export_voice_casting_json(manifest), encoding="utf-8")
            exported_files["voice_casting_script_json"] = str(p.resolve())
        elif kind == "ducking-csv":
            p = out_dir / "stem_ducking_automation.csv"
            p.write_text(export_stem_ducking_csv(manifest, fps=args.fps), encoding="utf-8")
            exported_files["stem_ducking_automation_csv"] = str(p.resolve())
        elif kind == "viseme-md":
            p = out_dir / "adr_viseme_timing.md"
            p.write_text(export_adr_viseme_md(manifest, bible), encoding="utf-8")
            exported_files["adr_viseme_timing_md"] = str(p.resolve())

    def _write_color_scopes_artifact(kind: str) -> None:
        from omni_director.tools.color_scopes import (
            compile_color_scopes_manifest,
            export_color_scopes_json,
            export_finishing_scopes_qc_md,
            export_shot_match_cdl_csv,
        )
        manifest = getattr(bible, "master_color_scopes", None) or compile_color_scopes_manifest(bible)
        if kind == "scopes-json":
            p = out_dir / "color_continuity_scopes.json"
            p.write_text(export_color_scopes_json(manifest), encoding="utf-8")
            exported_files["color_continuity_scopes_json"] = str(p.resolve())
        elif kind == "shot-match-csv":
            p = out_dir / "shot_match_cdl_deltas.csv"
            p.write_text(export_shot_match_cdl_csv(manifest), encoding="utf-8")
            exported_files["shot_match_cdl_deltas_csv"] = str(p.resolve())
        elif kind == "scopes-md":
            p = out_dir / "finishing_scopes_qc.md"
            p.write_text(export_finishing_scopes_qc_md(manifest, bible), encoding="utf-8")
            exported_files["finishing_scopes_qc_md"] = str(p.resolve())

    def _write_archive_vault_artifact(kind: str) -> None:
        from omni_director.tools.archive_vault import (
            compile_archive_vault_manifest,
            export_agency_delivery_readme_md,
            export_archive_vault_json,
            export_bag_info_txt,
            export_manifest_sha256_txt,
        )
        manifest = getattr(bible, "master_archive_vault", None) or compile_archive_vault_manifest(
            bible, output_dir=out_dir
        )
        if kind == "vault-json":
            p = out_dir / "archive_vault_manifest.json"
            p.write_text(export_archive_vault_json(manifest), encoding="utf-8")
            exported_files["archive_vault_manifest_json"] = str(p.resolve())
        elif kind == "bag-info":
            p = out_dir / "bag-info.txt"
            p.write_text(export_bag_info_txt(manifest, bible), encoding="utf-8")
            exported_files["bag_info_txt"] = str(p.resolve())
        elif kind == "bag-manifest":
            p = out_dir / "manifest-sha256.txt"
            p.write_text(export_manifest_sha256_txt(manifest), encoding="utf-8")
            exported_files["manifest_sha256_txt"] = str(p.resolve())
        elif kind == "delivery-readme":
            p = out_dir / "agency_delivery_readme.md"
            p.write_text(export_agency_delivery_readme_md(manifest, bible), encoding="utf-8")
            exported_files["agency_delivery_readme_md"] = str(p.resolve())

    if fmt == "all":
        exported_files.update(export_all_nle_artifacts(bible, out_dir, fps=args.fps))
        srt_path = out_dir / "subtitles.srt"
        vtt_path = out_dir / "subtitles.vtt"
        srt_path.write_text(compile_subtitles_srt(bible, fps=args.fps), encoding="utf-8")
        vtt_path.write_text(compile_subtitles_vtt(bible), encoding="utf-8")
        exported_files["srt"] = str(srt_path.resolve())
        exported_files["vtt"] = str(vtt_path.resolve())
        if baseline_path is not None:
            from omni_director.tools.pitch_treatment import (
                diff_production_bibles,
                export_bible_revision_diff_json,
                export_bible_revision_diff_md,
            )
            diff_report = diff_production_bibles(baseline_path, bible)
            diff_json_path = out_dir / "bible_revision_diff.json"
            diff_md_path = out_dir / "bible_revision_diff.md"
            diff_json_path.write_text(export_bible_revision_diff_json(diff_report), encoding="utf-8")
            diff_md_path.write_text(export_bible_revision_diff_md(diff_report), encoding="utf-8")
            exported_files["bible_revision_diff_json"] = str(diff_json_path.resolve())
            exported_files["bible_revision_diff_md"] = str(diff_md_path.resolve())
    elif fmt == "edl":
        p = out_dir / "timeline.edl"
        p.write_text(export_cmx3600_edl(bible, fps=args.fps), encoding="utf-8")
        exported_files["edl"] = str(p.resolve())
    elif fmt == "fcpxml":
        p = out_dir / "sequence.fcpxml"
        p.write_text(export_fcpxml(bible, fps=args.fps), encoding="utf-8")
        exported_files["fcpxml"] = str(p.resolve())
    elif fmt == "csv":
        p = out_dir / "shot_list.csv"
        p.write_text(export_shot_list_csv(bible, fps=args.fps), encoding="utf-8")
        exported_files["csv"] = str(p.resolve())
    elif fmt == "md":
        p = out_dir / "call_sheet.md"
        p.write_text(export_production_callsheet_md(bible), encoding="utf-8")
        exported_files["md"] = str(p.resolve())
    elif fmt == "srt":
        p = out_dir / "subtitles.srt"
        p.write_text(compile_subtitles_srt(bible, fps=args.fps), encoding="utf-8")
        exported_files["srt"] = str(p.resolve())
    elif fmt == "vtt":
        p = out_dir / "subtitles.vtt"
        p.write_text(compile_subtitles_vtt(bible), encoding="utf-8")
        exported_files["vtt"] = str(p.resolve())
    elif fmt == "cdl":
        p = out_dir / "production_grade.cdl"
        export_asc_cdl_file(bible, p)
        exported_files["cdl"] = str(p.resolve())
    elif fmt == "stems":
        p = out_dir / "audio_stems_manifest.json"
        export_audio_stems_file(bible, p)
        exported_files["stems"] = str(p.resolve())
    elif fmt == "lens":
        p = out_dir / "lens_package.csv"
        export_lens_metadata_file(bible, p)
        exported_files["lens"] = str(p.resolve())
    elif fmt == "vp":
        vp_files = export_virtual_production_bundle(bible, out_dir)
        exported_files.update(vp_files)
    elif fmt == "moco":
        moco_files = export_moco_bundle(bible, out_dir)
        exported_files.update(moco_files)
    elif fmt == "lighting":
        lighting_files = export_lighting_bundle(bible, out_dir)
        exported_files.update(lighting_files)
    elif fmt == "dof":
        dof_files = export_dof_bundle(bible, out_dir)
        exported_files.update(dof_files)
    elif fmt == "lut":
        lut_files = export_lut_bundle(bible, out_dir)
        exported_files.update(lut_files)
    elif fmt == "spatial":
        spatial_files = export_spatial_audio_bundle(bible, out_dir)
        exported_files.update(spatial_files)
    elif fmt == "vfx":
        vfx_files = export_vfx_compositing_bundle(bible, out_dir)
        exported_files.update(vfx_files)
    elif fmt == "hdr":
        from omni_director.tools.hdr_signal import export_hdr_bundle
        hdr_files = export_hdr_bundle(bible, out_dir)
        exported_files.update(hdr_files)
    elif fmt == "stripboard":
        from omni_director.tools.stripboard_scheduler import export_stripboard_bundle
        stripboard_files = export_stripboard_bundle(bible, out_dir)
        exported_files.update(stripboard_files)
    elif fmt == "film":
        film_spec = getattr(bible, "master_film_emulation", None) or getattr(bible, "film_emulation", None) or synthesize_default_film_stock()
        film_files = export_film_emulation_bundle(film_spec, out_dir, bible)
        exported_files.update(film_files)
    elif fmt == "slate":
        slate_spec = getattr(bible, "master_slate_spec", None) or getattr(bible, "slate_spec", None) or synthesize_default_slate_spec(bible)
        slate_files = export_slate_bundle(slate_spec, out_dir, bible)
        exported_files.update(slate_files)
    elif fmt == "drone":
        drone_files = export_drone_flight_bundle(bible, out_dir)
        exported_files.update(drone_files)
    elif fmt == "aicp":
        aicp_files = export_aicp_budget_bundle(bible, out_dir)
        exported_files.update(aicp_files)
    elif fmt == "reframe":
        reframe_files = export_reframe_bundle(bible, out_dir)
        exported_files.update(reframe_files)
    elif fmt == "qc":
        qc_files = export_broadcast_qc_bundle(bible, out_dir)
        exported_files.update(qc_files)
    elif fmt == "continuity":
        continuity_files = export_continuity_bundle(bible, out_dir)
        exported_files.update(continuity_files)
    elif fmt == "review":
        review_files = export_review_bundle(bible, out_dir, fps=args.fps)
        exported_files.update(review_files)
    elif fmt == "c2pa":
        from omni_director.tools.c2pa_provenance import export_c2pa_bundle
        c2pa_files = export_c2pa_bundle(bible, out_dir)
        exported_files.update(c2pa_files)
    elif fmt == "safety":
        from omni_director.tools.safety_risk import export_safety_bundle
        safety_files = export_safety_bundle(bible, out_dir)
        exported_files.update(safety_files)
    elif fmt == "i18n":
        from omni_director.tools.localization_adr import export_localization_bundle
        i18n_files = export_localization_bundle(bible, out_dir)
        exported_files.update(i18n_files)
    elif fmt == "spotting":
        from omni_director.tools.editorial_spotting import export_spotting_bundle
        spotting_files = export_spotting_bundle(bible, out_dir, fps=args.fps)
        exported_files.update(spotting_files)
    elif fmt == "s3d":
        from omni_director.tools.stereoscopic_3d import export_s3d_bundle
        s3d_files = export_s3d_bundle(bible, out_dir)
        exported_files.update(s3d_files)
    elif fmt in ("ad", "ad-vtt"):
        from omni_director.tools.accessibility_ad import export_accessibility_bundle
        ad_files = export_accessibility_bundle(bible, out_dir)
        exported_files.update(ad_files)
    elif fmt == "art-dept":
        from omni_director.tools.wardrobe_props import export_wardrobe_prop_bundle
        art_files = export_wardrobe_prop_bundle(bible, out_dir)
        exported_files.update(art_files)
    elif fmt == "economics":
        from omni_director.tools.render_economics import export_render_economics_bundle
        econ_files = export_render_economics_bundle(bible, out_dir)
        exported_files.update(econ_files)
    elif fmt == "motion-graphics":
        from omni_director.tools.motion_graphics import export_motion_graphics_bundle
        gfx_files = export_motion_graphics_bundle(bible, out_dir, fps=args.fps)
        exported_files.update({k: str(Path(v).resolve()) for k, v in gfx_files.items()})
    elif fmt in ("mogrt-json", "supers-ass", "endcard-md"):
        _write_motion_graphics_artifact(fmt)
    elif fmt == "coherence":
        from omni_director.tools.otio_coherence import export_otio_coherence_bundle
        otio_files = export_otio_coherence_bundle(bible, out_dir, fps=args.fps)
        exported_files.update({k: str(Path(v).resolve()) for k, v in otio_files.items()})
    elif fmt in ("otio", "coherence-json", "coherence-md"):
        _write_otio_coherence_artifact(fmt)
    elif fmt == "render-jobs":
        from omni_director.tools.render_orchestrator import export_render_jobs_bundle
        rj_files = export_render_jobs_bundle(bible, out_dir, fps=args.fps)
        exported_files.update({k: str(Path(v).resolve()) for k, v in rj_files.items()})
    elif fmt in ("render-manifest", "take-qa", "rough-cut"):
        _write_render_jobs_artifact(fmt)
    elif fmt == "treatment":
        from omni_director.tools.pitch_treatment import export_pitch_treatment_bundle
        pt_files = export_pitch_treatment_bundle(bible, out_dir, baseline_bible=baseline_path)
        exported_files.update({k: str(Path(v).resolve()) for k, v in pt_files.items()})
    elif fmt in ("lookbook", "treatment-md", "treatment-json"):
        _write_treatment_artifact(fmt)
    elif fmt == "imf-dcp":
        from omni_director.tools.imf_dcp_packager import export_imf_dcp_bundle
        imf_files = export_imf_dcp_bundle(bible, out_dir)
        exported_files.update({k: str(Path(v).resolve()) for k, v in imf_files.items()})
    elif fmt in ("imf-assetmap", "imf-pkl", "imf-cpl", "dcp-spec"):
        _write_imf_dcp_artifact(fmt)
    elif fmt == "voice-ducking":
        from omni_director.tools.voice_ducking import export_voice_ducking_bundle
        vd_files = export_voice_ducking_bundle(bible, out_dir, fps=args.fps)
        exported_files.update({k: str(Path(v).resolve()) for k, v in vd_files.items()})
    elif fmt in ("voice-cast", "ducking-csv", "viseme-md"):
        _write_voice_ducking_artifact(fmt)
    elif fmt == "color-scopes":
        from omni_director.tools.color_scopes import export_color_scopes_bundle
        cs_files = export_color_scopes_bundle(bible, out_dir)
        exported_files.update({k: str(Path(v).resolve()) for k, v in cs_files.items()})
    elif fmt in ("scopes-json", "shot-match-csv", "scopes-md"):
        _write_color_scopes_artifact(fmt)
    elif fmt == "archive-vault":
        from omni_director.tools.archive_vault import export_archive_vault_bundle
        av_files = export_archive_vault_bundle(bible, out_dir)
        exported_files.update({k: str(Path(v).resolve()) for k, v in av_files.items()})
    elif fmt in ("bag-info", "bag-manifest", "vault-json", "delivery-readme"):
        _write_archive_vault_artifact(fmt)

    # Process explicit granular artifact flags if requested
    if args.dof_chart:
        p = out_dir / "dof_chart.json"
        export_optical_chart_json(bible, p)
        exported_files["dof_chart"] = str(p.resolve())
    if args.cue_sheet:
        p = out_dir / "focus_puller_cue_sheet.csv"
        export_focus_puller_cue_sheet(bible, p)
        exported_files["cue_sheet"] = str(p.resolve())
    if args.cube_lut:
        p = out_dir / "production_look.cube"
        export_master_cube_lut(bible, p)
        exported_files["cube_lut"] = str(p.resolve())
    if args.dit_manifest:
        p = out_dir / "dit_cart_manifest.json"
        export_dit_cart_manifest_json(bible, p)
        exported_files["dit_manifest"] = str(p.resolve())
    if args.spatial_adm:
        p = out_dir / "spatial_audio_adm.json"
        export_adm_spatial_json(bible, p)
        exported_files["spatial_adm"] = str(p.resolve())
    if args.ambisonic_csv:
        p = out_dir / "ambisonic_b_format.csv"
        export_ambisonic_track_csv(bible, p)
        exported_files["ambisonic_csv"] = str(p.resolve())
    if args.webaudio_config:
        spatial_spec = getattr(bible, "master_spatial_audio", None) or synthesize_default_spatial_audio(bible)
        p = out_dir / "webaudio_spatial_config.json"
        p.write_text(json.dumps(export_web_audio_spatial_config(spatial_spec), indent=2), encoding="utf-8")
        exported_files["webaudio_config"] = str(p.resolve())
    if args.vfx_manifest:
        p = out_dir / "openexr_channels.json"
        export_openexr_channel_manifest_json(bible, p)
        exported_files["openexr_channels"] = str(p.resolve())
    if args.cryptomatte_sidecar:
        p = out_dir / "cryptomatte_manifest.json"
        export_cryptomatte_sidecar_json(bible, p)
        exported_files["cryptomatte_manifest"] = str(p.resolve())
    if args.nuke_script:
        p = out_dir / "nuke_composite.nk"
        export_nuke_comp_script(bible, p)
        exported_files["nuke_script"] = str(p.resolve())
    if args.hdr_json:
        p = out_dir / "hdr10_metadata.json"
        p.write_text(export_hdr10_metadata_json(bible), encoding="utf-8")
        exported_files["hdr_json"] = str(p.resolve())
    if args.hlg_xml:
        p = out_dir / "hlg_broadcast.xml"
        p.write_text(export_hlg_broadcast_xml(bible), encoding="utf-8")
        exported_files["hlg_xml"] = str(p.resolve())
    if args.resolve_hdr:
        p = out_dir / "resolve_hdr_rcm.xml"
        export_resolve_hdr_xml(bible, p)
        exported_files["resolve_hdr"] = str(p.resolve())
    if args.movie_magic_xml or args.stripboard_csv or args.dood_csv:
        schedule = getattr(bible, "master_stripboard_schedule", None) or getattr(bible, "stripboard_schedule", None) or generate_stripboard_schedule(bible)
        if args.movie_magic_xml:
            p = out_dir / "movie_magic_schedule.xml"
            export_movie_magic_xml(schedule, p)
            exported_files["movie_magic_xml"] = str(p.resolve())
        if args.stripboard_csv:
            p = out_dir / "stripboard_schedule.csv"
            export_stripboard_csv(schedule, p)
            exported_files["stripboard_csv"] = str(p.resolve())
        if args.dood_csv:
            p = out_dir / "dood_matrix.csv"
            export_dood_csv(schedule, p)
            exported_files["dood_csv"] = str(p.resolve())
    if args.film_dctl:
        film_spec = getattr(bible, "master_film_emulation", None) or getattr(bible, "film_emulation", None) or synthesize_default_film_stock()
        dctl_code = generate_davinci_dctl_shader(film_spec)
        p = out_dir / "film_emulation.dctl"
        p_shader = out_dir / "film_stock_shader.dctl"
        p.write_text(dctl_code, encoding="utf-8")
        p_shader.write_text(dctl_code, encoding="utf-8")
        exported_files["film_dctl"] = str(p.resolve())
        exported_files["film_stock_shader_dctl"] = str(p_shader.resolve())
    if args.film_ale:
        p = out_dir / "film_stock.ale"
        export_film_stock_ale(bible, p)
        exported_files["film_ale"] = str(p.resolve())
    if args.mhl_xml:
        slate_spec = getattr(bible, "master_slate_spec", None) or getattr(bible, "slate_spec", None) or synthesize_default_slate_spec(bible)
        p = out_dir / "asc_mhl_manifest.xml"
        manifest = getattr(slate_spec, "asc_mhl", None)
        if manifest:
            p.write_text(generate_asc_mhl_xml(manifest), encoding="utf-8")
        else:
            from omni_director.schemas import AscMhlManifestSpec
            from datetime import datetime, timezone
            default_m = AscMhlManifestSpec(
                project_title=bible.project_title,
                creation_date=datetime.now(timezone.utc).isoformat()
            )
            p.write_text(generate_asc_mhl_xml(default_m), encoding="utf-8")
        exported_files["mhl_xml"] = str(p.resolve())
    if args.sound_ale:
        p = out_dir / "sound_sync.ale"
        p.write_text(generate_sound_sync_ale(bible), encoding="utf-8")
        exported_files["sound_ale"] = str(p.resolve())
    if args.slate_csv:
        p = out_dir / "clapper_slate_log.csv"
        p.write_text(generate_clapper_slate_log_csv(bible), encoding="utf-8")
        exported_files["slate_csv"] = str(p.resolve())
    if args.drone_kml:
        drone_spec = getattr(bible, "master_drone_spec", None) or getattr(bible, "drone_spec", None) or synthesize_default_drone_flight()
        p = out_dir / "flight_path.kml"
        p.write_text(generate_drone_flight_kml(drone_spec, bible.project_title), encoding="utf-8")
        exported_files["drone_kml"] = str(p.resolve())
    if args.drone_gpx:
        drone_spec = getattr(bible, "master_drone_spec", None) or getattr(bible, "drone_spec", None) or synthesize_default_drone_flight()
        p = out_dir / "flight_waypoints.gpx"
        p.write_text(generate_drone_flight_gpx(drone_spec, bible.project_title), encoding="utf-8")
        exported_files["drone_gpx"] = str(p.resolve())
    if args.aicp_csv:
        aicp_bid = getattr(bible, "master_aicp_bid", None) or getattr(bible, "aicp_bid", None) or synthesize_default_aicp_bid(bible)
        p = out_dir / "aicp_bid_sheet.csv"
        p.write_text(generate_aicp_bid_sheet_csv(aicp_bid), encoding="utf-8")
        exported_files["aicp_csv"] = str(p.resolve())
    if args.aicp_json:
        aicp_bid = getattr(bible, "master_aicp_bid", None) or getattr(bible, "aicp_bid", None) or synthesize_default_aicp_bid(bible)
        p = out_dir / "aicp_bid_manifest.json"
        p.write_text(generate_aicp_bid_manifest_json(aicp_bid), encoding="utf-8")
        exported_files["aicp_json"] = str(p.resolve())
    if args.reframe_csv:
        p = out_dir / "reframe_crop_matrix.csv"
        p.write_text(generate_reframe_matrix_csv(bible), encoding="utf-8")
        exported_files["reframe_csv"] = str(p.resolve())
    if args.cutdown_edl:
        from omni_director.schemas import CutdownFormatType
        p15 = out_dir / "cutdown_15s.edl"
        p06 = out_dir / "cutdown_06s.edl"
        p15.write_text(generate_cutdown_edl(bible, CutdownFormatType.CUTDOWN_15S, fps=args.fps), encoding="utf-8")
        p06.write_text(generate_cutdown_edl(bible, CutdownFormatType.BUMPER_06S, fps=args.fps), encoding="utf-8")
        exported_files["cutdown_15s_edl"] = str(p15.resolve())
        exported_files["cutdown_06s_edl"] = str(p06.resolve())
    if args.reframe_fcpxml:
        p = out_dir / "reframe_9x16.fcpxml"
        p.write_text(generate_reframe_fcpxml(bible, fps=args.fps), encoding="utf-8")
        exported_files["reframe_fcpxml"] = str(p.resolve())
    if args.reframe_json:
        p = out_dir / "delivery_reframe_manifest.json"
        p.write_text(generate_reframe_manifest_json(bible), encoding="utf-8")
        exported_files["reframe_json"] = str(p.resolve())
    if args.qc_cert:
        p = out_dir / "broadcast_qc_certificate.md"
        p.write_text(generate_qc_certificate_md(bible), encoding="utf-8")
        exported_files["qc_cert"] = str(p.resolve())
    if args.clearance_csv:
        p = out_dir / "rights_clearance_matrix.csv"
        p.write_text(generate_clearance_matrix_csv(bible), encoding="utf-8")
        exported_files["clearance_csv"] = str(p.resolve())
    if args.qc_json:
        p = out_dir / "broadcast_qc_manifest.json"
        p.write_text(generate_qc_manifest_json(bible), encoding="utf-8")
        exported_files["qc_json"] = str(p.resolve())
    if args.continuity_csv:
        p = out_dir / "continuity_log.csv"
        p.write_text(generate_continuity_log_csv(bible), encoding="utf-8")
        exported_files["continuity_csv"] = str(p.resolve())
    if args.blocking_svg:
        p = out_dir / "blocking_floorplan.svg"
        p.write_text(generate_blocking_floorplan_svg(bible), encoding="utf-8")
        exported_files["blocking_svg"] = str(p.resolve())
    if args.continuity_json:
        p = out_dir / "continuity_manifest.json"
        p.write_text(generate_continuity_manifest_json(bible), encoding="utf-8")
        exported_files["continuity_json"] = str(p.resolve())
    if args.review_edl:
        p = out_dir / "review_markers.edl"
        p.write_text(generate_resolve_marker_edl(bible, fps=args.fps), encoding="utf-8")
        exported_files["review_edl"] = str(p.resolve())
    if args.review_fcpxml:
        p = out_dir / "review_markers.fcpxml"
        p.write_text(generate_review_fcpxml_markers(bible, fps=args.fps), encoding="utf-8")
        exported_files["review_fcpxml"] = str(p.resolve())
    if args.review_json:
        p = out_dir / "review_notes_frameio.json"
        p.write_text(generate_frameio_review_json(bible), encoding="utf-8")
        exported_files["review_json"] = str(p.resolve())
    if args.review_csv:
        p = out_dir / "review_notes.csv"
        p.write_text(generate_review_notes_csv(bible), encoding="utf-8")
        exported_files["review_csv"] = str(p.resolve())
    if args.signoff_md:
        p = out_dir / "client_signoff_report.md"
        p.write_text(generate_client_signoff_md(bible), encoding="utf-8")
        exported_files["signoff_md"] = str(p.resolve())
    if args.c2pa_json or args.disclosure_md or args.likeness_csv:
        from omni_director.tools.c2pa_provenance import (
            generate_ai_disclosure_md,
            generate_c2pa_manifest_json,
            generate_likeness_consent_csv,
        )
        if args.c2pa_json:
            p = out_dir / "c2pa_manifest.json"
            p.write_text(generate_c2pa_manifest_json(bible), encoding="utf-8")
            exported_files["c2pa_json"] = str(p.resolve())
        if args.disclosure_md:
            p = out_dir / "ai_disclosure_certificate.md"
            p.write_text(generate_ai_disclosure_md(bible), encoding="utf-8")
            exported_files["disclosure_md"] = str(p.resolve())
        if args.likeness_csv:
            p = out_dir / "likeness_consent_ledger.csv"
            p.write_text(generate_likeness_consent_csv(bible), encoding="utf-8")
            exported_files["likeness_csv"] = str(p.resolve())
    if args.safety_md or args.safety_csv or args.safety_json:
        from omni_director.tools.safety_risk import (
            generate_safety_bulletin_md,
            generate_safety_jsa_csv,
            generate_safety_manifest_json,
        )
        if args.safety_md:
            p = out_dir / "safety_bulletin.md"
            p.write_text(generate_safety_bulletin_md(bible), encoding="utf-8")
            exported_files["safety_md"] = str(p.resolve())
        if args.safety_csv:
            p = out_dir / "safety_jsa_matrix.csv"
            p.write_text(generate_safety_jsa_csv(bible), encoding="utf-8")
            exported_files["safety_csv"] = str(p.resolve())
        if args.safety_json:
            p = out_dir / "safety_risk_manifest.json"
            p.write_text(generate_safety_manifest_json(bible), encoding="utf-8")
            exported_files["safety_json"] = str(p.resolve())
    if args.i18n_json or args.adr_csv or args.ttml:
        from omni_director.tools.localization_adr import (
            export_adr_cue_sheet_csv,
            export_imsc1_ttml,
            export_localization_manifest_json,
        )
        if args.i18n_json:
            p = out_dir / "localization_manifest.json"
            export_localization_manifest_json(bible, p)
            exported_files["localization_manifest_json"] = str(p.resolve())
        if args.adr_csv:
            p = out_dir / "adr_cue_sheet.csv"
            export_adr_cue_sheet_csv(bible, p)
            exported_files["adr_cue_sheet_csv"] = str(p.resolve())
        if args.ttml:
            p = out_dir / "subtitles_localized.ttml"
            export_imsc1_ttml(bible, p, locale=target_locales[0] if target_locales else None)
            exported_files["subtitles_localized_ttml"] = str(p.resolve())
    if args.spotting_json or args.spotting_csv or args.spotting_md or args.split_edl:
        from omni_director.tools.editorial_spotting import (
            export_split_edit_edl,
            export_spotting_cue_sheet_csv,
            export_spotting_manifest_json,
            export_spotting_sheet_md,
        )
        if args.spotting_json:
            p = out_dir / "spotting_manifest.json"
            export_spotting_manifest_json(bible, p, fps=args.fps)
            exported_files["spotting_manifest_json"] = str(p.resolve())
        if args.spotting_csv:
            p = out_dir / "spotting_cue_sheet.csv"
            export_spotting_cue_sheet_csv(bible, p, fps=args.fps)
            exported_files["spotting_cue_sheet_csv"] = str(p.resolve())
        if args.spotting_md:
            p = out_dir / "spotting_sheet.md"
            export_spotting_sheet_md(bible, p, fps=args.fps)
            exported_files["spotting_sheet_md"] = str(p.resolve())
        if args.split_edl:
            p = out_dir / "timeline_split_edits.edl"
            export_split_edit_edl(bible, p, fps=args.fps)
            exported_files["timeline_split_edits_edl"] = str(p.resolve())
    if args.s3d_csv or args.spatial_manifest:
        from omni_director.tools.stereoscopic_3d import export_s3d_csv, export_spatial_manifest_json
        if args.s3d_csv:
            p = out_dir / "s3d_parallax_log.csv"
            export_s3d_csv(bible, p)
            exported_files["s3d_csv"] = str(p.resolve())
        if args.spatial_manifest:
            p = out_dir / "spatial_video_manifest.json"
            export_spatial_manifest_json(bible, p)
            exported_files["spatial_manifest"] = str(p.resolve())
    if args.ad_vtt or args.ad_csv or args.ad_manifest:
        from omni_director.tools.accessibility_ad import (
            export_accessibility_manifest_json,
            export_ad_script_csv,
            export_ad_vtt,
        )
        if args.ad_vtt:
            p = out_dir / "subtitles_ad.vtt"
            export_ad_vtt(bible, p)
            exported_files["ad_vtt"] = str(p.resolve())
        if args.ad_csv:
            p = out_dir / "ad_script_cue_sheet.csv"
            export_ad_script_csv(bible, p)
            exported_files["ad_csv"] = str(p.resolve())
        if args.ad_manifest:
            p = out_dir / "accessibility_ad_manifest.json"
            export_accessibility_manifest_json(bible, p)
            exported_files["ad_json"] = str(p.resolve())
    if args.art_dept or args.wardrobe_json or args.prop_csv or args.pull_list_md:
        from omni_director.tools.wardrobe_props import export_wardrobe_prop_bundle
        if args.art_dept:
            exported_files.update(
                {k: str(Path(v).resolve()) for k, v in export_wardrobe_prop_bundle(bible, out_dir).items()}
            )
        else:
            with tempfile.TemporaryDirectory() as tmp_art_dir:
                bundle_paths = export_wardrobe_prop_bundle(bible, tmp_art_dir)
                flag_map = [
                    (args.wardrobe_json, "wardrobe_prop_bible_json", "wardrobe_prop_bible.json"),
                    (args.prop_csv, "prop_continuity_matrix_csv", "prop_continuity_matrix.csv"),
                    (args.pull_list_md, "art_dept_pull_list_md", "art_dept_pull_list.md"),
                ]
                for enabled, key, filename in flag_map:
                    if enabled and key in bundle_paths:
                        dest = out_dir / filename
                        shutil.copy2(bundle_paths[key], dest)
                        exported_files[key] = str(dest.resolve())
    if args.economics or args.economics_json or args.takes_csv or args.compute_md:
        from omni_director.tools.render_economics import export_render_economics_bundle
        if args.economics:
            exported_files.update(
                {k: str(Path(v).resolve()) for k, v in export_render_economics_bundle(bible, out_dir).items()}
            )
        else:
            with tempfile.TemporaryDirectory() as tmp_econ_dir:
                bundle_paths = export_render_economics_bundle(bible, tmp_econ_dir)
                flag_map = [
                    (args.economics_json, "render_economics_manifest_json", "render_economics_manifest.json"),
                    (args.takes_csv, "take_variant_ledger_csv", "take_variant_ledger.csv"),
                    (args.compute_md, "ai_compute_estimate_md", "ai_compute_estimate.md"),
                ]
                for enabled, key, filename in flag_map:
                    if enabled and key in bundle_paths:
                        dest = out_dir / filename
                        shutil.copy2(bundle_paths[key], dest)
                        exported_files[key] = str(dest.resolve())
    if args.motion_graphics and fmt not in ("all", "motion-graphics"):
        from omni_director.tools.motion_graphics import export_motion_graphics_bundle
        exported_files.update(
            {k: str(Path(v).resolve()) for k, v in export_motion_graphics_bundle(bible, out_dir, fps=args.fps).items()}
        )
    elif not args.motion_graphics and fmt not in ("all", "motion-graphics"):
        if args.mogrt_json and fmt != "mogrt-json":
            _write_motion_graphics_artifact("mogrt-json")
        if args.supers_ass and fmt != "supers-ass":
            _write_motion_graphics_artifact("supers-ass")
        if args.endcard_md and fmt != "endcard-md":
            _write_motion_graphics_artifact("endcard-md")
    if args.coherence and fmt not in ("all", "coherence"):
        from omni_director.tools.otio_coherence import export_otio_coherence_bundle
        exported_files.update(
            {k: str(Path(v).resolve()) for k, v in export_otio_coherence_bundle(bible, out_dir, fps=args.fps).items()}
        )
    elif not args.coherence and fmt not in ("all", "coherence"):
        if args.otio and fmt != "otio":
            _write_otio_coherence_artifact("otio")
        if args.coherence_json and fmt != "coherence-json":
            _write_otio_coherence_artifact("coherence-json")
        if args.coherence_md and fmt != "coherence-md":
            _write_otio_coherence_artifact("coherence-md")
    if args.render_jobs and fmt not in ("all", "render-jobs"):
        from omni_director.tools.render_orchestrator import export_render_jobs_bundle
        exported_files.update(
            {k: str(Path(v).resolve()) for k, v in export_render_jobs_bundle(bible, out_dir, fps=args.fps).items()}
        )
    elif not args.render_jobs and fmt not in ("all", "render-jobs"):
        if args.render_manifest and fmt != "render-manifest":
            _write_render_jobs_artifact("render-manifest")
        if args.take_qa_csv and fmt != "take-qa":
            _write_render_jobs_artifact("take-qa")
        if args.assembly_sh and fmt != "rough-cut":
            _write_render_jobs_artifact("rough-cut")
    if args.treatment and fmt not in ("all", "treatment"):
        from omni_director.tools.pitch_treatment import export_pitch_treatment_bundle
        exported_files.update(
            {k: str(Path(v).resolve()) for k, v in export_pitch_treatment_bundle(bible, out_dir, baseline_bible=baseline_path).items()}
        )
    elif not args.treatment and fmt not in ("all", "treatment"):
        if args.treatment_html and fmt != "lookbook":
            _write_treatment_artifact("lookbook")
        if args.treatment_md and fmt != "treatment-md":
            _write_treatment_artifact("treatment-md")
        if args.treatment_json and fmt != "treatment-json":
            _write_treatment_artifact("treatment-json")
    if args.imf_dcp and fmt not in ("all", "imf-dcp"):
        from omni_director.tools.imf_dcp_packager import export_imf_dcp_bundle
        exported_files.update(
            {k: str(Path(v).resolve()) for k, v in export_imf_dcp_bundle(bible, out_dir).items()}
        )
    elif not args.imf_dcp and fmt not in ("all", "imf-dcp"):
        if args.imf_assetmap and fmt != "imf-assetmap":
            _write_imf_dcp_artifact("imf-assetmap")
        if args.imf_pkl and fmt != "imf-pkl":
            _write_imf_dcp_artifact("imf-pkl")
        if args.imf_cpl and fmt != "imf-cpl":
            _write_imf_dcp_artifact("imf-cpl")
        if args.dcp_spec and fmt != "dcp-spec":
            _write_imf_dcp_artifact("dcp-spec")
    if args.voice_ducking and fmt not in ("all", "voice-ducking"):
        from omni_director.tools.voice_ducking import export_voice_ducking_bundle
        exported_files.update(
            {k: str(Path(v).resolve()) for k, v in export_voice_ducking_bundle(bible, out_dir, fps=args.fps).items()}
        )
    elif not args.voice_ducking and fmt not in ("all", "voice-ducking"):
        if args.voice_cast and fmt != "voice-cast":
            _write_voice_ducking_artifact("voice-cast")
        if args.ducking_csv and fmt != "ducking-csv":
            _write_voice_ducking_artifact("ducking-csv")
        if args.viseme_md and fmt != "viseme-md":
            _write_voice_ducking_artifact("viseme-md")
    if args.color_scopes and fmt not in ("all", "color-scopes"):
        from omni_director.tools.color_scopes import export_color_scopes_bundle
        exported_files.update(
            {k: str(Path(v).resolve()) for k, v in export_color_scopes_bundle(bible, out_dir).items()}
        )
    elif not args.color_scopes and fmt not in ("all", "color-scopes"):
        if args.scopes_json and fmt != "scopes-json":
            _write_color_scopes_artifact("scopes-json")
        if args.shot_match_csv and fmt != "shot-match-csv":
            _write_color_scopes_artifact("shot-match-csv")
        if args.scopes_md and fmt != "scopes-md":
            _write_color_scopes_artifact("scopes-md")
    if args.archive_vault and fmt not in ("all", "archive-vault"):
        from omni_director.tools.archive_vault import export_archive_vault_bundle
        exported_files.update(
            {k: str(Path(v).resolve()) for k, v in export_archive_vault_bundle(bible, out_dir).items()}
        )
    elif not args.archive_vault and fmt not in ("all", "archive-vault"):
        if args.bag_info and fmt != "bag-info":
            _write_archive_vault_artifact("bag-info")
        if args.bag_manifest and fmt != "bag-manifest":
            _write_archive_vault_artifact("bag-manifest")
        if args.vault_json and fmt != "vault-json":
            _write_archive_vault_artifact("vault-json")
        if args.delivery_readme and fmt != "delivery-readme":
            _write_archive_vault_artifact("delivery-readme")

    exported_files = {k: str(v) for k, v in exported_files.items()}

    telemetry_path = out_dir / "telemetry.json"
    if telemetry_path.is_file() or args.refresh_telemetry or fmt == "all":
        from omni_director.telemetry import RuntimeTelemetry
        telemetry_obj: Optional[RuntimeTelemetry] = None
        if telemetry_path.is_file():
            try:
                existing_telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
                if isinstance(existing_telemetry, dict):
                    telemetry_obj = RuntimeTelemetry(**existing_telemetry)
            except Exception:
                telemetry_obj = None
        if telemetry_obj is None:
            telemetry_obj = RuntimeTelemetry(project_title=bible.project_title)
        telemetry_obj.write_manifest(out_dir)

    if args.json:
        print(json.dumps({"project_title": bible.project_title, "exported": exported_files}, indent=2))
    elif HAS_RICH:
        console = Console()
        print_banner()
        console.print(f"[bold green]✓ Exported {len(exported_files)} post-production artifact(s) for '{bible.project_title}':[/bold green]")
        for k, v in exported_files.items():
            console.print(f"  • [bold cyan]{k.upper()}[/bold cyan]: {v}")
    else:
        print(f"Exported {len(exported_files)} artifact(s) for '{bible.project_title}':")
        for k, v in exported_files.items():
            print(f"  - {k}: {v}")

    return 0


def _parse_promote_take_args(raw_values: Optional[List[str]]) -> Dict[int, str]:
    """Parses repeatable or comma-separated SCENE:TAKE overrides into Dict[int, str]."""
    mapping: Dict[int, str] = {}
    for entry in raw_values or []:
        for part in str(entry).split(","):
            item = part.strip()
            if not item:
                continue
            if ":" not in item:
                raise ValueError(f"Invalid --promote-take '{item}': expected SCENE:TAKE (e.g. 1:B or 1:SC01_T2)")
            sc_str, take_str = item.split(":", 1)
            sc_idx = int(sc_str.strip())
            take_id = take_str.strip()
            if sc_idx < 1 or not take_id:
                raise ValueError(f"Invalid --promote-take '{item}': scene index must be >= 1 and take must be non-empty")
            mapping[sc_idx] = take_id
    return mapping


def _parse_retry_scene_args(raw_values: Optional[List[str]]) -> List[int]:
    """Parses repeatable or comma-separated scene indices into a deduplicated List[int]."""
    indices: List[int] = []
    seen: set[int] = set()
    for entry in raw_values or []:
        for part in str(entry).split(","):
            tok = part.strip()
            if not tok:
                continue
            sc_idx = int(tok)
            if sc_idx < 1:
                raise ValueError(f"Invalid --retry-scene '{tok}': scene index must be >= 1")
            if sc_idx not in seen:
                seen.add(sc_idx)
                indices.append(sc_idx)
    return indices


def handle_diff(args_list: List[str]) -> int:
    """Compares two ProductionBible or ProductionBundle JSON files (PM-FEAT-036)."""
    from omni_director.tools.pitch_treatment import (
        diff_production_bibles,
        export_bible_revision_diff_json,
        export_bible_revision_diff_md,
    )

    parser = argparse.ArgumentParser(
        prog="omni diff",
        description="Compare two ProductionBible or ProductionBundle JSON files and emit SHA-256 revision deltas.",
    )
    parser.add_argument("baseline_json", type=str, help="Path to baseline MasterProductionBible or ProductionBundle JSON")
    parser.add_argument("target_json", type=str, help="Path to target MasterProductionBible or ProductionBundle JSON")
    parser.add_argument("--output-dir", "-o", type=str, default=None, help="Optional directory to write bible_revision_diff.json and bible_revision_diff.md")
    parser.add_argument("--json", action="store_true", default=False, help="Emit BibleRevisionDiffReport JSON to stdout")

    args = parser.parse_args(args_list)
    base_path = Path(args.baseline_json)
    targ_path = Path(args.target_json)
    for label, p in (("baseline", base_path), ("target", targ_path)):
        if not p.exists() or not p.is_file():
            print(f"Error: {label} JSON file does not exist at '{p}'", file=sys.stderr)
            return 1

    try:
        diff_report = diff_production_bibles(base_path, targ_path)
    except Exception as exc:
        print(f"Error computing revision diff: {exc}", file=sys.stderr)
        return 1

    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "bible_revision_diff.json").write_text(
            export_bible_revision_diff_json(diff_report), encoding="utf-8"
        )
        (out_dir / "bible_revision_diff.md").write_text(
            export_bible_revision_diff_md(diff_report), encoding="utf-8"
        )
        telemetry_path = out_dir / "telemetry.json"
        if telemetry_path.is_file():
            from omni_director.telemetry import RuntimeTelemetry
            try:
                existing_tel = json.loads(telemetry_path.read_text(encoding="utf-8"))
                tel_obj = RuntimeTelemetry(**existing_tel) if isinstance(existing_tel, dict) else RuntimeTelemetry(project_title=diff_report.target_title)
            except Exception:
                tel_obj = RuntimeTelemetry(project_title=diff_report.target_title)
            tel_obj.write_manifest(out_dir)

    if args.json:
        print(diff_report.model_dump_json(indent=2))
    elif HAS_RICH:
        console = Console()
        print_banner()
        council_delta_str = (
            f"{diff_report.council_score_delta:+.2f}"
            if diff_report.council_score_delta is not None
            else "N/A"
        )
        console.print(
            Panel(
                f"• [bold]Baseline:[/bold] {diff_report.baseline_title} (`{diff_report.baseline_sha256[:16]}`)\n"
                f"• [bold]Target:[/bold] {diff_report.target_title} (`{diff_report.target_sha256[:16]}`)\n"
                f"• [bold]Total Changes:[/bold] {diff_report.total_changes} | "
                f"[bold]Scene Prompt Deltas:[/bold] {diff_report.scene_prompt_deltas_count}\n"
                f"• [bold]AICP Delta:[/bold] ${diff_report.aicp_budget_delta_usd:+,.2f} | "
                f"[bold]Compute Delta:[/bold] ${diff_report.render_compute_delta_usd:+,.4f} | "
                f"[bold]Council Delta:[/bold] {council_delta_str}",
                title="Bible Revision Diff Summary",
                border_style="cyan",
            )
        )
        table = Table(title="Revision Deltas", border_style="magenta")
        table.add_column("Section", style="bold cyan")
        table.add_column("Field", style="white")
        table.add_column("Type", style="yellow")
        table.add_column("Previous", style="dim")
        table.add_column("Current", style="green")
        table.add_column("Severity", style="bold")
        table.add_column("Owner", style="cyan")
        if diff_report.deltas:
            for d in diff_report.deltas:
                table.add_row(
                    d.section,
                    d.field_path,
                    d.change_type,
                    d.previous_value,
                    d.current_value,
                    d.impact_severity,
                    d.department_owner,
                )
        else:
            table.add_row("All", "*", "none", "identical", "identical", "low", "Direction")
        console.print(table)
    else:
        council_delta_str = (
            f"{diff_report.council_score_delta:+.2f}"
            if diff_report.council_score_delta is not None
            else "N/A"
        )
        print(f"Bible Revision Diff: {diff_report.baseline_title} -> {diff_report.target_title}")
        print(f"  Baseline SHA-256: {diff_report.baseline_sha256}")
        print(f"  Target SHA-256:   {diff_report.target_sha256}")
        print(f"  Total Changes:    {diff_report.total_changes}")
        print(f"  Scene Prompt Deltas: {diff_report.scene_prompt_deltas_count}")
        print(f"  AICP Budget Delta:   ${diff_report.aicp_budget_delta_usd:+,.2f}")
        print(f"  Compute Cost Delta:  ${diff_report.render_compute_delta_usd:+,.4f}")
        print(f"  Council Score Delta: {council_delta_str}")
        for d in diff_report.deltas:
            print(
                f"  - [{d.impact_severity.upper()}] {d.section} {d.field_path} ({d.change_type}): "
                f"{d.previous_value} -> {d.current_value} [{d.department_owner}]"
            )

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)

    # Check for version
    if any(arg in args_list for arg in ("--version", "-v")):
        print(f"omni-movie-director {__version__}")
        return 0

    # Route subcommands
    if args_list and args_list[0] == "doctor":
        return handle_doctor(args_list[1:])
    if args_list and args_list[0] == "council":
        return handle_council(args_list[1:])
    if args_list and args_list[0] == "export":
        return handle_export(args_list[1:])
    if args_list and args_list[0] == "diff":
        return handle_diff(args_list[1:])
    if args_list and args_list[0] == "verify-bundle":
        positionals = [a for a in args_list[1:] if not a.startswith("-")]
        flags = [a for a in args_list[1:] if a.startswith("-")]
        verify_target = positionals[0] if positionals else "./output"
        return main(["--verify-bundle", verify_target] + flags)
    if "--doctor" in args_list:
        clean_args = [a for a in args_list if a != "--doctor"]
        return handle_doctor(clean_args)

    # Support 'omni run ...' as well as 'omni ...'
    if args_list and args_list[0] == "run":
        args_list = args_list[1:]

    parser = argparse.ArgumentParser(
        prog="omni-director",
        description="Autonomous ADK 2.0 multi-agent cinematic production suite for Gemini Omni.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Path to input brief file (JSON/text) or inline creative brief string.",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        choices=list(PRESETS.keys()),
        help="Select a pre-compiled golden production bible preset.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Custom user logline or creative brief to direct.",
    )
    parser.add_argument(
        "--bible-file",
        "-b",
        type=str,
        default=None,
        help="Path to an existing MasterProductionBible JSON file to execute directly.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="hybrid",
        choices=["parallel", "extension", "hybrid", "montage", "continuous"],
        help="Storytelling mode: 'parallel', 'extension', or 'hybrid' (default: hybrid).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="./output",
        help="Target output directory for the Dark-Room HTML and bundle JSON (default: ./output).",
    )
    parser.add_argument(
        "--render-video",
        action="store_true",
        default=False,
        help="Attempt live video generation via Gemini Omni (requires GOOGLE_API_KEY/GEMINI_API_KEY).",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=True,
        help="Run deterministic simulation mode without billable API requests (default: True).",
    )
    parser.add_argument(
        "--live",
        dest="dry_run",
        action="store_false",
        help="Run in live API mode with credentials.",
    )
    parser.add_argument(
        "--council",
        action="store_true",
        default=False,
        help="Execute Autonomous Product Council 4-persona audit during production wrap.",
    )
    parser.add_argument(
        "--council-strict",
        "--strict",
        dest="council_strict",
        action="store_true",
        default=False,
        help="Exit code 2 if council audit score < 88.0 or critical findings count > 0.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit JSON bundle and telemetry to stdout.",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List all built-in golden presets and exit.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run system doctor diagnostics and exit.",
    )
    parser.add_argument(
        "--verify-bundle",
        type=str,
        default=None,
        help="Verify SHA-256 artifact checksums of an existing bundle directory",
    )
    parser.add_argument(
        "--export-nle",
        action="store_true",
        default=False,
        help="Export CMX 3600 EDL, FCPXML, CSV shot list, Markdown call sheet, and SRT/VTT subtitles into output-dir.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=24,
        choices=[24, 25, 30, 48, 60],
        help="Frame rate for timecode calculations and NLE exports (default: 24).",
    )
    parser.add_argument(
        "--max-render-usd",
        type=float,
        default=None,
        help="Override maximum live-render compute budget ceiling in USD (overrides cfg.max_render_budget_usd).",
    )
    parser.add_argument(
        "--promote-take",
        action="append",
        default=[],
        help="Promote a specific take for a scene (repeatable or comma-separated SCENE:TAKE, e.g. 1:B or 1:SC01_T2).",
    )
    parser.add_argument(
        "--retry-scene",
        action="append",
        default=[],
        help="Scene index or comma-separated scene indices to retry during render orchestration (e.g. 2 or 1,3).",
    )

    args = parser.parse_args(args_list)

    if args.verify_bundle:
        from omni_director.telemetry import verify_bundle_checksums
        is_valid, errors = verify_bundle_checksums(args.verify_bundle)
        if args.json:
            print(json.dumps({"verified": is_valid, "bundle_dir": args.verify_bundle, "errors": errors}, indent=2))
        elif is_valid:
            if HAS_RICH:
                Console().print(f"[bold green]✓ Bundle artifact verification passed: All SHA-256 checksums match in '{args.verify_bundle}'.[/bold green]")
            else:
                print(f"Bundle artifact verification passed: All SHA-256 checksums match in '{args.verify_bundle}'.")
        else:
            if HAS_RICH:
                console = Console()
                console.print(f"[bold red]✗ Bundle artifact verification failed for '{args.verify_bundle}':[/bold red]")
                for err in errors:
                    console.print(f"  • [yellow]{err}[/yellow]")
            else:
                print(f"Bundle artifact verification failed for '{args.verify_bundle}':", file=sys.stderr)
                for err in errors:
                    print(f"  - {err}", file=sys.stderr)
        return 0 if is_valid else 1

    if args.doctor:
        return handle_doctor(["--output-dir", args.output_dir] + (["--json"] if args.json else []))

    if args.list_presets:
        list_presets()
        return 0

    # Ingest Bible file if provided
    loaded_bible: Optional[MasterProductionBible] = None
    if args.bible_file:
        bible_p = Path(args.bible_file)
        if not bible_p.exists() or not bible_p.is_file():
            if HAS_RICH:
                Console().print(f"[bold red]Error: Bible file does not exist at '{args.bible_file}'[/bold red]")
            else:
                print(f"Error: Bible file does not exist at '{args.bible_file}'", file=sys.stderr)
            return 1
        try:
            loaded_bible = load_bible_from_json(args.bible_file)
        except ValidationError as val_err:
            if HAS_RICH:
                Console().print(f"[bold red]Validation Error in Bible JSON '{args.bible_file}':[/bold red]")
                for err in val_err.errors():
                    Console().print(f"  • [bold yellow]{'.'.join(str(loc) for loc in err['loc'])}[/bold yellow]: {err['msg']}")
            else:
                print(f"Validation Error in Bible JSON '{args.bible_file}': {val_err}", file=sys.stderr)
            return 1
        except Exception as exc:
            if HAS_RICH:
                Console().print(f"[bold red]Failed to load Bible JSON '{args.bible_file}':[/bold red] {exc}")
            else:
                print(f"Failed to load Bible JSON '{args.bible_file}': {exc}", file=sys.stderr)
            return 1

    # Resolve input from --input or --prompt
    raw_prompt = args.prompt
    if args.input:
        input_path = Path(args.input)
        if input_path.is_file():
            try:
                data = json.loads(input_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    raw_prompt = data.get("prompt") or data.get("logline") or data.get("brief") or str(data)
                else:
                    raw_prompt = str(data)
            except Exception:
                raw_prompt = input_path.read_text(encoding="utf-8").strip()
        else:
            raw_prompt = args.input

    if not loaded_bible and not args.preset and not raw_prompt:
        # Default to ikea-asmr if nothing specified
        args.preset = "ikea-asmr"

    continuous_mode = args.mode in ("extension", "continuous")

    if not args.json:
        print_banner()

    try:
        if args.max_render_usd is not None:
            run_config = cfg.model_copy(update={"max_render_budget_usd": float(args.max_render_usd)})
            pipeline = DirectorPipeline(config=run_config)
        else:
            pipeline = DirectorPipeline()

        if not args.json:
            if HAS_RICH:
                console = Console()
                if loaded_bible:
                    target_desc = f"Bible File: [bold cyan]{args.bible_file}[/bold cyan] ('{loaded_bible.project_title}')"
                elif args.preset:
                    target_desc = f"Preset: [bold green]{args.preset}[/bold green]"
                else:
                    target_desc = f"Prompt: '{raw_prompt}'"
                console.print(f"🎬 Initiating Director Pipeline ({target_desc})...")
                console.print(f"📁 Target Output: [bold cyan]{args.output_dir}[/bold cyan]")
                console.print(f"⚙️ Mode: [bold magenta]{args.mode}[/bold magenta] | Dry Run: [bold]{args.dry_run}[/bold] | Council: [bold]{args.council or args.council_strict}[/bold]\n")
            else:
                print(f"Initiating Director Pipeline for {loaded_bible.project_title if loaded_bible else (args.preset or raw_prompt)}...")

        try:
            promote_take_map = _parse_promote_take_args(args.promote_take)
            retry_scenes_list = _parse_retry_scene_args(args.retry_scene)
        except ValueError as parse_exc:
            print(f"Error: {parse_exc}", file=sys.stderr)
            return 1

        run_council = args.council or args.council_strict
        defer_council_until_after_nle = bool(args.export_nle and run_council)

        run_sig = inspect.signature(pipeline.run)
        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in run_sig.parameters.values())
        extra_run_kwargs: Dict[str, Any] = {}
        if promote_take_map and ("promote_take" in run_sig.parameters or has_var_kw):
            normalized_promote_map: Dict[int, str] = {}
            for sc_idx, raw_take in promote_take_map.items():
                up_take = raw_take.strip().upper()
                shorthand = {
                    "A": f"SC{sc_idx:02d}_T1",
                    "B": f"SC{sc_idx:02d}_T2",
                    "C": f"SC{sc_idx:02d}_T3",
                    "T1": f"SC{sc_idx:02d}_T1",
                    "T2": f"SC{sc_idx:02d}_T2",
                    "T3": f"SC{sc_idx:02d}_T3",
                }
                normalized_promote_map[sc_idx] = shorthand.get(up_take, raw_take)
            extra_run_kwargs["promote_take"] = normalized_promote_map
        if retry_scenes_list:
            if "scene_filter" in run_sig.parameters:
                extra_run_kwargs["scene_filter"] = retry_scenes_list
            elif "retry_scene" in run_sig.parameters or has_var_kw:
                extra_run_kwargs["retry_scene"] = retry_scenes_list
            elif "retry_scenes" in run_sig.parameters:
                extra_run_kwargs["retry_scenes"] = retry_scenes_list

        if loaded_bible:
            bundle = pipeline.run_from_bible(
                bible=loaded_bible,
                output_dir=args.output_dir,
                render_video=args.render_video,
                dry_run=args.dry_run,
                continuous_mode=continuous_mode,
                run_council=(False if defer_council_until_after_nle else run_council),
                **extra_run_kwargs,
            )
        else:
            bundle = pipeline.run(
                preset_name=args.preset,
                raw_prompt=raw_prompt,
                output_dir=args.output_dir,
                render_video=args.render_video,
                dry_run=args.dry_run,
                continuous_mode=continuous_mode,
                run_council=(False if defer_council_until_after_nle else run_council),
                **extra_run_kwargs,
            )

        if promote_take_map and "promote_take" not in extra_run_kwargs:
            master_jobs = getattr(bundle.bible, "master_render_jobs", None)
            if master_jobs is not None:
                from omni_director.tools.render_orchestrator import promote_scene_take
                for sc_idx, raw_take in promote_take_map.items():
                    cand_take = raw_take
                    letter_map = {"A": f"SC{sc_idx:02d}_T1", "B": f"SC{sc_idx:02d}_T2", "C": f"SC{sc_idx:02d}_T3"}
                    if cand_take.upper() in letter_map:
                        cand_take = letter_map[cand_take.upper()]
                    try:
                        master_jobs = promote_scene_take(master_jobs, sc_idx, cand_take)
                    except ValueError:
                        pass
                bundle.bible.master_render_jobs = master_jobs

        if args.export_nle:
            from omni_director.tools.dialogue import compile_subtitles_srt, compile_subtitles_vtt
            from omni_director.tools.nle_export import export_all_nle_artifacts
            out_p = Path(args.output_dir)
            run_fps = getattr(args, "fps", 24)
            export_all_nle_artifacts(bundle.bible, out_p, fps=run_fps)
            (out_p / "subtitles.srt").write_text(compile_subtitles_srt(bundle.bible, fps=run_fps), encoding="utf-8")
            (out_p / "subtitles.vtt").write_text(compile_subtitles_vtt(bundle.bible), encoding="utf-8")

            telemetry_obj = getattr(pipeline, "telemetry", None)
            if telemetry_obj is None:
                from omni_director.telemetry import RuntimeTelemetry
                telemetry_obj = RuntimeTelemetry(project_title=bundle.bible.project_title)

            # Refresh telemetry manifest before council audit so all NLE exports are SHA-256 verified
            telemetry_obj.write_manifest(out_p)
            bundle.telemetry = telemetry_obj.to_dict()

            if defer_council_until_after_nle:
                orchestrator = ProductCouncilOrchestrator(config=pipeline.config)
                with telemetry_obj.record_stage("product_council"):
                    council_rep = orchestrator.audit(bundle, output_dir=out_p)
                bundle.council_report = council_rep
                council_json_path = out_p / "council_report.json"
                council_md_path = out_p / "council_report.md"
                if not council_json_path.is_file():
                    council_json_path.write_text(
                        json.dumps(council_rep.model_dump(), indent=2), encoding="utf-8"
                    )
                if not council_md_path.is_file():
                    council_md_path.write_text(
                        orchestrator.generate_markdown_report(council_rep), encoding="utf-8"
                    )
                telemetry_obj.write_manifest(out_p)
                bundle.telemetry = telemetry_obj.to_dict()

            bundle_json_file = (
                Path(bundle.bundle_json_path)
                if getattr(bundle, "bundle_json_path", None)
                else (out_p / "production_bundle.json")
            )
            bundle_json_file.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
            telemetry_obj.write_manifest(out_p)
            bundle.telemetry = telemetry_obj.to_dict()

        if args.json:
            print(bundle.model_dump_json(indent=2))
        elif HAS_RICH:
            console = Console()
            council_status = "Not Requested"
            if bundle.council_report:
                council_status = f"{bundle.council_report.overall_score:.1f}/100.0 ({'PASS' if bundle.council_report.passed else 'FAIL'})"

            console.print(Panel(
                f"[bold green]✓ Production Completed Successfully![/bold green]\n\n"
                f"• [bold]Project:[/bold] {bundle.bible.project_title}\n"
                f"• [bold]Scenes:[/bold] {len(bundle.bible.scenes)} scenes compiled\n"
                f"• [bold]Dark-Room Cinema UI:[/bold] [underline cyan]{bundle.storyboard_html_path}[/underline cyan]\n"
                f"• [bold]Production Bundle JSON:[/bold] [underline cyan]{bundle.bundle_json_path}[/underline cyan]\n"
                f"• [bold]Product Council:[/bold] {council_status}\n"
                f"• [bold]Prompt Auditor:[/bold] {'[green]All 7 Checks Passed[/green]' if all(r.passed for r in bundle.audit_reports) else '[yellow]Warnings/Errors Present[/yellow]'}",
                title="Director Wrap",
                border_style="green",
            ))
            if bundle.council_report:
                print_council_table(bundle.council_report, console)
        else:
            print("\n✓ Production Completed Successfully!")
            print(f"Title: {bundle.bible.project_title}")
            print(f"HTML Preview: {bundle.storyboard_html_path}")
            print(f"Bundle JSON: {bundle.bundle_json_path}")
            if bundle.council_report:
                print(f"Product Council: {bundle.council_report.overall_score:.1f}/100.0 (Passed: {bundle.council_report.passed})")

        # Check council-strict
        if args.council_strict and bundle.council_report:
            if not bundle.council_report.passed or bundle.council_report.overall_score < 88.0 or bundle.council_report.critical_findings_count > 0:
                if HAS_RICH:
                    Console().print("[bold red]✗ Council Strict Check Failed: Score < 88.0 or Critical Findings present.[/bold red]")
                else:
                    print("Council Strict Check Failed: Score < 88.0 or Critical Findings present.", file=sys.stderr)
                return 2

        return 0

    except Exception as exc:
        if HAS_RICH:
            Console().print(f"[bold red]Pipeline Error:[/bold red] {exc}")
        else:
            print(f"Pipeline Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
