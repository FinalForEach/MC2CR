"""Cosmic Reach skylight data representation and serialization."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from mc2cr.cosmicreach.constants import (
    CHUNK_WIDTH,
    NUM_BLOCKS_IN_CHUNK,
    SKYLIGHTDATA_LAYER_NIBBLE,
    SKYLIGHTDATA_LAYER_SINGLE,
    SKYLIGHTDATA_LAYERED,
    SKYLIGHTDATA_SINGLE,
)


class ChunkSkyLightData:
    """Encapsulates a 16x16x16 sky light level grid (0-15) for a Cosmic Reach chunk."""

    def __init__(self, light_levels: Sequence[int]):
        """Initialize with 4096 light levels (0-15).

        Index formula: (local_y * 16 + local_x) * 16 + local_z.
        """
        if len(light_levels) != NUM_BLOCKS_IN_CHUNK:
            raise ValueError(f"Expected {NUM_BLOCKS_IN_CHUNK} light levels, got {len(light_levels)}")
        self.light_levels = list(light_levels)

    def get_light(self, x: int, y: int, z: int) -> int:
        return self.light_levels[(y * CHUNK_WIDTH + x) * CHUNK_WIDTH + z]

    def serialize(self) -> bytes:
        """Serialize into Cosmic Reach binary skylight data."""
        buf = bytearray()
        first_val = self.light_levels[0]

        # 1. Single uniform skylight value across all 4096 blocks
        if len(set(self.light_levels)) == 1:
            buf.append(SKYLIGHTDATA_SINGLE)
            buf.append(first_val & 0x0F)
            return bytes(buf)

        # 2. Layered skylight data
        buf.append(SKYLIGHTDATA_LAYERED)
        for y in range(CHUNK_WIDTH):
            layer_vals = self.light_levels[y * 256 : (y + 1) * 256]
            first_layer_val = layer_vals[0]

            if len(set(layer_vals)) == 1:
                buf.append(SKYLIGHTDATA_LAYER_SINGLE)
                buf.append(first_layer_val & 0x0F)
            else:
                buf.append(SKYLIGHTDATA_LAYER_NIBBLE)
                vals_2d = np.array(layer_vals, dtype=np.uint8).reshape((CHUNK_WIDTH, CHUNK_WIDTH))
                even_x = vals_2d[0::2, :] & 0x0F
                odd_x = (vals_2d[1::2, :] & 0x0F) << 4
                buf.extend(np.ascontiguousarray((even_x | odd_x).T).tobytes())

        return bytes(buf)
