"""Unit tests for Modern Minecraft (1.13+ / Flattening) block mapping and chunk decoding."""

from mc2cr.minecraft.modern_blocks import ModernBlockMapper
from mc2cr.minecraft.modern_chunk import unpack_modern_palette_indices


def test_modern_block_mapper():
    mapper = ModernBlockMapper()

    # Legacy inherited blocks
    assert mapper.get_block_save_key("minecraft:stone") == "base:stone_basalt[default]"
    assert mapper.get_block_save_key("minecraft:grass_block") == "base:grass[default]"
    assert mapper.get_block_save_key("minecraft:dirt") == "base:dirt[default]"
    assert mapper.get_block_save_key("minecraft:granite") == "base:stone_basalt[default]"
    assert mapper.get_block_save_key("minecraft:red_wool") == "base:plastic_block[color=red]"
    assert mapper.get_block_save_key({"Name": "minecraft:ladder", "Properties": {"facing": "west"}}) == "base:ladder_wooden[direction=PosX]"

    # Modern 1.13+ additions
    assert mapper.get_block_save_key("minecraft:deepslate") == "base:stone_shale[default]"
    assert mapper.get_block_save_key("minecraft:copper_ore") == "base:ore_bauxite[default]"
    assert mapper.get_block_save_key("minecraft:tuff") == "base:stone_shale[default]"
    assert mapper.get_block_save_key("minecraft:barrel") == "base:crate[default]"
    assert mapper.get_block_save_key("minecraft:lantern") == "base:torch[level=4,type=ground]"

    # Fallback to verbatim
    assert mapper.get_block_save_key("minecraft:unknown_custom_block") == "minecraft:unknown_custom_block[default]"


def test_unpack_modern_palette_single():
    palette = [{"Name": "minecraft:air"}]
    indices = unpack_modern_palette_indices(palette, None, data_version=4903)
    assert len(indices) == 4096
    assert all(i == 0 for i in indices)


def test_unpack_modern_palette_multi():
    palette = [{"Name": "minecraft:stone"}, {"Name": "minecraft:dirt"}]
    # 2 entries -> min 4 bits per block (16 blocks per long). 4096 / 16 = 256 longs.
    # Alternating 4-bit nibbles: 0x1010101010101010 -> index 0 is 0, index 1 is 1
    val = 0x1010101010101010
    data_arr = [val] * 256
    indices = unpack_modern_palette_indices(palette, data_arr, data_version=4903)
    assert len(indices) == 4096
    assert indices[0] == 0
    assert indices[1] == 1
