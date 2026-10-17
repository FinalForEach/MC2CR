"""Modern theme and styling configuration for MC2CR GUI using sv-ttk."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

try:
    import sv_ttk
    HAS_SV_TTK = True
except ImportError:
    HAS_SV_TTK = False


def setup_native_theme(root: tk.Tk, theme: str = "dark") -> ttk.Style:
    """Configure TTK style with modern Sun Valley theme and polished typography."""
    style = ttk.Style(root)

    if HAS_SV_TTK:
        sv_ttk.set_theme(theme)
    else:
        available_themes = style.theme_names()
        if sys.platform == "win32" and "vista" in available_themes:
            style.theme_use("vista")
        elif sys.platform == "darwin" and "aqua" in available_themes:
            style.theme_use("aqua")
        elif "clam" in available_themes:
            style.theme_use("clam")

    # Typography
    default_font = ("Segoe UI", 10) if sys.platform == "win32" else ("Inter", 10)
    heading_font = ("Segoe UI", 12, "bold") if sys.platform == "win32" else ("Inter", 12, "bold")
    bold_font = ("Segoe UI", 10, "bold") if sys.platform == "win32" else ("Inter", 10, "bold")

    root.option_add("*Font", default_font)

    style.configure("Title.TLabel", font=heading_font)
    style.configure("Bold.TLabel", font=bold_font)
    style.configure("Accent.TButton", font=bold_font, padding=6)
    style.configure("Action.TButton", padding=5)

    return style


def toggle_theme() -> None:
    """Toggle between dark and light Sun Valley theme."""
    if HAS_SV_TTK:
        sv_ttk.toggle_theme()
