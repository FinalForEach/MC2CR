"""Click CLI for MC2CR conversion tool."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click

from mc2cr.converter import convert_mc_world
from mc2cr.paths import (
    get_fallback_cr_saves_dir,
    get_fallback_mc_saves_dir,
    resolve_cr_saves_root,
    resolve_mc_saves_root,
)
from mc2cr.scanner import scan_mc_worlds


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--gui", is_flag=True, help="Launch the graphical user interface.")
def main(ctx: click.Context, gui: bool) -> None:
    """MC2CR: Minecraft to Cosmic Reach World Converter."""
    if gui or ctx.invoked_subcommand is None:
        if gui:
            from mc2cr.gui.app import main as launch_gui

            launch_gui()
            return
        elif ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())


@main.command()
def gui() -> None:
    """Launch the native MC2CR GUI."""
    from mc2cr.gui.app import main as launch_gui

    launch_gui()


@main.command()
@click.option(
    "--input",
    "-i",
    "input_path",
    type=str,
    required=False,
    help="Path or name of the Minecraft world to convert (e.g. '1.7.3 world').",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=str,
    required=False,
    help="Output path for the converted Cosmic Reach world.",
)
@click.option(
    "--mapping",
    "-m",
    "mapping_path",
    type=str,
    required=False,
    help="Optional path to a custom JSON block mapping override file.",
)
@click.option(
    "--y-offset",
    "-y",
    "y_offset",
    type=int,
    default=-64,
    show_default=True,
    help="Vertical block offset to apply when converting to Cosmic Reach.",
)
@click.option(
    "--workers",
    "-w",
    "max_workers",
    type=int,
    default=None,
    show_default=False,
    help="Number of parallel worker processes to use (default: CPU core count).",
)
@click.option(
    "--list-worlds",
    "-l",
    "list_worlds",
    is_flag=True,
    help="List all discovered Minecraft worlds.",
)
def convert(
    input_path: str | None,
    output_path: str | None,
    mapping_path: str | None,
    y_offset: int,
    max_workers: int | None,
    list_worlds: bool,
) -> None:
    """Convert a Minecraft world (Beta 1.7.3, Release 1.0 - 1.13+) to Cosmic Reach."""
    mc_saves_dir = resolve_mc_saves_root()
    fallback_mc_dir = get_fallback_mc_saves_dir()
    cr_worlds_dir = resolve_cr_saves_root()
    fallback_cr_dir = get_fallback_cr_saves_dir()

    if list_worlds:
        worlds = scan_mc_worlds(mc_saves_dir)
        if not worlds and fallback_mc_dir.exists() and fallback_mc_dir != mc_saves_dir:
            worlds = scan_mc_worlds(fallback_mc_dir)

        if not worlds:
            click.echo(f"No Minecraft worlds found in '{mc_saves_dir}'.")
            return

        click.echo("Available Minecraft worlds:")
        for w in worlds:
            click.echo(f" - {w.display_label}")
        return

    if not input_path:
        click.echo("Error: Please specify a world using --input / -i (or use --list-worlds).", err=True)
        sys.exit(1)

    in_p = Path(input_path)
    if not in_p.is_absolute() and not in_p.exists():
        candidate_default = mc_saves_dir / input_path
        candidate_fallback = fallback_mc_dir / input_path
        if candidate_default.exists():
            in_p = candidate_default
        elif candidate_fallback.exists():
            in_p = candidate_fallback

    if not in_p.exists():
        click.echo(f"Error: Source Minecraft world not found at '{in_p}'.", err=True)
        sys.exit(1)

    if not output_path:
        target_cr_root = cr_worlds_dir if cr_worlds_dir.exists() or not fallback_cr_dir.exists() else fallback_cr_dir
        out_p = target_cr_root / in_p.name
    else:
        out_p = Path(output_path)
        if not out_p.is_absolute() and not out_p.parent.exists():
            out_p = cr_worlds_dir / output_path

    click.echo(f"Converting '{in_p.name}' from Minecraft to Cosmic Reach...")
    click.echo(f"Source: {in_p}")
    click.echo(f"Destination: {out_p}")

    if mapping_path:
        click.echo(f"Block Mapping Override: {mapping_path}")
    if y_offset != 0:
        click.echo(f"Y Offset:             {y_offset} blocks")

    start_time = time.time()
    current_phase = "convert"
    phase_start_time = time.time()

    def progress(item_name: str, current: int, total: int, phase: str = "convert") -> None:
        nonlocal current_phase, phase_start_time
        if phase != current_phase:
            current_phase = phase
            phase_start_time = time.time()
            click.echo(f"Saving {total} Cosmic Reach region files to disk...")

        elapsed_phase = time.time() - phase_start_time
        remaining = total - current
        avg_per_item = elapsed_phase / current if current > 0 else 0
        eta_seconds = int(avg_per_item * remaining)

        if eta_seconds >= 60:
            eta_str = f"{eta_seconds // 60}m {eta_seconds % 60:02d}s"
        else:
            eta_str = f"{eta_seconds}s"

        verb = "Converted" if phase == "convert" else "Saved"
        if remaining > 0:
            click.echo(f"[{current}/{total}] {verb} {item_name} (ETA: {eta_str})")
        else:
            click.echo(f"[{current}/{total}] {verb} {item_name}")

    stats = convert_mc_world(
        in_p,
        out_p,
        mapping_override=mapping_path,
        progress_callback=progress,
        y_offset=y_offset,
        max_workers=max_workers,
    )

    click.echo("=" * 40)
    click.echo("Conversion complete!")
    click.echo(f"World Name:          {stats['world_name']}")
    click.echo(f"Region Files Read:   {stats['mcr_files_processed']}")
    click.echo(f"MC Chunks Read:      {stats['mc_chunks_converted']}")
    click.echo(f"CR Chunks Created:   {stats['cr_chunks_generated']}")
    click.echo(f"CR Regions Saved:    {stats['cr_regions_saved']}")
    click.echo(f"Time Taken:          {stats['elapsed_seconds']:.2f}s")
    click.echo("=" * 40)


if __name__ == "__main__":
    main()
