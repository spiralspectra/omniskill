"""CLI entry point for omni-director command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    from rich import print as rprint
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from omni_director.agents import DirectorPipeline
from omni_director.config import DirectorConfig, cfg
from omni_director.presets import PRESETS, get_preset_bible


def print_banner() -> None:
    banner_text = (
        "[bold cyan]OMNI MOVIE DIRECTOR 2.0[/bold cyan] [dim]| ADK 2.0 Multi-Agent Cinema Engine[/dim]\n"
        "[italic]Gemini 4 Argon (Lead) • Gemini 3.8 Flash • Nano Banana • Gemini Omni[/italic]"
    )
    if HAS_RICH:
        console = Console()
        console.print(Panel(banner_text, border_style="cyan"))
    else:
        print("=" * 70)
        print("OMNI MOVIE DIRECTOR 2.0 | ADK 2.0 Multi-Agent Cinema Engine")
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


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="omni-director",
        description="Autonomous ADK 2.0 multi-agent cinematic production suite for Gemini Omni.",
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
        help="Attempt live video generation via Gemini Omni (requires GEMINI_API_KEY).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run deterministic simulation with Nano Banana SVG plates (default: True).",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List all built-in golden presets and exit.",
    )

    args = parser.parse_args(argv)

    if args.list_presets:
        list_presets()
        return 0

    if not args.preset and not args.prompt:
        # Default to ikea-asmr if nothing specified
        args.preset = "ikea-asmr"

    print_banner()

    try:
        pipeline = DirectorPipeline()

        if HAS_RICH:
            console = Console()
            target_desc = f"Preset: [bold green]{args.preset}[/bold green]" if args.preset else f"Prompt: '{args.prompt}'"
            console.print(f"🎬 Initiating Director Pipeline ({target_desc})...")
            console.print(f"📁 Target Output: [bold cyan]{args.output_dir}[/bold cyan]\n")
        else:
            print(f"Initiating Director Pipeline for preset: {args.preset or args.prompt}...")

        bundle = pipeline.run(
            preset_name=args.preset,
            raw_prompt=args.prompt,
            output_dir=args.output_dir,
            render_video=args.render_video,
            dry_run=not args.render_video,
        )

        if HAS_RICH:
            console = Console()
            console.print(Panel(
                f"[bold green]✓ Production Completed Successfully![/bold green]\n\n"
                f"• [bold]Project:[/bold] {bundle.bible.project_title}\n"
                f"• [bold]Scenes:[/bold] {len(bundle.bible.scenes)} scenes compiled\n"
                f"• [bold]Dark-Room Cinema UI:[/bold] [underline cyan]{bundle.storyboard_html_path}[/underline cyan]\n"
                f"• [bold]Production Bundle JSON:[/bold] [underline cyan]{bundle.bundle_json_path}[/underline cyan]\n"
                f"• [bold]Prompt Auditor:[/bold] {'[green]All 7 Checks Passed[/green]' if all(r.passed for r in bundle.audit_reports) else '[yellow]Warnings/Errors Present[/yellow]'}",
                title="Director Wrap",
                border_style="green"
            ))
        else:
            print("\n✓ Production Completed Successfully!")
            print(f"Title: {bundle.bible.project_title}")
            print(f"HTML Preview: {bundle.storyboard_html_path}")
            print(f"Bundle JSON: {bundle.bundle_json_path}")

        return 0

    except Exception as exc:
        if HAS_RICH:
            Console().print(f"[bold red]Pipeline Error:[/bold red] {exc}")
        else:
            print(f"Pipeline Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
