"""CLI entry point for omni-director and omni commands."""

from __future__ import annotations

import argparse
import json
import sys
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
        # Default: audit all 4 golden presets
        for key in list(CURATED_PRESETS.keys()):
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

    return 0 if overall_success else (2 if args.council_strict else 0)


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

    parser = argparse.ArgumentParser(prog="omni export", description="Export NLE timelines (EDL/FCPXML), shot lists, call sheets, subtitles, CDL color grades, audio stem manifests, lens packages, virtual production stage manifests, MoCo kinematics tracks, and lighting plots")
    parser.add_argument("--preset", type=str, default=None, choices=list(PRESETS.keys()), help="Preset name to export")
    parser.add_argument("--bible-file", "-b", type=str, default=None, help="Path to MasterProductionBible or ProductionBundle JSON")
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="all",
        choices=["all", "edl", "fcpxml", "csv", "md", "srt", "vtt", "cdl", "stems", "lens", "vp", "moco", "lighting"],
        help="Artifact format to export (default: all)",
    )
    parser.add_argument("--output-dir", "-o", type=str, default="./output", help="Target directory for exported files")
    parser.add_argument("--fps", type=int, default=24, help="Frame rate for timecode calculations (default: 24)")
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

    exported_files: Dict[str, str] = {}
    fmt = args.format.lower()

    if fmt == "all":
        exported_files.update(export_all_nle_artifacts(bible, out_dir, fps=args.fps))
        srt_path = out_dir / "subtitles.srt"
        vtt_path = out_dir / "subtitles.vtt"
        srt_path.write_text(compile_subtitles_srt(bible, fps=args.fps), encoding="utf-8")
        vtt_path.write_text(compile_subtitles_vtt(bible), encoding="utf-8")
        exported_files["srt"] = str(srt_path.resolve())
        exported_files["vtt"] = str(vtt_path.resolve())
        cdl_path = out_dir / "production_grade.cdl"
        stems_path = out_dir / "audio_stems_manifest.json"
        export_asc_cdl_file(bible, cdl_path)
        export_audio_stems_file(bible, stems_path)
        exported_files["cdl"] = str(cdl_path.resolve())
        exported_files["stems"] = str(stems_path.resolve())
        lens_path = out_dir / "lens_package.csv"
        export_lens_metadata_file(bible, lens_path)
        exported_files["lens"] = str(lens_path.resolve())
        vp_files = export_virtual_production_bundle(bible, out_dir)
        exported_files.update(vp_files)
        moco_files = export_moco_bundle(bible, out_dir)
        exported_files.update(moco_files)
        lighting_files = export_lighting_bundle(bible, out_dir)
        exported_files.update(lighting_files)
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
        p.write_text(export_shot_list_csv(bible), encoding="utf-8")
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

        run_council = args.council or args.council_strict

        if loaded_bible:
            bundle = pipeline.run_from_bible(
                bible=loaded_bible,
                output_dir=args.output_dir,
                render_video=args.render_video,
                dry_run=args.dry_run,
                continuous_mode=continuous_mode,
                run_council=run_council,
            )
        else:
            bundle = pipeline.run(
                preset_name=args.preset,
                raw_prompt=raw_prompt,
                output_dir=args.output_dir,
                render_video=args.render_video,
                dry_run=args.dry_run,
                continuous_mode=continuous_mode,
                run_council=run_council,
            )

        if args.export_nle:
            from omni_director.tools.dialogue import compile_subtitles_srt, compile_subtitles_vtt
            from omni_director.tools.nle_export import export_all_nle_artifacts
            from omni_director.tools.color_grade import export_asc_cdl_file
            from omni_director.tools.audio_mixer import export_audio_stems_file
            from omni_director.tools.optical_lens import export_lens_metadata_file
            from omni_director.tools.virtual_production import export_virtual_production_bundle
            out_p = Path(args.output_dir)
            export_all_nle_artifacts(bundle.bible, out_p, fps=24)
            (out_p / "subtitles.srt").write_text(compile_subtitles_srt(bundle.bible, fps=24), encoding="utf-8")
            (out_p / "subtitles.vtt").write_text(compile_subtitles_vtt(bundle.bible), encoding="utf-8")
            export_asc_cdl_file(bundle.bible, out_p / "production_grade.cdl")
            export_audio_stems_file(bundle.bible, out_p / "audio_stems_manifest.json")
            export_lens_metadata_file(bundle.bible, out_p / "lens_package.csv")
            export_virtual_production_bundle(bundle.bible, out_p)

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
