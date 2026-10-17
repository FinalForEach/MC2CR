"""Backwards-compatibility forwarder for mc2cr.minecraft.blocks."""

from mc2cr.minecraft.blocks import (
    DEFAULT_MAPPING_PATH,
    B173BlockMapper,
    BlockMapper,
    LegacyBlockMapper,
    get_b173_block_save_key,
    get_block_save_key,
)

__all__ = [
    "DEFAULT_MAPPING_PATH",
    "LegacyBlockMapper",
    "B173BlockMapper",
    "BlockMapper",
    "get_block_save_key",
    "get_b173_block_save_key",
]
