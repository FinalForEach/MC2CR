"""Build script to create a standalone static single-file executable for MC2CR."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def build_standalone_executable() -> None:
    """Build a standalone, single-file executable using PyInstaller."""
    project_root = Path(__file__).resolve().parent.parent
    src_dir = project_root / "src"
    entry_point = src_dir / "mc2cr" / "gui" / "app.py"
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    print(f"Building MC2CR standalone executable from: {entry_point}")
    print(f"Output directory: {dist_dir}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=MC2CR",
        "--onefile",
        "--windowed",
        f"--paths={src_dir}",
        "--collect-data=mc2cr",
        "--collect-data=sv_ttk",
        "--clean",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        str(entry_point),
    ]

    print("Running command:", " ".join(cmd))
    try:
        subprocess.check_call(cmd, cwd=str(project_root))
        print("\nBuild completed successfully!")
        print(f"Standalone executable located in: {dist_dir}")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with exit code: {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    build_standalone_executable()
