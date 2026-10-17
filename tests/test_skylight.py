"""Tests for Cosmic Reach skylight data serialization."""

from mc2cr.cosmicreach.constants import (
    NUM_BLOCKS_IN_CHUNK,
    SKYLIGHTDATA_LAYER_NIBBLE,
    SKYLIGHTDATA_LAYER_SINGLE,
    SKYLIGHTDATA_LAYERED,
    SKYLIGHTDATA_SINGLE,
)
from mc2cr.cosmicreach.skylight_data import ChunkSkyLightData


def test_skylight_single_uniform():
    # Full daylight = 15
    lights = [15] * NUM_BLOCKS_IN_CHUNK
    sky_data = ChunkSkyLightData(lights)
    serialized = sky_data.serialize()

    # Should serialize to [SKYLIGHTDATA_SINGLE, 15]
    assert serialized[0] == SKYLIGHTDATA_SINGLE
    assert serialized[1] == 15
    assert len(serialized) == 2


def test_skylight_layered():
    lights = [15] * NUM_BLOCKS_IN_CHUNK
    # Darken bottom layer (y=0)
    for x in range(16):
        for z in range(16):
            lights[(0 * 16 + x) * 16 + z] = 0

    sky_data = ChunkSkyLightData(lights)
    serialized = sky_data.serialize()

    # Should serialize to SKYLIGHTDATA_LAYERED (2)
    assert serialized[0] == SKYLIGHTDATA_LAYERED
    # First layer (y=0) should be SINGLE with value 0
    assert serialized[1] == SKYLIGHTDATA_LAYER_SINGLE
    assert serialized[2] == 0
    # Remaining layers should be SINGLE with value 15
    offset = 3
    for y in range(1, 16):
        assert serialized[offset] == SKYLIGHTDATA_LAYER_SINGLE
        assert serialized[offset + 1] == 15
        offset += 2


def test_skylight_nibble_layer():
    lights = [15] * NUM_BLOCKS_IN_CHUNK
    # Partial shadow on layer 0: checkerboard of 0 and 15
    for x in range(16):
        for z in range(16):
            lights[(0 * 16 + x) * 16 + z] = 0 if (x % 2 == 0) else 15

    sky_data = ChunkSkyLightData(lights)
    serialized = sky_data.serialize()

    assert serialized[0] == SKYLIGHTDATA_LAYERED
    # Layer 0 is NIBBLE (128 bytes)
    assert serialized[1] == SKYLIGHTDATA_LAYER_NIBBLE
    # 128 bytes of nibbles
    nibble_bytes = serialized[2 : 2 + 128]
    assert len(nibble_bytes) == 128
    # Lower nibble 0, upper nibble 15 -> 0xF0
    assert nibble_bytes[0] == 0xF0
