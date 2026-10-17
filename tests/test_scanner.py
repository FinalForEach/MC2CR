"""Unit tests for Minecraft world scanner and metadata extraction."""

from pathlib import Path

from mc2cr.scanner import MinecraftWorldInfo, inspect_mc_world, scan_mc_worlds


def test_scan_mc_worlds_directory():
    mc_dir = Path(__file__).parent / "data"
    if not mc_dir.exists():
        return

    worlds = scan_mc_worlds(mc_dir)
    assert len(worlds) > 0

    world_names = [w.folder_name for w in worlds]
    assert "r1.0" in world_names

    r10_info = next(w for w in worlds if w.folder_name == "r1.0")
    assert r10_info.folder_name == "r1.0"
    assert r10_info.display_name != ""
    assert r10_info.region_count > 0
    assert "Release 1.0" in r10_info.display_label


def test_inspect_non_world(tmp_path):
    empty_dir = tmp_path / "not_a_world"
    empty_dir.mkdir()
    assert inspect_mc_world(empty_dir) is None


def test_display_label():
    info = MinecraftWorldInfo(
        folder_name="World1",
        path=Path("/tmp/World1"),
        display_name="My Cool World",
        version_str="Minecraft Beta 1.7.3",
        is_anvil=False,
        last_played_str="2026-01-01 12:00",
        region_count=3,
    )
    label = info.display_label
    assert "My Cool World" in label
    assert "Beta 1.7.3" in label
    assert "3 regions" in label
