"""Integration test for converting Minecraft Release 1.0 worlds."""

from pathlib import Path
from mc2cr.converter import convert_mc_world


def test_convert_release_100_world(tmp_path):
    source_world = Path(__file__).parent / "data" / "r1.0"
    if not source_world.exists():
        return

    dest_world = tmp_path / "r1.0 CR"
    stats = convert_mc_world(source_world, dest_world, y_offset=-64)

    assert stats["world_name"] == "Release 1.0"
    assert stats["mcr_files_processed"] == 2
    assert stats["mc_chunks_converted"] > 0
    assert stats["cr_chunks_generated"] > 0
    assert stats["cr_regions_saved"] > 0

    # Verify worldInfo and zoneInfo
    assert (dest_world / "worldInfo.json").exists()
    assert (dest_world / "zones" / "base" / "earth" / "zoneInfo.json").exists()
