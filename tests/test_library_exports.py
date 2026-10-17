"""Unit test for verifying public library API surface."""

import mc2cr


def test_mc2cr_public_api():
    expected_exports = [
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

    for export in expected_exports:
        assert hasattr(mc2cr, export), f"mc2cr missing expected export: {export}"

    assert hasattr(mc2cr, "__version__")
