"""Scanner for discovering and extracting metadata from Minecraft save directories."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from mc2cr.converter import detect_mc_version, read_level_dat


@dataclass
class MinecraftWorldInfo:
    """Metadata representing an individual Minecraft world save."""

    folder_name: str
    path: Path
    display_name: str
    version_str: str
    is_anvil: bool
    last_played_str: str
    region_count: int

    @property
    def display_label(self) -> str:
        """Formatted human-readable label for UI selection."""
        details = []
        if self.version_str:
            details.append(self.version_str)
        if self.region_count > 0:
            details.append(f"{self.region_count} region{'s' if self.region_count != 1 else ''}")
        if self.last_played_str:
            details.append(self.last_played_str)

        info = f" ({', '.join(details)})" if details else ""
        return f"{self.display_name}{info}"


def inspect_mc_world(world_path: Path | str) -> Optional[MinecraftWorldInfo]:
    """Inspect a single folder to check if it's a valid Minecraft world and extract info."""
    path = Path(world_path)
    if not path.is_dir():
        return None

    level_dat = path / "level.dat"
    level_data = read_level_dat(level_dat) if level_dat.exists() else {}

    # Check for region files in overworld and dimensions
    mca_files = list(path.glob("**/region/*.mca"))
    mcr_files = list(path.glob("**/region/*.mcr"))
    is_anvil = len(mca_files) > 0
    total_regions = len(mca_files) if is_anvil else len(mcr_files)

    # If no level.dat and no region files, not a valid MC world
    if not level_dat.exists() and total_regions == 0:
        return None

    display_name = str(level_data.get("LevelName", path.name))
    version_str = detect_mc_version(level_data, path, is_anvil)

    # Format last played timestamp
    last_played_ts = level_data.get("LastPlayed")
    last_played_str = ""
    if isinstance(last_played_ts, (int, float)) and last_played_ts > 0:
        try:
            # LastPlayed is in milliseconds in Minecraft level.dat
            dt = datetime.datetime.fromtimestamp(last_played_ts / 1000.0)
            last_played_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, OSError):
            pass
    elif level_dat.exists():
        try:
            mtime = level_dat.stat().st_mtime
            dt = datetime.datetime.fromtimestamp(mtime)
            last_played_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, OSError):
            pass

    return MinecraftWorldInfo(
        folder_name=path.name,
        path=path.resolve(),
        display_name=display_name,
        version_str=version_str,
        is_anvil=is_anvil,
        last_played_str=last_played_str,
        region_count=total_regions,
    )


def scan_mc_worlds(saves_dir: Path | str) -> List[MinecraftWorldInfo]:
    """Scan a root directory for all subdirectories containing Minecraft worlds."""
    root = Path(saves_dir)
    if not root.is_dir():
        return []

    worlds: List[MinecraftWorldInfo] = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return []

    for item in entries:
        if item.is_dir():
            info = inspect_mc_world(item)
            if info is not None:
                worlds.append(info)

    return worlds
