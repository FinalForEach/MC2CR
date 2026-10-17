"""Tests for Cosmic Reach block data serialization and region writing."""

import gzip
import struct

from mc2cr.cosmicreach.block_data import ChunkBlockData
from mc2cr.cosmicreach.constants import (
    BLOCK_LAYERED,
    BLOCK_SINGLE,
    COMPRESSION_TYPE_GZIP,
    FILE_VERSION,
    MAGIC,
    NUM_BLOCKS_IN_CHUNK,
)
from mc2cr.cosmicreach.region_writer import CRChunk, CRRegion


def test_single_block_data_serialization():
    blocks = ["base:air[default]"] * NUM_BLOCKS_IN_CHUNK
    chunk_data = ChunkBlockData(blocks)
    serialized = chunk_data.serialize()

    # Should start with BLOCK_SINGLE (1)
    assert serialized[0] == BLOCK_SINGLE
    # Length of "base:air[default]" is 17
    str_len = struct.unpack(">i", serialized[1:5])[0]
    assert str_len == 17
    assert serialized[5 : 5 + str_len] == b"base:air[default]"


def test_layered_block_data_serialization():
    blocks = ["base:air[default]"] * NUM_BLOCKS_IN_CHUNK
    # Place a single debug block at (0, 0, 0)
    blocks[0] = "minecraft:b173_1[default]"
    chunk_data = ChunkBlockData(blocks)
    serialized = chunk_data.serialize()

    # Should start with BLOCK_LAYERED (2)
    assert serialized[0] == BLOCK_LAYERED
    palette_size = struct.unpack(">i", serialized[1:5])[0]
    assert palette_size == 2


def test_cr_region_serialization():
    region = CRRegion(0, 0, 0)
    blocks = ["base:air[default]"] * NUM_BLOCKS_IN_CHUNK
    chunk = CRChunk(0, 0, 0, ChunkBlockData(blocks))
    region.add_chunk(chunk)

    raw_region_file = region.serialize()
    # Check header (12 bytes)
    magic, file_ver, comp_type = struct.unpack(">Iii", raw_region_file[:12])
    assert magic == MAGIC
    assert file_ver == FILE_VERSION
    assert comp_type == COMPRESSION_TYPE_GZIP

    # Decompress payload
    decompressed = gzip.decompress(raw_region_file[12:])
    num_cols = struct.unpack(">i", decompressed[:4])[0]
    assert num_cols == 1


def test_direct_binary_streaming_equivalence():
    from mc2cr.cosmicreach.region_writer import (
        AIR_BLOCK_DATA_BYTES,
        SKY_15_BYTES,
        serialize_chunk_from_data,
    )
    from mc2cr.cosmicreach.skylight_data import ChunkSkyLightData

    # 1. Verify AIR_BLOCK_DATA_BYTES exactly matches ChunkBlockData serialization
    expected_air = ChunkBlockData(["base:air[default]"] * NUM_BLOCKS_IN_CHUNK).serialize()
    assert AIR_BLOCK_DATA_BYTES == expected_air

    # 2. Verify serialize_chunk_from_data produces identical bytes to CRChunk.serialize()
    cr_chunk = CRChunk(
        chunk_x=3,
        chunk_y=4,
        chunk_z=5,
        block_data=ChunkBlockData(["base:air[default]"] * NUM_BLOCKS_IN_CHUNK),
        skylight_data=ChunkSkyLightData([15] * NUM_BLOCKS_IN_CHUNK),
    )
    standard_bytes = cr_chunk.serialize()
    raw_streamed_bytes = serialize_chunk_from_data(
        chunk_x=3,
        chunk_y=4,
        chunk_z=5,
        block_data_bytes=AIR_BLOCK_DATA_BYTES,
        skylight_data_bytes=SKY_15_BYTES,
    )
    assert raw_streamed_bytes == standard_bytes

    # 3. Verify region serialization equivalence
    r1 = CRRegion(0, 0, 0)
    r1.add_chunk(cr_chunk)

    r2 = CRRegion(0, 0, 0)
    r2.add_raw_chunk(3, 4, 5, raw_streamed_bytes)

    assert r1.serialize(compress_level=1) == r2.serialize(compress_level=1)


def test_write_world_structure_with_player(tmp_path):
    from mc2cr.cosmicreach.world_writer import write_world_structure
    import json

    world_dir = tmp_path / "test_world"
    write_world_structure(
        output_dir=world_dir,
        world_name="TestWorld",
        world_seed=12345,
        spawn_coords=(10.0, 5.0, 20.0),
        player_pos=(10.0, 5.0, 20.0),
        player_rotation=(90.0, 0.0),
        gamemode="creative",
    )

    player_file = world_dir / "players" / "localPlayer.json"
    assert player_file.exists()
    with open(player_file, "r") as f:
        data = json.load(f)

    assert data["zoneId"] == "base:earth"
    assert data["gamemode"] == "creative"
    assert data["entity"]["position"] == {"x": 10.0, "y": 5.0, "z": 20.0}
    assert "viewDirection" in data["entity"]


def test_write_world_structure_multi_dimension(tmp_path):
    from mc2cr.cosmicreach.world_writer import write_world_structure
    import json

    world_dir = tmp_path / "multi_dim_world"
    write_world_structure(
        output_dir=world_dir,
        world_name="MultiDimWorld",
        world_seed=999,
        spawn_coords=(0.0, 64.0, 0.0),
        default_zone_id="base:earth",
        active_zone_ids=["base:earth", "base:lux", "base:moon"],
        player_zone_id="base:lux",
        player_pos=(5.0, 10.0, 15.0),
        gamemode="survival",
    )

    # Check earth zone
    earth_info = world_dir / "zones" / "base" / "earth" / "zoneInfo.json"
    assert earth_info.exists()
    with open(earth_info) as f:
        earth_data = json.load(f)
    assert earth_data["zoneId"] == "base:earth"
    assert earth_data["skyId"] == "base:dynamic_sky"
    assert earth_data["worldGenSaveKey"] == "base:void"

    # Check lux zone
    lux_info = world_dir / "zones" / "base" / "lux" / "zoneInfo.json"
    assert lux_info.exists()
    with open(lux_info) as f:
        lux_data = json.load(f)
    assert lux_data["zoneId"] == "base:lux"
    assert lux_data["skyId"] == "base:lux_sky"
    assert lux_data["worldGenSaveKey"] == "base:void"

    # Check moon zone
    moon_info = world_dir / "zones" / "base" / "moon" / "zoneInfo.json"
    assert moon_info.exists()
    with open(moon_info) as f:
        moon_data = json.load(f)
    assert moon_data["zoneId"] == "base:moon"
    assert moon_data["skyId"] == "base:space_day"
    assert moon_data["worldGenSaveKey"] == "base:void"

    # Check player is in lux
    player_file = world_dir / "players" / "localPlayer.json"
    with open(player_file) as f:
        p_data = json.load(f)
    assert p_data["zoneId"] == "base:lux"
    assert p_data["entity"]["position"] == {"x": 5.0, "y": 10.0, "z": 15.0}
