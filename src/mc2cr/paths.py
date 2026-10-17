"""Cross-platform path detection for Minecraft and Cosmic Reach save directories."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def get_default_mc_saves_dir() -> Path:
    """Return the default Minecraft 'saves' directory for the current operating system."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / ".minecraft" / "saves"
        return Path.home() / "AppData" / "Roaming" / ".minecraft" / "saves"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "minecraft" / "saves"

    # Linux / BSD / Unix
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        xdg_mc = Path(xdg_data) / ".minecraft" / "saves"
        if xdg_mc.exists():
            return xdg_mc

    return Path.home() / ".minecraft" / "saves"


def get_default_cr_saves_dir() -> Path:
    """Return the default Cosmic Reach 'worlds' save directory for the current OS.

    Matches the directory resolution logic from Cosmic Reach's SaveLocation.java.
    """
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / "cosmic-reach" / "worlds"
        return Path.home() / "AppData" / "Local" / "cosmic-reach" / "worlds"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "cosmic-reach" / "worlds"

    # Linux / BSD / Unix (XDG_DATA_HOME or ~/.local/share)
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data and xdg_data.strip():
        root_folder = Path(xdg_data)
    else:
        root_folder = Path.home() / ".local" / "share"

    return root_folder / "cosmic-reach" / "worlds"


def get_fallback_mc_saves_dir() -> Path:
    """Return the local workspace fallback directory for Minecraft worlds."""
    return Path.cwd() / "MC worlds"


def get_fallback_cr_saves_dir() -> Path:
    """Return the local workspace fallback directory for Cosmic Reach worlds."""
    return Path.cwd() / "CR worlds"


def resolve_mc_saves_root() -> Path:
    """Resolve the best existing Minecraft saves directory (default or local fallback)."""
    default_dir = get_default_mc_saves_dir()
    if default_dir.exists():
        return default_dir
    fallback = get_fallback_mc_saves_dir()
    if fallback.exists():
        return fallback
    return default_dir


def resolve_cr_saves_root() -> Path:
    """Resolve the best Cosmic Reach worlds directory (creates default if needed)."""
    default_dir = get_default_cr_saves_dir()
    return default_dir
