"""CLI entry point for omni-director and omni commands."""

from __future__ import annotations

import argparse
import json
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
from omni_director.config import DirectorConfig, cfg, get_settings
from omni_director.presets import PRESETS, get_preset_bible
from omni_director.schemas import StorytellingMode


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
    args_list = list(sys.argv[1:] if argv is None else argv)
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
        "--list-presets",
        action="store_true",
        help="List all built-in golden presets and exit.",
    )

    args = parser.parse_args(args_list)

    if args.list_presets:
        list_presets()
        return 0

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

    if not args.preset and not raw_prompt:
        # Default to ikea-asmr if nothing specified
        args.preset = "ikea-asmr"

    continuous_mode = args.mode in ("extension", "continuous")

    print_banner()

    try:
        pipeline = DirectorPipeline()

        if HAS_RICH:
            console = Console()
            target_desc = f"Preset: [bold green]{args.preset}[/bold green]" if args.preset else f"Prompt: '{raw_prompt}'"
            console.print(f"🎬 Initiating Director Pipeline ({target_desc})...")
            console.print(f"📁 Target Output: [bold cyan]{args.output_dir}[/bold cyan]")
            console.print(f"⚙️ Mode: [bold magenta]{args.mode}[/bold magenta] | Dry Run: [bold]{args.dry_run}[/bold] | Render Video: [bold]{args.render_video}[/bold]\n")
        else:
            print(f"Initiating Director Pipeline for {args.preset or raw_prompt}...")

        bundle = pipeline.run(
            preset_name=args.preset,
            raw_prompt=raw_prompt,
            output_dir=args.output_dir,
            render_video=args.render_video,
            dry_run=args.dry_run,
            continuous_mode=continuous_mode,
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
