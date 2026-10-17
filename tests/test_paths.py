"""Unit tests for cross-platform path resolution."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

from mc2cr.paths import (
    get_default_cr_saves_dir,
    get_default_mc_saves_dir,
    get_fallback_cr_saves_dir,
    get_fallback_mc_saves_dir,
    resolve_cr_saves_root,
    resolve_mc_saves_root,
)


def test_mc_saves_dir_linux():
    with patch("sys.platform", "linux"), patch.dict(os.environ, {"HOME": "/home/testuser"}, clear=True):
        p = get_default_mc_saves_dir()
        assert str(p) == "/home/testuser/.minecraft/saves"


def test_mc_saves_dir_windows():
    with patch("sys.platform", "win32"), patch.dict(os.environ, {"APPDATA": "C:\\Users\\testuser\\AppData\\Roaming"}):
        p = get_default_mc_saves_dir()
        assert "AppData" in str(p) and ".minecraft" in str(p) and "saves" in str(p)


def test_cr_saves_dir_linux():
    with patch("sys.platform", "linux"), patch.dict(os.environ, {"HOME": "/home/testuser"}, clear=True):
        p = get_default_cr_saves_dir()
        assert str(p) == "/home/testuser/.local/share/cosmic-reach/worlds"


def test_cr_saves_dir_linux_xdg():
    with patch("sys.platform", "linux"), patch.dict(os.environ, {"XDG_DATA_HOME": "/custom/data"}):
        p = get_default_cr_saves_dir()
        assert str(p) == "/custom/data/cosmic-reach/worlds"


def test_cr_saves_dir_windows():
    with patch("sys.platform", "win32"), patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\testuser\\AppData\\Local"}):
        p = get_default_cr_saves_dir()
        assert "AppData" in str(p) and "cosmic-reach" in str(p) and "worlds" in str(p)


def test_fallbacks():
    mc_fallback = get_fallback_mc_saves_dir()
    cr_fallback = get_fallback_cr_saves_dir()
    assert mc_fallback.name == "MC worlds"
    assert cr_fallback.name == "CR worlds"
