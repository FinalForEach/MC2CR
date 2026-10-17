"""Tests for McRegion reader and world conversion integration."""

from pathlib import Path
import json

from mc2cr.converter import convert_b173_world
from mc2cr.minecraft.mcregion import McRegionFile


DATA_DIR = Path(__file__).parent / "data"


def test_read_existing_mcr():
    mcr_path = DATA_DIR / "b1.7.3" / "region" / "r.0.1.mcr"
    if not mcr_path.exists():
        return
    region = McRegionFile(mcr_path)
    chunks = list(region.iter_chunks())
    assert len(chunks) > 0
    first = chunks[0]
    assert len(first.blocks) == 32768


def test_convert_b173_world(tmp_path):
    mc_world = DATA_DIR / "b1.7.3"
    if not mc_world.exists():
        return
    out_dir = tmp_path / "b1.7.3"
    stats = convert_b173_world(mc_world, out_dir)

    assert stats["mc_chunks_converted"] > 0
    assert stats["cr_chunks_generated"] == stats["mc_chunks_converted"] * 8
    assert (out_dir / "worldInfo.json").exists()
    assert (out_dir / "zones/base/earth/zoneInfo.json").exists()

    with open(out_dir / "zones/base/earth/zoneInfo.json", "r") as f:
        zone_info = json.load(f)
        assert zone_info["worldGenSaveKey"] == "base:void"
        assert zone_info["zoneId"] == "base:earth"
