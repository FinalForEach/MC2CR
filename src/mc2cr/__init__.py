"""MC2CR: Minecraft to Cosmic Reach World Converter.

A library and tool for converting Minecraft worlds (Beta 1.7.3 McRegion, Anvil 1.0 - 1.13+)
into Cosmic Reach worlds.
"""

from __future__ import annotations

from mc2cr.converter import convert_mc_world, detect_mc_version, read_level_dat
from mc2cr.paths import (
    get_default_cr_saves_dir,
    get_default_mc_saves_dir,
    get_fallback_cr_saves_dir,
    get_fallback_mc_saves_dir,
    resolve_cr_saves_root,
    resolve_mc_saves_root,
)
from mc2cr.scanner import MinecraftWorldInfo, inspect_mc_world, scan_mc_worlds

__version__ = "0.1.1"

__all__ = [
    "convert_mc_world",
    "detect_mc_version",
    "read_level_dat",
    "get_default_mc_saves_dir",
    "get_default_cr_saves_dir",
    "get_fallback_mc_saves_dir",
    "get_fallback_cr_saves_dir",
    "resolve_mc_saves_root",
    "resolve_cr_saves_root",
    "MinecraftWorldInfo",
    "inspect_mc_world",
    "scan_mc_worlds",
]
