"""Unit tests for Anvil (.mca) region and chunk parser."""

from pathlib import Path
from mc2cr.minecraft.anvil import AnvilRegionFile

MCA_TEST_FILE = Path(__file__).parent / "data" / "r1.2.5" / "region" / "r.1.1.mca"


def test_anvil_region_reading():
    if not MCA_TEST_FILE.exists():
        return

    mca = AnvilRegionFile(MCA_TEST_FILE)
    chunks = list(mca.iter_chunks())
    assert len(chunks) > 0

    first_chunk = chunks[0]
    assert len(first_chunk.sections) > 0

    # Section 0 should have 4096 bytes of blocks and 2048 bytes of data
    sec0 = next(iter(first_chunk.sections.values()))
    assert len(sec0.blocks) == 4096
    assert len(sec0.data) == 2048
