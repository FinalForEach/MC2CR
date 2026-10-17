"""Tests for LegacyBlockMapper default loading and user overrides."""

from mc2cr.minecraft.blocks import LegacyBlockMapper


def test_default_mappings():
    mapper = LegacyBlockMapper()

    # Air
    assert mapper.get_block_save_key(0) == "base:air[default]"
    # Stone
    assert mapper.get_block_save_key(1) == "base:stone_basalt[default]"
    # Grass
    assert mapper.get_block_save_key(2) == "base:grass[default]"
    # Dirt
    assert mapper.get_block_save_key(3) == "base:dirt[default]"
    # Wool colors (35)
    assert mapper.get_block_save_key(35, 0) == "base:plastic_block[color=white]"
    assert mapper.get_block_save_key(35, 1) == "base:plastic_block[color=orange]"
    assert mapper.get_block_save_key(35, 14) == "base:plastic_block[color=red]"
    assert mapper.get_block_save_key(35, 15) == "base:plastic_block[color=black]"
    # Torch directionality (50)
    assert mapper.get_block_save_key(50, 0) == "base:torch[level=4,type=ground]"
    assert mapper.get_block_save_key(50, 1) == "base:torch[level=4,type=wall_NegX]"
    assert mapper.get_block_save_key(50, 2) == "base:torch[level=4,type=wall_PosX]"
    assert mapper.get_block_save_key(50, 3) == "base:torch[level=4,type=wall_NegZ]"
    assert mapper.get_block_save_key(50, 4) == "base:torch[level=4,type=wall_PosZ]"
    assert mapper.get_block_save_key(50, 5) == "base:torch[level=4,type=ground]"
    # Doors (64, 71)
    assert mapper.get_block_save_key(64, 0) == "base:wood_door[direction=NegX,part=bottom,power=off]"
    assert mapper.get_block_save_key(64, 8) == "base:wood_door[direction=NegX,part=top,power=off]"
    assert mapper.get_block_save_key(64, 5) == "base:wood_door[direction=NegZ,part=bottom,power=on]"
    assert mapper.get_block_save_key(71, 2) == "base:door_iron[direction=PosX,part=bottom,power=off]"
    assert mapper.get_block_save_key(71, 10) == "base:door_iron[direction=PosX,part=top,power=off]"
    # Release 1.0 block (Stone Bricks)
    assert mapper.get_block_save_key(98) == "base:stone_bricks[default]"
    # Unmapped/fallback ID
    assert mapper.get_block_save_key(999) == "minecraft:999[default]"


def test_user_mapping_overrides(tmp_path):
    custom_config = tmp_path / "custom_mapping.json"
    custom_config.write_text(
        '{"1": "mymod:custom_stone[default]", "35": {"target": "mymod:wool[default]", "data": {"14": "mymod:wool[color=super_red]"}}, "999": "mymod:custom_block[default]"}'
    )

    mapper = LegacyBlockMapper(override_path_or_dict=custom_config)

    # Overridden
    assert mapper.get_block_save_key(1) == "mymod:custom_stone[default]"
    assert mapper.get_block_save_key(35, 0) == "mymod:wool[default]"
    assert mapper.get_block_save_key(35, 14) == "mymod:wool[color=super_red]"
    assert mapper.get_block_save_key(999) == "mymod:custom_block[default]"
    # Preserved defaults
    assert mapper.get_block_save_key(0) == "base:air[default]"
    assert mapper.get_block_save_key(2) == "base:grass[default]"
    assert mapper.get_block_save_key(50, 1) == "base:torch[level=4,type=wall_NegX]"
    # Unmapped fallback
    assert mapper.get_block_save_key(500) == "minecraft:500[default]"
