"""Tests for chest tile entity conversion to Cosmic Reach crate block entities."""

from mc2cr.minecraft.b173_blocks import B173BlockMapper
from mc2cr.minecraft.tile_entities import build_chunk_block_entities_binary, convert_chest_tile_entity


def test_convert_chest_tile_entity():
    mapper = B173BlockMapper()
    chest_te = {
        "id": "Chest",
        "x": 10,
        "y": 64,
        "z": -20,
        "Items": [
            {"id": 1, "Count": 64, "Damage": 0, "Slot": 0},  # Stone
            {"id": 3, "Count": 32, "Damage": 0, "Slot": 5},  # Dirt
            {"id": 264, "Count": 5, "Damage": 0, "Slot": 26},  # Diamond item -> base:ruby
            {"id": 999, "Count": 1, "Damage": 0, "Slot": 27},  # Unknown item -> fallback debug item
        ],
    }

    be_bytes = build_chunk_block_entities_binary([chest_te], mapper, y_offset=-64)
    assert be_bytes is not None
    assert be_bytes.startswith(b"CRB\x02")
    assert b"base:container" in be_bytes
    assert b"base:stone_basalt[default]" in be_bytes
    assert b"base:dirt[default]" in be_bytes
    assert b"base:ruby" in be_bytes
    assert b"minecraft:999[default]" in be_bytes


def test_build_empty_tile_entities():
    mapper = B173BlockMapper()
    be_bytes = build_chunk_block_entities_binary([], mapper)
    assert be_bytes is None
